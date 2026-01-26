# L9 Development Roadmap

## Completed ✅

### Stage 1: Basic Wiring & Interfaces

- [x] Memory Substrate schema and repository
- [x] Semantic search with pgvector
- [x] World Model engine and state
- [x] WebSocket agent protocol
- [x] PacketEnvelope schema

### Stage 2: Memory + World Model Integration

- [x] Slack ingest → thread context retrieval
- [x] Slack ingest → semantic memory hits
- [x] Insights → World Model orchestrator propagation
- [x] `MemorySubstrateService.trigger_world_model_update()`

### Stage 3: Autonomous Execution

- [x] Mac Agent shell executor (with LocalAPI whitelist)
- [x] Mac Agent browser executor (Playwright automation)
- [x] Mac Agent Python executor (Docker sandbox with subprocess fallback)

---

### Stage 4: LLM-Powered Artifact Generation

- [x] `generate_artifact_with_llm()` function for plans, code, docs
- [x] `draft_work_node` now generates real artifacts via GPT-4
- [x] Context-aware generation (governance rules, project history)
- [x] Auto-detect when code/docs artifacts are needed

---

### Stage 2.5: Memory API & Client SDK (2025-01-27)

- [x] Fixed memory router path: `/memory` → `/api/v1/memory` (matches client SDK expectations)
- [x] Added 8 missing API route handlers in `api/memory/router.py`:
  - `GET /api/v1/memory/packet/{id}` - Get packet by ID
  - `GET /api/v1/memory/thread/{id}` - Get thread packets
  - `GET /api/v1/memory/lineage/{id}` - Get packet lineage
  - `POST /api/v1/memory/hybrid/search` - Hybrid search (semantic + filters)
  - `GET /api/v1/memory/facts` - Query knowledge facts
  - `GET /api/v1/memory/insights` - Query insights
  - `POST /api/v1/memory/gc/run` - Run garbage collection
  - `GET /api/v1/memory/gc/stats` - Get GC statistics
- [x] All 9 MemoryClient SDK methods now have corresponding API endpoints
- [x] Integration tests: 12/12 passing (all new endpoints verified)
- [x] Client SDK tests: Added comprehensive test for all 9 methods
- [x] Created gap analysis documentation (`docs/API_GAP_ANALYSIS.md`)
- [x] Created orchestrator wiring status documentation (`docs/ORCHESTRATOR_WIRING_STATUS.md`)

---

## In Progress 🔄

### Stage 2.7: PacketEnvelope v2.0 Schema Migration

> **Sunset Deadline: 2026-04-05**

**Status:** Schema v2.0.0 is canonical, SchemaRegistry auto-upcasts at runtime. 72 files still import from deprecated modules.

- [x] **Phase 1: Schema Consolidation (Complete)**

  - [x] Created `core/schemas/packet_envelope_v2.py` (v2.0.0 canonical)
  - [x] Added `SchemaRegistry` with chained upcasting (v1.0.0 → v2.0.0)
  - [x] Immutability enforcement (`frozen=True`)
  - [x] Content hash integrity (`compute_content_hash()`, `verify_integrity()`)
  - [x] DAG lineage tracking (`PacketLineage`)
  - [x] Deprecation warnings on import of old modules

- [x] **Phase 2: CI Gate (Complete)**

  - [x] Created `ci/check_schema_deprecation.py`
  - [x] Phase-based enforcement (warnings → errors → block)
  - [x] Excluded tests/docs/archive from gate

- [ ] **Phase 3: Import Migration (~25 active files)**

  - [ ] Migrate `core/agents/executor.py`
  - [ ] Migrate `core/governance/*.py` (3 files)
  - [ ] Migrate `core/compliance/audit_log.py`
  - [ ] Migrate `memory/*.py` (5 files)
  - [ ] Migrate `orchestration/*.py` (3 files)
  - [ ] Migrate `api/*.py` (4 files)
  - [ ] Migrate `services/*.py` (2 files)
  - [ ] Run full test suite

