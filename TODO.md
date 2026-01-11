# TODO

> **Last Updated:** 2026-01-11

---

## 🔴 High Priority

### Memory Graph Cleanup

**Status:** SQL generated, ready to execute

**Action Required:**
- [ ] Execute SQL deletion to remove 52 trash embeddings containing error messages
  - SQL file: `/tmp/delete_trash.sql`
  - Command: `psql -d l9_memory -f /tmp/delete_trash.sql` (or via Docker/VPS)
  - See: `scripts/DELETE_TRASH_INSTRUCTIONS.md` for options

**Context:**
- Found 52 trash embeddings with error messages like "Sorry, I encountered a temporary error. Please try again."
- These pollute semantic search results
- Re-indexing of high-value content is complete (GMP reports, errors, architecture, preferences, tool usage)

**Verification:**
- After deletion, run: `python3 scripts/check_embeddings_via_api.py`
- Semantic search should return better results (no error messages)

### L's Memory — Local Docker Verification

**Blocker**: NO GitHub push, NO VPS deployment until local Docker works.

**Status**: All phases complete, but need ongoing verification:
- [ ] **Confirm local Docker memory is still healthy** (Postgres/Neo4j/Redis up; memory_write + memory_search smoke)
- [ ] **Enforce `PacketValidator`** at the ingestion chokepoint (`memory/substrate_service.py:write_packet()`), with explicit error semantics + targeted tests

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
