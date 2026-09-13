"""
L9 API - Simulation Routes
===========================

API endpoints for simulation engine operations.

Provides:
- POST /simulation/run — Execute simulation on IR graph
- GET /simulation/{run_id} — Get simulation run status
- GET /simulation/graph/{graph_id} — Get all runs for a graph

Version: 1.0.0 (GMP-24)
"""

from __future__ import annotations


from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.auth import verify_api_key
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/simulation", tags=["simulation"])

# AUTO-REGISTRATION (Phase 2 Auto-Wiring)
from api.routes.registry import router_registry

router_registry.register(
    router=router,
    prefix="",  # Router already has prefix="/simulation"
    tags=["simulation"],
    module_id="simulation",
    display_name="Simulation Engine",
)


# =============================================================================
# Request/Response Models
# =============================================================================


class SimulationRequest(BaseModel):
    """Request to run a simulation."""

    graph_data: dict[str, Any] = Field(
        ..., description="IR graph data from IRGenerator"
    )
    scenario_params: dict[str, Any] | None = Field(
        None, description="Optional scenario configuration"
    )
    mode: str = Field(
        "standard",
        description="Simulation mode: 'fast', 'standard', or 'thorough'",
    )


class SimulationMetricsResponse(BaseModel):
    """Simulation metrics."""

    total_steps: int
    successful_steps: int
    failed_steps: int
    duration_ms: int
    parallelism_factor: float
    critical_path_length: int = 0
    bottlenecks: list[str] = []


class SimulationResponse(BaseModel):
    """Response from simulation execution."""

    run_id: str
    graph_id: str
    status: str
    score: float
    metrics: SimulationMetricsResponse
    failure_modes: list[str]


# =============================================================================
# Engine Singleton
# =============================================================================

_simulation_engine = None


def _get_engine():
    """Get or create simulation engine singleton."""
    global _simulation_engine
    if _simulation_engine is None:
        from simulation.simulation_engine import SimulationConfig, SimulationEngine

        _simulation_engine = SimulationEngine(config=SimulationConfig())
        logger.info("SimulationEngine singleton created")
    return _simulation_engine


# =============================================================================
# Routes
# =============================================================================


@router.post("/run", response_model=SimulationResponse)
@must_stay_async("callers use await")
async def run_simulation(
    request: SimulationRequest,
    _: bool = Depends(verify_api_key),
) -> SimulationResponse:
    """
    Execute a simulation on an IR graph.

    Simulates the graph execution to evaluate:
    - Feasibility
    - Risk assessment
    - Resource requirements
    - Failure modes

    Returns simulation results with score, metrics, and identified failure modes.
    """
    try:
        from simulation.simulation_engine import (
            SimulationConfig,
            SimulationEngine,
            SimulationMode,
        )

        # Map mode string to enum
        mode_map = {
            "fast": SimulationMode.FAST,
            "standard": SimulationMode.STANDARD,
            "thorough": SimulationMode.THOROUGH,
        }
        sim_mode = mode_map.get(request.mode, SimulationMode.STANDARD)

        config = SimulationConfig(mode=sim_mode)
        engine = SimulationEngine(config=config)

        # Run simulation
        run = await engine.simulate(
            graph_data=request.graph_data,
            scenario=request.scenario_params,
        )

        logger.info(
            f"Simulation complete: run_id={run.run_id}, "
            f"score={run.score:.2f}, status={run.status}"
        )

        return SimulationResponse(
            run_id=str(run.run_id),
            graph_id=str(run.graph_id),
            status=run.status,
            score=run.score,
            metrics=SimulationMetricsResponse(
                total_steps=run.metrics.total_steps,
                successful_steps=run.metrics.successful_steps,
                failed_steps=run.metrics.failed_steps,
                duration_ms=run.metrics.total_duration_ms,
                parallelism_factor=run.metrics.parallelism_factor,
                critical_path_length=run.metrics.critical_path_length,
                bottlenecks=run.metrics.bottlenecks,
            ),
            failure_modes=run.failure_modes,
        )

    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{run_id}")
@must_stay_async("FastAPI/ASGI route handler")
async def get_simulation_run(
    run_id: str,
    _: bool = Depends(verify_api_key),
) -> dict[str, Any]:
    """
    Get a simulation run by ID.

    Returns the full run data including all steps and metrics.
    """
    try:
        engine = _get_engine()
        run = engine.get_run(UUID(run_id))

        if run is None:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

        return run.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get run failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/graph/{graph_id}")
@must_stay_async("FastAPI/ASGI route handler")
async def get_runs_for_graph(
    graph_id: str,
    _: bool = Depends(verify_api_key),
) -> list[dict[str, Any]]:
    """
    Get all simulation runs for a graph.

    Returns list of all runs for the specified graph ID.
    """
    try:
        engine = _get_engine()
        runs = engine.get_runs_for_graph(UUID(graph_id))

        return [r.to_dict() for r in runs]

    except Exception as e:
        logger.error(f"Get runs for graph failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/health")
@must_stay_async("FastAPI/ASGI route handler")
async def simulation_health() -> dict[str, Any]:
    """
    Health check for simulation engine.

    Returns engine status and configuration.
    """
    try:
        engine = _get_engine()

        return {
            "status": "healthy",
            "engine": "SimulationEngine",
            "mode": engine._config.mode.value,
            "max_steps": engine._config.max_steps,
            "timeout_ms": engine._config.timeout_ms,
            "runs_in_memory": len(engine._runs),
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


# Runtime execution trace - updated automatically on every execution