- [ ] **Phase 4: Upgrade Engine Activation**
  - [ ] Activate phases 2-5 via `/api/v1/upgrades/packet-envelope/activate/all`
  - [ ] Add lifespan auto-activation (optional, for persistence across restarts)
  - [ ] Verify Jaeger + Prometheus integration

**Sunset Timeline:**
| Date | Phase | Effect |
|------|-------|--------|
| 2026-01-05 | Phase 1 | Warnings only (current) |
| 2026-02-20 | Phase 2 | Errors in new files |
| 2026-03-22 | Phase 3 | Errors for all |
| 2026-04-05 | Phase 4 | Complete block |

**Files:**

- Canonical schema: `core/schemas/packet_envelope_v2.py`
- Registry: `core/schemas/schema_registry.py`
- CI gate: `ci/check_schema_deprecation.py`
- Upgrade engine: `l9/upgrades/packet_envelope/`

---

### Stage 3.5: Proactive World Model Updates ✅ COMPLETE

- [x] `MemorySubstrateService.query_packets()` for world model polling
- [x] `MemorySubstratePacketSource` implementation
- [x] `create_runtime_with_substrate()` factory function
- [x] Integration with API server startup ✅ (2026-01-08 - fixed `run_loop()` → `run_forever()`)
- [x] Background task for `runtime.run_forever()` ✅ (wired in `api/server.py` lifespan)

---

### Stage 2.6: Orchestrator API Wiring (HIGH PRIORITY) 🚨

- [x] **Phase 1: ActionTool Orchestrator** ✅ COMPLETE (2026-01-01)

  - [x] Add optional import check for `ActionToolOrchestrator` in `api/server.py`
  - [x] Instantiate `ActionToolOrchestrator` in `lifespan()` startup
  - [x] Store in `app.state.action_tool_orchestrator`
  - [x] Mount `api/tools/router.py` at `/tools` prefix
  - [x] Test `/tools/test` and `/tools/execute` endpoints

- [x] **Phase 2: Reasoning Orchestrator** ✅ COMPLETE (2026-01-08)

  - [x] Add optional import check for `ReasoningOrchestrator` in `api/server.py`
  - [x] Instantiate `ReasoningOrchestrator` in `lifespan()` startup
  - [x] Store in `app.state.reasoning_orchestrator`
  - [x] Mount `api/routes/reasoning.py` at `/reasoning` prefix
  - [ ] Test `/reasoning/execute` endpoint (manual verification pending)

- [x] **Phase 3: ResearchSwarm Orchestrator** ✅ COMPLETE (2026-01-08)
  - [x] Add optional import check for `ResearchSwarmOrchestrator` in `api/server.py`
  - [ ] Complete stub implementation in `orchestrators/research_swarm/orchestrator.py` (stub functional, full impl deferred)
  - [x] Instantiate `ResearchSwarmOrchestrator` in `lifespan()` startup
  - [x] Store in `app.state.research_swarm_orchestrator`
  - [x] Mount `api/routes/research.py` at `/research/swarm` prefix
  - [ ] Test `/research/swarm/execute` endpoint (manual verification pending)

**Dependencies:**

- Stage 2.6 blocks: None ✅
- Stage 2.6 enables: Tool execution API ✅, reasoning orchestration API ✅, research swarm API ✅

**Notes:**

- All three orchestrators NOW WIRED (2026-01-08)
- ActionTool and Reasoning are fully implemented
- ResearchSwarm is stub (returns success=True, full orchestration logic deferred)

---

## Planned 📋

### Stage 7: L-CTO Agent Integration (HIGHEST PRIORITY) 🚨

