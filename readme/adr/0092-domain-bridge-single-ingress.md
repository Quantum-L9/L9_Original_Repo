# ADR-0092: Domain Bridge as Mandatory Single Ingress Point

- **Status:** Accepted
- **Date:** 2026-02-19
- **Author:** Igor (L-CTO)
- **Category:** ARCHITECTURE / GOVERNANCE
- **Tier:** T3 (Irreversible / High-Impact)
- **Supersedes:** None
- **Related ADRs:** ADR-0006 (PacketEnvelope Audit Trail), ADR-0012 (Memory DAG Pipeline), ADR-0013 (Governance Authority Hierarchy)

---

## Context

L9 currently has multiple paths by which data enters the memory substrate:

1. **`memory/ingestion.py`** — The documented "single entry point" for the SubstrateDAG pipeline.
2. **`memory/graph_memory.py`** — Direct Neo4j writes for conversation graph storage.
3. **`services/research/graph_persistence.py`** — Research findings written directly to Neo4j.
4. **`memory/neo4j_strategy_memory.py`** — Strategy nodes written directly to Neo4j.
5. **`core/integration/wm_to_graph_sync.py`** — World Model state synced back to Neo4j.
6. **`memory/dead_letter.py`** / **`memory/dead_letter_queue.py`** — Failed packets written to Redis.
7. **`memory/graph_search_cache.py`** / **`memory/predictive_cache.py`** — Cache writes to Redis.
8. **`memory/slack_ingest.py`** — Slack idempotency markers written to Redis.
9. **`runtime/rate_limiter.py`** / **`runtime/auth_rate_limiter.py`** — Rate limit counters in Redis.
10. **`runtime/task_queue.py`** — Task dispatch via Redis.
11. **`memory/tool_router.py`** — Tool embedding cache in Redis.
12. **`memory/cache/working_memory_service.py`** — Session-scoped context in Redis.
13. **Batch scripts** (`scripts/memory/load_indexes_to_neo4j.py`, `bootstrap_neo4j_schema.py`, etc.) — Periodic bulk loads.

This proliferation of write paths creates:

- **Governance blind spots:** Data enters substrates without PacketEnvelope validation, principal_id enforcement, or audit trail generation.
- **Schema drift risk:** Writers bypass PacketEnvelope v2.1+ schema enforcement.
- **Impossible auditability:** No single point where all writes can be logged, metered, or blocked.
- **Security surface sprawl:** Each write path is a potential attack vector without centralized authentication/authorization.

## Decision

### The Domain Bridge (formerly DomainTensorBridge / DBT, soon to be renamed SDK) becomes the **mandatory single ingress point** for ALL data entering L9 substrates.

**Architectural position:** The Domain Bridge sits **upstream of** `memory/ingestion.py`. It is the chokepoint through which every write — to Postgres, Neo4j, Redis, pgvector, or the World Model — must pass.

```
External Sources          Internal Agents          Batch Jobs
      │                        │                       │
      └────────────┬───────────┘───────────────────────┘
                   │
          ┌────────▼─────────┐
          │   DOMAIN BRIDGE  │  ← Single Ingress (this ADR)
          │   (SDK Gateway)  │
          │                  │
          │  ┌─────────────┐ │
          │  │ Validate PE  │ │  PacketEnvelope v2.1+ required
          │  │ v2.1+ schema │ │  (may upgrade to v2.2)
          │  ├─────────────┤ │
          │  │ Enforce      │ │  principal_id MUST be present
          │  │ principal_id │ │  on every packet
          │  ├─────────────┤ │
          │  │ Governance   │ │  GovernanceEngine.evaluate()
          │  │ check        │ │  before any write proceeds
          │  ├─────────────┤ │
          │  │ Audit trail  │ │  Structured log + packet
          │  │ emission     │ │  provenance stamp
          │  └─────────────┘ │
          └────────┬─────────┘
                   │
          ┌────────▼─────────┐
          │   INGESTION      │  ← memory/ingestion.py
          │   PIPELINE       │    (existing SubstrateDAG)
          └────────┬─────────┘
                   │
       ┌───────────┼───────────┐
       ▼           ▼           ▼
   Postgres     Neo4j       Redis/pgvector
```

### Enforcement Rules

1. **PacketEnvelope v2.1+ (possibly v2.2) is mandatory.** Every payload entering the Domain Bridge MUST be wrapped in a valid `PacketEnvelope` with:
   - `packet_id` (UUID)
   - `packet_type` (from registered enum)
   - `principal_id` (non-null — identifies the human, agent, or system principal that initiated the write)
   - `provenance` block (source, timestamp, trace_id)
   - `metadata` block (at minimum: `created_at`, `source_system`)

2. **`principal_id` is non-negotiable.** Every write to every substrate MUST carry a `principal_id`. Anonymous writes are forbidden. System-initiated writes use well-known system principal IDs (e.g., `system:scheduler`, `system:bootstrap`, `agent:<agent_id>`).

3. **Governance gate is mandatory.** The Domain Bridge calls `GovernanceEngine.evaluate()` on every inbound packet before forwarding to the ingestion pipeline. Denied packets are rejected with structured error responses and audit trail entries.

