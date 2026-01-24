# TODO

> **Last Updated:** 2026-01-21 (PRs 28-30 merge tracking, adaptive cache, api/server.py deferred)

---

## 🔴 High Priority

### PRs #28, #29, #30 Merge (BLOCKED on CI)

**Status:** CI failing on all 3 PRs — Manus fixing (prompts sent)

| PR | Title | CI Status | Blocker |
|----|-------|-----------|---------|
| #28 | ExecutorComposer + DIContainer | ❌ FAILED | CI Gates, Docker Validation, Path Safety |
| #29 | Observability Infrastructure | ❌ FAILED | CI Gates, Docker Validation, Path Safety |
| #30 | Memory & Governance | ❌ FAILED | CI Gates, Docker Validation, Path Safety |

**Merge Order:** #28 → #29 → #30 (dependency chain)

**Post-Merge TODO:**
- [ ] Wire `DeduplicationEngine` into `memory/consolidation.py` `_run_deduplication()`
- [ ] Wire `registry_cache.py` into `core/tools/registry_adapter.py`
- [ ] Add tracing decorators to high-traffic routes

**DEFERRED:** `api/server.py` refactor → separate future PR

---

### Tool Registry Adaptive Cache (ADR-0050 Extension)

**Status:** Future enhancement — add after PR #30 merged

**Current:** Fixed 5-minute TTL for all tools in `core/tools/registry_cache.py`

**Proposed:** HOT tools get longer TTL based on access frequency:
- `>100 accesses` → 1 hour TTL
- `>10 accesses` → 10 min TTL  
- `<10 accesses` → 5 min TTL (default)

**Files to update:**
- `core/tools/registry_cache.py` — Add access counter + adaptive TTL logic
- `readme/ADR/0050-tool-registry-cache.md` — Document adaptive behavior

**Priority:** 🟢 Low (optimization, not blocking)

---

### Agent/Tenant ID Naming Review

**Status:** Review needed

**Issue:** L9 has multiple identifiers for the same entities, causing confusion:

| Identifier | What It Is | Canonical? |
|------------|------------|------------|
| `l-cto` | L's agent_id | ✅ PRIMARY |
| `l9-standard-v1` | Alias for l-cto (config name) | Keep as alias |
| `l9-kernel` | MCP memory source field | Different concept (source, not agent) |
| `cursor` | Cursor's agent_id | ✅ PRIMARY |
| `cursor-agent` | Folder name for Cursor files | Should rename to `cursor`? |

**Questions to resolve:**
1. Should `agents/cursor/` folder be renamed to `agents/cursor/`? (consistency)
2. Should `l9-kernel` MCP source be changed to `l-cto`? (reduce confusion)
3. Should we deprecate `l9-standard-v1` eventually or keep as permanent alias?

**Files using these identifiers:**
- `core/agents/kernel_registry.py` — Aliases l-cto ↔ l9-standard-v1
- `mcp_memory/src/main.py` — Uses `l9-kernel` as source
- `agents/cursor/cursor_memory_kernel.py` — Uses `cursor`
- `runtime/kernel_loader.py` — Checks for multiple L aliases

---

### UUID Standardization Refactor

**Status:** Deferred — bigger refactor for later

**Issue:** L9 mixes UUID objects and UUID strings, causing conversions like:
```python
UUID(source_packet) if isinstance(source_packet, str) else source_packet
```

**Decision needed:** Standardize on:
- Always store as `str` (simpler, JSON-friendly)
- Always store as `UUID` object (type-safe, DB-native)

**Files affected:** `memory/substrate_repository.py`, `core/schemas/packet_envelope.py`, many others

---

### Gmail Client Thread ID Logic Review

**Status:** Review needed

**File:** `email_agent/gmail_client.py:597-603`

**Issue:** When forwarding email, if thread lookup fails, we set `thread_id = None` and continue. This may cause:
- Forward appears as new thread instead of reply
- Potential conversation fragmentation

**Question:** Is this acceptable fallback or should we fail/warn?

---

### Ruff Unused Variable Review (GMP-78)

**Status:** Review needed for 4 cases

