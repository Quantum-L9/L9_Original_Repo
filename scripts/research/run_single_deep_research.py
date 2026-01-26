#!/usr/bin/env python3
"""
Single deep research request for config_loader module.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Run Single Deep Research",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-20T15:08:40Z",
    "updated_at": "2026-01-07T13:35:58Z",
    "layer": "operations",
    "domain": "scripts",
    "module_name": "run_single_deep_research",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API", "Perplexity API", "PostgreSQL", "Redis"],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import os
import sys
import time

import httpx
import structlog

# Get API key directly from .env

logger = structlog.get_logger(__name__)


def get_api_key():
    env_path = "/Users/ib-mac/Projects/L9/.env"
    with open(env_path) as f:
        for line in f:
            if line.startswith("PERPLEXITY_API_KEY="):
                return line.split("=", 1)[1].strip()
    return None


API_KEY = get_api_key()
if not API_KEY:
    logger.info("❌ No API key found")
    sys.exit(1)

PROMPT = """You are a senior L9 system architect conducting deep research to generate a production-ready Module Specification.

# MODULE TO SPECIFY

**Module ID:** config_loader
**Name:** Configuration Loader
**Tier:** 0 (Core Infrastructure - loads before everything else)
**Description:** Environment and YAML configuration management with validation. Provides typed access to all L9 configuration via Pydantic Settings. Fails fast on missing required environment variables.

# RESEARCH REQUIREMENTS

Conduct comprehensive research on:
1. Pydantic Settings v2 — BaseSettings, environment variable binding, nested models, validation
2. Python-dotenv patterns — .env file loading, precedence rules
3. YAML configuration loading — PyYAML, safe loading
4. 12-Factor App config — environment variable best practices
5. FastAPI lifespan integration — startup configuration
6. Fail-fast patterns — ValidationError handling, boot-time validation

# L9 SYSTEM CONTEXT

system: L9, core_protocol: PacketEnvelope, memory: PostgreSQL + pgvector, cache: Redis, logging: structlog, http_client: httpx

# OUTPUT FORMAT

Generate a COMPLETE Module-Spec-v2.5 YAML with ALL sections filled with real production values.

# CRITICAL REQUIREMENTS

1. Tier 0 semantics: This loads FIRST. Cannot depend on any other L9 module.
2. Fail-fast: Missing required env vars MUST crash at startup.
3. Type safety: All config values must be typed via Pydantic.

Generate the COMPLETE specification."""

logger.info("🚀 Sending config_loader to Sonar Deep Research...")
logger.info(f"   API Key: {API_KEY[:15]}...")
logger.info("   ⏳ This may take 2-5 minutes...")
start = time.time()

try:
    with httpx.Client(timeout=300.0) as client:
        resp = client.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "sonar-deep-research",
                "messages": [{"role": "user", "content": PROMPT}],
                "temperature": 0.2,
                "max_tokens": 8000,
            },
        )

        elapsed = time.time() - start
        logger.info(f"\n⏱️  Response in {elapsed:.1f}s (status: {resp.status_code})")

        if resp.status_code == 200:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            citations = data.get("citations", [])
            usage = data.get("usage", {})

            logger.info("✅ SUCCESS!")
            logger.info(f"   Citations: {len(citations)}")
            logger.info(f"   Tokens: {usage.get('total_tokens', 'N/A')}")
            logger.info(f"   Cost: ${usage.get('cost', {}).get('total_cost', 'N/A')}")

            # Save output
            output_path = "/Users/ib-mac/Projects/L9/docs/Perplexity/outputs/01_config_loader_spec.md"
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w") as f:
                f.write("# config_loader Module Spec\n\n")
                f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"Citations: {len(citations)}\n\n---\n\n")
                f.write(content)
                f.write("\n\n---\n\n## Sources\n\n")
                for i, cite in enumerate(citations[:20], 1):
                    f.write(f"{i}. {cite}\n")

            logger.info(f"\n📁 Saved to: {output_path}")
            logger.info(f"\n{'=' * 60}")
            logger.info("SPEC OUTPUT:")
            logger.info("=" * 60)
            logger.info(content[:2000])
            if len(content) > 2000:
                logger.info("\n... [truncated, full output in file] ...")
        else:
            logger.error(f"❌ Error: {resp.status_code}")
            logger.info(resp.text)

except httpx.TimeoutException:
    logger.info(
        f"❌ Timeout after {time.time() - start:.1f}s - deep research taking too long"
    )
except Exception as e:
    logger.error(f"❌ Exception: {type(e).__name__}: {e}")

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
        "caching",
        "http-client",
        "logging",
        "messaging",
        "operations",
        "scripts",
        "utility",
    ],
    "keywords": ["api", "deep", "research", "single"],
    "business_value": "Utility module for run single deep research",
    "last_modified": "2026-01-07T13:35:58Z",
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
