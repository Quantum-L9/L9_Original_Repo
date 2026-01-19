"""
SuperPrompt Emitter for Perplexity Enrichment
==============================================

Generates enrichment prompts from incomplete or gap-detected YAML specs,
sends them to Perplexity API, and patches the original spec with results.

Key Features:
- Gap detection in Module-Spec-v2.4 schemas
- Structured prompt generation for LLM enrichment
- Perplexity API integration
- Automatic spec patching

Part of the CodeGenAgent pipeline (Phase 6).

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Superprompt Emitter",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "operations",
    "domain": "runtime_operations",
    "module_name": "superprompt_emitter",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API", "Perplexity API"],
        "memory_layers": [],
        "imported_by": ["runtime.construct_enhancer"],
    },
}
# ============================================================================

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import structlog
import yaml


logger = structlog.get_logger(__name__)


# =============================================================================
# GAP DETECTION
# =============================================================================


@dataclass
class SpecGap:
    """A detected gap in a specification."""

    section: str
    field: str
    severity: str  # critical, important, optional
    description: str
    suggestion: Optional[str] = None


@dataclass
class GapAnalysis:
    """Result of gap analysis on a spec."""

    spec_path: str
    module_id: str
    total_gaps: int
    critical_gaps: int
    important_gaps: int
    optional_gaps: int
    gaps: List[SpecGap] = field(default_factory=list)

    @property
    def has_critical_gaps(self) -> bool:
        return self.critical_gaps > 0

    @property
    def can_proceed(self) -> bool:
        """Can proceed with code generation despite gaps."""
        return self.critical_gaps == 0


class GapDetector:
    """
    Detects gaps in Module-Spec-v2.4 specifications.

    Identifies:
    - Missing required sections
    - Placeholder values ({{...}})
    - Empty lists that should have content
    - TBD/TODO markers
    """

    # Sections that must have content
    REQUIRED_CONTENT_SECTIONS = {
        "metadata.description": "Module must have a description",
        "ownership.team": "Team must be specified",
        "ownership.primary_contact": "Primary contact must be specified",
        "runtime_wiring.service": "Service type must be specified",
        "packet_contract.emits": "At least one packet type must be declared",
        "acceptance.positive": "At least one positive acceptance test required",
        "acceptance.negative": "At least one negative acceptance test required",
    }

    # Placeholder patterns to detect
    PLACEHOLDER_PATTERNS = [
        "{{",  # Template placeholders
        "TBD",
        "TODO",
        "FIXME",
        "XXX",
        "<placeholder>",
        "your_value",
        "example",
    ]

    def analyze(self, spec: Dict[str, Any]) -> GapAnalysis:
        """
        Analyze a spec for gaps.

        Args:
            spec: Parsed YAML specification

        Returns:
            GapAnalysis with detected gaps
        """
        gaps: List[SpecGap] = []
        module_id = spec.get("metadata", {}).get("module_id", "unknown")

        # Check required content sections
        self._check_required_content(spec, gaps)

        # Check for placeholders
        self._check_placeholders(spec, gaps)

        # Check for empty required lists
        self._check_empty_lists(spec, gaps)

        # Calculate severity counts
        critical = sum(1 for g in gaps if g.severity == "critical")
        important = sum(1 for g in gaps if g.severity == "important")
        optional = sum(1 for g in gaps if g.severity == "optional")

        logger.info(
            "gap_analysis_complete",
            module_id=module_id,
            total_gaps=len(gaps),
            critical=critical,
            important=important,
        )

        return GapAnalysis(
            spec_path="",
            module_id=module_id,
            total_gaps=len(gaps),
            critical_gaps=critical,
            important_gaps=important,
            optional_gaps=optional,
            gaps=gaps,
        )

    def _check_required_content(
        self, spec: Dict[str, Any], gaps: List[SpecGap]
    ) -> None:
        """Check required content sections."""
        for path, description in self.REQUIRED_CONTENT_SECTIONS.items():
            parts = path.split(".")
            value = spec
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    value = None
                    break

            if value is None:
                gaps.append(
                    SpecGap(
                        section=parts[0],
                        field=".".join(parts[1:]) if len(parts) > 1 else parts[0],
                        severity="critical",
                        description=description,
                    )
                )
            elif isinstance(value, str) and not value.strip():
                gaps.append(
                    SpecGap(
                        section=parts[0],
                        field=".".join(parts[1:]) if len(parts) > 1 else parts[0],
                        severity="critical",
                        description=f"{path} is empty",
                    )
                )

    def _check_placeholders(
        self, spec: Dict[str, Any], gaps: List[SpecGap], path: str = ""
    ) -> None:
        """Recursively check for placeholder patterns."""
        if isinstance(spec, dict):
            for key, value in spec.items():
                current_path = f"{path}.{key}" if path else key
                self._check_placeholders(value, gaps, current_path)
        elif isinstance(spec, list):
            for i, item in enumerate(spec):
                current_path = f"{path}[{i}]"
                self._check_placeholders(item, gaps, current_path)
        elif isinstance(spec, str):
            for pattern in self.PLACEHOLDER_PATTERNS:
                if pattern.lower() in spec.lower():
                    parts = path.split(".")
                    gaps.append(
                        SpecGap(
                            section=parts[0] if parts else "unknown",
                            field=".".join(parts[1:]) if len(parts) > 1 else path,
                            severity="important",
                            description=f"Placeholder detected: {spec[:50]}...",
                            suggestion=f"Replace placeholder value in {path}",
                        )
                    )
                    break  # Only report once per field

    def _check_empty_lists(self, spec: Dict[str, Any], gaps: List[SpecGap]) -> None:
        """Check for empty lists that should have content."""
        required_lists = [
            ("dependencies.outbound_calls", "optional"),
            ("interfaces.inbound", "optional"),
            ("interfaces.outbound", "optional"),
            ("environment.required", "optional"),
            ("observability.metrics.counters", "optional"),
        ]

        for path, severity in required_lists:
            parts = path.split(".")
            value = spec
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    value = None
                    break

            if isinstance(value, list) and len(value) == 0:
                gaps.append(
                    SpecGap(
                        section=parts[0],
                        field=".".join(parts[1:]) if len(parts) > 1 else parts[0],
                        severity=severity,
                        description=f"{path} is empty",
                        suggestion=f"Consider adding items to {path}",
                    )
                )


# =============================================================================
# SUPERPROMPT GENERATION
# =============================================================================


@dataclass
class SuperPrompt:
    """A structured prompt for LLM enrichment."""

    module_id: str
    purpose: str
    context: Dict[str, Any]
    gaps_to_fill: List[SpecGap]
    prompt_text: str
    expected_format: str = "yaml"


class SuperPromptEmitter:
    """
    Generates enrichment prompts from gap analysis.

    Creates structured prompts suitable for Perplexity or other LLMs
    to fill in missing specification details.
    """

    # System prompt template for Perplexity
    SYSTEM_PROMPT = """You are an L9 AI OS specification expert. Your task is to fill in missing 