| Case | File | Variable | Decision Needed |
|------|------|----------|-----------------|
| 3 | `orchestration/plan_executor.py:512` | `step_map` | DELETE or DEVELOP? Map created but iteration uses `plan.steps` directly. If O(1) lookup needed, wire it up. |
| 7 | `core/governance/approval_manager.py:415` | `now` | Clarify: `is_expired()` calculates time internally. Is `now` needed for something else or truly dead? |
| 9 | `ir_engine/ir_to_plan_adapter.py:450` | `removed` | Review: `removed = plan.steps.pop(idx)` — is removed step needed for logging? |
| 10 | `ci/check_syntax.py:348` | `original_lines` | Add rollback logic (see `scripts/deployment/rollback_vps.sh` for pattern) or delete |

**Reference:** GMP-78 /reasoning analysis

---

### Dead Code Investigation (77 findings)

**Status:** Audit complete, manual triage needed

**Summary:**
- Phase 1: Found 306 dataclass fields
- Phase 2: Eliminated 229 false positives 
- Remaining: 77 findings (45 HIGH, 21 MEDIUM, 11 LOW)

**Actions:**
- [ ] DELETE CalendarAdapterConfig entirely (not wired, unused)
- [ ] DEPRECATE EmailAdapterConfig (replaced by email_agent/)
- [ ] REVIEW Memory/RAG fields: `Memory.semantic_importance`, `HybridResult.vector_hit`, `HybridResult.enrichment` — likely bugs worth wiring up
- [ ] REVIEW runtime/superprompt_emitter.py fields: `gaps_to_fill`, `expected_format`
- [ ] REVIEW core/evaluation/evaluator.py fields: `expected_output`, `success_criteria`

**Reports:**
- `reports/dead_code_baseline.json` — Phase 1 raw findings
- `reports/dead_code_resolved.json` — Phase 2 after false positive filtering
- `reports/dead_code_risk_matrix.md` — Human-readable categorization

**Note:** Many "HIGH" findings are config placeholders for future features (added to `.vultureignore`).

---

### Memory Graph Cleanup

**Status:** ✅ COMPLETE (2026-01-13)

**Executed:**
- [x] Deleted 2 trash embeddings containing error messages via VPS PostgreSQL
  - `1a45f42c-0fbc-460e-b916-0344b12e7645` (SESSION 2026-01-11 with errors)
  - `a3749a07-4b6b-40ca-ba77-53511a73e192` (SESSION 2026-01-09 with errors)
  - Before: 14,773 embeddings → After: 14,771 embeddings

**Context:**
- Original estimate was 52 trash embeddings, but most were already cleaned or excluded
- Re-indexing of high-value content is complete (GMP reports, errors, architecture, preferences, tool usage)
- One LESSON embedding (`d77b0fd2...`) mentions error text but is VALID (documents GMP-42 fix)

**Verification (all 3 scripts run):**
- [x] `python3 scripts/memory/cleanup_trash_embeddings_via_api.py --dry-run` — Only 1 false positive remains (valid LESSON)
- [x] `python3 scripts/memory/generate_delete_sql.py` — Generated SQL, 2 trash IDs identified
- [x] `python3 scripts/memory/check_embeddings_via_api.py` — Returns 0 results for test queries (search is clean)

### L's Memory — Local Docker Verification

**Blocker**: NO GitHub push, NO VPS deployment until local Docker works.

**Status**: All phases complete, but need ongoing verification:
- [ ] **Confirm local Docker memory is still healthy** (Postgres/Neo4j/Redis up; memory_write + memory_search smoke)
- [x] **Enforce `PacketValidator`** at the ingestion chokepoint — ✅ Done (GMP-55, integrated in `substrate_service.py:write_packet()`)

**Completed Phases** (archived):
- ✅ Phase 1: Diagnose Current State (2026-01-07)
- ✅ Phase 2: Memory Write Path (2026-01-07)
- ✅ Phase 3: Memory Read Path (2026-01-07)
- ✅ Phase 4: End-to-End Verification (2026-01-07)

---

## 📋 Immediate Next Steps

- [x] **Fix PATH for git hooks**: ✅ DONE (2026-01-14) — Added to `~/.zshrc`:
  ```bash
  export PATH="$HOME/Library/Python/3.9/bin:$PATH"
  ```

