"""
L9 IR Engine - Simulation Router
================================

Routes IR candidates to the simulation engine for evaluation.

Responsibilities:
- Select IR candidates for simulation
- Prepare simulation scenarios
- Route to simulation engine
- Collect and rank results
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "Simulation Router",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "intelligence",
    "domain": "ir_compilation",
    "module_name": "simulation_router",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "ir_engine.__init__",
            "orchestration.orchestrator_kernel",
            "orchestration.unified_controller",
            "tests.ir_engine.test_ir_simulation_router_integration",
        ],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import structlog

if TYPE_CHECKING:
    from ir_engine.ir_schema import IRGraph

logger = structlog.get_logger(__name__)


@dataclass
class SimulationRequest:
    """Request to simulate an IR graph."""

    request_id: UUID = field(default_factory=uuid4)
    graph_id: UUID = field(default_factory=uuid4)
    graph_snapshot: dict[str, Any] = field(default_factory=dict)
    scenario_type: str = "default"
    parameters: dict[str, Any] = field(default_factory=dict)
    priority: int = 5  # 1-10, higher = more priority
    timeout_ms: int = 30000
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class SimulationResult:
    """Result from simulation engine."""

    request_id: UUID
    graph_id: UUID
    success: bool
    score: float = 0.0  # 0.0 to 1.0
    metrics: dict[str, Any] = field(default_factory=dict)
    failure_modes: list[str] = field(default_factory=list)
    execution_time_ms: int = 0
    completed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary representation of the simulation result, including identifiers, success status, score, metrics, and failure modes for further processing or logging."""
        return {
            "request_id": str(self.request_id),
            "graph_id": str(self.graph_id),
            "success": self.success,
            "score": self.score,
            "metrics": self.metrics,
            "failure_modes": self.failure_modes,
            "execution_time_ms": self.execution_time_ms,
            "completed_at": self.completed_at.isoformat(),
        }


@dataclass
class RankedCandidate:
    """A ranked IR candidate after simulation."""

    graph: IRGraph
    result: SimulationResult
    rank: int
    selection_reason: str


