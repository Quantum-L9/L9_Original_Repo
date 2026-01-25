"""
L9 Runtime - Background Task Registry
======================================

Auto-register and manage periodic background tasks.

Features:
- Feature flag integration (enable/disable via env vars)
- Automatic retry on failures
- Graceful shutdown
- Structured logging

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Background Task Registry",
    "module_version": "1.0.0",
    "created_by": "L9_Auto_Wiring_System",
    "created_at": "2026-01-19T00:00:00Z",
    "updated_at": "2026-01-19T00:00:00Z",
    "layer": "runtime",
    "domain": "task_management",
    "module_name": "background_tasks",
    "type": "registry",
    "status": "active",
}
# ============================================================================

import asyncio
import os
from typing import Any, Awaitable, Callable, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)


class BackgroundTaskRegistry:
    """
    Auto-register and manage background tasks.

    Consolidates background task management into a single registry,
    reducing boilerplate in api/server.py lifespan.

    Usage:
        bg_tasks = BackgroundTaskRegistry()

        # Register periodic task
        bg_tasks.register(
            name="memory_consolidation",
            coro=run_consolidation,
            interval_seconds=3600,
            enabled_flag="L9_STAGE4_CONSOLIDATION"
        )

        # At shutdown
        await bg_tasks.shutdown_all()
    """

    def __init__(self):
        self._tasks: Dict[str, asyncio.Task] = {}
        self._configs: Dict[str, Dict[str, Any]] = {}
        logger.info("BackgroundTaskRegistry initialized")

    def register(
        self,
        name: str,
        coro: Callable[[], Awaitable[Any]],
        interval_seconds: int,
        enabled_flag: Optional[str] = None,
        run_immediately: bool = False,
    ) -> bool:
        """
        Register a background task.

        Args:
            name: Task name (unique identifier)
            coro: Async coroutine to run periodically (no args)
            interval_seconds: Run interval in seconds
            enabled_flag: Optional env var to check (e.g., "L9_ENABLE_FOO")
            run_immediately: If True, run coro before first sleep

        Returns:
            True if task was registered, False if disabled
        """
        # Check feature flag
        if enabled_flag:
            flag_value = os.getenv(enabled_flag, "true").lower()
            if flag_value not in ("true", "1", "yes"):
                logger.info(
                    f"Background task '{name}' disabled",
                    task=name,
                    flag=enabled_flag,
                    flag_value=flag_value,
                )
                return False

        # Don't re-register
        if name in self._tasks:
            logger.warning(f"Background task '{name}' already registered, skipping")
            return False

        # Create task loop
        async def task_loop():
            if not run_immediately:
                await asyncio.sleep(interval_seconds)

            while True:
                try:
                    await coro()
                except asyncio.CancelledError:
                    logger.info(f"Background task '{name}' cancelled")
                    break
                except Exception as e:
                    logger.error(
                        f"Background task '{name}' failed",
                        task=name,
                        error=str(e),
                        exc_info=True,
                    )

                try:
                    await asyncio.sleep(interval_seconds)
                except asyncio.CancelledError:
                    break

        # Store config for observability
        self._configs[name] = {
            "interval_seconds": interval_seconds,
            "enabled_flag": enabled_flag,
            "run_immediately": run_immediately,
        }

        # Create and store task
        task = asyncio.create_task(task_loop(), name=f"bg_{name}")
        self._tasks[name] = task

        logger.info(
            "Background task registered",
            task=name,
            interval_seconds=interval_seconds,
            enabled_flag=enabled_flag,
        )
        return True

    def register_oneshot(
        self,
        name: str,
        coro: Callable[[], Awaitable[Any]],
        enabled_flag: Optional[str] = None,
    ) -> bool:
        """
        Register a one-shot background task (runs once, doesn't repeat).

        Useful for initialization tasks that should run in background.
        """
        if enabled_flag:
            if os.getenv(enabled_flag, "true").lower() not in ("true", "1", "yes"):
                logger.info(f"One-shot task '{name}' disabled via {enabled_flag}")
                return False

        if name in self._tasks:
            logger.warning(f"Task '{name}' already registered")
            return False

        async def oneshot_wrapper():
            try:
                await coro()
                logger.info(f"One-shot task '{name}' completed")
            except Exception as e:
                logger.error(f"One-shot task '{name}' failed: {e}", exc_info=True)

        task = asyncio.create_task(oneshot_wrapper(), name=f"oneshot_{name}")
        self._tasks[name] = task
        self._configs[name] = {"type": "oneshot", "enabled_flag": enabled_flag}

        logger.info(f"One-shot task '{name}' registered")
        return True

    async def shutdown_all(self, timeout: float = 5.0) -> int:
        """
        Cancel all background tasks gracefully.

        Args:
            timeout: Max seconds to wait for tasks to complete

        Returns:
            Number of tasks that were cancelled
        """
        if not self._tasks:
            return 0

        cancelled = 0
        for name, task in self._tasks.items():
            if not task.done():
                task.cancel()
                cancelled += 1

        # Wait for all tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks.values(), return_exceptions=True)

        logger.info(
            "Background tasks shutdown complete",
            cancelled=cancelled,
            total=len(self._tasks),
        )

        self._tasks.clear()
        return cancelled

    def get_status(self, name: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task."""
        if name not in self._tasks:
            return None

        task = self._tasks[name]
        config = self._configs.get(name, {})

        return {
            "name": name,
            "running": not task.done(),
            "cancelled": task.cancelled(),
            **config,
        }

    def snapshot(self) -> Dict[str, Any]:
        """Get JSON-serializable snapshot of all tasks."""
        return {
            "count": len(self._tasks),
            "running": sum(1 for t in self._tasks.values() if not t.done()),
            "tasks": [
                {
                    "name": name,
                    "running": not task.done(),
                    "cancelled": task.cancelled(),
                    **self._configs.get(name, {}),
                }
                for name, task in self._tasks.items()
            ],
        }

    def __len__(self) -> int:
        return len(self._tasks)

    def __repr__(self) -> str:
        running = sum(1 for t in self._tasks.values() if not t.done())
        return f"BackgroundTaskRegistry(total={len(self)}, running={running})"


# Global singleton (optional - can also instantiate per-app)
_background_task_registry: Optional[BackgroundTaskRegistry] = None


def get_background_task_registry() -> BackgroundTaskRegistry:
    """Get or create the global background task registry."""
    global _background_task_registry
    if _background_task_registry is None:
        _background_task_registry = BackgroundTaskRegistry()
    return _background_task_registry


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED
# ============================================================================
__dora_footer__ = {
    "component_id": "RUNTIME-BG-TASKS-001",
    "governance_level": "standard",
    "compliance_required": False,
    "audit_trail": False,
    "dependencies": ["asyncio", "structlog"],
    "tags": ["runtime", "background", "tasks", "registry"],
    "keywords": ["background", "task", "periodic", "scheduler"],
    "business_value": "Consolidates background task management, reducing api/server.py boilerplate by ~100 lines",
}
# ============================================================================

__all__ = [
    "BackgroundTaskRegistry",
    "get_background_task_registry",
]
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