- [x] **S3 Backup System**: ✅ DONE (2026-01-18) — Full PostgreSQL + Config backup to S3
  - Created `scripts/backup/backup_l9_memory.sh` (backup script)
  - Created `scripts/backup/restore_l9_memory.sh` (restore script)
  - Created `scripts/backup/setup_s3_bucket.sh` (S3 bucket setup)
  - S3 bucket `l9-backups` created with 30-day lifecycle policy
  - AWS CLI installed on Mac and VPS
  - First backup uploaded: 12.4MB PostgreSQL + 2.3KB config
  - Deprecated old scripts moved to `_archived/deprecated_backup_scripts/`

- [x] **Set VPS backup cron** (12-hour interval): ✅ DONE (2026-01-19)
  - Runs at 00:00 and 12:00 daily
  - Logs to `/opt/l9/logs/l9-backup-cron.log`

- [ ] **Test deployment script** locally: `./scripts/deploy_agent_executor.sh`
- [ ] **Test server startup** to verify fail-loudly behavior (GMP-47 removed silent stubs)
- [ ] **Test Slack integration** after deployment to verify agent_executor responds

---

## 🔧 Current Work Files

<!-- Files currently being worked on this run -->
- `api/server.py`
- `api/routes/modules.py`
- `core/moduleregistry.py`
- `core/tools/registry_adapter.py`
- `core/tools/sanitizer.py`
- `tests/unit/test_tool_input_sanitizer.py`
- `tests/unit/test_registry_adapter_sanitization.py`
- `reports/Report_GMP-45-ToolInputSanitizer-ModuleRegistry.md`

---

## ❓ Blockers / Questions

**Awaiting Decisions:**
- [ ] Decide on exact scope names (`cursor` vs `cursor-dev` vs `igor`)

**Resolved (2026-01-09):**
- ✅ **VPS Neo4j Auth**: `NEO4J_PASSWORD=FVmgaD1diPcz41zRbYLLP0UzyGvAi4E`
- ✅ **VPS Postgres**: `POSTGRES_USER=postgres`, `POSTGRES_PASSWORD=8e4fXWM6Q3M87*b3`, `POSTGRES_DB=l9_memory`
- ✅ **Caddy config**: `/etc/caddy/Caddyfile` (found + verified)

---

## 🟣 Deferred Work

### Strategy Memory Phase 2: RAFA & Agent Q (GMP-103 Follow-up)

**Status**: Deferred — Phase 1 Auto-Capture complete (GMP-103)

**Source**: `current_work/Strategy Memory for Repeat Task Optimization/`

**Context**: Strategy Memory enables L9 to remember and reuse successful planning strategies. Phase 0 (retrieval-only) and Phase 1 (auto-capture) are complete. Phase 2 adds advanced learning capabilities.

| Feature | Description | Effort | Priority |
|---------|-------------|--------|----------|
| **RAFA Adapter** | Retrieval-Augmented Fine-tuning Adapter — adapts retrieved strategies to new contexts via in-context learning | 4-6 hours | 🟡 Medium |
| **Agent Q** | Q-learning-based strategy scoring — learns optimal strategy selection from feedback over time | 6-8 hours | 🟡 Medium |
| **Native Vector Index** | Neo4j 5.11+ vector index for embeddings (currently uses pgvector) | 2-3 hours | 🟢 Low |

**RAFA Adapter Scope:**
- [ ] Create `memory/rafa_adapter.py` — in-context strategy adaptation
- [ ] Integrate with `PlanExecutor.maybe_apply_strategy()` — adapt before execute
- [ ] Add `was_adapted` and `adaptation_distance` tracking to feedback
- [ ] Create unit tests for adaptation logic

**Agent Q Scope:**
- [ ] Create `memory/agent_q.py` — Q-value tracking per strategy-context pair
- [ ] Implement exploration/exploitation (ε-greedy or UCB)
- [ ] Wire into retrieval scoring (boost high Q-value strategies)
- [ ] Add feedback loop to update Q-values on execution outcomes
- [ ] Create unit tests for learning dynamics

**Prerequisites:**
- ✅ Phase 0: Retrieval-only (Neo4j service, hybrid scoring) — **COMPLETE**
- ✅ Phase 1: Auto-capture (trigger, threshold, tests) — **COMPLETE** (GMP-103)

**Reference**: 
- `reports/GMP-Report-103-Strategy-Memory-Phase1-AutoCapture.md`
- `memory/neo4j_strategy_memory.py` (current implementation)
- `orchestration/plan_executor.py` (integration point)

