"""
L9 Master Architecture Orchestrator
====================================

Orchestrates multiple subsystems using the same pattern pipeline,
respecting dependencies and parallelization rules.

Usage:
    from orchestrators.pattern import MasterOrchestrator

    master = MasterOrchestrator(
        master_config_path="config/subsystems/master.yaml",
        pattern_path="config/patterns/pipeline_v1.yaml",
    )
    result = await master.execute_all(user_prompts=["Build feature X"])

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Master Architecture Orchestrator",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-20T00:30:00Z",
    "updated_at": "2026-01-20T00:30:00Z",
    "layer": "intelligence",
    "domain": "orchestration",
    "module_name": "master_orchestrator",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": ["orchestrators.pattern.__init__"],
    },
}
# ============================================================================

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Optional
from uuid import uuid4

import structlog
import yaml
from pydantic import BaseModel, Field

from orchestrators.pattern.orchestrator import PatternOrchestrator
from orchestrators.pattern.cell_adapter import CellAgentAdapter
from orchestrators.pattern.interface import PipelineResult

logger = structlog.get_logger(__name__)


# =============================================================================
# Models
# =============================================================================


class SubsystemEntry(BaseModel):
    """Entry for a subsystem in master config."""

    config_path: str
    enabled: bool = True
    priority: str = "medium"
    max_parallel: int = 1
    description: str = ""


class MasterConfig(BaseModel):
    """Master configuration for all subsystems."""

    subsystems: dict[str, SubsystemEntry] = Field(default_factory=dict)
    orchestration: dict[str, Any] = Field(default_factory=dict)


class MasterExecutionResult(BaseModel):
    """Result of executing all subsystems."""

    trace_id: str
    status: str  # "success" | "partial" | "failure"
    subsystems_executed: int
    subsystems_failed: int
    results: dict[str, Optional[dict[str, Any]]] = Field(default_factory=dict)
    total_duration_ms: float = 0.0
    started_at: datetime
    completed_at: Optional[datetime] = None
    errors: list[str] = Field(default_factory=list)


# =============================================================================
# Master Orchestrator
# =============================================================================


class MasterOrchestrator:
    """
    Orchestrates multiple subsystems using the same pattern pipeline.

    Execution Strategy:
    1. Load master.yaml to get all enabled subsystems
    2. Execute code_mutation first (if enabled) - blocks other mutations
    3. Execute remaining subsystems in parallel (respecting max_parallel)
    4. Aggregate results and return

    Example:
        master = MasterOrchestrator("config/subsystems/master.yaml")
        result = await master.execute_all(["Build user auth"])
    """

    def __init__(
        self,
        master_config_path: str = "config/subsystems/master.yaml",
        pattern_path: Optional[str] = None,
        agent: Optional[CellAgentAdapter] = None,
    ):
        """
        Initialize the master orchestrator.

        Args:
            master_config_path: Path to master.yaml
            pattern_path: Override pattern path (uses master config default if not set)
            agent: Agent adapter for node execution
        """
        self._master_config_path = Path(master_config_path)
        self._master_config = self._load_master_config()

        # Get pattern path from config or override
        self._pattern_path = pattern_path or self._master_config.orchestration.get(
            "default_pattern", "config/patterns/pipeline_v1.yaml"
        )

        self._agent = agent or CellAgentAdapter()

        logger.info(
            "MasterOrchestrator initialized",
            subsystems=list(self._master_config.subsystems.keys()),
            pattern=self._pattern_path,
        )

    def _load_master_config(self) -> MasterConfig:
        """Load and parse master configuration."""
        if not self._master_config_path.exists():
            raise FileNotFoundError(
                f"Master config not found: {self._master_config_path}"
            )

        with open(self._master_config_path) as f:
            data = yaml.safe_load(f)

        # Parse subsystems into SubsystemEntry models
        subsystems = {}
        for name, cfg in data.get("subsystems", {}).items():
            subsystems[name] = SubsystemEntry(**cfg)

        return MasterConfig(
            subsystems=subsystems,
            orchestration=data.get("orchestration", {}),
        )

    def get_enabled_subsystems(self) -> list[str]:
        """Get list of enabled subsystem names."""
        return [
            name for name, cfg in self._master_config.subsystems.items() if cfg.enabled
        ]

    def get_subsystem_config(self, name: str) -> Optional[SubsystemEntry]:
        """Get configuration for a specific subsystem."""
        return self._master_config.subsystems.get(name)

    async def execute_all(
        self,
        user_prompts: Optional[list[str]] = None,
        context: Optional[dict[str, Any]] = None,
        dry_run: bool = False,
        subsystems: Optional[list[str]] = None,
    ) -> MasterExecutionResult:
        """
        Execute pipelines for all enabled subsystems.

        Execution order:
        1. code_mutation (sequential, blocks others)
        2. auth (sequential, critical)
        3. tools, memory_retrieval (parallel)

        Args:
            user_prompts: User prompts to process
            context: Additional context
            dry_run: If True, simulate without agent calls
            subsystems: Specific subsystems to run (defaults to all enabled)

        Returns:
            MasterExecutionResult with aggregated results
        """
        trace_id = str(uuid4())
        started_at = datetime.now(timezone.utc)
        start_time = perf_counter()

        # Determine which subsystems to run
        target_subsystems = subsystems or self.get_enabled_subsystems()

        logger.info(
            "Starting master execution",
            trace_id=trace_id,
            subsystems=target_subsystems,
            dry_run=dry_run,
        )

        results: dict[str, Optional[dict[str, Any]]] = {}
        errors: list[str] = []

        # Phase 1: Execute code_mutation first (sequential, blocks others)
        if "code_mutation" in target_subsystems:
            logger.info("Phase 1: Executing code_mutation (sequential)")
            result = await self._execute_subsystem(
                "code_mutation",
                user_prompts=user_prompts,
                context=context,
                dry_run=dry_run,
                trace_id=trace_id,
            )
            results["code_mutation"] = result
            if result and result.get("status") == "failure":
                errors.append(f"code_mutation failed: {result.get('error')}")
                # Don't block others on code_mutation failure - continue

        # Phase 2: Execute critical subsystems (auth - sequential)
        critical_subsystems = [s for s in target_subsystems if s == "auth"]
        for subsystem in critical_subsystems:
            logger.info(f"Phase 2: Executing {subsystem} (sequential, critical)")
            result = await self._execute_subsystem(
                subsystem,
                user_prompts=user_prompts,
                context=context,
                dry_run=dry_run,
                trace_id=trace_id,
            )
            results[subsystem] = result
            if result and result.get("status") == "failure":
                errors.append(f"{subsystem} failed: {result.get('error')}")

        # Phase 3: Execute remaining subsystems in parallel
        parallel_subsystems = [
            s
            for s in target_subsystems
            if s not in ("code_mutation", "auth") and s not in results
        ]

        if parallel_subsystems:
            logger.info(
                f"Phase 3: Executing {len(parallel_subsystems)} subsystems in parallel",
                subsystems=parallel_subsystems,
            )

            parallel_tasks = [
                self._execute_subsystem(
                    subsystem,
                    user_prompts=user_prompts,
                    context=context,
                    dry_run=dry_run,
                    trace_id=trace_id,
                )
                for subsystem in parallel_subsystems
            ]

            parallel_results = await asyncio.gather(
                *parallel_tasks, return_exceptions=True
            )

            for subsystem, result in zip(parallel_subsystems, parallel_results):
                if isinstance(result, Exception):
                    errors.append(f"{subsystem} failed: {str(result)}")
                    results[subsystem] = {"status": "failure", "error": str(result)}
                else:
                    results[subsystem] = result
                    if result and result.get("status") == "failure":
                        errors.append(f"{subsystem} failed: {result.get('error')}")

        # Calculate final status
        completed_at = datetime.now(timezone.utc)
        total_duration_ms = (perf_counter() - start_time) * 1000

        successful = sum(
            1 for r in results.values() if r and r.get("status") == "success"
        )
        failed = sum(1 for r in results.values() if r and r.get("status") == "failure")

        if failed == 0:
            status = "success"
        elif successful > 0:
            status = "partial"
        else:
            status = "failure"

        logger.info(
            "Master execution complete",
            trace_id=trace_id,
            status=status,
            successful=successful,
            failed=failed,
            duration_ms=total_duration_ms,
        )

        return MasterExecutionResult(
            trace_id=trace_id,
            status=status,
            subsystems_executed=len(results),
            subsystems_failed=failed,
            results=results,
            total_duration_ms=total_duration_ms,
            started_at=started_at,
            completed_at=completed_at,
            errors=errors,
        )

    async def _execute_subsystem(
        self,
        subsystem_name: str,
        user_prompts: Optional[list[str]] = None,
        context: Optional[dict[str, Any]] = None,
        dry_run: bool = False,
        trace_id: str = "",
    ) -> Optional[dict[str, Any]]:
        """
        Execute the pipeline for a single subsystem.

        Args:
            subsystem_name: Name of the subsystem
            user_prompts: User prompts
            context: Execution context
            dry_run: Simulation mode
            trace_id: Parent trace ID

        Returns:
            Pipeline result as dictionary
        """
        subsystem_entry = self._master_config.subsystems.get(subsystem_name)
        if not subsystem_entry:
            logger.warning(f"Subsystem not found: {subsystem_name}")
            return None

        if not subsystem_entry.enabled:
            logger.info(f"Subsystem disabled: {subsystem_name}")
            return {"status": "skipped", "reason": "disabled"}

        try:
            orchestrator = PatternOrchestrator(
                pattern_path=self._pattern_path,
                subsystem_config_path=subsystem_entry.config_path,
                agent=self._agent,
            )

            result: PipelineResult = await orchestrator.execute(
                user_prompts=user_prompts,
                context={**(context or {}), "master_trace_id": trace_id},
                dry_run=dry_run,
            )

            return {
                "status": result.status.value,
                "trace_id": str(result.trace_id),
                "nodes_completed": result.nodes_completed,
                "total_duration_ms": result.total_duration_ms,
                "error": result.error,
            }

        except Exception as e:
            logger.error(
                f"Subsystem execution failed: {subsystem_name}",
                error=str(e),
            )
            return {"status": "failure", "error": str(e)}

    async def execute_subsystem(
        self,
        subsystem_name: str,
        user_prompts: Optional[list[str]] = None,
        context: Optional[dict[str, Any]] = None,
        dry_run: bool = False,
    ) -> Optional[dict[str, Any]]:
        """
        Execute the pipeline for a single named subsystem.

        Public method for running individual subsystems.

        Args:
            subsystem_name: Name of the subsystem to execute
            user_prompts: User prompts to process
            context: Additional context
            dry_run: If True, simulate without agent calls

        Returns:
            Pipeline result as dictionary
        """
        trace_id = str(uuid4())
        return await self._execute_subsystem(
            subsystem_name,
            user_prompts=user_prompts,
            context=context,
            dry_run=dry_run,
            trace_id=trace_id,
        )


# =============================================================================
# Factory Function
# =============================================================================


def create_master_orchestrator(
    master_config_path: str = "config/subsystems/master.yaml",
    pattern_path: Optional[str] = None,
) -> MasterOrchestrator:
    """
    Factory function to create a MasterOrchestrator.

    Args:
        master_config_path: Path to master.yaml
        pattern_path: Override pattern path

    Returns:
        Configured MasterOrchestrator instance
    """
    return MasterOrchestrator(
        master_config_path=master_config_path,
        pattern_path=pattern_path,
    )


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "ORC-INTE-027",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "orchestrators.pattern.orchestrator",
        "orchestrators.pattern.cell_adapter",
    ],
    "tags": [
        "async",
        "config",
        "intelligence",
        "logging",
        "orchestration",
        "parallel",
        "subsystem",
    ],
    "keywords": [
        "execute",
        "master",
        "orchestrator",
        "parallel",
        "subsystem",
    ],
    "business_value": "Enables multi-subsystem parallel execution with dependency ordering",
    "last_modified": "2026-01-20T00:30:00Z",
    "modified_by": "GMP-106",
    "change_summary": "Initial implementation of MasterArchitectureOrchestrator",
}
# ============================================================================