class SimulationRouter:
    """
    Routes IR graphs to simulation engine and manages results.

    Supports:
    - Single graph simulation
    - Multi-candidate comparison
    - Scenario-based simulation
    - Result ranking
    """

    def __init__(
        self,
        simulation_engine: Any | None = None,
        default_timeout_ms: int = 30000,
        max_candidates: int = 5,
    ):
        """
        Initialize the simulation router.

        Args:
            simulation_engine: Optional simulation engine instance
            default_timeout_ms: Default simulation timeout
            max_candidates: Maximum candidates to simulate
        """
        self._engine = simulation_engine
        self._default_timeout_ms = default_timeout_ms
        self._max_candidates = max_candidates
        self._pending_requests: dict[UUID, SimulationRequest] = {}
        self._results: dict[UUID, SimulationResult] = {}

        logger.info(f"SimulationRouter initialized (max_candidates={max_candidates})")

    def set_engine(self, engine: Any) -> None:
        """Set the simulation engine."""
        self._engine = engine
        logger.info("Simulation engine attached")

    # ==========================================================================
    # Request Creation
    # ==========================================================================

    def create_request(
        self,
        graph: IRGraph,
        scenario_type: str = "default",
        parameters: dict[str, Any] | None = None,
        priority: int = 5,
        timeout_ms: int | None = None,
    ) -> SimulationRequest:
        """
        Create a simulation request for a graph.

        Args:
            graph: IR graph to simulate
            scenario_type: Type of simulation scenario
            parameters: Simulation parameters
            priority: Request priority (1-10)
            timeout_ms: Timeout override

        Returns:
            SimulationRequest ready for submission
        """
        from ir_engine.ir_generator import IRGenerator

        generator = IRGenerator(include_metadata=False)

        request = SimulationRequest(
            graph_id=graph.graph_id,
            graph_snapshot=generator.to_dict(graph),
            scenario_type=scenario_type,
            parameters=parameters or {},
            priority=max(1, min(10, priority)),
            timeout_ms=timeout_ms or self._default_timeout_ms,
        )

        self._pending_requests[request.request_id] = request
        logger.debug(
            f"Created simulation request {request.request_id} for graph {graph.graph_id}"
        )

        return request

    # ==========================================================================
    # Routing
    # ==========================================================================

    @must_stay_async("callers use await")
    async def route(self, request: SimulationRequest) -> SimulationResult:
        """
        Route a request to the simulation engine.

        Args:
            request: Simulation request

        Returns:
            SimulationResult
        """
        logger.info(f"Routing simulation request {request.request_id}")

        start_time = datetime.now(UTC)

        try:
            if self._engine is None:
                # No engine attached - return stub result
                result = self._stub_simulation(request)
            else:
                # Route to actual engine
                result = await self._engine.simulate(request)

            # Calculate execution time
            result.execution_time_ms = int(
                (datetime.now(UTC) - start_time).total_seconds() * 1000
            )

        except Exception as e:
            logger.error(f"Simulation failed: {e}")
            result = SimulationResult(
                request_id=request.request_id,
                graph_id=request.graph_id,
                success=False,
                failure_modes=[str(e)],
            )

        # Store result
        self._results[request.request_id] = result

        # Clean up pending
        if request.request_id in self._pending_requests:
            del self._pending_requests[request.request_id]

        logger.info(
            f"Simulation complete: request={request.request_id}, "
            f"score={result.score:.2f}, success={result.success}"
        )

        return result

    def _stub_simulation(self, request: SimulationRequest) -> SimulationResult:
        """
        Stub simulation when no engine is attached.

        Provides heuristic scoring based on graph structure.
        """
        snapshot = request.graph_snapshot

        # Calculate heuristic score
        intent_count = len(snapshot.get("intents", []))
        action_count = len(snapshot.get("actions", []))
        constraint_count = len(snapshot.get("constraints", []))

        # Score based on completeness
        completeness = 0.0
        if intent_count > 0:
            completeness += 0.3
        if action_count > 0:
            completeness += 0.4
        if constraint_count > 0:
            completeness += 0.2

        # Penalize if no actions for intents
        if intent_count > 0 and action_count == 0:
            completeness -= 0.2

        # Bonus for balanced constraint ratio
        if intent_count > 0:
            constraint_ratio = constraint_count / intent_count
            if 0.5 <= constraint_ratio <= 2.0:
                completeness += 0.1

        return SimulationResult(
            request_id=request.request_id,
            graph_id=request.graph_id,
            success=True,
            score=max(0.0, min(1.0, completeness)),
            metrics={
                "intent_count": intent_count,
                "action_count": action_count,
                "constraint_count": constraint_count,
                "stub_simulation": True,
            },
            failure_modes=[],
        )

    # ==========================================================================
    # Multi-Candidate Operations
    # ==========================================================================

    @must_stay_async("callers use await")
    async def simulate_candidates(
        self,
        candidates: list[IRGraph],
        scenario_type: str = "default",
        parameters: dict[str, Any] | None = None,
    ) -> list[RankedCandidate]:
        """
        Simulate multiple candidates and return ranked results.

        Args:
            candidates: List of IR graphs to compare
            scenario_type: Simulation scenario type
            parameters: Simulation parameters

        Returns:
            List of RankedCandidate sorted by score (best first)
        """
        if len(candidates) > self._max_candidates:
            logger.warning(
                f"Too many candidates ({len(candidates)}), "
                f"truncating to {self._max_candidates}"
            )
            candidates = candidates[: self._max_candidates]

        # Create and route requests
        results: list[tuple[IRGraph, SimulationResult]] = []

        for graph in candidates:
            request = self.create_request(
                graph=graph,
                scenario_type=scenario_type,
                parameters=parameters,
            )
            result = await self.route(request)
            results.append((graph, result))

        # Sort by score
        results.sort(key=lambda x: x[1].score, reverse=True)

        # Build ranked candidates
        ranked: list[RankedCandidate] = []
        for rank, (graph, result) in enumerate(results, 1):
            selection_reason = self._determine_selection_reason(result, rank)
            ranked.append(
                RankedCandidate(
                    graph=graph,
                    result=result,
                    rank=rank,
                    selection_reason=selection_reason,
                )
            )

        return ranked

    def _determine_selection_reason(
        self,
        result: SimulationResult,
        rank: int,
    ) -> str:
        """Determine why a candidate was ranked at this position."""
        if rank == 1:
            return f"Highest score: {result.score:.2f}"
        if result.failure_modes:
            return f"Has failure modes: {', '.join(result.failure_modes[:2])}"
        return f"Score: {result.score:.2f}"

    async def select_best(
        self,
        candidates: list[IRGraph],
        min_score: float = 0.5,
    ) -> IRGraph | None:
        """
        Select the best candidate from simulation results.

        Args:
            candidates: List of IR graphs
            min_score: Minimum acceptable score

        Returns:
            Best IRGraph or None if none meet threshold
        """
        ranked = await self.simulate_candidates(candidates)

        if ranked and ranked[0].result.score >= min_score:
            best = ranked[0]
            logger.info(
                f"Selected best candidate: {best.graph.graph_id} "
                f"(score={best.result.score:.2f})"
            )
            return best.graph

        logger.warning(f"No candidate met minimum score threshold ({min_score})")
        return None

    # ==========================================================================
    # Status and Results
    # ==========================================================================

    def get_pending_count(self) -> int:
        """Get count of pending requests."""
        return len(self._pending_requests)

    def get_result(self, request_id: UUID) -> SimulationResult | None:
        """Get a simulation result by request ID."""
        return self._results.get(request_id)

    def get_results_for_graph(self, graph_id: UUID) -> list[SimulationResult]:
        """Get all results for a specific graph."""
        return [r for r in self._results.values() if r.graph_id == graph_id]

    def clear_results(self) -> None:
        """Clear all stored results."""
        self._results.clear()
        logger.info("Cleared simulation results")


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "IR_-INTE-012",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "dataclass",
        "debugging",
        "intelligence",
        "ir-compilation",
        "logging",
        "metrics",
        "routing",
    ],
    "keywords": [
        "best",
        "candidate",
        "candidates",
        "clear",
        "count",
        "create",
        "engine",
        "graph",
    ],
    "business_value": "Provides simulation router components including SimulationRequest, SimulationResult, RankedCandidate",
    "last_modified": "2026-01-07T13:35:57Z",
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