---

### Auto-Wiring & WebSocket Consolidation (Gap Analysis 2026-01-19)

**Source:** `current_work/01-19-2026/Autowiring3/` and `current_work/01-19-2026/L9_AUTOWIRING2/`

#### Missing Runtimes

| Runtime | File | Status | Notes |
|---------|------|--------|-------|
| Multi-Agent Debate Runtime | `core/runtimes/debate_runtime.py` | ❌ Not created | Multiple agents debate → consensus |
| Self-Refinement Runtime | `core/runtimes/refinement_runtime.py` | ❌ Not created | Agent reflects on mistakes → refines |
| Tool-Augmented Generation Runtime | `core/runtimes/tag_runtime.py` | ❌ Not created | Semantic tool retrieval → dynamic binding |

**Existing:** `core/runtimes/react_runtime.py` ✅ (Think → Act → Observe loop)

#### WebSocket Consolidation — ✅ COMPLETE (verified 2026-01-19)

| Task | Status | Evidence |
|------|--------|----------|
| `/lws` route through `ws_orchestrator` | ✅ DONE | `server.py:3478` → `ws_orchestrator.handle_incoming()` → `handle_conversation_task()` |
| `verify_ws_token()` centralization | ✅ DONE | `runtime/websocket_orchestrator.py:63-120`, imported by server.py |
| Delete `/chat` endpoint | ✅ DONE | Removed, comments at lines 3117-3121 point to `/lchat` |
| Delete legacy flags | ✅ DONE | `L9_ENABLE_LEGACY_CHAT` and `L9_ENABLE_LEGACY_SLACK_ROUTER` removed from settings |
| `runtime/background_tasks.py` | ✅ DONE | 286 lines, `BackgroundTaskRegistry` fully implemented |

**TODO (remaining):**
- [ ] Create Multi-Agent Debate Runtime
- [ ] Create Self-Refinement Runtime
- [ ] Create Tool-Augmented Generation Runtime

---

### Scaffolding / Future Features (from Dead Code Audit)

**Status:** Scaffolding only — not dead code, just not yet exposed via API routes

**Orchestrators (no API exposure yet):**
| Feature | File Path | Purpose |
|---------|-----------|---------|
| MetaOrchestrator | `orchestrators/meta/orchestrator.py` | Blueprint evaluation (choosing between approaches) |
| WorldModelOrchestrator | `orchestrators/world_model/orchestrator.py` | World model operations |
| EvolutionOrchestrator | `orchestrators/evolution/orchestrator.py` | Evolutionary improvement cycles |

**Adapter Services (WIP scaffolding):**
| Feature | File Path | Purpose |
|---------|-----------|---------|
| Calendar Adapter | `api/adapters/calendar_adapter/` (4 files) | Calendar integration |
| Email Adapter | `api/adapters/email_adapter/` (4 files) | Email integration |
| Twilio Adapter | `api/adapters/twilio_adapter/` (4 files) | SMS/Voice integration |

**TODO (when developing these):**
- [ ] Create `/orchestrators/evolution` router for kernel evolution management (GMP-91 follow-up)
  - Endpoints: `GET /evolution/status`, `POST /evolution/trigger`, `GET /evolution/history`
  - Wire EvolutionOrchestrator in FastAPI lifespan
- [ ] Create API routes for orchestrators (`api/routes/meta.py`, etc.)
- [ ] Wire orchestrators in FastAPI lifespan (follow GMP-87 CursorExecutor pattern)
- [ ] Complete adapter implementations (currently skeleton code)
- [ ] Add adapter config to settings.py
- [ ] Create adapter service tests

**Reference:** GMP-87 dead code audit analysis

---

### CI/CD Enhancements (GMP-78 Review)

**Status**: Deferred — Nice-to-have, not urgent

**Source**: Frontier AI Lab patterns review (Pre-Commit-Hooks-1.md)

| Enhancement | Description | Effort | Priority |
|-------------|-------------|--------|----------|
| **Claude PR Reviewer** | GitHub Action that uses Claude to review PRs | 2-4 hrs | 🟡 Medium |
| **Performance Regression** | Track response times, flag >20% slowdowns | 4-8 hrs | 🟡 Medium |

