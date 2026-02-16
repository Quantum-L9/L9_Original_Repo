#!/usr/bin/env python3
"""
L9 Module Spec Generator
========================

Generates Module-Spec-v2.4 YAML from research synthesis or module description.

Usage:
    python generate_spec.py --topic "slack_webhook_adapter" --description "..."
    python generate_spec.py --from-synthesis synthesis_result.json
    python generate_spec.py --interactive

Output:
    codegen/specs/{module_id}.yaml
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Generate Spec",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-16T00:17:40Z",
    "layer": "foundation",
    "domain": "code_generation",
    "module_name": "generate_spec",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API", "Perplexity API"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import structlog

logger = structlog.get_logger(__name__)

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
import yaml
from tenacity import retry, stop_after_attempt, wait_exponential

# ============================================================================
# Configuration
# ============================================================================

CODEGEN_ROOT = Path(__file__).parent.parent  # noqa: ADR-0001 - internal path
SPECS_DIR = CODEGEN_ROOT / "specs"
PROMPTS_DIR = CODEGEN_ROOT / "templates" / "prompts"
SPEC_GENERATOR_PROMPT_PATH = PROMPTS_DIR / "Module-Spec-Generator-v1.0.md"

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
PERPLEXITY_MODEL = "sonar-pro"  # Use sonar-pro for spec generation


# ============================================================================
# Prompt Loading
# ============================================================================


def load_spec_generator_prompt() -> str:
    """Load the spec generator prompt template."""
    if not SPEC_GENERATOR_PROMPT_PATH.exists():
        raise FileNotFoundError(
            f"Spec generator prompt not found at {SPEC_GENERATOR_PROMPT_PATH}"
        )

    content = SPEC_GENERATOR_PROMPT_PATH.read_text()

    # Extract the prompt section (between the first ``` and the closing ```)
    # For now, return the full content - the model will understand it
    return content


def build_prompt(module_description: str, synthesis: dict | None = None) -> str:
    """Build the full prompt for spec generation."""
    base_prompt = load_spec_generator_prompt()

    if synthesis:
        description = f"""
Based on this research synthesis:

CONSENSUS FINDINGS:
{json.dumps(synthesis.get("consensus_patterns", {}), indent=2)}

UNIQUE INSIGHTS:
{json.dumps(synthesis.get("unique_insights", []), indent=2)}

ARCHITECTURE RECOMMENDATIONS:
{json.dumps(synthesis.get("recommended_architecture", {}), indent=2)}

IMPLEMENTATION ROADMAP:
{json.dumps(synthesis.get("implementation_roadmap", []), indent=2)}

