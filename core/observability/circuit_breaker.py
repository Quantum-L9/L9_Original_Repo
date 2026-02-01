"""
L9 Observability - Circuit Breaker

Production-grade circuit breaker for preventing cascade failures.
Implements the fail-fast pattern with three-state machine (CLOSED → OPEN → HALF_OPEN).

Usage:
    from core.observability.circuit_breaker import CircuitBreaker, CircuitBreakerConfig

    # Create with custom config
    cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=5, window_seconds=60))

    # In operation loop
    if cb.is_open():
        # Fast-fail, don't attempt operation
        raise CircuitOpenError("Circuit breaker is open")

    try:
        result = await risky_operation()
        cb.record_success()
    except Exception as e:
        cb.record_failure(str(e))
        raise

    # Or use from ObservabilitySettings
    from core.observability.config import load_config
    settings = load_config()
    cb = CircuitBreaker.from_settings(settings)
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Circuit Breaker",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-09T01:42:58Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "circuit_breaker",
    "type": "dataclass",
    "status": "production",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "api.memory.router",
            "api.routes.observability",
            "core.agents.executor",
            "core.observability.circuit_breaker",
            "mcp_memory.src.audit",
            "memory.substrate_dag_wrapper",
            "memory.substrate_service",
            "tests.memory.test_substrate_alignment",
        ],
    },
}
# ============================================================================

import time
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from .config import ObservabilitySettings

logger = structlog.get_logger(__name__)


class CircuitBreakerState(str, Enum):
    """Circuit breaker states following standard pattern."""

    CLOSED = "closed"  # Normal operation, requests flow through
    OPEN = "open"  # Failing fast, requests blocked
    HALF_OPEN = "half_open"  # Testing recovery, limited requests allowed


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior.

    Attributes:
        failure_threshold: Number of failures within window to trip circuit
        window_seconds: Time window for counting failures (sliding window)
        reset_timeout: Seconds to wait in OPEN state before testing recovery
        name: Optional name for logging (e.g., "aios", "memory", "tool_registry")
    """

    failure_threshold: int = 5
    window_seconds: int = 60
    reset_timeout: int = 30
    name: str = "default"

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if self.window_seconds < 1:
            raise ValueError("window_seconds must be >= 1")
        if self.reset_timeout < 1:
            raise ValueError("reset_timeout must be >= 1")


class CircuitOpenError(Exception):
    """Raised when an operation is blocked by an open circuit breaker."""

    def __init__(self, message: str, circuit_name: str = "default"):
        """
        Performs initialization of a CircuitOpenError with a message and optional circuit name for circuit breaker observability.

        Args:
            message: Description of the error or reason for circuit open state.
            circuit_name: Identifier for the specific circuit, defaults to "default".

        Raises:
            CircuitOpenError: Always raised with provided message and circuit name.
        """
        self.circuit_name = circuit_name
        super().__init__(message)