**Claude PR Reviewer Implementation:**
```yaml
# .github/workflows/pr_review.yml
name: Claude PR Review
on: [pull_request]
jobs:
  claude-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Claude Code Review
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          python3 scripts/ci/claude_pr_reviewer.py \
            --pr-number ${{ github.event.pull_request.number }}
```

**Performance Regression Implementation:**
- Requires baseline metrics from Prometheus/Grafana first
- Track: API latency p50/p95, memory query time, embedding generation time
- Alert on >20% degradation

**Prerequisites:**
- [ ] Prometheus/Grafana stack fully operational
- [ ] Baseline metrics collected for 1+ weeks
- [ ] GitHub Actions configured for L9 repo

---

### Cross-DB Conflict Resolution Loop

**Status**: Deferred — Future enhancement

**Source**: `current_work/10-TODO's.md` analysis (2026-01-14)

**Problem**: When both PostgreSQL and Neo4j return data for the same query, results may conflict (e.g., "Sum of Sales" in SQL vs "Count of Nodes" in Graph).

**Solution**: Implement a "Reflector" step where the agent compares outputs from both databases and identifies discrepancies before answering.

**Scope**:
- [ ] Add discrepancy detector to Saga pattern (`memory/saga.py`)
- [ ] Create `ConflictResolver` class that compares PG vs Neo4j results
- [ ] Define conflict types: count mismatch, value drift, missing entity
- [ ] Add resolution strategies: prefer PG, prefer Neo4j, merge, escalate
- [ ] Emit PacketEnvelope with `kind=CONFLICT_DETECTED` for audit trail

**Estimated Effort**: 4-6 hours

**Priority**: 🟡 Medium — Useful for complex cross-DB queries

---

### Multi-Agent Specialization (DB-Specific Agents)

**Status**: Deferred — Future enhancement

**Source**: `current_work/10-TODO's.md` analysis (2026-01-14)

**Problem**: Current agents see all tools (SQL + Cypher), causing "context dilution" and reducing accuracy.

**Solution**: Split into specialized agents: **Postgres Analyst** (SQL only), **Neo4j Cartographer** (Cypher only), **Manager** (routing).

**Benefits**:
- Smaller context window per agent = higher accuracy
- Each agent is expert in one DB type
- Manager routes to appropriate specialist

**Scope**:
- [ ] Create `PostgresAnalystAgent` — SQL tools only
- [ ] Create `Neo4jCartographerAgent` — Cypher tools only  
- [ ] Create `DBManagerAgent` — routes queries to specialists
- [ ] Update tool registry with agent-type filtering
- [ ] Wire into existing orchestration layer

**Estimated Effort**: 8-12 hours

**Priority**: 🟡 Medium — Improves accuracy for DB-heavy workloads

**Note**: Partially exists in `orchestration/` but not fully specialized per DB type.

---

### Symbolic Computation Service (DISABLED)

**Status**: DISABLED (2026-01-13) — Not actively used

**Location**: `services/symbolic_computation/`

**What it is**: Standalone SymPy/NumPy service for symbolic math (Quantum AI Factory)

**What was disabled**:
- Dockerfile CMD changed from running pytest to echo message
- Service has its own docker-compose.yml (NOT part of main L9 stack)

**TODO** (when needed):
- [ ] Review if this service is still needed
- [ ] If yes, re-enable CMD in Dockerfile: `CMD ["python", "-m", "pytest", "tests/"]`
- [ ] Consider converting to actual server if needed (currently just runs tests)
- [ ] Integrate into main docker-compose.yml if production-ready

---

### Frontier Memory Retrieval Architecture

**Status**: 🟡 IN PROGRESS — Phase 1 (Database Schema) complete

**Completed (2026-01-15):**
- ✅ **GMP-80-A3:** `semantic_facts` table (migration 0018)
- ✅ **GMP-80-A4:** `episodic_events` + `episodic_semantic_links` tables (migration 0019)
- ✅ Pydantic DTOs: `SemanticFactRow`, `EpisodicEventRow`, `EpisodicSemanticLinkRow`
- ✅ Repository CRUD methods for both semantic and episodic operations

**Remaining GMPs:**
| GMP ID | Task | Effort | Status |
|--------|------|--------|--------|
| GMP-80-A2 | Create Phase 0-6 Cursor prompts | 3-4 days | ✅ Complete |
| GMP-80-A5 | Implement Identity Tier | 2-3 days | ✅ Complete |
| GMP-80-A6 | Strategy-based retrieval | 3-5 days | ✅ Complete |
| GMP-80-A7 | Active memory management | 5-7 days | ✅ Complete |

