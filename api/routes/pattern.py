"""
L9 Pattern Orchestrator API Router
==================================

API endpoints for executing architecture patterns via PatternOrchestrator.

Version: 1.0.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Pattern",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-16T12:13:08Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "pattern",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [
            "GET /test",
            "GET /config",
            "POST /execute",
            "POST /validate",
        ],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["api.server", "tests.orchestrators.test_pattern_orchestrator"],
    },
}
# ============================================================================

from typing import Any

import aiofiles
import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from api.auth import verify_api_key
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)

router = APIRouter()

# ============================================================================
# AUTO-REGISTRATION: Register router for auto-wiring (Phase 2 Auto-Wiring)
# ============================================================================
from api.routes.registry import router_registry

router_registry.register(
    router=router,
    prefix="/pattern",
    tags=["pattern"],
    display_name="Pattern Orchestrator",
    dependencies=["pattern_orchestrator"],  # Validates app.state
)


# ============================================================================
# Request/Response Models
# ============================================================================


class PatternExecuteRequest(BaseModel):
    """Request model for pattern execution."""

    user_prompts: list[str] = Field(
        ...,
        min_length=1,
        description="User prompts/requirements to process through pipeline",
    )
    pattern_config: str | None = Field(
        default=None,
        description="Path to pattern config YAML (uses default if not provided)",
    )
    subsystem_config: str | None = Field(
        default=None,
        description="Path to subsystem config YAML (uses default if not provided)",
    )
    dry_run: bool = Field(
        default=False,
        description="If true, validate without executing agents",
    )
    trace_id: str | None = Field(
        default=None,
        description="Optional trace ID for distributed tracing",
    )


class NodeResultResponse(BaseModel):
    """Response model for a single node result."""

    node_id: str
    status: str
    output: dict[str, Any] = Field(default_factory=dict)
    duration_ms: int = 0
    errors: list[str] = Field(default_factory=list)


class PatternExecuteResponse(BaseModel):
    """Response model for pattern execution."""

    success: bool = Field(..., description="Whether execution succeeded")
    pipeline_id: str = Field(..., description="Pipeline execution ID")
    status: str = Field(..., description="Pipeline status")
    nodes_executed: int = Field(default=0, description="Number of nodes executed")
    node_results: list[NodeResultResponse] = Field(
        default_factory=list,
        description="Results from each node",
    )
    final_output: dict[str, Any] = Field(
        default_factory=dict,
        description="Final pipeline output",
    )
    duration_ms: int = Field(default=0, description="Total duration in milliseconds")
    errors: list[str] = Field(default_factory=list, description="Any errors")


class PatternConfigResponse(BaseModel):
    """Response model for pattern configuration."""

    pattern_name: str
    pattern_version: str
    nodes: list[dict[str, Any]]
    observability: dict[str, Any]


# ============================================================================
# Dependency: Get PatternOrchestrator from app.state
# ============================================================================


def get_pattern_orchestrator(request: Request):
    """Get PatternOrchestrator from app.state."""
    orchestrator = getattr(request.app.state, "pattern_orchestrator", None)
    if orchestrator is None:
        raise HTTPException(
            status_code=503,
            detail="PatternOrchestrator not initialized. Check server logs.",
        )
    return orchestrator


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/test")
@must_stay_async("FastAPI/ASGI route handler")
async def pattern_test(
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Test endpoint to verify pattern router is reachable."""
    return {"ok": True, "msg": "pattern endpoint reachable"}


