"""
Quantum Swarm Loader
====================

Parallel code generation orchestrator with SymPy cache acceleration.
Loads swarm capsules and triggers batch generation.

Part of the Quantum AI Factory architecture.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Quantum Swarm Loader",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-17T23:51:17Z",
    "layer": "intelligence",
    "domain": "error_handling",
    "module_name": "quantum_swarm_loader",
    "type": "exception",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
import yaml

from agents.codegenagent.c_gmp_engine import CGMPEngine
from agents.codegenagent.meta_loader import MetaLoader
from services.symbolic_computation import SymbolicComputation

logger = structlog.get_logger(__name__)


class SwarmLoaderError(Exception):
    """Exception raised when swarm loading fails."""


class QuantumSwarmLoader:
    """
    Loads and executes quantum swarm capsules for parallel code generation.

    Pre-warms the SymPy expression cache for common patterns
    then runs parallel generation across all specs.
    """

    def __init__(
        self,
        symbolic_engine: Optional[SymbolicComputation] = None,
        max_parallel: int = 10,
    ):
        """
        Initialize the quantum swarm loader.

        Args:
            symbolic_engine: Shared SymbolicComputation engine
            max_parallel: Maximum parallel generation tasks
        """
        self._symbolic = symbolic_engine or SymbolicComputation(cache_size=256)
        self._max_parallel = max_parallel
        self._swarm_stats: Dict[str, Any] = {
            "capsules_loaded": 0,
            "specs_processed": 0,
            "files_generated": 0,
            "cache_warmups": 0,
        }

        logger.info(
            "quantum_swarm_loader_initialized",
            max_parallel=max_parallel,
        )

    async def load_quantum_swarm(
        self,
        capsule_path: str,
    ) -> Dict[str, Any]:
        """
        Load and execute a quantum swarm capsule.

        A capsule is a YAML file that references multiple spec files
        to generate in parallel.

        Args:
            capsule_path: Path to swarm.yaml capsule

        Returns:
            Swarm execution results
        """
        try:
            capsule = self._load_capsule(capsule_path)

            # Warm up cache with common expressions
            await self._warmup_cache(capsule.get("cache_warmup", []))

            # Get list of specs to generate
            specs = capsule.get("specs", [])
            if not specs:
                raise SwarmLoaderError("No specs defined in capsule")

            # Resolve spec paths relative to capsule
            capsule_dir = Path(capsule_path).parent
            resolved_specs = [
                str(capsule_dir / spec) if not Path(spec).is_absolute() else spec
                for spec in specs
            ]

            # Create engine with shared symbolic computation
            engine = CGMPEngine(
                meta_loader=MetaLoader(str(capsule_dir)),
                symbolic_engine=self._symbolic,
            )

            # Generate in parallel with semaphore for rate limiting
            semaphore = asyncio.Semaphore(self._max_parallel)

            async def generate_with_limit(spec_path: str) -> Dict[str, Any]:
                async with semaphore:
                    return await engine.generate_from_meta(spec_path)

            tasks = [generate_with_limit(spec) for spec in resolved_specs]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            processed_results = []
            success_count = 0
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed_results.append(
                        {
                            "spec": resolved_specs[i],
                            "success": False,
                            "error": str(result),
                        }
                    )
                else:
                    processed_results.append(result)
                    if result.get("success"):
                        success_count += 1

            # Update stats
            self._swarm_stats["capsules_loaded"] += 1
            self._swarm_stats["specs_processed"] += len(specs)
            self._swarm_stats["files_generated"] += sum(
                len(r.get("output_files", []))
                for r in processed_results
                if isinstance(r, dict) and r.get("success")
            )

            result = {
                "success": True,
                "capsule_path": capsule_path,
                "capsule_name": capsule.get("name", "unnamed"),
                "specs_total": len(specs),
                "specs_success": success_count,
                "results": processed_results,
                "generated_files": engine.get_generated_files(),
            }

            logger.info(
                "quantum_swarm_complete",
                capsule=capsule_path,
                specs_total=len(specs),
                specs_success=success_count,
            )

            return result

        except Exception as e:
            logger.error("quantum_swarm_failed", error=str(e))
            return {
                "success": False,
                "capsule_path": capsule_path,
                "error": str(e),
            }

    def _load_capsule(self, capsule_path: str) -> Dict[str, Any]:
        """
        Load a swarm capsule YAML file.

        Args:
            capsule_path: Path to capsule file

        Returns:
            Parsed capsule configuration
        """
        path = Path(capsule_path)

        if not path.exists():
            raise SwarmLoaderError(f"Capsule not found: {capsule_path}")

        with open(path, "r", encoding="utf-8") as f:
            capsule = yaml.safe_load(f)

        if not isinstance(capsule, dict):
            raise SwarmLoaderError("Invalid capsule format")

        logger.info(
            "capsule_loaded",
            path=capsule_path,
            specs_count=len(capsule.get("specs", [])),
        )

        return capsule

    async def _warmup_cache(self, expressions: List[str]) -> None:
        """
        Pre-compile common expressions to warm the cache.

        Args:
            expressions: List of expressions to pre-compile
        """
        if not expressions:
            return

        for expr in expressions:
            try:
                # Just compute a simple evaluation to cache the expression
                await self._symbolic.compute(
                    expression=expr,
                    variables={"x": 1.0},
                    backend="numpy",
                )
                self._swarm_stats["cache_warmups"] += 1
            except Exception as e:
                logger.warning("cache_warmup_failed", expression=expr, error=str(e))

        logger.info(
            "cache_warmup_complete",
            expressions_warmed=len(expressions),
        )

    def get_stats(self) -> Dict[str, Any]:
        """
        Get swarm loader statistics.

        Returns:
            Statistics dictionary
        """
        return self._swarm_stats.copy()


async def load_quantum_swarm(capsule_path: str) -> Dict[str, Any]:
    """
    Convenience function to load and execute a quantum swarm.

    Args:
        capsule_path: Path to swarm.yaml capsule

    Returns:
        Swarm execution results
    """
    loader = QuantumSwarmLoader()
    return await loader.load_quantum_swarm(capsule_path)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "ORC-INTE-030",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "agents.codegenagent.c_gmp_engine",
        "agents.codegenagent.meta_loader",
    ],
    "tags": [
        "async",
        "batch-processing",
        "caching",
        "config",
        "error-handling",
        "exception",
        "filesystem",
        "intelligence",
        "loader",
        "logging",
    ],
    "keywords": [
        "cache",
        "generate",
        "generation",
        "limit",
        "load",
        "loader",
        "orchestrator",
        "quantum",
    ],
    "business_value": "Provides quantum swarm loader components including SwarmLoaderError, QuantumSwarmLoader",
    "last_modified": "2026-01-17T23:51:17Z",
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
