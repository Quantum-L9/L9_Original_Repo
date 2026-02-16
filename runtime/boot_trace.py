from __future__ import annotations

"""
L9 Runtime Boot Trace
=====================
Deterministic boot instrumentation for server startup.

Records each init stage with step name, timestamp, status (START/OK/FAIL),
and error summary. Stored in app.state.boot_trace after lifespan completes.

Usage in api/server.py lifespan:
    from runtime.boot_trace import BootTrace
    trace = BootTrace()
    trace.start("neo4j_init")
    ...
    trace.ok("neo4j_init")
    app.state.boot_trace = trace

ADR: No noqa suppressions.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "BootTrace",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-02-16T18:00:00Z",
    "updated_at": "2026-02-16T18:00:00Z",
    "layer": "runtime",
    "domain": "observability",
    "module_name": "boot_trace",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["api.server"],
    },
}
# ============================================================================

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BootStep:
    """A single boot stage record."""

    name: str
    status: str  # "START", "OK", "FAIL"
    timestamp: float  # time.monotonic()
    wall_clock: str  # ISO-8601 UTC
    error: str | None = None
    duration_ms: float | None = None


@dataclass
class BootTrace:
    """
    Ordered list of boot steps for deterministic startup tracing.

    Provides start/ok/fail methods to record each init stage.
    Immutable after freeze() is called.
    """

    steps: list[BootStep] = field(default_factory=list)
    _start_times: dict[str, float] = field(default_factory=dict, repr=False)
    _frozen: bool = field(default=False, repr=False)

    def _now_iso(self) -> str:
        """Return current UTC time as ISO-8601 string."""
        import datetime

        return datetime.datetime.now(datetime.timezone.utc).isoformat()

    def start(self, name: str) -> None:
        """Record the START of a boot stage."""
        if self._frozen:
            raise RuntimeError("BootTrace is frozen; cannot add steps after freeze()")
        mono = time.monotonic()
        self._start_times[name] = mono
        self.steps.append(
            BootStep(
                name=name,
                status="START",
                timestamp=mono,
                wall_clock=self._now_iso(),
            )
        )

    def ok(self, name: str) -> None:
        """Record the successful completion of a boot stage."""
        if self._frozen:
            raise RuntimeError("BootTrace is frozen; cannot add steps after freeze()")
        mono = time.monotonic()
        start_mono = self._start_times.get(name)
        duration_ms = (
            round((mono - start_mono) * 1000, 2) if start_mono is not None else None
        )
        self.steps.append(
            BootStep(
                name=name,
                status="OK",
                timestamp=mono,
                wall_clock=self._now_iso(),
                duration_ms=duration_ms,
            )
        )

    def fail(self, name: str, error: str) -> None:
        """Record the failure of a boot stage."""
        if self._frozen:
            raise RuntimeError("BootTrace is frozen; cannot add steps after freeze()")
        mono = time.monotonic()
        start_mono = self._start_times.get(name)
        duration_ms = (
            round((mono - start_mono) * 1000, 2) if start_mono is not None else None
        )
        self.steps.append(
            BootStep(
                name=name,
                status="FAIL",
                timestamp=mono,
                wall_clock=self._now_iso(),
                error=error,
                duration_ms=duration_ms,
            )
        )

    def freeze(self) -> None:
        """Freeze the trace — no more steps can be added."""
        self._frozen = True

    @property
    def is_frozen(self) -> bool:
        return self._frozen

    def get_failed(self) -> list[BootStep]:
        """Return all FAIL steps."""
        return [s for s in self.steps if s.status == "FAIL"]

    def get_ok(self) -> list[BootStep]:
        """Return all OK steps."""
        return [s for s in self.steps if s.status == "OK"]

    def summary(self) -> dict[str, Any]:
        """Return a summary dict suitable for structured logging."""
        ok_names = [s.name for s in self.steps if s.status == "OK"]
        fail_names = [s.name for s in self.steps if s.status == "FAIL"]
        total_ms = sum(
            s.duration_ms for s in self.steps if s.status == "OK" and s.duration_ms
        )
        return {
            "total_steps": len(ok_names) + len(fail_names),
            "ok": ok_names,
            "failed": fail_names,
            "total_boot_ms": round(total_ms, 2),
            "frozen": self._frozen,
        }

    def to_list(self) -> list[dict[str, Any]]:
        """Serialize all steps to a list of dicts."""
        return [
            {
                "name": s.name,
                "status": s.status,
                "wall_clock": s.wall_clock,
                "duration_ms": s.duration_ms,
                "error": s.error,
            }
            for s in self.steps
        ]