- [ ] **Phase 1: Memory Migration**

  - [x] Archive deprecated Supabase clients (`l-cto/l_memory/memory_client.py`, `kg_client.py`)
  - [ ] Remove Supabase dependencies from `l-cto/memory/` routers
  - [ ] Migrate `MemoryRouterV4` to use `MemorySubstrateService` instead of Supabase
  - [ ] Replace custom L1/MAC/META table routing with `PacketEnvelope` + `agent_id` filtering
  - [ ] Delete deprecated `l-cto/l_memory/` directory (already archived)

- [ ] **Phase 2: Agent Architecture Refactor**

  - [ ] **CRITICAL**: Refactor `LMission` + `LEngine` into separate, granular layers
  - [ ] Extract reasoning engine as shared component (not L-CTO-specific)
  - [ ] Extract governance checks as shared component (not L-CTO-specific)
  - [ ] Make L-CTO use `agents/l_cto.py` (BaseAgent) + shared reasoning/governance layers
  - [ ] Ensure all agents can plug into shared reasoning engines (architectural requirement)

- [ ] **Phase 3: Multi-Agent Memory Infrastructure**

  - [ ] Verify `PacketEnvelope.metadata.agent` supports multi-agent filtering
  - [ ] Add agent_id constants: `l-cto`, `l9`, `cursor`, `emma`
  - [ ] Ensure memory queries filter by `agent_id` for isolation
  - [ ] Test cross-agent memory access patterns (shared vs private)

- [ ] **Phase 4: L-CTO Integration Points**

  - [ ] Wire `agents/l_cto.py` into `AgentExecutorService` (task routing)
  - [ ] Add FastAPI route `/api/agents/l-cto/directive` (direct HTTP access)
  - [ ] Register L-CTO in `AgentRegistry` with `agent_id="l-cto"`
  - [ ] Test both integration points (executor + HTTP route)

- [ ] **Phase 5: Slack Integration for L-CTO**

  - [ ] Wire L-CTO into Slack webhook routing (similar to existing Slack → L9 flow)
  - [ ] Ensure L-CTO can receive DMs and channel messages
  - [ ] Add placeholder for Emma Slack integration (future)

- [ ] **Phase 6: Naming Standardization**
  - [ ] Run rename script: `python scripts/rename_l_to_l_cto.py` (dry-run completed)
  - [ ] Rename all code references: "l" → "l-cto" (agent_id, class names, imports)
  - [ ] Keep "L" as display name in user-facing messages only
  - [ ] Update all YAML configs, kernel files, docs to use "l-cto" in code
  - [ ] Consider renaming `l-cto/` directory to `l_cto/` for Python import compatibility

**Dependencies:**

- Stage 7 blocks: None (can start immediately)
- Stage 7 enables: Multi-agent orchestration, Emma agent integration, advanced agent coordination

**Notes:**

- L-CTO integration is **HIGHEST PRIORITY**
- Architecture principle: Granular, pluggable agents with shared reasoning engines (NOT monolithic LMission/LEngine)
- Memory principle: Shared infrastructure with `agent_id` filtering (NOT per-agent databases)
- Emma agent: Spec outside repo, add placeholders where prudent
- Supabase: Fully deprecated - use `MemorySubstrateService` + `PacketEnvelope` only

---

### Stage 4: LLM-Powered Artifact Generation

- [ ] `long_plan_graph.py` → LLM code generation in planning nodes
- [ ] `long_plan_graph.py` → LLM documentation generation
- [ ] Artifact storage and versioning
- [ ] Plan → Executable workflow conversion

### Stage 5: Research Swarm

- [ ] `orchestrators/research_swarm/orchestrator.py` → Implement orchestration logic (currently stub)
- [ ] `orchestrators/research_swarm/convergence.py` → Implement convergence/specialized logic
- [ ] Wire ResearchSwarmOrchestrator into API (see Stage 2.6 Phase 3)

### Stage 6: Persistence & Reliability

- [ ] World Model snapshots persisted to storage
- [ ] World Model restore from snapshot
- [ ] Checkpoint-based recovery
- [ ] Event sourcing for state reconstruction

---

---