@router.get("/config")
@must_stay_async("FastAPI/ASGI route handler")
async def get_pattern_config(
    request: Request,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Get current pattern configuration."""
    orchestrator = getattr(request.app.state, "pattern_orchestrator", None)

    if orchestrator is None:
        return {
            "status": "not_initialized",
            "message": "PatternOrchestrator not initialized",
            "default_configs": {
                "pattern": "config/patterns/pipeline_v1.yaml",
                "subsystem": "config/subsystems/code_mutation.yaml",
            },
        }

    config = orchestrator.get_config()
    return {
        "status": "initialized",
        "pattern_name": config.get("pattern_name", "unknown"),
        "pattern_version": config.get("version", "unknown"),
        "nodes": config.get("nodes", []),
        "observability": config.get("observability", {}),
    }


@router.post("/execute", response_model=PatternExecuteResponse)
async def execute_pattern(
    request: PatternExecuteRequest,
    http_request: Request,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """
    Execute a pattern pipeline.

    Runs the N1-N9 architecture pipeline with the provided prompts.
    Supports dry-run mode for validation without agent execution.
    """
    try:
        logger.info(
            "Pattern execution request",
            prompt_count=len(request.user_prompts),
            dry_run=request.dry_run,
            trace_id=request.trace_id,
        )

        # Get or create orchestrator
        orchestrator = getattr(http_request.app.state, "pattern_orchestrator", None)

        if orchestrator is None:
            # Create on-demand with defaults or provided configs
            from orchestrators.pattern import CellAgentAdapter, PatternOrchestrator

            pattern_path = request.pattern_config or "config/patterns/pipeline_v1.yaml"
            subsystem_path = (
                request.subsystem_config or "config/subsystems/code_mutation.yaml"
            )

            logger.info(
                "Creating PatternOrchestrator on-demand",
                pattern_path=pattern_path,
                subsystem_path=subsystem_path,
            )

            orchestrator = PatternOrchestrator(
                pattern_path=pattern_path,
                subsystem_config_path=subsystem_path,
                agent=CellAgentAdapter(),
            )

        # Execute pipeline
        result = await orchestrator.execute(
            user_prompts=request.user_prompts,
            dry_run=request.dry_run,
            context={"trace_id": request.trace_id} if request.trace_id else None,
        )

        # Convert node results
        node_results = [
            NodeResultResponse(
                node_id=nr.node_id,
                status=(
                    nr.status.value if hasattr(nr.status, "value") else str(nr.status)
                ),
                output=nr.output or {},
                duration_ms=nr.duration_ms,
                errors=nr.errors,
            )
            for nr in result.node_results
        ]

        logger.info(
            "Pattern execution complete",
            success=result.success,
            nodes_executed=len(node_results),
            duration_ms=result.duration_ms,
        )

        return PatternExecuteResponse(
            success=result.success,
            pipeline_id=result.pipeline_id,
            status=(
                result.status.value
                if hasattr(result.status, "value")
                else str(result.status)
            ),
            nodes_executed=len(node_results),
            node_results=node_results,
            final_output=result.final_output or {},
            duration_ms=result.duration_ms,
            errors=result.errors,
        )

    except FileNotFoundError as e:
        logger.error(f"Config file not found: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Configuration file not found: {e!s}",
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Pattern execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Pattern execution failed: {e!s}",
        ) from e


@router.post("/validate")
@must_stay_async("FastAPI/ASGI route handler")
async def validate_pattern_config(
    pattern_path: str = "config/patterns/pipeline_v1.yaml",
    subsystem_path: str = "config/subsystems/code_mutation.yaml",
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """
    Validate pattern and subsystem configuration files.

    Returns validation status without executing any pipeline.
    """
    import os

    errors = []

    # Check pattern config exists
    if not os.path.exists(pattern_path):
        errors.append(f"Pattern config not found: {pattern_path}")

    # Check subsystem config exists
    if not os.path.exists(subsystem_path):
        errors.append(f"Subsystem config not found: {subsystem_path}")

    if errors:
        return {
            "valid": False,
            "errors": errors,
        }

    # Try to load configs
    try:
        import yaml

        async with aiofiles.open(pattern_path) as f:
            pattern_config = yaml.safe_load(await f.read())

        async with aiofiles.open(subsystem_path) as f:
            subsystem_config = yaml.safe_load(await f.read())

        return {
            "valid": True,
            "pattern": {
                "name": pattern_config.get("pattern_name", "unknown"),
                "version": pattern_config.get("version", "unknown"),
                "node_count": len(pattern_config.get("nodes", [])),
            },
            "subsystem": {
                "name": subsystem_config.get("metadata", {}).get("name", "unknown"),
                "version": subsystem_config.get("metadata", {}).get(
                    "version", "unknown"
                ),
            },
        }
    except Exception as e:
        return {
            "valid": False,
            "errors": [f"Failed to parse config: {e!s}"],
        }


# ============================================================================
# Multi-Subsystem Execution
# ============================================================================


class MasterExecuteRequest(BaseModel):
    """Request model for multi-subsystem execution."""

    user_prompts: list[str] = Field(
        ...,
        min_length=1,
        description="User prompts/requirements to process through all pipelines",
    )
    subsystems: list[str] | None = Field(
        default=None,
        description="Specific subsystems to run (defaults to all enabled)",
    )
    dry_run: bool = Field(
        default=False,
        description="If true, validate without executing agents",
    )


class MasterExecuteResponse(BaseModel):
    """Response model for multi-subsystem execution."""

    success: bool = Field(..., description="Whether all subsystems succeeded")
    trace_id: str = Field(..., description="Master execution trace ID")
    status: str = Field(..., description="Overall status: success|partial|failure")
    subsystems_executed: int = Field(
        default=0, description="Number of subsystems executed"
    )
    subsystems_failed: int = Field(
        default=0, description="Number of subsystems that failed"
    )
    results: dict[str, Any] = Field(
        default_factory=dict, description="Per-subsystem results"
    )
    duration_ms: int = Field(default=0, description="Total duration in milliseconds")
    errors: list[str] = Field(
        default_factory=list, description="Any errors encountered"
    )


@router.post("/execute-all", response_model=MasterExecuteResponse)
async def execute_all_subsystems(
    request: MasterExecuteRequest,
    http_request: Request,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """
    Execute pattern pipelines for all enabled subsystems.

    Runs the N1-N9 architecture pipeline for each enabled subsystem in master.yaml.
    Execution order: code_mutation (sequential) → auth (sequential) → others (parallel)
    """
    try:
        logger.info(
            "Master execution request",
            prompt_count=len(request.user_prompts),
            subsystems=request.subsystems,
            dry_run=request.dry_run,
        )

        from orchestrators.pattern import MasterOrchestrator

        master = MasterOrchestrator(
            master_config_path="config/subsystems/master.yaml",
            pattern_path="config/patterns/pipeline_v1.yaml",
        )

        result = await master.execute_all(
            user_prompts=request.user_prompts,
            dry_run=request.dry_run,
            subsystems=request.subsystems,
        )

        logger.info(
            "Master execution complete",
            status=result.status,
            executed=result.subsystems_executed,
            failed=result.subsystems_failed,
        )

        return MasterExecuteResponse(
            success=result.status == "success",
            trace_id=result.trace_id,
            status=result.status,
            subsystems_executed=result.subsystems_executed,
            subsystems_failed=result.subsystems_failed,
            results=result.results,
            duration_ms=int(result.total_duration_ms),
            errors=result.errors,
        )

    except FileNotFoundError as e:
        logger.error(f"Config file not found: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Configuration file not found: {e!s}",
        ) from e
    except Exception as e:
        logger.error(f"Master execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Master execution failed: {e!s}",
        ) from e


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "API-OPER-019",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["api.auth", "core.decorators"],
    "tags": [
        "api",
        "api-gateway",
        "async",
        "auth",
        "config",
        "endpoint",
        "logging",
        "messaging",
        "operations",
        "pydantic",
    ],
    "keywords": ["execute", "orchestrator", "pattern", "router", "test", "validate"],
    "business_value": "Provides pattern components including PatternExecuteRequest, NodeResultResponse, PatternExecuteResponse",
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
