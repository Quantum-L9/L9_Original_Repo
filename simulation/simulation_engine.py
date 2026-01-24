"""
L9 Simulation - Simulation Engine
=================================

Core engine for simulating IR graph execution.

Simulates:
- Action execution sequences
- Resource consumption
- Failure scenarios
- Timing and dependencies
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Simulation Engine",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "data_models",
    "module_name": "simulation_engine",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [
            "api.routes.simulation",
            "runtime.l_tools",
            "simulation.__init__",
            "simulation.outcome_evaluator",
            "tests.simulation.test_simulation_engine",
            "world_model.runtime",
        ],
    },
}
# ============================================================================

import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID, uuid4

import structlog

if TYPE_CHECKING:
    from memory.substrate_service import MemorySubstrateService

from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)

# Memory substrate packet emission (optional integration)
_memory_substrate: Optional["MemorySubstrateService"] = None


def set_memory_substrate(substrate: "MemorySubstrateService") -> None:
    """Set the memory substrate for packet emission."""
    global _memory_substrate
    _memory_substrate = substrate
    logger.info("SimulationEngine: Memory substrate attached")


class SimulationMode(str, Enum):
    """Simulation modes."""

    FAST = "fast"  # Quick heuristic simulation
    STANDARD = "standard"  # Normal simulation
    THOROUGH = "thorough"  # Deep simulation with more scenarios


@dataclass
class SimulationConfig:
    """Configuration for simulation."""

    mode: SimulationMode = SimulationMode.STANDARD
    max_steps: int = 100
    timeout_ms: int = 60000
    failure_probability: float = 0.1  # Base failure probability
    resource_constraints: dict[str, float] = field(default_factory=dict)
    random_seed: Optional[int] = None
    parallel_actions: bool = True
    collect_metrics: bool = True


@dataclass
class SimulationMetrics:
    """Metrics collected during simulation."""

    total_steps: int = 0
    successful_steps: int = 0
    failed_steps: int = 0
    total_duration_ms: int = 0
    resource_usage: dict[str, float] = field(default_factory=dict)
    bottlenecks: list[str] = field(default_factory=list)
    critical_path_length: int = 0
    parallelism_factor: float = 1.0


@dataclass
class SimulationStep:
    """A single step in simulation."""

    step_id: UUID = field(default_factory=uuid4)
    action_id: UUID = field(default_factory=uuid4)
    action_type: str = ""
    status: str = "pending"  # pending, running, completed, failed, skipped
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_ms: int = 0
    resource_used: dict[str, float] = field(default_factory=dict)
    error: Optional[str] = None
    dependencies_satisfied: bool = True


@dataclass
class SimulationRun:
    """Complete simulation run."""

    run_id: UUID = field(default_factory=uuid4)
    graph_id: UUID = field(default_factory=uuid4)
    config: SimulationConfig = field(default_factory=SimulationConfig)
    status: str = "created"  # created, running, completed, failed
    steps: list[SimulationStep] = field(default_factory=list)
    metrics: SimulationMetrics = field(default_factory=SimulationMetrics)
    failure_modes: list[str] = field(default_factory=list)
    score: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": str(self.run_id),
            "graph_id": str(self.graph_id),
            "status": self.status,
            "score": self.score,
            "total_steps": len(self.steps),
            "successful_steps": sum(1 for s in self.steps if s.status == "completed"),
            "failed_steps": sum(1 for s in self.steps if s.status == "failed"),
            "failure_modes": self.failure_modes,
            "duration_ms": self.metrics.total_duration_ms,
        }


class SimulationEngine:
    """
    Core simulation engine for IR graph evaluation.

    Simulates IR graph execution to:
    - Estimate feasibility
    - Identify failure modes
    - Calculate resource requirements
    - Score candidates
    """

    def __init__(self, config: Optional[SimulationConfig] = None):
        """
        Initialize the simulation engine.

        Args:
            config: Simulation configuration
        """
        self._config = config or SimulationConfig()
        self._runs: dict[UUID, SimulationRun] = {}
        self._random = random.Random(self._config.random_seed)

        logger.info(f"SimulationEngine initialized (mode={self._config.mode})")

    # ==========================================================================
    # Main Simulation
    # ==========================================================================

    async def simulate(
        self,
        graph_data: dict[str, Any],
        scenario: Optional[dict[str, Any]] = None,
    ) -> SimulationRun:
        """
        Simulate IR graph execution.

        Args:
            graph_data: IR graph data (from IRGenerator.to_dict())
            scenario: Optional scenario parameters

        Returns:
            SimulationRun with results
        """
        run = SimulationRun(
            graph_id=UUID(graph_data.get("graph_id", str(uuid4()))),
            config=self._config,
            status="running",
            started_at=datetime.utcnow(),
        )

        self._runs[run.run_id] = run

        logger.info(f"Starting simulation {run.run_id} for graph {run.graph_id}")

        try:
            # Extract actions from graph
            actions = graph_data.get("actions", [])

            if not actions:
                run.status = "completed"
                run.score = 0.5  # Neutral score for empty graph
                run.completed_at = datetime.utcnow()
                return run

            # Build dependency graph
            dep_graph = self._build_dependency_graph(actions)

            # Simulate execution
            if self._config.mode == SimulationMode.FAST:
                await self._simulate_fast(run, actions, dep_graph, scenario)
            elif self._config.mode == SimulationMode.THOROUGH:
                await self._simulate_thorough(run, actions, dep_graph, scenario)
            else:
                await self._simulate_standard(run, actions, dep_graph, scenario)

            # Calculate final score
            run.score = self._calculate_score(run)
            run.status = "completed"

        except Exception as e:
            logger.error(f"Simulation failed: {e}")
            run.status = "failed"
            run.failure_modes.append(str(e))
            run.score = 0.0

        run.completed_at = datetime.utcnow()
        run.metrics.total_duration_ms = int(
            (run.completed_at - run.started_at).total_seconds() * 1000
        )

        logger.info(f"Simulation {run.run_id} completed: score={run.score:.2f}")

        # Emit packet to memory substrate if available
        await self._emit_simulation_packet(run)

        return run

    async def _emit_simulation_packet(self, run: SimulationRun) -> None:
        """
        Emit a PacketEnvelope to memory substrate with simulation results.

        Enables audit trail, memory retrieval, and world model ingestion.
        """
        global _memory_substrate

        if _memory_substrate is None:
            return  # No substrate attached, skip emission

        try:
            from core.schemas import (PacketConfidence, PacketEnvelope,
                                      PacketProvenance)

            packet = PacketEnvelope(
                packet_type="simulation_result",
                payload={
                    "run_id": str(run.run_id),
                    "graph_id": str(run.graph_id),
                    "status": run.status,
                    "score": run.score,
                    "metrics": {
                        "total_steps": run.metrics.total_steps,
                        "successful_steps": run.metrics.successful_steps,
                        "failed_steps": run.metrics.failed_steps,
                        "duration_ms": run.metrics.total_duration_ms,
                        "parallelism_factor": run.metrics.parallelism_factor,
                        "critical_path_length": run.metrics.critical_path_length,
                        "bottlenecks": run.metrics.bottlenecks,
                    },
                    "failure_modes": run.failure_modes,
                    "started_at": (
                        run.started_at.isoformat() if run.started_at else None
                    ),
                    "completed_at": (
                        run.completed_at.isoformat() if run.completed_at else None
                    ),
                },
                provenance=PacketProvenance(
                    source="simulation_engine",
                    tool="SimulationEngine.simulate",
                ),
                confidence=PacketConfidence(
                    score=run.score,
                    rationale=f"Simulation {run.status} with {run.metrics.successful_steps}/{run.metrics.total_steps} steps",
                ),
            )

            await _memory_substrate.ingest_packet(packet)
            logger.debug(f"Simulation packet emitted: run_id={run.run_id}")

        except ImportError:
            logger.debug(
                "Memory substrate models not available, skipping packet emission"
            )
        except Exception as e:
            # Non-fatal: log and continue
            logger.warning(f"Failed to emit simulation packet: {e}")

    def _build_dependency_graph(
        self,
        actions: list[dict[str, Any]],
    ) -> dict[str, list[str]]:
        """Build dependency graph from actions."""
        dep_graph: dict[str, list[str]] = {}

        for action in actions:
            action_id = action.get("node_id", "")
            dependencies = action.get("depends_on", [])
            dep_graph[action_id] = dependencies

        return dep_graph

    @must_stay_async("callers use await")
    async def _simulate_fast(
        self,
        run: SimulationRun,
        actions: list[dict[str, Any]],
        dep_graph: dict[str, list[str]],
        scenario: Optional[dict[str, Any]],
    ) -> None:
        """Fast heuristic simulation."""
        for action in actions:
            step = SimulationStep(
                action_id=UUID(action.get("node_id", str(uuid4()))),
                action_type=action.get("action_type", "unknown"),
            )

            # Simple success/failure based on action type risk
            risk = self._estimate_action_risk(action)
            if self._random.random() < risk:
                step.status = "failed"
                step.error = f"Simulated failure for {action.get('action_type')}"
                run.failure_modes.append(step.error)
            else:
                step.status = "completed"

            step.duration_ms = self._estimate_duration(action)
            run.steps.append(step)

        run.metrics.total_steps = len(run.steps)
        run.metrics.successful_steps = sum(
            1 for s in run.steps if s.status == "completed"
        )
        run.metrics.failed_steps = sum(1 for s in run.steps if s.status == "failed")

    async def _simulate_standard(
        self,
        run: SimulationRun,
        actions: list[dict[str, Any]],
        dep_graph: dict[str, list[str]],
        scenario: Optional[dict[str, Any]],
    ) -> None:
        """Standard simulation with dependency tracking."""
        completed: set[str] = set()
        action_map = {a.get("node_id", ""): a for a in actions}

        # Topological order execution
        remaining = list(action_map.keys())

        while remaining:
            # Find actions whose dependencies are satisfied
            ready = [
                aid
                for aid in remaining
                if all(d in completed for d in dep_graph.get(aid, []))
            ]

            if not ready:
                # Deadlock detected
                run.failure_modes.append("Dependency deadlock detected")
                break

            # Execute ready actions
            for action_id in ready:
                action = action_map[action_id]
                step = await self._simulate_action(action, scenario)
                run.steps.append(step)

                if step.status == "completed":
                    completed.add(action_id)
                else:
                    run.failure_modes.append(f"Action {action_id} failed: {step.error}")

                remaining.remove(action_id)

        # Calculate metrics
        run.metrics.total_steps = len(run.steps)
        run.metrics.successful_steps = len(completed)
        run.metrics.failed_steps = (
            run.metrics.total_steps - run.metrics.successful_steps
        )
        run.metrics.critical_path_length = self._calculate_critical_path(
            actions, dep_graph
        )

    async def _simulate_thorough(
        self,
        run: SimulationRun,
        actions: list[dict[str, Any]],
        dep_graph: dict[str, list[str]],
        scenario: Optional[dict[str, Any]],
    ) -> None:
        """Thorough simulation with multiple scenarios."""
        # Run standard simulation first
        await self._simulate_standard(run, actions, dep_graph, scenario)

        # Additional analysis
        run.metrics.bottlenecks = self._identify_bottlenecks(run.steps)
        run.metrics.parallelism_factor = self._calculate_parallelism(actions, dep_graph)

        # Stress test with increased failure probability
        original_prob = self._config.failure_probability
        self._config.failure_probability = min(0.5, original_prob * 2)

        # Run additional stress scenarios
        stress_failures: list[str] = []
        for _ in range(3):
            stress_run = SimulationRun(graph_id=run.graph_id, config=self._config)
            await self._simulate_standard(stress_run, actions, dep_graph, scenario)
            stress_failures.extend(stress_run.failure_modes)

        # Add unique stress failures
        for failure in set(stress_failures):
            if failure not in run.failure_modes:
                run.failure_modes.append(f"[stress] {failure}")

        self._config.failure_probability = original_prob

    async def _simulate_action(
        self,
        action: dict[str, Any],
        scenario: Optional[dict[str, Any]],
    ) -> SimulationStep:
        """Simulate a single action."""
        step = SimulationStep(
            action_id=UUID(action.get("node_id", str(uuid4()))),
            action_type=action.get("action_type", "unknown"),
            start_time=datetime.utcnow(),
        )

        # Estimate duration
        duration = self._estimate_duration(action)

        # Simulate execution time
        await asyncio.sleep(duration / 10000)  # Scaled down for simulation

        # Determine success/failure
        risk = self._estimate_action_risk(action)
        scenario_risk = (scenario or {}).get("risk_multiplier", 1.0)

        if self._random.random() < risk * scenario_risk:
            step.status = "failed"
            step.error = self._generate_failure_reason(action)
        else:
            step.status = "completed"

        step.end_time = datetime.utcnow()
        step.duration_ms = duration
        step.resource_used = self._estimate_resources(action)

        return step

    # ==========================================================================
    # Estimation Methods
    # ==========================================================================

    def _estimate_action_risk(self, action: dict[str, Any]) -> float:
        """Estimate failure risk for an action."""
        base_risk = self._config.failure_probability

        # Risk multipliers by action type
        risk_multipliers = {
            "code_write": 1.2,
            "code_modify": 1.5,
            "file_delete": 1.3,
            "api_call": 2.0,
            "simulation": 1.5,
            "code_read": 0.5,
            "validation": 0.8,
        }

        action_type = action.get("action_type", "unknown")
        multiplier = risk_multipliers.get(action_type, 1.0)

        # Higher risk for complex actions
        params = action.get("parameters", {})
        if len(params) > 5:
            multiplier *= 1.2

        return min(0.9, base_risk * multiplier)

    def _estimate_duration(self, action: dict[str, Any]) -> int:
        """Estimate action duration in milliseconds."""
        # Use estimated duration if provided
        if action.get("estimated_duration_ms"):
            return action["estimated_duration_ms"]

        # Default durations by type
        default_durations = {
            "code_write": 5000,
            "code_read": 1000,
            "code_modify": 3000,
            "file_create": 2000,
            "file_delete": 500,
            "api_call": 2000,
            "reasoning": 10000,
            "validation": 1500,
            "simulation": 5000,
        }

        action_type = action.get("action_type", "unknown")
        return default_durations.get(action_type, 2000)

    def _estimate_resources(self, action: dict[str, Any]) -> dict[str, float]:
        """Estimate resource usage for an action."""
        action_type = action.get("action_type", "unknown")

        # Base resource estimates
        resources = {
            "cpu": 0.1,
            "memory_mb": 50,
            "io_ops": 10,
        }

        if action_type in ("code_write", "code_modify"):
            resources["io_ops"] = 50
            resources["memory_mb"] = 100
        elif action_type == "reasoning":
            resources["cpu"] = 0.5
            resources["memory_mb"] = 200
        elif action_type == "api_call":
            resources["network_kb"] = 100

        return resources

    def _generate_failure_reason(self, action: dict[str, Any]) -> str:
        """Generate a plausible failure reason."""
        action_type = action.get("action_type", "unknown")

        failure_reasons = {
            "code_write": ["File permission denied", "Disk full", "Invalid path"],
            "code_modify": ["File locked", "Merge conflict", "Syntax error introduced"],
            "api_call": ["Network timeout", "Rate limited", "Service unavailable"],
            "file_delete": ["File not found", "Permission denied"],
            "validation": ["Schema validation failed", "Constraint violated"],
        }

        reasons = failure_reasons.get(action_type, ["Unknown error"])
        return self._random.choice(reasons)

    # ==========================================================================
    # Analysis Methods
    # ==========================================================================

    def _calculate_score(self, run: SimulationRun) -> float:
        """Calculate overall simulation score."""
        if not run.steps:
            return 0.5

        # Base score from success rate
        success_rate = run.metrics.successful_steps / max(1, run.metrics.total_steps)

        # Penalty for failure modes
        failure_penalty = min(0.3, len(run.failure_modes) * 0.05)

        # Bonus for efficient execution
        efficiency_bonus = 0.0
        if run.metrics.parallelism_factor > 1.5:
            efficiency_bonus = 0.1

        score = success_rate - failure_penalty + efficiency_bonus
        return max(0.0, min(1.0, score))

    def _calculate_critical_path(
        self,
        actions: list[dict[str, Any]],
        dep_graph: dict[str, list[str]],
    ) -> int:
        """Calculate critical path length."""
        if not actions:
            return 0

        # Simple longest path calculation
        action_ids = [a.get("node_id", "") for a in actions]

        def path_length(action_id: str, memo: dict[str, int]) -> int:
            if action_id in memo:
                return memo[action_id]

            deps = dep_graph.get(action_id, [])
            if not deps:
                memo[action_id] = 1
            else:
                memo[action_id] = 1 + max(
                    path_length(d, memo) for d in deps if d in action_ids
                )
            return memo[action_id]

        memo: dict[str, int] = {}
        return max(path_length(aid, memo) for aid in action_ids)

    def _calculate_parallelism(
        self,
        actions: list[dict[str, Any]],
        dep_graph: dict[str, list[str]],
    ) -> float:
        """Calculate parallelism factor."""
        total_actions = len(actions)
        if total_actions == 0:
            return 1.0

        critical_path = self._calculate_critical_path(actions, dep_graph)
        if critical_path == 0:
            return 1.0

        return total_actions / critical_path

    def _identify_bottlenecks(self, steps: list[SimulationStep]) -> list[str]:
        """Identify bottleneck actions."""
        bottlenecks = []

        # Find slow steps
        if steps:
            avg_duration = sum(s.duration_ms for s in steps) / len(steps)
            for step in steps:
                if step.duration_ms > avg_duration * 2:
                    bottlenecks.append(f"{step.action_type}: {step.duration_ms}ms")

        return bottlenecks

    # ==========================================================================
    # Run Management
    # ==========================================================================

    def get_run(self, run_id: UUID) -> Optional[SimulationRun]:
        """Get a simulation run by ID."""
        return self._runs.get(run_id)

    def get_runs_for_graph(self, graph_id: UUID) -> list[SimulationRun]:
        """Get all runs for a graph."""
        return [r for r in self._runs.values() if r.graph_id == graph_id]

    def clear_runs(self) -> None:
        """Clear all stored runs."""
        self._runs.clear()


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SIM-LEAR-002",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators", "core.schemas", "memory.substrate_service"],
    "tags": [
        "api",
        "async",
        "authorization",
        "data-models",
        "dataclass",
        "debugging",
        "engine",
        "learning",
        "logging",
        "metrics",
    ],
    "keywords": [
        "clear",
        "engine",
        "execution",
        "graph",
        "length",
        "memory",
        "metrics",
        "mode",
    ],
    "business_value": "Provides simulation engine components including SimulationMode, SimulationConfig, SimulationMetrics",
    "last_modified": "2026-01-17T23:47:56Z",
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
