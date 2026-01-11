#!/usr/bin/env python3
"""
Batch Module Spec Generator using Perplexity API
================================================

Generates YAML module specs using controlled async parallel calls.

Rate Limits (from Perplexity API):
- sonar-reasoning-pro: 50 req/min → 5 concurrent is safe
- sonar-deep-research: 5 req/min → 1 at a time only

Usage:
    # From module list file:
    python scripts/batch_generate_specs.py --modules modules.txt --batch-size 5

    # Single module:
    python scripts/batch_generate_specs.py --module slack_webhook_adapter

    # Dry run:
    python scripts/batch_generate_specs.py --modules modules.txt --dry-run
"""

import asyncio
import structlog
import argparse
import os
import sys
import time
import random
from pathlib import Path
from typing import List
from dataclasses import dataclass

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = structlog.get_logger(__name__)

try:
    import httpx
except ImportError:
    logger.error("❌ httpx not installed. Run: pip install httpx")
    sys.exit(1)

# ============================================================================
# Configuration
# ============================================================================


@dataclass
class BatchConfig:
    """Batch processing configuration"""

    api_key: str
    model: str = "sonar-reasoning-pro"  # Best for spec generation
    batch_size: int = 5  # Concurrent requests
    delay_between_batches: float = 2.0  # Seconds
    timeout: float = 120.0  # Per-request timeout
    max_retries: int = 3
    output_dir: Path = Path("generated/specs")


# ============================================================================
# Module Spec Prompt Template
# ============================================================================

MODULE_SPEC_PROMPT = """You are a senior software architect. Generate a complete YAML module specification following the L9 Module-Spec-v2.5 format.

MODULE TO SPECIFY: {module_name}
DESCRIPTION: {module_description}

Generate a YAML file with ALL of these sections filled in (do not skip any):

```yaml
# ============================================================================
# L9 MODULE SPEC — {module_name}
# ============================================================================

module:
  name: {module_name}
  version: "1.0.0"
  description: "{module_description}"
  category: [determine: api | service | adapter | core | agent]

# Runtime placement
runtime:
  placement: [vps | mac | both]
  startup_order: [1-100, lower = earlier]
  health_check:
    endpoint: /health
    interval_seconds: 30

# Dependencies
dependencies:
  internal: []  # Other L9 modules this depends on
  external: []  # pip packages needed
  services: []  # postgres, redis, etc.

# API Surface (if any)
api:
  routes: []  # List of routes with method, path, handler
  websockets: []  # WS endpoints if any

# Configuration
config:
  env_vars: []  # Required environment variables
  settings_class: null  # Pydantic settings class path

# Testing
testing:
  unit_tests: []
  integration_tests: []
  smoke_test: null  # Quick validation command

# Observability
observability:
  logs: true
  metrics: []
  traces: false

# Failure handling
failure:
  blast_radius: [isolated | service | system]
  fallback: null
  circuit_breaker: false
```

Fill in ALL sections with realistic, production-ready values based on the module name and description. Be specific and actionable.
"""


# ============================================================================
# Rate Limiter
# ============================================================================