details in Module-Spec-v2.4 YAML specifications.

Rules:
1. Follow the Module-Spec-v2.4 schema exactly
2. Use concrete, production-ready values (no placeholders)
3. Be specific and detailed in descriptions
4. Generate realistic acceptance test names
5. Output valid YAML only

Module-Spec-v2.4 requires:
- metadata: module_id, name, tier, description
- ownership: team (core|infra|integrations|security|observability), primary_contact
- runtime_wiring: service (api|worker|scheduler|memory), startup_phase, depends_on, blocks_startup_on_failure
- packet_contract: emits (list of packet types), requires_metadata
- acceptance: positive and negative test cases
"""

    def __init__(self, include_examples: bool = True):
        """
        Initialize the emitter.

        Args:
            include_examples: Include example values in prompts
        """
        self.include_examples = include_examples
        self._gap_detector = GapDetector()
        logger.info("superprompt_emitter_initialized")

    def emit_from_spec(
        self,
        spec: Dict[str, Any],
        gap_analysis: Optional[GapAnalysis] = None,
    ) -> SuperPrompt:
        """
        Generate a SuperPrompt from a specification.

        Args:
            spec: Parsed YAML specification
            gap_analysis: Optional pre-computed gap analysis

        Returns:
            SuperPrompt ready for LLM submission
        """
        if gap_analysis is None:
            gap_analysis = self._gap_detector.analyze(spec)

        module_id = spec.get("metadata", {}).get("module_id", "unknown")

        # Build prompt text
        prompt_text = self._build_prompt(spec, gap_analysis)

        return SuperPrompt(
            module_id=module_id,
            purpose="Fill gaps in Module-Spec-v2.4 specification",
            context={
                "current_spec": spec,
                "gap_count": gap_analysis.total_gaps,
            },
            gaps_to_fill=gap_analysis.gaps,
            prompt_text=prompt_text,
        )

    def emit_from_yaml(self, yaml_path: str) -> SuperPrompt:
        """
        Generate a SuperPrompt from a YAML file.

        Args:
            yaml_path: Path to YAML file

        Returns:
            SuperPrompt ready for LLM submission
        """
        with open(yaml_path, "r", encoding="utf-8") as f:
            spec = yaml.safe_load(f)

        return self.emit_from_spec(spec)

    def get_system_prompt(self) -> str:
        """Get the system prompt for LLM configuration."""
        return self.SYSTEM_PROMPT

    def _build_prompt(
        self,
        spec: Dict[str, Any],
        gap_analysis: GapAnalysis,
    ) -> str:
        """Build the enrichment prompt."""
        module_id = spec.get("metadata", {}).get("module_id", "unknown")
        module_name = spec.get("metadata", {}).get("name", "Unknown Module")
        description = spec.get("metadata", {}).get("description", "")

        # Format gaps
        gap_text = []
        for gap in gap_analysis.gaps:
            gap_text.append(
                f"- [{gap.severity.upper()}] {gap.section}.{gap.field}: {gap.description}"
            )

        prompt = f"""# Module Specification Enrichment Request

## Target Module
- Module ID: {module_id}
- Name: {module_name}
- Description: {description}

## Gaps to Fill ({gap_analysis.total_gaps} total)