### Stage 2.8: MCP Memory Scope Enforcement ❌ CANCELLED

**Status:** CANCELLED (2026-01-08) — MCP Memory server was deprecated in favor of REST API.

**Reason:** MCP Memory SSE endpoints were never implemented. Memory access now works via:

- `cursor_memory_client.py` → REST API (`/api/v1/memory/*`)
- Direct `MemorySubstrateService` calls for L-CTO

**Archived Files:**

- `_archived/archived_mcp_memory/` — Historical MCP server code
- `~/.cursor/mcp.json` — Removed `l9-memory` entry

**Scope enforcement (if needed in future):** Implement in REST API memory router, not MCP.

---

---

### Stage 2.9: Systematic Capability Enabling (GMP-31 + GMP-32) ✅ COMPLETE

**Status:** ✅ COMPLETE (2026-01-06)
**Completion Date:** 2026-01-06 10:20 EST → 13:00 EST
**Report:** `reports/GMP-31-Systematic-Capability-Enabling.md`

**Final Results:**

| Metric              | Before | After   |
| ------------------- | ------ | ------- |
| L's Tools           | 21     | **70**  |
| Hidden Capabilities | 78     | **0**   |
| Capability Gap      | 78.8%  | **0%**  |
| New Tools Added     | —      | **+50** |

**What Was Done:**

GMP-31 and GMP-32 enabled **ALL 70 high-value capabilities** across 10 batches:

| Batch | Category                     | Status      |
| ----- | ---------------------------- | ----------- |
| 1     | Memory Substrate Direct (9)  | ✅ Complete |
| 2     | Memory Client API (7)        | ✅ Complete |
| 3     | Redis State Management (8)   | ✅ Complete |
| 4     | Tool Graph Introspection (6) | ✅ Complete |
| 5     | World Model Operations (6)   | ✅ Complete |
| 6     | MCP Server Control (3)       | ✅ Complete |
| 7     | Rate Limiting (4)            | ✅ Complete |
| 8     | Memory Advanced (3)          | ✅ Complete |
| 9     | Tool Graph Analysis (5)      | ✅ Complete |
| 10    | World Model Advanced (2)     | ✅ Complete |

**Files Modified:**

| File                             | Changes                  |
| -------------------------------- | ------------------------ |
| `runtime/l_tools.py`             | 67 executor functions    |
| `core/tools/registry_adapter.py` | 71 schemas + definitions |
| `core/tools/tool_graph.py`       | 67 ToolDefinitions       |

**Acceptance Criteria:**

- [x] All Batch 1-10 methods enabled (70 total)
- [x] Each method has: executor, schema, definition
- [x] All py_compile passes
- [x] L can call all new tools

---

## Future (Deferred) 🔮

### Stage 2.10: CircuitBreaker Enhancements

> **Added:** 2026-01-09 (GMP-32/33 completed)

**Status:** 🔮 DEFERRED

**Completed:**

- [x] Created reusable `CircuitBreaker` class in `core/observability/circuit_breaker.py`
- [x] Wired CB to AIOS calls in `executor.py` (threshold: 3)
- [x] Wired CB to memory DAG in `substrate_service.py` (threshold: 5)

**Deferred:**

- [ ] Add CB health endpoint to API (`GET /api/v1/memory/circuit-breaker/stats`)
- [ ] Wire CB to `ingest_batch()` for batch operation protection
- [ ] Add Prometheus metrics for CB state changes (trips, recoveries)
- [ ] Wire CB to tool registry external calls

**Files:**

- `core/observability/circuit_breaker.py` — Reusable CB class
- `core/observability/config.py` — CB settings (threshold, window, reset_timeout)
- `reports/GMP_Report_GMP-32-CircuitBreaker-Integration.md`
- `reports/GMP_Report_GMP-33-CircuitBreaker-Memory-Wiring.md`

---

### Stage 8: Self-Reflection Governance Tracking 🔄