**🎉 GMP-80 SERIES COMPLETE — Frontier Memory Retrieval Architecture fully implemented.**

**Next Step:** Apply migrations to VPS, then start GMP-80-A5 (Identity Tier)

**Reference**: `current_work/MEMORY RETRIEVAL ARCHITECTURE.md`
**Report**: `reports/GMP_Report_GMP-80-A3A4-Semantic-Episodic-Schema.md`

---

### Anti-Pattern Regression Tests (GMP-58 Follow-up)

**Status**: Scoped, ready to implement

**Context**: Identified during Memory Ingestion Pipeline Audit (2026-01-13). GMP-58 fixed frozen model mutation bug — need regression tests to prevent similar bugs from returning.

**Deliverable**: Create `tests/ci/test_anti_patterns.py` with 5 regression test categories:

| # | Test | Anti-Pattern | Severity |
|---|------|--------------|----------|
| 1 | `test_auto_tagging_with_frozen_envelope` | Frozen model mutation (GMP-58) | 🔴 Critical |
| 2 | `test_no_hardcoded_user_paths` | `/Users/ib-mac` in prod code | 🔴 Critical |
| 3 | `test_no_bare_except_in_core` | `bare except:` swallows errors | 🟠 High |
| 4 | `test_no_print_in_core_modules` | `print()` breaks structured logging | 🟠 High |
| 5 | `test_no_stdlib_logging_in_core` | stdlib `logging` vs `structlog` | 🟡 Medium |

**Current Anti-Pattern Counts** (from analyze+evaluate 2026-01-13):
- `print()` in production: 17 files
- `bare except:`: 9 files
- Hardcoded paths: 10 files
- stdlib `logging`: 8 files
- `requests` vs `httpx`: 10 files

**TODO**:
- [ ] Create `tests/ci/test_anti_patterns.py`
- [ ] Add to CI pipeline (`ci/run_ci_gates.sh`)
- [ ] Fix existing violations or add to `.vultureignore` equivalent

**Reference**: GMP-58 Report (`reports/GMP_Report_GMP-58-Fix-Frozen-Envelope-Tag-Bug.md`)

---

### Dual Ingestion Path Consolidation

**Status**: SIMPLIFIED (2026-01-13) — Using IngestionPipeline ONLY

**Decision**: Route all ingestion through `IngestionPipeline` only until core pipeline is stable. DAG path (reasoning, insights, world model) deferred.

**Current Flow** (SIMPLIFIED):
```
ingest_packet() → IngestionPipeline.ingest()
                      ↓
              ┌───────────────────┐
              │ Validation        │
              │ Security audit    │
              │ Auto-tagging      │
              │ packet_store      │ (transactional)
              │ memory_events     │ (transactional)
              │ Embeddings        │
              │ Neo4j sync        │
              │ Critical checkpoint│
              └───────────────────┘
```

**What's ACTIVE now**:
- ✅ PacketValidator
- ✅ Security audit (injection detection)
- ✅ Auto-tagging
- ✅ Transactional writes (packet_store + memory_events)
- ✅ Embedding generation
- ✅ Neo4j sync
- ✅ Critical checkpoint trigger

**What's DEFERRED** (DAG path):
- ❌ Reasoning block generation
- ❌ Insight extraction
- ❌ World model trigger
- ❌ Graph checkpoint (LangGraph)

**TODO** (when ready to add DAG):
- [ ] Wire DAG as optional enhancement after `pipeline.ingest()`
- [ ] Add feature flag `L9_ENABLE_DAG_INGESTION`
- [ ] Test DAG path doesn't break core ingestion

**Files**:
- `memory/ingestion.py` — `ingest_packet()` now uses IngestionPipeline directly
- `memory/substrate_graph.py` — DAG (not currently used for ingestion)
- `memory/substrate_service.py` — `write_packet()` (bypassed for now)

**Reference**: `reports/AUDIT_PacketEnvelope_PacketStore_Integration.md` (Section 5)

---

### CodeGenAgent System

**Status**: Deferred until L's memory is fully working in local Docker.

