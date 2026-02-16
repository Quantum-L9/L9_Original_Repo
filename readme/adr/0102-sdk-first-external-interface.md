# ADR-0102: SDK-First External Interface — Reduce Exposed API Surface

## Status

**Accepted** — 2026-02-14

## Context

L9 currently exposes **225+ FastAPI routes** across 30+ routers. External clients (L, Emma, future agents) consume these services via direct HTTP calls to individual endpoints. This creates:

1. **Massive attack surface** — every route is a potential entry point
2. **No unified auth context** — each route handles auth independently
3. **No automatic context injection** — callers must manually pass agent_id, tenant_id, thread_id
4. **Route sprawl** — every new service adds more endpoints
5. **Inconsistent interfaces** — each router has its own conventions
6. **Difficult to audit** — 225 routes to review for security, compliance, permissions

Meanwhile, the `L9SDK` adapter (ADR-0061) already provides a per-agent instance with automatic context injection, governance checks, and a consistent interface pattern. But only ~10% of services are wired through it.

### The Security Argument

Every externally-facing HTTP endpoint is an attack vector. With 225+ routes:
- Each needs authentication, rate limiting, input validation
- Each is a potential injection point
- Each must be individually audited
- Nginx/reverse proxy rules grow linearly

With SDK-first:
- **One** authenticated entry point (the SDK initialization)
- Agent identity verified once, injected everywhere
- Governance checks applied uniformly
- Internal service calls bypass HTTP overhead entirely

## Decision

**External clients MUST consume L9 services through the SDK adapter (`SDK/SDK.py`), not through individual API endpoints.**

### What This Means

| Consumer | Access Method | Auth |
|----------|--------------|------|
| L (CTO agent) | `L9SDK(agent_id="l-cto")` | SDK-level |
| Emma | `L9SDK(agent_id="emma")` | SDK-level |
| Future agents | `L9SDK(agent_id="...")` | SDK-level |
| Cursor (local) | Direct imports + SessionDAGs | Local |
| Webhooks (Slack, Twilio, WABA) | Dedicated webhook routes (keep) | Webhook-specific |
| Health checks | `/health` endpoints (keep) | None |
| Internal services | Direct async calls | In-process |

### What Routes STAY as HTTP

Some routes are inherently HTTP-facing and should remain:

- **Health endpoints** — `/health`, `/health/neo4j`, `/health/services` (monitoring)
- **Webhook receivers** — `/slack/events`, `/twilio/webhook`, `/waba/webhook` (inbound from external services)
- **MCP protocol** — `/mcp/*` (protocol-specific)
- **WebSocket** — `/lws`, `/ws/agent` (real-time transport)

### What Routes Get REPLACED by SDK Interfaces

These route groups should be consumed via SDK, not direct HTTP:

| Current Routes | SDK Interface | Priority |
|---|---|---|
| `/memory/packet`, `/memory/search`, `/memory/batch` | `sdk.memory` | P0 |
| `/memory/graph/*` | `sdk.memory.graph` | P0 |
| `/memory/cache/*` | `sdk.memory.cache` | P1 |
| `/agent/execute`, `/agent/task` | `sdk.run_task()` (exists) | Done |
| `/tools/execute` | `sdk.execute_tool()` (exists) | Done |
| `/workflows/*` | `sdk.workflows` (ADR-0101) | Done |
| `/research-agent/*` | `sdk.research` | P1 |
| `/commands/execute` | `sdk.commands` | P1 |
| `/worldmodel/*` | `sdk.world_model` (expand) | P1 |
| `/observability/*` | `sdk.observability` (expand) | P2 |
| `/compliance/*` | `sdk.compliance` (expand) | P2 |
| `/evaluation/*` | `sdk.evaluation` | P2 |
| `/factory/*` | `sdk.factory` | P2 |
| `/simulation/*` | `sdk.simulation` | P2 |
| `/email/*` | `sdk.email` | P2 |
| `/reasoning/*`, `/tensor-bridge/*` | `sdk.reasoning` (expand) | P2 |

### Implementation Pattern

Every new SDK interface follows the established pattern:

```python
class MemoryInterface:
    """Interface to L9 memory subsystem."""

    def __init__(self, sdk: L9SDK):
        self._sdk = sdk

    @must_stay_async("callers use await")
    async def search(self, query: str, **kwargs) -> list[dict]:
        """Search memory with auto-injected agent context."""
        kwargs.setdefault("agent_id", self._sdk.agent_id)
        # Call service directly — no HTTP round-trip
        from memory.retrieval import MemoryRetrievalService
        service = MemoryRetrievalService()
        return await service.search(query=query, **kwargs)

    @must_stay_async("callers use await")
    async def ingest(self, content: str, kind: str, **kwargs) -> str:
        """Ingest a packet with auto-injected context."""
        ...
```

Key principles:
1. **Direct service calls** — SDK interfaces call services in-process, not via HTTP
2. **Auto-inject context** — agent_id, tenant_id injected from SDK instance
3. **Lazy loading** — services instantiated on first use
4. **Async-first** — all interface methods are async

### Migration Strategy

This is NOT a "rip out all routes" decision. Routes stay for backwards compatibility. The migration is:

1. **New consumers** — MUST use SDK (no new direct HTTP integrations)
2. **Existing consumers** — migrate to SDK as they're touched
3. **Routes** — keep but mark as internal/deprecated over time
4. **Nginx** — progressively restrict external access to non-SDK routes

### Route Deprecation Path

```
Phase 1 (now):     SDK interfaces for P0 services (memory, agent, tools)
Phase 2 (next):    SDK interfaces for P1 services (research, commands, world model)
Phase 3 (later):   SDK interfaces for P2 services (eval, factory, simulation)
Phase 4 (future):  Restrict non-SDK routes to internal network only
```

## Consequences

### Positive
- **Reduced attack surface** — one auth point instead of 225
- **Automatic governance** — every SDK call goes through permission checks
- **Context injection** — agent_id/tenant_id/thread_id always present
- **No HTTP overhead** — in-process service calls for co-located agents
- **Consistent interface** — every service follows the same pattern
- **Easier auditing** — audit SDK interfaces, not 225 routes
- **Type safety** — SDK methods have typed signatures vs raw HTTP

### Negative
- **SDK coupling** — agents must use Python SDK (mitigated: HTTP routes remain for non-Python clients)
- **Migration effort** — existing consumers need updating
- **SDK versioning** — interface changes require SDK updates

### Risk Mitigation
- HTTP routes remain available as fallback
- SDK is backwards-compatible (new interfaces don't break existing ones)
- Lazy loading prevents startup overhead

## References

- **ADR-0061:** L9 Facade Pattern for Simplified API
- **ADR-0101:** DAG Executors via SDK (first application of this principle)
- **SDK:** `SDK/SDK.py` — current 11 interfaces
- **API Audit:** 225+ routes across 30+ routers (2026-02-14)
