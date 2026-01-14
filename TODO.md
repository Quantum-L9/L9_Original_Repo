# TODO

> **Last Updated:** 2026-01-13

---

## 🔴 High Priority

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

**Status**: 🚫 BLOCKED — Waiting on MCP memory testing & confirmation

**Blocker**: Do NOT start until MCP memory is tested and confirmed working in production.

**Scope**: Implement frontier-grade memory retrieval system based on elite AI lab patterns (Anthropic, OpenAI, DeepMind).

**Key Components**:
- 4-tier hierarchical memory (Identity → Project → Session → Working)
- Dual semantic + episodic memory streams
- Graph-based retrieval with multi-factor ranking
- Active memory management (system decides what to encode)
- SQL migrations: `semantic_facts`, `episodic_events`, `episodic_semantic_links`
- Python services: `SemanticMemoryService`, `EpisodicMemoryService`
- Context engineering: hierarchical injection per task

**Reference**: `current_work/MEMORY RETRIEVAL ARCHITECTURE.md`

**Estimated Effort**: 3 phases (Week 1-2: Fix immediate issues, Week 3-8: Architecture upgrade, Week 9-16: Context engineering)

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
