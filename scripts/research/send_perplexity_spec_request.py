#!/usr/bin/env python3
# ============================================================================
__dora_meta__ = {
    "component_name": "Send Perplexity Spec Request",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-20T15:08:40Z",
    "updated_at": "2026-01-09T12:30:43Z",
    "layer": "operations",
    "domain": "scripts",
    "module_name": "send_perplexity_spec_request",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API", "Perplexity API", "PostgreSQL", "Redis"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import structlog

logger = structlog.get_logger(__name__)
"""
Send Module Spec generation request to Perplexity with full context embedded.

Usage:
    python scripts/send_perplexity_spec_request.py
"""
import json
import os
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import httpx
except ImportError:
    logger.info("❌ httpx not installed. Run: pip install httpx")
    sys.exit(1)


def load_env():
    """Load API key from .env file."""
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("PERPLEXITY_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("PERPLEXITY_API_KEY")


def load_file(path: Path) -> str:
    """Load file content."""
    with open(path) as f:
        return f.read()


def main():
    """
    Performs initialization and setup for sending a Perplexity specification request, including loading API keys and context files.



    Raises:
        SystemExit: If the API key is not found in environment variables or .env file.
    """
    # Load API key
    api_key = load_env()
    if not api_key:
        logger.info("❌ PERPLEXITY_API_KEY not found in .env or environment")
        sys.exit(1)

    # Load context files
    superprompt_path = PROJECT_ROOT / "docs/Perplexity/Module-Spec-SuperPrompt-v2.5.md"
    spec_template_path = PROJECT_ROOT / "docs/Perplexity/Module-Spec-v2.5.yaml"

    logger.info("📚 Loading context files...")
    superprompt = load_file(superprompt_path)
    spec_template = load_file(spec_template_path)

    logger.info(f"   SuperPrompt: {len(superprompt)} chars")
    logger.info(f"   Spec Template: {len(spec_template)} chars")

    # Build the request
    system_context = f"""SUPERPROMPT (CANONICAL v2.5):
{superprompt}

MODULE-SPEC SCHEMA (v2.5):
{spec_template}"""

    user_prompt = """TASK: Generate ONE complete Module-Spec v2.5 YAML.

FIXED INPUTS (AUTHORITATIVE — DO NOT INFER):
- module_id: config_loader
- module_name: Configuration Loader
- tier: 0
- schema_version: 2.5

RULES:
- Do NOT infer module_id, tier, or dependencies
- Include ALL 26 required v2.5 sections
- Output ONLY valid YAML (no markdown code blocks, no commentary)
- Fill ALL placeholder fields with real values

MODULE DESCRIPTION:
Configuration loader for L9 system. Uses Pydantic Settings v2 to load environment variables and optional YAML config files. Validates configuration at startup using Pydantic validators. Fails fast with sys.exit(1) on missing required env vars or validation errors. Exposes no HTTP endpoints. Provides typed Settings object to all other modules via dependency injection.

TIER 0 CONSTRAINTS:
- depends_on: [] (must be empty - no L9 dependencies)
- blocks_startup_on_failure: true
- packet_contract.emits: [] (infrastructure module - no packets)
- external_surface: all false (no HTTP, no webhook, no tool)

REQUIRED ENVIRONMENT VARIABLES:
- DATABASE_URL: PostgreSQL connection string
- REDIS_URL: Redis connection string
- AIOS_BASE_URL: AIOS API endpoint (optional, default: http://localhost:8000)
- LOG_LEVEL: Logging level (optional, default: INFO)
- LOG_FORMAT: json or console (optional, default: json)

OUTPUT:
Generate the complete Module-Spec v2.5 YAML now. Start immediately with 'schema_version:' - no preamble."""

    payload = {
        "model": "sonar-reasoning",
        "temperature": 0,
        "max_tokens": 10000,
        "messages": [
            {
                "role": "system",
                "content": "You are a stateless technical specification compiler. Follow the SUPERPROMPT and MODULE-SPEC SCHEMA exactly. Output ONLY valid YAML. No markdown. No commentary. No thinking blocks.",
            },
            {"role": "system", "content": system_context},
            {"role": "user", "content": user_prompt},
        ],
    }

    logger.info("\n🚀 Sending request to Perplexity sonar-reasoning...")
    logger.info(f"   Total prompt: ~{len(json.dumps(payload))} chars")
    logger.info("   ⏳ This may take 30-60 seconds...")

    start = time.time()

    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

            elapsed = time.time() - start
            logger.info(f"\n⏱️  Response in {elapsed:.1f}s (status: {resp.status_code})")

            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})

                logger.info("✅ SUCCESS!")
                logger.info(f"   Tokens: {usage}")

                # Clean up content - remove thinking blocks if present
                if "<think>" in content:
                    # Extract content after </think>
                    think_end = content.find("</think>")
                    if think_end > 0:
                        content = content[think_end + 8 :].strip()

                # Remove markdown code blocks if present
                if content.startswith("```yaml"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

                # Save output
                output_path = PROJECT_ROOT / "generated/specs/config_loader.yaml"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "w") as f:
                    f.write(content)

                logger.info(f"\n📁 Saved to: {output_path}")
                logger.info(f"\n{'=' * 70}")
                logger.info("YAML OUTPUT:")
                logger.info("=" * 70)
                logger.info(content)

            else:
                logger.info(f"❌ Error: {resp.status_code}")
                logger.info(resp.text)

    except httpx.TimeoutException:
        logger.info(f"❌ Timeout after {time.time() - start:.1f}s")
    except Exception as e:
        logger.info(f"❌ Exception: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "auth",
        "cli",
        "filesystem",
        "http-client",
        "logging",
        "messaging",
        "operations",
        "scripts",
        "serialization",
    ],
    "keywords": ["env", "load", "perplexity", "send", "spec"],
    "business_value": "Utility module for send perplexity spec request",
    "last_modified": "2026-01-09T12:30:43Z",
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
