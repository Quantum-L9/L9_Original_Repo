# ADR 0042: Rate Limiting Middleware

**Date**: 2026-01-21

**Status**: Proposed

## Context

The Priming Prompt Sequence analysis (Step 3) identified a gap in the API surface: the absence of rate limiting. This exposes the L9 API to potential abuse, DDoS attacks, and resource exhaustion.

## Decision

We will implement a rate limiting middleware using the **token bucket algorithm**. This middleware will be applied to all API endpoints and will limit requests per client IP address.

The middleware will be configurable via environment variables:
- `RATE_LIMIT_RPM`: Requests per minute (default: 60)
- `RATE_LIMIT_BURST`: Burst size (default: 10)
- `RATE_LIMIT_ENABLED`: Enable/disable rate limiting (default: true)

## Consequences

### Positive
- **Protects the API from abuse and DDoS attacks**.
- **Improves API stability and availability**.
- **Provides a mechanism for throttling clients**.

### Negative
- **Adds a small amount of latency** to each request.
- **May require tuning** of rate limits for specific use cases.

### Neutral
- Introduces a new dependency on `starlette.middleware.base`.

## Alternatives Considered

- **Fixed Window Rate Limiting**: Simpler to implement, but can lead to request bursts at the window boundary.
- **Sliding Window Rate Limiting**: More accurate, but more complex to implement and maintain.
- **Third-Party Rate Limiting Service**: Considered using a service like Cloudflare or an API gateway, but this adds external dependencies and cost.

## DORA Metadata

- **component_id**: ADR-0042
- **governance_level**: high
- **compliance_required**: True
- **audit_trail**: True
- **dependencies**: ["api.middleware.rate_limiter"]
- **tags**: ["adr", "security", "rate_limiting", "middleware", "ddos"]
- **keywords": ["adr", "security", "rate", "limiter", "middleware", "ddos"]
- **business_value**: "Protects the L9 API from abuse and DDoS attacks by implementing token bucket rate limiting."
- **last_modified**: "2026-01-21T19:05:00Z"
- **modified_by**: "Manus_AI"
- **change_summary**: "Initial ADR for rate limiting middleware"
