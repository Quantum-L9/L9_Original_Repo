"""
CodeGenAgent AP Generator
=========================

Generates GMP-ready prompts based on meta.yaml or schema contracts.
Injects AI-CTO styles, capsule continuity, cursor-marked anchor prompts.

Consumers:
- cursor-agent
- CodeGenAgent
- ReflectionAgent

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Ap Generator",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-15T23:24:51Z",
    "updated_at": "2026-01-15T23:24:51Z",
    "layer": "intelligence",
    "domain": "data_models",
    "module_name": "ap_generator",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from pathlib import Path
from string import Template
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================


class PromptStyle(str, Enum):
    """Available prompt generation styles."""

    AI_CTO = "ai_cto"
    CAPSULE_CONTINUITY = "capsule_continuity"
    GODMODE_FEEDBACK = "godmode_feedback"


# Style-specific templates
STYLE_TEMPLATES: dict[PromptStyle, str] = {
    PromptStyle.AI_CTO: """
## AI-CTO Mode: ${module_name}

You are acting as the AI Chief Technology Officer for L9. Your task is to implement
${module_name} following these specifications precisely.

### Strategic Context
${description}

### Technical Requirements
${requirements}

### Quality Gates
- All code must pass lint and type checks
- Test coverage >= 85%
- No TODOs in production code
- Full docstrings on public APIs

### Deliverables
${deliverables}
""",
    PromptStyle.CAPSULE_CONTINUITY: """
## Capsule Continuity: ${module_name}

### Previous Context
This module continues from prior work on the CodeGenAgent pipeline.

### Current Capsule
Module: ${module_name}
Description: ${description}

### Inputs from Previous Capsule
${inputs}

### Outputs to Next Capsule
${outputs}

### Implementation Notes
${requirements}

### Continuity Markers
- Previous: MetaLoader, C-GMP Engine
- Current: ${module_name}
- Next: File Emitter, Telemetry
""",
    PromptStyle.GODMODE_FEEDBACK: """
## GodMode Feedback: ${module_name}

### DIRECTIVE
Generate complete, production-ready implementation for ${module_name}.

### CONSTRAINTS
- No placeholders
- No TODOs
- No "implement later" comments
- Full implementation required

### SPECIFICATION
${description}

### REQUIRED METHODS
${requirements}

### VALIDATION
${validation}

