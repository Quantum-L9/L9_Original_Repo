"""
FastAPI Lifespan Integration with DI Bootstrap

Demonstrates proper integration of L9 DI container with FastAPI lifespan.

Lifecycle:
  1. Startup: bootstrap_di_container() → global singleton
  2. Startup: set_global_di_container() → make available to composer
  3. Startup: create ExecutorComposer() → ready for requests
  4. Request handling: Executor already initialized via global DI
  5. Shutdown: await container.close() → cleanup all resources

Usage:
    uvicorn examples.fastapi_lifespan_di_bootstrap:app --reload

Reference:
    - Design doc: "DUAL DELIVERY: Docstring Edits + Wiring Sketch"
    - ADR-0052: Dependency Injection
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Fastapi Lifespan Di Bootstrap",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-24T17:28:01Z",
    "updated_at": "2026-01-31T22:21:55Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "fastapi_lifespan_di_bootstrap",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": ["GET /health", "GET /executor/info", "GET /di/services"],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

logger = structlog.get_logger(__name__)

# Global references (set during lifespan startup)
_di_container: DIContainer | None = None
_executor_composer: ExecutorComposer | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan: startup → yield → shutdown.

    Startup:
      1. Bootstrap DIContainer (all services)
      2. Set global container
      3. Initialize ExecutorComposer
      4. Warm up kernel (optional)

    Shutdown:
      1. Cleanup container (disconnect DB, etc.)
    """
    global _di_container, _executor_composer

    logger.info("=" * 80)
    logger.info("L9 API SERVER STARTUP")
    logger.info("=" * 80)

    try:
        # ====================================================================
        # STARTUP: Bootstrap DI
        # ====================================================================

        logger.info("lifespan.bootstrap.starting")
        from core.di.container import bootstrap_di_container, set_global_di_container

        _di_container = await bootstrap_di_container()
        set_global_di_container(_di_container)

        logger.info(
            "lifespan.bootstrap.complete",
            services_registered=len(_di_container._bindings),
        )

        # ====================================================================
        # STARTUP: Initialize ExecutorComposer (if available)
        # ====================================================================

        try:
            logger.info("lifespan.executor.initializing")
            from core.executor_composer import ExecutorComposer

            _executor_composer = ExecutorComposer()
            _executor_composer.set_di_container(_di_container)
            executor = _executor_composer.compose()

            logger.info(
                "lifespan.executor.ready",
                executor_type=executor.__class__.__name__,
            )
        except ImportError:
            logger.info("lifespan.executor.not_available")
        except Exception as e:
            logger.warning("lifespan.executor.failed", error=str(e))

        # ====================================================================
        # STARTUP: Warmup (Optional)
        # ====================================================================

        logger.info("lifespan.warmup.starting")
        # Optional: run a test execution to prime caches, connect pools, etc.
        # await warmup_services(_di_container)

        logger.info("L9 API SERVER READY")
        logger.info("=" * 80)

        # Yield control to request handling
        yield

    except Exception as e:
        logger.error("lifespan.startup.failed", error=str(e), exc_info=True)
        raise

    finally:
        # ====================================================================
        # SHUTDOWN: Cleanup
        # ====================================================================

        logger.info("=" * 80)
        logger.info("L9 API SERVER SHUTDOWN")
        logger.info("=" * 80)

        if _di_container:
            logger.info("lifespan.cleanup.starting")
            try:
                # Close all resources
                _di_container.clear_all()
                logger.info("lifespan.cleanup.complete")
            except Exception as e:
                logger.error("lifespan.cleanup.failed", error=str(e), exc_info=True)

        logger.info("L9 API SERVER STOPPED")
        logger.info("=" * 80)


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="L9 Agent Control Plane",
    version="1.0.0",
    description="AI agent execution platform with DI-based architecture",
    lifespan=lifespan,
)


# ============================================================================
# Health Check Endpoint
# ============================================================================


@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns container status and registered services.
    """
    if not _di_container:
        return {
            "status": "initializing",
            "message": "DI container not yet bootstrapped",
        }

    return {
        "status": "healthy",
        "services_registered": len(_di_container._bindings),
        "executor_available": _executor_composer is not None,
    }


# ============================================================================
# Executor Info Endpoint
# ============================================================================


@app.get("/executor/info")
async def get_executor_info():
    """
    Get executor configuration (debug endpoint).

    Uses the global ExecutorComposer to fetch current executor.
    """
    if not _executor_composer:
        return {"error": "Executor not initialized"}

    try:
        executor = _executor_composer.compose()
        config = _executor_composer.get_config()

        return {
            "executor": executor.__class__.__name__,
            "config": {
                "default_agent_id": config.default_agent_id,
                "max_iterations": config.max_iterations,
                "enable_persistence": config.enable_persistence,
                "enable_approval_gates": config.enable_approval_gates,
            },
            "di_services": list(_di_container._bindings.keys())
            if _di_container
            else [],
        }
    except Exception as e:
        logger.error("executor_info.failed", error=str(e))
        return {"error": str(e)}


# ============================================================================
# DI Container Debug Endpoint
# ============================================================================


@app.get("/di/services")
async def list_di_services():
    """
    List all registered DI services (debug endpoint).

    Returns service names and lifecycle info.
    """
    if not _di_container:
        return {"error": "DI container not initialized"}

    services = {}
    for interface in _di_container._bindings:
        is_singleton = interface in _di_container._singleton_bindings
        is_cached = interface in _di_container._singletons

        services[interface.__name__] = {
            "lifecycle": "singleton" if is_singleton else "transient",
            "cached": is_cached,
        }

    return {
        "total_services": len(services),
        "services": services,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "EXA-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.di.container", "core.executor_composer"],
    "tags": [
        "api",
        "api-gateway",
        "async",
        "caching",
        "debugging",
        "endpoint",
        "logging",
        "messaging",
        "operations",
        "router",
    ],
    "keywords": [
        "bootstrap",
        "check",
        "container",
        "executor",
        "fastapi",
        "global",
        "health",
        "integration",
    ],
    "business_value": "Utility module for fastapi lifespan di bootstrap",
    "last_modified": "2026-01-31T22:21:55Z",
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