**Status:** 🔄 PARTIAL (Data Flow Complete, Action Handlers Missing)
**Implementation Spec:** `docs/IMPL-Self-Reflection-Governance-Tracking.md`
**GMP:** governance_tracking_enterprise_frontier

**Completed:**

- [x] Track governance blocks (authority, safety, tool approval) on AgentInstance
- [x] Track user corrections on AgentInstance
- [x] Wire to ExecutionResult schema
- [x] Populate in self-reflection TaskExecutionContext
- [x] GovernanceBlockPattern (POLICY) and UserCorrectionPattern (CONSTRAINT) fire correctly
- [x] Integration tests (20 tests passing)

**Remaining:**

- [ ] Severity escalation for GovernanceBlockPattern (currently always LOW)
- [ ] Wire user correction detection from conversation layer (chat, websocket, slack)
- [ ] Slack notification for kernel evolution plans
- [ ] API endpoints for evolution plan management
- [ ] ApprovalManager integration for evolution proposals

**Dependencies:**

- Enables: Kernel hot-reload based on behavioral gaps
- Blocks: Full self-evolution capabilities

---

### Self-Evolution Capabilities

> ⚠️ **DEFERRED** - Requires careful security review and governance framework.

The following capabilities are intentionally deferred until proper safety mechanisms are in place:

- **Code self-modification**: Evolution engine reading/writing its own source code
- **Autonomous refactoring**: L9 proposing and applying changes to itself
- **Capability expansion**: L9 adding new tools/executors without human approval

**Prerequisites before implementation:**

1. Comprehensive governance framework
2. Human-in-the-loop approval workflow
3. Rollback mechanisms with full audit trail
4. Sandboxed testing environment for self-modifications
5. Rate limiting on self-modification operations
6. External monitoring and kill switch

**Related stubs (not to be implemented without approval):**

- `orchestrators/evolution/apply_engine.py` → `_read_file()`, `_write_file()`
- Any code that would allow L9 to modify files in its own repository

---

## Development Environment 🛠️

### Python Environment Fix (LibreSSL → OpenSSL)

**Problem:** macOS system Python (`/usr/bin/python3`) uses LibreSSL 2.8.3, which triggers `NotOpenSSLWarning` from urllib3 v2.

**Current Status:** Warning suppressed in `conftest.py` (temporary workaround).

- [ ] **Recreate venv with Homebrew Python**
  - [ ] Delete existing venv: `rm -rf venv`
  - [ ] Create with Homebrew Python: `/opt/homebrew/bin/python3 -m venv venv`
  - [ ] Reinstall dependencies: `source venv/bin/activate && pip install -r requirements.txt`
  - [ ] Verify OpenSSL: `python -c "import ssl; print(ssl.OPENSSL_VERSION)"` → should show OpenSSL 3.x

**Why:** Homebrew Python is compiled with OpenSSL 3.6.0, eliminating the SSL compatibility warning and enabling full TLS 1.3 support.

---

## Version History

| Version | Date       | Changes                                                                                                      |
| ------- | ---------- | ------------------------------------------------------------------------------------------------------------ |
| 0.6.0   | 2026-01-09 | Added Stage 2.10 (CircuitBreaker Enhancements) — GMP-32/33 completed, deferred items                         |
| 0.5.0   | 2026-01-08 | Added Stage 8 (Self-Reflection Governance Tracking) with implementation spec                                 |
| 0.4.0   | 2026-01-08 | Added Development Environment section (venv Homebrew Python migration)                                       |
| 0.3.0   | 2026-01-05 | Added Stage 2.7 (PacketEnvelope v2.0 Schema Migration) with sunset timeline                                  |
| 0.2.0   | 2025-01-27 | Added Stage 2.5 (Memory API & Client SDK completion), Stage 2.6 (Orchestrator API Wiring), gap analysis docs |
| 0.1.0   | 2025-12-26 | Initial roadmap created                                                                                      |