### OUTPUT FORMAT
Complete Python module with all imports, classes, and methods implemented.
""",
}


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class GMPPromptBlock:
    """
    Structured GMP prompt block.

    Contains all sections needed for a complete GMP prompt.
    """

    module_name: str
    style: PromptStyle

    # Core sections
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    responsibilities: list[str] = field(default_factory=list)

    # Content
    description: str = ""
    requirements: str = ""
    deliverables: str = ""
    validation: str = ""

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    version: str = "1.0.0"

    # Rendered prompt
    rendered_prompt: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "module_name": self.module_name,
            "style": self.style.value,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "responsibilities": self.responsibilities,
            "description": self.description,
            "requirements": self.requirements,
            "deliverables": self.deliverables,
            "validation": self.validation,
            "created_at": self.created_at.isoformat(),
            "version": self.version,
            "rendered_prompt": self.rendered_prompt,
        }


@dataclass
class GenerationResult:
    """Result of prompt generation."""

    success: bool
    prompt_block: GMPPromptBlock | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# =============================================================================
# EXCEPTIONS
# =============================================================================


class APGeneratorError(Exception):
    """Exception raised when prompt generation fails."""

    pass


class InvalidMetaError(APGeneratorError):
    """Exception raised when meta specification is invalid."""

    pass


class StyleNotFoundError(APGeneratorError):
    """Exception raised when requested style is not found."""

    pass


# =============================================================================
# AP GENERATOR
# =============================================================================


class APGenerator:
    """
    GMP Prompt Generator.

    Generates GMP-ready prompts based on meta.yaml or schema contracts.
    Supports multiple prompt styles for different use cases.
    """

    def __init__(
        self,
        default_style: PromptStyle = PromptStyle.AI_CTO,
        custom_templates: dict[PromptStyle, str] | None = None,
    ):
        """
        Initialize the AP Generator.

        Args:
            default_style: Default prompt style to use
            custom_templates: Optional custom templates to override defaults
        """
        self.default_style = default_style
        self._templates = {**STYLE_TEMPLATES}

        if custom_templates:
            self._templates.update(custom_templates)

        logger.info(
            "ap_generator_initialized",
            default_style=default_style.value,
            available_styles=list(self._templates.keys()),
        )

    def generate_prompt(
        self,
        meta: dict[str, Any],
        style: PromptStyle | None = None,
    ) -> GenerationResult:
        """
        Generate a GMP prompt from a meta specification.

        Args:
            meta: Meta specification dictionary
            style: Optional style override

        Returns:
            GenerationResult with rendered prompt block
        """
        use_style = style or self.default_style

        try:
            # Validate meta
            self._validate_meta(meta)

            # Build prompt block
            prompt_block = self.build_gmp_block(meta)
            prompt_block.style = use_style

            # Inject style and render
            prompt_block.rendered_prompt = self.inject_style(prompt_block, use_style)

            logger.info(
                "prompt_generated",
                module_name=prompt_block.module_name,
                style=use_style.value,
                prompt_length=len(prompt_block.rendered_prompt),
            )

            return GenerationResult(
                success=True,
                prompt_block=prompt_block,
            )

        except APGeneratorError as e:
            logger.error("prompt_generation_failed", error=str(e))
            return GenerationResult(
                success=False,
                errors=[str(e)],
            )
        except Exception as e:
            logger.error("prompt_generation_error", error=str(e))
            return GenerationResult(
                success=False,
                errors=[f"Unexpected error: {e}"],
            )

    def inject_style(
        self,
        prompt_block: GMPPromptBlock,
        style: PromptStyle,
    ) -> str:
        """
        Inject a style into a prompt block.

        Args:
            prompt_block: The prompt block to style
            style: The style to apply

        Returns:
            Rendered prompt string
        """
        if style not in self._templates:
            raise StyleNotFoundError(f"Style not found: {style}")

        template_str = self._templates[style]
        template = Template(template_str)

        # Build substitution dict
        substitutions = {
            "module_name": prompt_block.module_name,
            "description": prompt_block.description,
            "requirements": prompt_block.requirements,
            "deliverables": prompt_block.deliverables,
            "validation": prompt_block.validation,
            "inputs": self._format_list(prompt_block.inputs),
            "outputs": self._format_list(prompt_block.outputs),
        }

        try:
            rendered = template.safe_substitute(substitutions)
            return rendered.strip()
        except Exception as e:
            raise APGeneratorError(f"Template rendering failed: {e}") from e

    def build_gmp_block(self, meta: dict[str, Any]) -> GMPPromptBlock:
        """
        Build a GMP prompt block from meta specification.

        Args:
            meta: Meta specification dictionary

        Returns:
            GMPPromptBlock with extracted information
        """
        # Extract module name
        module_name = meta.get("name") or meta.get("filename", "unknown")
        if "/" in module_name:
            module_name = Path(module_name).stem

        # Extract inputs/outputs
        inputs = meta.get("inputs", [])
        if isinstance(inputs, str):
            inputs = [inputs]

        outputs = meta.get("outputs", [])
        if isinstance(outputs, str):
            outputs = [outputs]

        # Extract wiring info
        wiring = meta.get("wiring", {})
        if wiring:
            if "source" in wiring:
                inputs.append(f"Source: {wiring['source']}")
            if "output" in wiring:
                outputs.append(f"Output: {wiring['output']}")

        # Extract responsibilities
        responsibilities = meta.get("responsibilities", [])
        if isinstance(responsibilities, str):
            responsibilities = [responsibilities]

        # Build description
        description = meta.get("description", "")
        if isinstance(description, str):
            description = description.strip()

        # Build requirements from code hints
        requirements = self._extract_requirements(meta)

        # Build deliverables
        deliverables = self._extract_deliverables(meta)

        # Build validation
        validation = self._extract_validation(meta)

        return GMPPromptBlock(
            module_name=module_name,
            style=self.default_style,
            inputs=inputs,
            outputs=outputs,
            responsibilities=responsibilities,
            description=description,
            requirements=requirements,
            deliverables=deliverables,
            validation=validation,
        )

    def _validate_meta(self, meta: dict[str, Any]) -> None:
        """Validate meta specification has required fields."""
        if not meta:
            raise InvalidMetaError("Meta specification is empty")

        # At minimum, need name or filename
        if not meta.get("name") and not meta.get("filename"):
            raise InvalidMetaError("Meta must have 'name' or 'filename'")

    def _extract_requirements(self, meta: dict[str, Any]) -> str:
        """Extract requirements from meta."""
        lines = []

        # From wiring
        wiring = meta.get("wiring", {})
        if wiring:
            if "styles" in wiring:
                lines.append(f"- Styles: {', '.join(wiring['styles'])}")
            if "checks" in wiring:
                lines.append(f"- Checks: {', '.join(wiring['checks'])}")
            if "required_fields" in wiring:
                lines.append(
                    f"- Required fields: {', '.join(wiring['required_fields'])}"
                )

        # From responsibilities
        for resp in meta.get("responsibilities", []):
            lines.append(f"- {resp}")

        return "\n".join(lines) if lines else "See specification above."

    def _extract_deliverables(self, meta: dict[str, Any]) -> str:
        """Extract deliverables from meta."""
        lines = []

        filename = meta.get("filename", "module.py")
        lines.append(f"- Primary file: {filename}")

        outputs = meta.get("outputs", [])
        for output in outputs:
            lines.append(f"- {output}")

        return "\n".join(lines) if lines else "Complete module implementation."

    def _extract_validation(self, meta: dict[str, Any]) -> str:
        """Extract validation criteria from meta."""
        lines = [
            "- All public methods have type hints",
            "- All classes have docstrings",
            "- No TODO comments in code",
            "- Passes mypy --strict",
        ]

        # Add any custom validation from meta
        if "required_tests" in meta:
            lines.append(f"- Tests: {meta['required_tests']}")

        return "\n".join(lines)

    def _format_list(self, items: list[str]) -> str:
        """Format a list as bullet points."""
        if not items:
            return "None specified"
        return "\n".join(f"- {item}" for item in items)

    def get_available_styles(self) -> list[str]:
        """Get list of available prompt styles."""
        return [s.value for s in self._templates]

    def add_custom_template(
        self,
        style: PromptStyle,
        template: str,
    ) -> None:
        """
        Add or override a custom template.

        Args:
            style: Style identifier
            template: Template string with ${variable} placeholders
        """
        self._templates[style] = template
        logger.info("custom_template_added", style=style.value)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def generate_gmp_prompt(
    meta: dict[str, Any],
    style: str = "ai_cto",
) -> str:
    """
    Generate a GMP prompt from meta specification.

    Args:
        meta: Meta specification dictionary
        style: Style name (ai_cto, capsule_continuity, godmode_feedback)

    Returns:
        Rendered prompt string
    """
    generator = APGenerator()
    style_enum = PromptStyle(style)
    result = generator.generate_prompt(meta, style=style_enum)

    if result.success and result.prompt_block:
        return result.prompt_block.rendered_prompt

    raise APGeneratorError(f"Generation failed: {result.errors}")


def build_prompt_block(meta: dict[str, Any]) -> GMPPromptBlock:
    """
    Build a GMP prompt block from meta specification.

    Args:
        meta: Meta specification dictionary

    Returns:
        GMPPromptBlock instance
    """
    generator = APGenerator()
    return generator.build_gmp_block(meta)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "AGE-INTE-017",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "data-models",
        "dataclass",
        "filesystem",
        "intelligence",
        "linting",
        "logging",
        "testing",
    ],
    "keywords": [
        "agent",
        "available",
        "block",
        "build",
        "codegenagent",
        "cursor",
        "custom",
        "found",
    ],
    "business_value": "Provides ap generator components including PromptStyle, GMPPromptBlock, GenerationResult",
    "last_modified": "2026-01-15T23:24:51Z",
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
