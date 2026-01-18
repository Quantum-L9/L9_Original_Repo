#!/usr/bin/env python3
"""
L9 Deep Research Delegation Script
===================================

Sends module spec requests to Perplexity Sonar Deep Research.

Rate Limit: 5 requests/minute (12 second delay between calls)
Response Time: 2-5 minutes per query
Cost: ~$0.50-$2.00 per query

Usage:
    # Run first 5 modules:
    python scripts/delegate_deep_research.py

    # Dry run (show what would be sent):
    python scripts/delegate_deep_research.py --dry-run

    # Single module:
    python scripts/delegate_deep_research.py --module 01_config_loader
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Delegate Deep Research",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-20T15:08:40Z",
    "updated_at": "2026-01-09T12:30:43Z",
    "layer": "operations",
    "domain": "scripts",
    "module_name": "delegate_deep_research",
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

import asyncio
import structlog
import os
import sys
import time
from pathlib import Path
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env file
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass  # dotenv not installed, rely on environment

logger = structlog.get_logger(__name__)

try:
    import httpx
except ImportError:
    logger.error("❌ httpx not installed. Run: pip install httpx")
    sys.exit(1)

# ============================================================================
# Configuration

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
MODEL = "sonar-deep-research"
RATE_LIMIT_DELAY = 20  # 5 req/min = 12s, use 20s for extra safety
TIMEOUT = 300  # 5 minutes - Deep Research takes time!

PAYLOADS_DIR = (
    Path(__file__).parent.parent / "docs" / "Perplexity" / "payloads" / "deep_research"
)
OUTPUT_DIR = Path(__file__).parent.parent / "generated" / "specs"

# First 5 modules
MODULES = [
    "01_config_loader",
    "02_structlog_setup",
    "03_packet_protocol",
    # "04_slack_webhook_adapter",  # ARCHIVED: Use api/routes/slack.py
    "05_health_routes",
]

# ============================================================================
# Payload Extraction

def extract_prompt_from_payload(payload_path: Path) -> str:
    """Extract the prompt section from a payload markdown file."""
    content = payload_path.read_text()

    # Find the prompt section (after the last "---")
    parts = content.split("---")
    if len(parts) >= 3:
        # Last section before "END OF PAYLOAD"
        prompt = parts[-2].strip()
        if "END OF PAYLOAD" in prompt:
            prompt = prompt.split("END OF PAYLOAD")[0].strip()
        return prompt

    # Fallback: return everything after "## PROMPT"
    if "## PROMPT" in content:
        return content.split("## PROMPT")[1].split("# END")[0].strip()

    raise ValueError(f"Could not extract prompt from {payload_path}")

# ============================================================================
# API Client

async def call_deep_research(prompt: str, api_key: str) -> dict:
    """Call Perplexity Sonar Deep Research API."""

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(
            PERPLEXITY_API_URL,
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 8000,
            },
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

        if response.status_code == 429:
            return {"error": "rate_limited", "status": 429}

        response.raise_for_status()
        return response.json()

def extract_yaml_from_response(response: dict) -> str:
    """Extract YAML spec from API response."""
    content = response["choices"][0]["message"]["content"]

    # Try to extract YAML block
    if "```yaml" in content:
        start = content.find("```yaml") + 7
        end = content.find("```", start)
        return content[start:end].strip()
    elif "```" in content:
        start = content.find("```") + 3
        end = content.find("```", start)
        return content[start:end].strip()

    # Return full content if no code block
    return content

# ============================================================================
# Orchestration

async def process_module(module_name: str, api_key: str, dry_run: bool = False) -> dict:
    """Process a single module."""

    payload_path = PAYLOADS_DIR / f"{module_name}.md"

    if not payload_path.exists():
        return {"module": module_name, "error": f"Payload not found: {payload_path}"}

    try:
        prompt = extract_prompt_from_payload(payload_path)
    except ValueError as e:
        return {"module": module_name, "error": str(e)}

    if dry_run:
        logger.info(f"\n📋 {module_name}")
        logger.info(f"   Payload: {payload_path}")
        logger.info(f"   Prompt length: {len(prompt)} chars")
        return {"module": module_name, "dry_run": True}

    logger.info(f"\n🔬 Delegating {module_name} to Sonar Deep Research...")
    logger.info("   ⏳ This may take 2-5 minutes...")

    start_time = time.time()

    try:
        response = await call_deep_research(prompt, api_key)

        if "error" in response:
            logger.error(f"   ❌ Error: {response['error']}")
            return {"module": module_name, "error": response["error"]}

        elapsed = time.time() - start_time
        yaml_content = extract_yaml_from_response(response)

        # Save output
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_name = (
            module_name.split("_", 1)[1] if "_" in module_name else module_name
        )
        output_path = OUTPUT_DIR / f"{output_name}.yaml"
        output_path.write_text(yaml_content)

        tokens = response.get("usage", {})

        logger.info(f"   ✅ Complete in {elapsed:.1f}s")
        logger.info(f"   📁 Saved to: {output_path}")
        logger.info(f"   📊 Tokens: {tokens.get('total_tokens', 'N/A')}")

        return {
            "module": module_name,
            "success": True,
            "elapsed": elapsed,
            "output_path": str(output_path),
            "tokens": tokens,
        }

    except httpx.TimeoutException:
        logger.info(f"   ❌ Timeout after {TIMEOUT}s")
        return {"module": module_name, "error": "timeout"}

    except Exception as e:
        logger.error(f"   ❌ Error: {e}")
        return {"module": module_name, "error": str(e)}

async def main():
    parser = argparse.ArgumentParser(
        description="Delegate module specs to Perplexity Deep Research"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be sent"
    )
    parser.add_argument(
        "--module", type=str, help="Process single module (e.g., 01_config_loader)"
    )
    args = parser.parse_args()

    # Check API key
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key and not args.dry_run:
        logger.info("❌ PERPLEXITY_API_KEY not set")
        logger.info("   Add to .env: PERPLEXITY_API_KEY=pplx-...")
        sys.exit(1)

    # Determine modules to process
    modules = [args.module] if args.module else MODULES

    logger.info("=" * 60)
    logger.info("  L9 DEEP RESEARCH DELEGATION")
    logger.info("=" * 60)
    logger.info(f"\n🔬 Model: {MODEL}")
    logger.info(f"📋 Modules: {len(modules)}")
    logger.info(f"⏱️  Rate limit delay: {RATE_LIMIT_DELAY}s between calls")
    logger.info(
        f"💰 Estimated cost: ${len(modules) * 1.00:.2f} - ${len(modules) * 2.00:.2f}"
    )

    if args.dry_run:
        logger.info("\n🔍 DRY RUN MODE")

    logger.info("\n" + "-" * 60)

    results = []

    for i, module in enumerate(modules):
        result = await process_module(module, api_key, args.dry_run)
        results.append(result)

        # Rate limit delay (except for last module)
        if not args.dry_run and i < len(modules) - 1:
            logger.info(
                f"\n⏳ Rate limit: waiting {RATE_LIMIT_DELAY}s before next call..."
            )
            await asyncio.sleep(RATE_LIMIT_DELAY)

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("  DELEGATION COMPLETE")
    logger.info("=" * 60)

    successful = sum(1 for r in results if r.get("success"))
    failed = sum(1 for r in results if r.get("error"))

    logger.info(f"\n✅ Successful: {successful}/{len(modules)}")
    logger.error(f"❌ Failed: {failed}/{len(modules)}")

    if successful > 0:
        logger.info(f"\n📁 Specs saved to: {OUTPUT_DIR}/")
        logger.info("\n📝 Next steps:")
        logger.info("   1. Review generated specs")
        logger.info("   2. Use Module-Prompt-PERPLEXITY-v3.0.md to generate code")
        logger.info("   3. /wire the generated code into the repo")

if __name__ == "__main__":
    asyncio.run(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["api", "async", "auth", "cli", "filesystem", "http-client", "logging", "messaging", "operations", "scripts"],
    "keywords": ["deep", "delegate", "extract", "module", "payload", "process", "prompt", "research"],
    "business_value": "Utility module for delegate deep research",
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