Generate Module-Spec-v2.4 YAML for: {module_description}
"""
    else:
        description = module_description

    # Replace placeholder
    return base_prompt.replace("{{MODULE_DESCRIPTION}}", description)


# ============================================================================
# Perplexity Client
# ============================================================================


class PerplexityClient:
    """Client for Perplexity API with retry logic."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError(
                "PERPLEXITY_API_KEY not set. "
                "Set via environment variable or --api-key argument."
            )

    @retry(  # noqa: ADR-0024 - direct retry is intentional
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def generate_spec(
        self,
        prompt: str,
        model: str = PERPLEXITY_MODEL,
        temperature: float = 0.2,
        max_tokens: int = 8000,
    ) -> str:
        """Generate spec from prompt."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                PERPLEXITY_API_URL,
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]


# ============================================================================
# YAML Extraction & Validation
# ============================================================================


def extract_yaml_from_response(response: str) -> str:
    """Extract YAML content from response (may be wrapped in code blocks)."""
    # Try to find YAML in code blocks
    yaml_pattern = r"```(?:yaml)?\n(.*?)```"
    matches = re.findall(yaml_pattern, response, re.DOTALL)

    if matches:
        # Return the longest match (likely the full spec)
        return max(matches, key=len).strip()

    # If no code blocks, try to find content starting with 'metadata:'
    if "metadata:" in response:
        start = response.find("metadata:")
        return response[start:].strip()

    # Return as-is
    return response.strip()


def validate_yaml_syntax(yaml_content: str) -> tuple[bool, str | None]:
    """Validate YAML syntax."""
    try:
        yaml.safe_load(yaml_content)
        return True, None
    except yaml.YAMLError as e:
        return False, str(e)


def validate_spec_structure(spec: dict) -> list[str]:
    """Validate Module-Spec-v2.4 structure."""
    required_sections = [
        "metadata",
        "ownership",
        "runtime_wiring",
        "external_surface",
        "dependencies",
        "packet_contract",
        "idempotency",
        "error_policy",
        "observability",
        "runtime_touchpoints",
        "test_scope",
        "acceptance",
        "global_invariants_ack",
        "spec_confidence",
        "repo",
        "interfaces",
        "environment",
        "orchestration",
        "boot_impact",
        "standards",
        "goals",
        "non_goals",
        "notes_for_codegen",
    ]

    errors = []

    # Check required sections
    for section in required_sections:
        if section not in spec:
            errors.append(f"Missing required section: {section}")

    # Check metadata
    if "metadata" in spec:
        metadata = spec["metadata"]
        if "module_id" not in metadata:
            errors.append("metadata.module_id is required")
        elif not re.match(r"^[a-z][a-z0-9_]*$", metadata.get("module_id", "")):
            errors.append("metadata.module_id must be lowercase_snake_case")

        if "tier" in metadata:
            tier = metadata["tier"]
            if not isinstance(tier, int) or tier < 0 or tier > 7:
                errors.append("metadata.tier must be integer 0-7")

    # Check packet_contract
    if "packet_contract" in spec:
        pc = spec["packet_contract"]
        if "emits" not in pc or not pc["emits"]:
            errors.append("packet_contract.emits must have at least one packet type")

    # Check acceptance tests
    if "acceptance" in spec:
        acc = spec["acceptance"]
        if "positive" not in acc or not acc["positive"]:
            errors.append("acceptance.positive must have at least one test case")
        if "negative" not in acc or not acc["negative"]:
            errors.append("acceptance.negative must have at least one test case")

    return errors


# ============================================================================
# Main Logic
# ============================================================================


async def generate_module_spec(
    module_description: str,
    synthesis: dict | None = None,
    api_key: str | None = None,
    output_path: Path | None = None,
    validate: bool = True,
) -> tuple[str, Path]:
    """
    Generate a Module-Spec-v2.4 YAML file.

    Args:
        module_description: Description of the module to generate
        synthesis: Optional research synthesis to incorporate
        api_key: Perplexity API key (or uses env var)
        output_path: Where to save the spec (default: codegen/specs/)
        validate: Whether to validate the generated spec

    Returns:
        Tuple of (yaml_content, output_path)
    """
    logger.info(f"[*] Generating spec for: {module_description[:50]}...")

    # Build prompt
    prompt = build_prompt(module_description, synthesis)

    # Generate spec via Perplexity
    client = PerplexityClient(api_key)
    logger.info("[*] Calling Perplexity API...")
    response = await client.generate_spec(prompt)

    # Extract YAML
    yaml_content = extract_yaml_from_response(response)

    # Validate
    if validate:
        logger.info("[*] Validating YAML syntax...")
        is_valid, error = validate_yaml_syntax(yaml_content)
        if not is_valid:
            logger.info(f"[!] YAML syntax error: {error}")
            logger.info("[!] Saving raw response for manual review...")
        else:
            spec = yaml.safe_load(yaml_content)
            errors = validate_spec_structure(spec)
            if errors:
                logger.info("[!] Spec validation warnings:")
                for err in errors:
                    logger.info(f"    - {err}")
            else:
                logger.info("[+] Spec validation passed!")

    # Determine output path
    if output_path is None:
        # Extract module_id from spec
        try:
            spec = yaml.safe_load(yaml_content)
            module_id = spec.get("metadata", {}).get("module_id", "unknown")
        except Exception:
            module_id = "unknown"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = SPECS_DIR / f"{module_id}_{timestamp}.yaml"

    # Ensure directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save
    output_path.write_text(yaml_content)
    logger.info(f"[+] Spec saved to: {output_path}")

    return yaml_content, output_path


async def generate_from_synthesis(
    synthesis_path: Path,
    module_name: str,
    api_key: str | None = None,
) -> tuple[str, Path]:
    """Generate spec from a synthesis result JSON file."""
    synthesis = json.loads(synthesis_path.read_text())
    return await generate_module_spec(
        module_description=module_name,
        synthesis=synthesis,
        api_key=api_key,
    )


def interactive_mode() -> tuple[str, dict | None]:
    """Interactive mode for gathering module description."""
    logger.info("\n=== L9 Module Spec Generator (Interactive) ===\n")

    module_id = input("Module ID (lowercase_snake_case): ").strip()
    name = input("Human-readable name: ").strip()
    description = input("One-line description: ").strip()
    tier = input("Tier (0-7): ").strip()
    service = input("Service (api/worker/scheduler/memory): ").strip()

    logger.info("\nOptional: Describe additional requirements (empty to skip):")
    additional = input("> ").strip()

    module_description = f"""
Module: {module_id}
Name: {name}
Description: {description}
Tier: {tier}
Service: {service}
{f"Additional: {additional}" if additional else ""}
"""

    return module_description, None


# ============================================================================
# CLI
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Generate L9 Module-Spec-v2.4 YAML from description or synthesis"
    )

    parser.add_argument(
        "--topic", type=str, help="Module topic/name (e.g., 'slack_webhook_adapter')"
    )

    parser.add_argument("--description", type=str, help="Full module description")

    parser.add_argument(
        "--from-synthesis", type=Path, help="Path to synthesis result JSON file"
    )

    parser.add_argument("--interactive", action="store_true", help="Interactive mode")

    parser.add_argument("--output", type=Path, help="Output path for generated spec")

    parser.add_argument(
        "--api-key",
        type=str,
        help="Perplexity API key (or set PERPLEXITY_API_KEY env var)",
    )

    parser.add_argument(
        "--no-validate", action="store_true", help="Skip spec validation"
    )

    args = parser.parse_args()

    # Determine input mode
    if args.interactive:
        module_description, synthesis = interactive_mode()
    elif args.from_synthesis:
        if not args.topic:
            logger.info("Error: --topic required when using --from-synthesis")
            sys.exit(1)
        synthesis = json.loads(args.from_synthesis.read_text())
        module_description = args.topic
    elif args.description:
        module_description = args.description
        synthesis = None
    elif args.topic:
        module_description = f"Module: {args.topic}"
        synthesis = None
    else:
        parser.print_help()
        sys.exit(1)

    # Run async generation
    try:
        yaml_content, output_path = asyncio.run(
            generate_module_spec(
                module_description=module_description,
                synthesis=synthesis,
                api_key=args.api_key,
                output_path=args.output,
                validate=not args.no_validate,
            )
        )

        logger.info("\n[+] Success! Spec ready for codegen pipeline:")
        logger.info(f"    python -m agents.codegenagent generate {output_path}")

    except Exception as e:
        logger.info(f"[!] Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COD-FOUN-030",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "async",
        "auth",
        "cli",
        "client",
        "code-generation",
        "config",
        "filesystem",
        "foundation",
        "http-client",
    ],
    "keywords": [
        "build",
        "client",
        "extract",
        "generate",
        "generator",
        "interactive",
        "load",
        "mode",
    ],
    "business_value": "Implements PerplexityClient for generate spec functionality",
    "last_modified": "2026-01-16T00:17:40Z",
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