#### 1. Document & Standardize Specs
- [ ] Add `status:` field to all 67 specs missing it
- [ ] Add Suite 6 governance headers to all specs

**Completed:**
- [x] Extract 90 YAML specs from chat transcript
- [x] Organize into `specs/` (81) and `patches/` (archived)
- [x] Apply 8 patch merges + convert 14 standalone patches
- [x] Create README.md documenting CGA vision

#### 2. Build Extraction Pipeline (DEFERRED)
- [ ] Create `codegen_extractor.py` — extracts `code:` blocks from YAML specs
- [ ] Validate all `filename:` target paths
- [ ] Build dependency graph from `wiring:` sections
- [ ] Implement linter integration

#### 3. Implement CGA Core (DEFERRED)
- [ ] `agents/codegen_agent/codegen_agent.py` — main agent
- [ ] `agents/codegen_agent/meta_loader.py` — YAML parsing
- [ ] `agents/codegen_agent/c_gmp_engine.py` — code expansion
- [ ] `agents/codegen_agent/file_emitter.py` — file writing with rollback
- [ ] `agents/codegen_agent/pipeline_validator.py` — validation

#### 4. Wire into L9 (DEFERRED)
- [ ] Register CGA in AgentRegistry
- [ ] Add API routes (`api/routes/codegen.py`)
- [ ] Create orchestration DAG
- [ ] Bind to governance hooks

### Agent Persistence GMP Pack (2026-01-11)

**Status**: DEFERRED — Analysis complete, not urgent per current priorities

**Analysis Summary:**
- **Tech Debt Score**: 62% (🟡 MEDIUM)
- **Existing Code**: `memory/agent_persistence.py` has partial implementation (create/restore work, but list/delete are stubs)
- **GMP Pack Quality**: ✅ Excellent (95% GMP compliance, frontier lab patterns)
- **Conflict**: Pack assumes clean slate, but existing code exists — needs merge strategy

**Key Findings:**
- ✅ Core methods partially implemented (create_checkpoint, restore_checkpoint work)
- ❌ Integration wiring missing (0/6 points wired — executor, server, approval_manager, ingestion, agent_instance)
- ❌ Production features missing (retention engine, checksums, schema versioning, observability)
- ⚠️ Stub methods need completion (list_checkpoints, delete_old_checkpoints return empty/0)

**Recommendation**: DEFER until:
1. L's memory fully working in local Docker (current priority)
2. Agent state recovery becomes urgent requirement
3. Need production-grade checkpointing (retention, integrity, observability)

**If Implementing:**
- **Phase 1** (6-7 hours): Resolve code conflict + wire 6 integration points
- **Phase 2** (8-10 hours): Complete stub methods + add PacketEnvelope emission
- **Phase 3** (6-8 hours): Production features (retention, checksums, schema versioning, observability)
- **Total**: ~20-25 hours

**Alternative Quick Path** (3-4 hours):
- Keep current basic implementation
- Add integration wiring only (make checkpoints functional)
- Defer production features until needed

**Reference**: `docs/__Notes/agent_persistence.py/` (8 GMP stage files + runbook)

### Memory Files Packet (Advanced Memory Features)

**Status**: Partially implemented (~30-40%)

**Location**: `current_work/Memory Files/`

**Overview**: 6 specification/research documents for advanced memory and AI system concepts.

| File | Purpose | Status |
|------|---------|--------|
| `Data_Pipeline_Orchestration_v4.0.md` | ERP/Odoo data pipeline (Mack domain) | ❌ External to L9 |
| `chunking-protocol.md` | Build orchestrator for chunked code gen | ❌ Prompt protocol only |
| `DSL_Compiler_Description.md` | Governance rules MD→FOL JSON compiler | ❌ Not implemented |
| `enforceable_recursive_extractor.prompt.md` | Schema-enforced preference/SOP extractor | ⚠️ Partial (extractors exist) |
| `implement belief calibration in LLM driven agents.md` | Belief calibration with confidence tracking | ⚠️ Partial (fields exist) |
| `inverse reinforcement learning (IRL).md` | Intent detection via IRL | ❌ Research only |

**What's IMPLEMENTED:**
- ✅ Confidence fields (`confidence_scores`, `KnowledgeFact.confidence`, etc.)
- ✅ Semantic search with pgvector
- ✅ Packet ingestion DAG with validation
- ✅ TTL expiration in `ConsolidationPipeline`
- ✅ Idempotency patterns in executor/adapters