class TokenBucketLimiter:
    """Token bucket rate limiter for API calls"""

    def __init__(self, rate_per_minute: int = 50):
        self.rate = rate_per_minute / 60.0  # Tokens per second
        self.tokens = rate_per_minute  # Start full
        self.max_tokens = rate_per_minute
        self.last_update = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self) -> float:
        """Acquire a token, returning wait time if needed"""
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(self.max_tokens, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens >= 1:
                self.tokens -= 1
                return 0

            # Calculate wait time
            wait_time = (1 - self.tokens) / self.rate
            return wait_time

    async def wait_for_token(self):
        """Wait until a token is available"""
        wait_time = await self.acquire()
        if wait_time > 0:
            await asyncio.sleep(wait_time)


# ============================================================================
# Perplexity Client with Retry
# ============================================================================


class PerplexityBatchClient:
    """Async Perplexity client with rate limiting and retry"""

    def __init__(self, config: BatchConfig):
        self.config = config
        self.limiter = TokenBucketLimiter(rate_per_minute=50)
        self.base_url = "https://api.perplexity.ai/chat/completions"

    async def generate_spec(
        self, module_name: str, module_description: str, semaphore: asyncio.Semaphore
    ) -> dict:
        """Generate a single module spec with rate limiting"""

        async with semaphore:
            # Wait for rate limit token
            await self.limiter.wait_for_token()

            prompt = MODULE_SPEC_PROMPT.format(
                module_name=module_name, module_description=module_description
            )

            for attempt in range(self.config.max_retries):
                try:
                    async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                        response = await client.post(
                            self.base_url,
                            json={
                                "model": self.config.model,
                                "messages": [{"role": "user", "content": prompt}],
                                "temperature": 0.3,  # Lower = more consistent
                                "max_tokens": 4000,
                            },
                            headers={"Authorization": f"Bearer {self.config.api_key}"},
                        )

                        if response.status_code == 429:
                            # Rate limited - exponential backoff
                            delay = (2**attempt) + random.uniform(0, 1)
                            logger.info(
                                f"  ⚠️  Rate limited on {module_name}, waiting {delay:.1f}s..."
                            )
                            await asyncio.sleep(delay)
                            continue

                        response.raise_for_status()
                        data = response.json()
                        content = data["choices"][0]["message"]["content"]

                        return {
                            "success": True,
                            "module": module_name,
                            "content": content,
                            "tokens": data.get("usage", {}),
                        }

                except httpx.TimeoutException:
                    logger.info(
                        f"  ⚠️  Timeout on {module_name}, attempt {attempt + 1}/{self.config.max_retries}"
                    )
                    await asyncio.sleep(2**attempt)

                except Exception as e:
                    logger.error(f"  ❌ Error on {module_name}: {e}")
                    if attempt < self.config.max_retries - 1:
                        await asyncio.sleep(2**attempt)

            return {
                "success": False,
                "module": module_name,
                "error": "Max retries exceeded",
            }


# ============================================================================
# Batch Processor
# ============================================================================


class BatchSpecGenerator:
    """Orchestrates batch spec generation"""

    def __init__(self, config: BatchConfig):
        self.config = config
        self.client = PerplexityBatchClient(config)
        self.results = []

    async def process_batch(self, modules: List[tuple]) -> List[dict]:
        """Process a batch of modules with controlled concurrency"""

        semaphore = asyncio.Semaphore(self.config.batch_size)

        tasks = [
            self.client.generate_spec(name, desc, semaphore) for name, desc in modules
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        return [
            r if not isinstance(r, Exception) else {"success": False, "error": str(r)}
            for r in results
        ]

    def save_spec(self, module_name: str, content: str) -> Path:
        """Extract and save YAML spec from response"""
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

        # Extract YAML block
        yaml_content = content
        if "```yaml" in content:
            start = content.find("```yaml") + 7
            end = content.find("```", start)
            yaml_content = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            yaml_content = content[start:end].strip()

        output_path = self.config.output_dir / f"{module_name}.yaml"
        output_path.write_text(yaml_content)
        return output_path

    async def run(self, modules: List[tuple], dry_run: bool = False) -> dict:
        """Run batch generation"""

        logger.info("=" * 60)
        logger.info("  L9 BATCH MODULE SPEC GENERATOR")
        logger.info("=" * 60)
        logger.info(f"\n📋 Modules to process: {len(modules)}")
        logger.info(f"🔧 Model: {self.config.model}")
        logger.info(f"⚡ Batch size: {self.config.batch_size} concurrent")
        logger.info(
            f"⏱️  Estimated time: {len(modules) / self.config.batch_size * 35:.0f}s"
        )
        logger.info(f"📁 Output: {self.config.output_dir}/")

        if dry_run:
            logger.info("\n🔍 DRY RUN - Would generate:")
            for name, desc in modules:
                logger.info(f"   • {name}: {desc[:50]}...")
            return {"dry_run": True, "modules": len(modules)}

        logger.info("\n" + "-" * 60)

        start_time = time.time()
        successful = 0
        failed = 0

        # Process in batches with delay between
        batch_count = (
            len(modules) + self.config.batch_size - 1
        ) // self.config.batch_size

        for i in range(0, len(modules), self.config.batch_size):
            batch = modules[i : i + self.config.batch_size]
            batch_num = i // self.config.batch_size + 1

            logger.info(
                f"\n📦 Batch {batch_num}/{batch_count}: {', '.join(m[0] for m in batch)}"
            )

            results = await self.process_batch(batch)

            for result in results:
                if result.get("success"):
                    path = self.save_spec(result["module"], result["content"])
                    logger.info(f"   ✅ {result['module']} → {path}")
                    successful += 1
                else:
                    logger.error(
                        f"   ❌ {result.get('module', 'unknown')}: {result.get('error', 'Unknown error')}"
                    )
                    failed += 1

            # Delay between batches (except last)
            if i + self.config.batch_size < len(modules):
                logger.info(
                    f"   ⏳ Waiting {self.config.delay_between_batches}s before next batch..."
                )
                await asyncio.sleep(self.config.delay_between_batches)

        elapsed = time.time() - start_time

        logger.info("\n" + "=" * 60)
        logger.info(f"✅ Completed: {successful}/{len(modules)} specs")
        logger.error(f"❌ Failed: {failed}/{len(modules)}")
        logger.info(f"⏱️  Total time: {elapsed:.1f}s")
        logger.info(f"📁 Output: {self.config.output_dir}/")
        logger.info("=" * 60)

        return {
            "successful": successful,
            "failed": failed,
            "elapsed": elapsed,
            "output_dir": str(self.config.output_dir),
        }


# ============================================================================
# CLI
# ============================================================================


def parse_modules_file(path: Path) -> List[tuple]:
    """Parse modules file (format: module_name | description)"""
    modules = []
    for line in path.read_text().strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if "|" in line:
            name, desc = line.split("|", 1)
            modules.append((name.strip(), desc.strip()))
        else:
            # Infer description from name
            name = line
            desc = f"L9 module for {name.replace('_', ' ')}"
            modules.append((name, desc))

    return modules


async def main():
    parser = argparse.ArgumentParser(description="Batch generate module specs")
    parser.add_argument("--modules", type=Path, help="File with module list")
    parser.add_argument("--module", type=str, help="Single module name")
    parser.add_argument(
        "--description", type=str, help="Module description (with --module)"
    )
    parser.add_argument("--batch-size", type=int, default=5, help="Concurrent requests")
    parser.add_argument("--output", "-o", type=Path, default=Path("generated/specs"))
    parser.add_argument("--model", default="sonar-reasoning-pro")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be generated"
    )

    args = parser.parse_args()

    # Get API key
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        logger.info("❌ PERPLEXITY_API_KEY not set")
        sys.exit(1)

    # Parse modules
    if args.module:
        desc = args.description or f"L9 module for {args.module.replace('_', ' ')}"
        modules = [(args.module, desc)]
    elif args.modules:
        if not args.modules.exists():
            logger.info(f"❌ Modules file not found: {args.modules}")
            sys.exit(1)
        modules = parse_modules_file(args.modules)
    else:
        logger.info("❌ Provide --modules file or --module name")
        sys.exit(1)

    # Configure and run
    config = BatchConfig(
        api_key=api_key,
        model=args.model,
        batch_size=args.batch_size,
        output_dir=args.output,
    )

    generator = BatchSpecGenerator(config)
    await generator.run(modules, dry_run=args.dry_run)


if __name__ == "__main__":
    asyncio.run(main())
