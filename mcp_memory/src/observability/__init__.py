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

from observability.logging import get_logger, setup_logging
from observability.tracing import get_tracer, setup_tracing
from observability.metrics import get_meter, setup_metrics

__all__ = [
    "get_logger",
    "setup_logging",
    "get_tracer",
    "setup_tracing",
    "get_meter",
    "setup_metrics",
]
