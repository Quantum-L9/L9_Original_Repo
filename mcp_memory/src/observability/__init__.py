"""L9 Observability - Logging, Tracing, Metrics.

Bounded Context: Observability
Domain: Structured logging, distributed tracing, metrics collection.
Owner: L (CTO)

Observability is responsible for:
  1. Structured logging with correlation IDs
  2. Distributed tracing (OpenTelemetry)
  3. Metrics export (Prometheus)
  4. Performance monitoring
  5. Circuit breaker observability

Observability MUST implement:
  - get_logger(name: str) -> Logger
  - get_tracer(name: str) -> Tracer
  - get_meter(name: str) -> Meter
  - Correlation ID injection middleware

Observability MUST NOT:
  - Be imported by kernel.protocol or safety.audit (avoid circular deps)
  - Store state (stateless adapters only)
  - Enforce business logic

Every kernel/substrate/safety operation SHOULD use observability exports.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Logging, Tracing, Metrics.",
    "module_version": "1.0.0",
    "created_by": "cryptoxdog",
    "created_at": "2026-01-25T05:34:48Z",
    "updated_at": "2026-01-31T22:21:56Z",
    "layer": "integration",
    "domain": "mcp_integration",
    "module_name": "__init__",
    "type": "adapter",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from observability.logging import get_logger, setup_logging
from observability.metrics import get_meter, setup_metrics
from observability.tracing import get_tracer, setup_tracing

__all__ = [
    "get_logger",
    "get_meter",
    "get_tracer",
    "setup_logging",
    "setup_metrics",
    "setup_tracing",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MCP-INTE-013",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "adapter",
        "audit-tool",
        "integration",
        "mcp-integration",
        "metrics",
        "monitoring",
        "tracing",
    ],
    "keywords": [
        "audit",
        "correlation",
        "distributed",
        "kernel",
        "logging",
        "logging,",
        "metrics",
        "metrics.",
    ],
    "business_value": "Utility module for   init  ",
    "last_modified": "2026-01-31T22:21:56Z",
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
