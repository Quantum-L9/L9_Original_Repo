"""
L9 Core - Resilience Protocols
==============================

Protocol definitions for resilient services.
Enables DIP: components depend on protocol, not concrete implementations.

Usage:
    from core.resilience.protocols import ResilientService

    class MyService(ResilientService, ResilienceMixin):
        ...

Version: 1.0.0
ADR: readme/adr/0014-resilience-mixin-pattern.md
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Resilience Protocols",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-20T16:00:00Z",
    "updated_at": "2026-01-20T16:00:00Z",
    "layer": "foundation",
    "domain": "resilience",
    "module_name": "protocols",
    "type": "protocol",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "core.resilience.mixin",
        ],
    },
}
# ============================================================================

from typing import Protocol

from core.observability.circuit_breaker import CircuitBreaker
from memory.dead_letter import DeadLetterQueue
from memory.substrate_dag_wrapper import RetryPolicy


class ResilientService(Protocol):
    """
    Protocol for services that support resilience patterns.

    Components implementing this protocol have:
    - Circuit breaker for cascade failure prevention
    - Dead letter queue for failed operations
    - Retry policy for transient failures

    Usage:
        class MyService(ResilientService):
            def __init__(self, circuit_breaker=None, dlq=None, retry_policy=None):
                self._circuit_breaker = circuit_breaker
                self._dlq = dlq
                self._retry_policy = retry_policy or RetryPolicy()
    """

    _circuit_breaker: CircuitBreaker | None
    _dlq: DeadLetterQueue | None
    _retry_policy: RetryPolicy | None


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-091",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "dip",
        "foundation",
        "protocol",
        "resilience",
    ],
    "keywords": [
        "circuit_breaker",
        "dlq",
        "protocol",
        "resilient",
        "retry_policy",
    ],
    "business_value": "Protocol for resilient services enabling DIP pattern",
    "last_modified": "2026-01-20T16:00:00Z",
    "modified_by": "GMP-091",
    "change_summary": "Initial creation per ADR-0014",
}
# ============================================================================
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