4. **All other direct write paths will be sealed.** Every file identified in the Context section that writes directly to a substrate will be refactored to route through the Domain Bridge. Direct client instantiation of `Neo4jClient`, `redis_client`, or `SubstrateRepository` for write operations outside the Domain Bridge is forbidden.

5. **Minimal API surface.** The Domain Bridge exposes exactly:
   - `async submit(packet: PacketEnvelope) -> WriteResult` — single-packet ingestion
   - `async submit_batch(packets: list[PacketEnvelope]) -> BatchWriteResult` — batch ingestion
   - `async health() -> HealthStatus` — liveness/readiness probe

6. **Redis operational writes are exempt but classified.** The following Redis write patterns are classified as **operational infrastructure** (not data ingestion) and are exempt from PacketEnvelope wrapping, but MUST still carry `principal_id` in their key namespace:
   - Rate limit counters (`runtime/rate_limiter.py`)
   - Idempotency markers (`memory/slack_ingest.py`)
   - Working memory session cache (`memory/cache/working_memory_service.py`)
   - Dead letter queue entries (`memory/dead_letter.py`) — these already contain the original PacketEnvelope

   These operational writes MUST be audited via structlog with `principal_id` in the log context. A future ADR may tighten this exemption.

### Renaming

The component currently known as `DomainTensorBridge` (directory: `domain_tensor_bridge/`) will be renamed to **`SDK`** or **`DomainBridge`**. The final name is TBD and will be settled before implementation begins. This ADR uses "Domain Bridge" as the canonical reference.

## Consequences

### Positive
- **Single audit chokepoint** — Every write to every substrate is observable, governable, and auditable from one location.
- **Schema enforcement** — PacketEnvelope v2.1+ is guaranteed system-wide; no more v1 payloads sneaking through side channels.
- **Principal accountability** — Every byte stored in L9 is traceable to a principal via `principal_id`.
- **Reduced attack surface** — One ingress point to secure instead of 13+.
- **Governance-by-default** — Impossible to bypass governance checks for data writes.

### Negative
- **Migration effort** — 13+ write paths must be refactored. Some (batch scripts, graph_memory) require significant rework.
- **Latency increase** — Adding a governance gate and validation layer to every write adds ~2-5ms per packet.
- **Operational Redis exemption** — Rate limiters and caches retain direct Redis access, creating a controlled exception that must be monitored.

### Risks
- **Batch script breakage** — Scripts like `load_indexes_to_neo4j.py` and `bootstrap_neo4j_schema.py` run during deployment; they must be updated or granted explicit bootstrap principal IDs.
- **Performance regression** — High-throughput paths (Slack ingest, embedding writes) must be load-tested after migration.

## Implementation Phases

| Phase | Scope | Files Affected |
|-------|-------|----------------|
| **Phase A: Schema** | Add `principal_id` to PacketEnvelope v2.1 → v2.2 | `core/schemas/packet_envelope_v2.py` |
| **Phase B: Domain Bridge Gateway** | Build `submit()` / `submit_batch()` / `health()` API on Domain Bridge | `domain_tensor_bridge/gateway.py` (new) |
| **Phase C: Governance Wiring** | Wire `GovernanceEngine.evaluate()` into Domain Bridge submit path | `domain_tensor_bridge/gateway.py`, `core/governance/engine.py` |
| **Phase D: Seal Neo4j Direct Writes** | Refactor `graph_memory.py`, `graph_persistence.py`, `neo4j_strategy_memory.py`, `wm_to_graph_sync.py` | 4 files in `memory/` and `core/integration/` |
| **Phase E: Seal Ingestion Bypass** | Ensure `memory/ingestion.py` only accepts calls from Domain Bridge | `memory/ingestion.py` |
| **Phase F: Seal Batch Scripts** | Add bootstrap principal IDs to batch loaders | `scripts/memory/*.py` |
| **Phase G: Audit Redis Exemptions** | Add structlog `principal_id` context to all exempt Redis writers | `runtime/rate_limiter.py`, `memory/slack_ingest.py`, `memory/cache/working_memory_service.py`, `memory/dead_letter.py` |

## Compliance

- **ADR-0006 (PacketEnvelope Audit Trail):** This ADR strengthens 0006 by making audit trails impossible to bypass.
- **ADR-0012 (Memory DAG Pipeline):** The DAG pipeline remains intact; the Domain Bridge sits upstream of it.
- **ADR-0013 (Governance Authority Hierarchy):** Governance evaluation is now enforced at ingress, not just at agent execution time.
- **ADR-0019 (structlog):** All Domain Bridge logging uses structlog exclusively.

## Open Questions

1. **Final name:** `SDK`, `DomainBridge`, or `L9Gateway`? To be decided before Phase B.
2. **PacketEnvelope version:** v2.1 with `principal_id` added, or bump to v2.2? Depends on whether `principal_id` is additive-only or requires breaking changes.
3. **World Model writes (Phase 4 from roadmap):** The WM trigger node in the SubstrateDAG already fires downstream of ingestion. Confirming whether `world_model/runtime.py` has any write paths that bypass the DAG requires further investigation. This ADR does NOT mandate sealing WM writes until that investigation is complete.

---

*This ADR was created on 2026-02-19 as part of the L9 Single Ingress architecture initiative.*