**What's STUB/PARTIAL:**
- ⚠️ Deduplication (`consolidation.py` — marked "not fully implemented")
- ⚠️ Archival (basic query exists, actual logic is TODO)
- ⚠️ Summarization (structure only, marked TODO)

**What's NOT IMPLEMENTED:**
- [ ] DSL Compiler (Markdown → FOL JSON) for governance rules
- [ ] Belief Calibration Loop (ECE/Brier tracking, confidence adjustment)
- [ ] Multi-Agent Belief Consensus (BCCS-style weighted coordination)
- [ ] Complete consolidation strategies (dedup, archival, summarization)

**Next Steps (if prioritized):**
1. Complete `ConsolidationPipeline` strategies (dedup, archival, summarization)
2. Build belief calibration module with confidence tracking over time
3. Create DSL compiler for governance rule enforcement (if needed)

**Reference**: Analysis performed 2026-01-14

---

### Emma/L9 Substrate Integration

**Status**: Analysis complete, most enhancements done. Remaining items:

#### Remaining L9 Core Enhancements
- [ ] Add crash recovery slide to roadmap
- [ ] Add step-level priority to PlanStep in plan_executor

**Completed:**
- [x] Add feedback_events table to L9 core substrate (0009)
- [x] Add effectiveness tracking to reflection_store (0009)
- [x] Build core/commands/intent_extractor.py per GMP spec (GMP-11 complete)
- [x] All Emma Substrate Enhancements (from L9 0008)

**Findings from Jan 1 Analysis:**
- **TaskRoute vs AgentExecutorService**: BOTH active, NOT redundant. TaskRoute = routing decisions, AgentExecutorService = execution. Different layers.
- **Intent Extraction**: ✅ BUILT via GMP-11 - `core/commands/intent_extractor.py` now exists with LLM + rule-based fallback.
- **Priority System**: Fragmented across TaskRoute.priority, AgentTask.priority, ws_task_router.default_priority. Needs unification.
- **Graph Checkpoints**: Missing fields for comprehensive recovery (checkpoint_version, parent_checkpoint_id, execution_plan_snapshot).

---

## ✅ Completed

### Memory Graph Population (2026-01-11)

- [x] Fixed semantic search threshold (added min_score parameter, default 0.5)
- [x] Fixed knowledge facts queries (handle empty subject)
- [x] Created extraction pipeline test
- [x] Created GMP reports indexing script
- [x] Extended Slack ingestion for conversation indexing
- [x] Created tool usage indexing script
- [x] Created error patterns indexing script
- [x] Created architectural decisions indexing script
- [x] Created user preferences indexing script
- [x] Re-indexed all high-value content (GMP, errors, architecture, preferences, tools)
- [x] Generated SQL for trash embedding deletion

### L's Memory — Local Docker (2026-01-07)

- [x] Phase 1: Diagnose Current State — All containers verified, tables confirmed
- [x] Phase 2: Memory Write Path — POST /api/v1/memory/packet works, embeddings stored
- [x] Phase 3: Memory Read Path — Semantic search operational, Neo4j queries work
- [x] Phase 4: End-to-End Verification — Full DAG pipeline functional

### Agent Executor Deployment (2026-01-10)

- [x] GMP-48 — Agent Executor Deployment Automation (verification script, deployment script, CI integration)
- [x] Unstub ResearchSwarmOrchestrator (GMP-47)

---

## 📝 Notes

### MCP Memory (DEPRECATED - 2026-01-07)

**DEPRECATED:** MCP Memory server was never implemented. Memory access works via REST API.

**Current Memory Access (WORKING):**
```bash
python3 .cursor-commands/cursor-memory/cursor_memory_client.py [command]
```
- `search "query"` — Semantic search
- `write "content" --kind TYPE` — Write packet
- `inject "task"` — 5-layer context injection
- `health` — Check VPS connectivity

**Archived Files:**
- `_archived/archived_mcp_memory/` — Historical MCP server code
- `~/.cursor/mcp.json` — Removed `l9-memory` entry
- `runtime/mcp_client.py` — Deprecated l9-memory registration
- `core/worldmodel/service.py` — Commented out MCP-Memory system