class CircuitBreaker:
    """
    Circuit breaker for protecting against cascade failures.

    Implements the standard three-state machine:
    - CLOSED: Normal operation, failures are counted
    - OPEN: Fast-fail mode, no operations attempted
    - HALF_OPEN: Recovery probe, single operation allowed to test

    Thread-safe for async usage (no locks needed for counters).
    """

    def __init__(self, config: CircuitBreakerConfig | None = None):
        """Initialize circuit breaker.

        Args:
            config: Configuration settings. Uses defaults if not provided.
        """
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitBreakerState.CLOSED
        self._failures: list[tuple[float, str]] = []
        self._last_failure_time: float | None = None
        self._last_success_time: float | None = None
        self._total_failures: int = 0
        self._total_successes: int = 0
        self._trips: int = 0  # Number of times circuit has opened
        self.logger = logger.bind(
            component="CircuitBreaker",
            circuit_name=self.config.name,
        )

    @classmethod
    def from_settings(
        cls,
        settings: "ObservabilitySettings",
        name: str = "default",
    ) -> "CircuitBreaker":
        """Create circuit breaker from ObservabilitySettings.

        Args:
            settings: Loaded observability settings
            name: Name for this circuit breaker instance

        Returns:
            Configured CircuitBreaker instance
        """
        config = CircuitBreakerConfig(
            failure_threshold=settings.circuit_breaker_threshold,
            window_seconds=settings.circuit_breaker_window_sec,
            reset_timeout=getattr(settings, "circuit_breaker_reset_timeout_sec", 30),
            name=name,
        )
        return cls(config)

    @property
    def state(self) -> CircuitBreakerState:
        """Current circuit breaker state."""
        return self._state

    def record_success(self) -> None:
        """Record a successful operation.

        In HALF_OPEN state, this closes the circuit (recovery successful).
        In CLOSED state, this is a no-op (normal operation continues).
        """
        self._last_success_time = time.monotonic()
        self._total_successes += 1

        if self._state == CircuitBreakerState.HALF_OPEN:
            self.logger.info(
                "circuit_breaker_closed",
                reason="recovery_success",
                total_successes=self._total_successes,
            )
            self._state = CircuitBreakerState.CLOSED
            self._failures = []

    def record_failure(self, error: str) -> None:
        """Record a failed operation.

        Adds failure to sliding window. If threshold exceeded, trips circuit.

        Args:
            error: Error message or description for logging
        """
        now = time.monotonic()
        self._last_failure_time = now
        self._total_failures += 1
        self._failures.append((now, error))

        # Prune failures outside window (sliding window)
        cutoff = now - self.config.window_seconds
        self._failures = [(t, e) for t, e in self._failures if t > cutoff]

        # Check if threshold exceeded
        if len(self._failures) >= self.config.failure_threshold:
            if self._state == CircuitBreakerState.CLOSED:
                self._trips += 1
                self.logger.warning(
                    "circuit_breaker_opened",
                    failure_count=len(self._failures),
                    window_seconds=self.config.window_seconds,
                    threshold=self.config.failure_threshold,
                    total_trips=self._trips,
                    last_error=error[:200] if error else None,
                )
                self._state = CircuitBreakerState.OPEN
            elif self._state == CircuitBreakerState.HALF_OPEN:
                # Recovery failed, back to OPEN
                self.logger.warning(
                    "circuit_breaker_recovery_failed",
                    error=error[:200] if error else None,
                )
                self._state = CircuitBreakerState.OPEN

    def is_open(self) -> bool:
        """Check if circuit breaker is blocking operations.

        Also handles state transition from OPEN → HALF_OPEN after reset timeout.

        Returns:
            True if operations should be blocked, False if allowed
        """
        if self._state == CircuitBreakerState.CLOSED:
            return False

        if self._state == CircuitBreakerState.OPEN:
            # Check if reset timeout has elapsed
            if self._last_failure_time is not None:
                elapsed = time.monotonic() - self._last_failure_time
                if elapsed >= self.config.reset_timeout:
                    self.logger.info(
                        "circuit_breaker_half_open",
                        reason="reset_timeout_elapsed",
                        elapsed_seconds=round(elapsed, 2),
                    )
                    self._state = CircuitBreakerState.HALF_OPEN
                    return False  # Allow one probe request
            return True

        # HALF_OPEN state allows requests
        return False

    def get_state(self) -> str:
        """Get current state as string.

        Returns:
            State value: "closed", "open", or "half_open"
        """
        return self._state.value

    def get_stats(self) -> dict:
        """Get circuit breaker statistics.

        Returns:
            Dictionary with state, counters, and timing info
        """
        return {
            "state": self._state.value,
            "name": self.config.name,
            "failures_in_window": len(self._failures),
            "failure_threshold": self.config.failure_threshold,
            "window_seconds": self.config.window_seconds,
            "reset_timeout": self.config.reset_timeout,
            "total_failures": self._total_failures,
            "total_successes": self._total_successes,
            "total_trips": self._trips,
            "last_failure_time": self._last_failure_time,
            "last_success_time": self._last_success_time,
        }

    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state.

        Use with caution - typically for admin/ops intervention.
        """
        self.logger.info(
            "circuit_breaker_manually_reset",
            previous_state=self._state.value,
            failures_cleared=len(self._failures),
        )
        self._state = CircuitBreakerState.CLOSED
        self._failures = []

    def __repr__(self) -> str:
        """Returns a string representation of the CircuitBreaker instance, including its name, current state, and failure count for debugging and observability purposes."""
        return (
            f"CircuitBreaker(name={self.config.name!r}, "
            f"state={self._state.value!r}, "
            f"failures={len(self._failures)}/{self.config.failure_threshold})"
        )


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-063",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "data-models",
        "dataclass",
        "event-driven",
        "foundation",
        "logging",
        "messaging",
        "testing",
    ],
    "keywords": [
        "breaker",
        "circuit",
        "circuitbreaker",
        "circuitbreakerconfig",
        "core",
        "fail",
        "failure",
        "fast",
    ],
    "business_value": "Implements the fail-fast pattern with three-state machine (CLOSED → OPEN → HALF_OPEN). from core.observability.circuit_breaker import CircuitBreaker, CircuitBreakerConfig # Create with custom config c",
    "last_modified": "2026-01-14T15:03:00Z",
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