{chr(10).join(gap_text)}

## Current Specification

```yaml
{yaml.dump(spec, default_flow_style=False, sort_keys=False)}
```

## Instructions

Please provide YAML patches for each gap listed above. For each gap:
1. Provide the exact YAML path and value
2. Use realistic, production-ready values
3. Follow L9 naming conventions

Format your response as:
```yaml
patches:
  - path: "section.field"
    value: "concrete_value"
```
"""

        return prompt


# =============================================================================
# PERPLEXITY INTEGRATION
# =============================================================================


class PerplexityEnricher:
    """
    Sends SuperPrompts to Perplexity API and retrieves enrichments.

    Requires PERPLEXITY_API_KEY environment variable.
    """

    API_URL = "https://api.perplexity.ai/chat/completions"
    DEFAULT_MODEL = "llama-3.1-sonar-large-128k-online"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize the enricher.

        Args:
            api_key: Perplexity API key (or use env var)
            model: Model to use (default: llama-3.1-sonar-large)
        """
        self.api_key = api_key or os.environ.get("PERPLEXITY_API_KEY")
        self.model = model or self.DEFAULT_MODEL

        if not self.api_key:
            logger.warning("perplexity_api_key_not_set")
        else:
            logger.info(
                "perplexity_enricher_initialized",
                model=self.model,
            )

    async def enrich(
        self,
        superprompt: SuperPrompt,
    ) -> Dict[str, Any]:
        """
        Send SuperPrompt to Perplexity and get enrichment.

        Args:
            superprompt: SuperPrompt to send

        Returns:
            Enrichment result with patches
        """
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEY not set")

        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": SuperPromptEmitter.SYSTEM_PROMPT,
                        },
                        {
                            "role": "user",
                            "content": superprompt.prompt_text,
                        },
                    ],
                },
                timeout=60.0,
            )

            response.raise_for_status()
            data = response.json()

        # Extract content from response
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        logger.info(
            "perplexity_enrichment_received",
            module_id=superprompt.module_id,
            content_length=len(content),
        )

        return {
            "module_id": superprompt.module_id,
            "raw_response": content,
            "patches": self._parse_patches(content),
        }

    def _parse_patches(self, content: str) -> List[Dict[str, Any]]:
        """Parse patches from LLM response."""
        patches = []

        # Look for YAML code blocks
        import re

        yaml_blocks = re.findall(r"```yaml\n(.*?)\n```", content, re.DOTALL)

        for block in yaml_blocks:
            try:
                parsed = yaml.safe_load(block)
                if isinstance(parsed, dict) and "patches" in parsed:
                    patches.extend(parsed["patches"])
                elif isinstance(parsed, dict):
                    # Single patch
                    patches.append(parsed)
            except yaml.YAMLError:
                logger.debug("failed_to_parse_yaml_block")

        return patches


# =============================================================================
# SPEC PATCHER
# =============================================================================


class SpecPatcher:
    """
    Applies enrichment patches to YAML specifications.
    """

    def apply_patches(
        self,
        spec: Dict[str, Any],
        patches: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Apply patches to a specification.

        Args:
            spec: Original specification
            patches: List of patches with path and value

        Returns:
            Patched specification
        """
        import copy

        patched = copy.deepcopy(spec)

        for patch in patches:
            path = patch.get("path", "")
            value = patch.get("value")

            if path and value is not None:
                self._set_nested(patched, path, value)

        return patched

    def _set_nested(
        self,
        data: Dict[str, Any],
        path: str,
        value: Any,
    ) -> None:
        """Set a nested value by path."""
        parts = path.split(".")
        current = data

        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {}
            current = current[part]

        if parts:
            current[parts[-1]] = value


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def detect_gaps(spec: Dict[str, Any]) -> GapAnalysis:
    """Detect gaps in a specification."""
    detector = GapDetector()
    return detector.analyze(spec)


def emit_superprompt(spec: Dict[str, Any]) -> SuperPrompt:
    """Generate SuperPrompt from specification."""
    emitter = SuperPromptEmitter()
    return emitter.emit_from_spec(spec)


async def enrich_spec(spec_path: str) -> Dict[str, Any]:
    """
    Enrich a specification via Perplexity.

    Args:
        spec_path: Path to YAML file

    Returns:
        Enriched specification
    """
    with open(spec_path, "r") as f:
        spec = yaml.safe_load(f)

    emitter = SuperPromptEmitter()
    superprompt = emitter.emit_from_spec(spec)

    enricher = PerplexityEnricher()
    result = await enricher.enrich(superprompt)

    patcher = SpecPatcher()
    return patcher.apply_patches(spec, result.get("patches", []))


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "RUN-OPER-015",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "auth",
        "config",
        "dataclass",
        "debugging",
        "http-client",
        "logging",
        "messaging",
        "metrics",
        "operations",
    ],
    "keywords": [
        "analysis",
        "analyze",
        "apply",
        "can",
        "critical",
        "detect",
        "detection",
        "detector",
    ],
    "business_value": "Provides superprompt emitter components including SpecGap, GapAnalysis, GapDetector",
    "last_modified": "2026-01-14T15:03:00Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
