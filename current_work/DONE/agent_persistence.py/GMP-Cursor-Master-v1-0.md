# GMP MASTER: L9 Agent Persistence Implementation v1.0

**Status**: Ready for Cursor execution
**Target**: L9 Repository (Production)
**Timeline**: 8 sequential GMP stages
**Quality Bar**: Frontier AI Lab (OpenAI/DeepMind/Anthropic)

---

## PURPOSE

Design and execute production-grade `agent_persistence.py` for L9 OS with:
- 7 required checkpoint management methods
- 6 integration points fully wired
- Frontier-lab-quality resilience, observability, and security
- Deterministic execution via 8 sequential GMP runs

---

## CANONICAL GMP INHERITANCE

This master GMP and all 8 stage GMPs inherit from `GMP-Action-Prompt-Canonical-v1.0.md`:
- Phase 0–6 definitions (audit, baseline, implementation, enforcement, validation, finalization)
- STOP rules: No scope expansion, locked TODO plans, no assumptions
- Single-report requirement: 10 sections + final declaration per stage
- Modification locks: Protected systems require explicit TODO approval

---

## ORCHESTRATION MODEL

**Master GMP Role**: Decision engine only
- Proposes stage sequence and stage-specific GMP invocations
- Does NOT execute implementation (delegates to stage GMPs)
- Validates stage prerequisites and dependencies

**Stage GMP Role**: Execution agent
- Inherits canonical GMP phases 0–6
- Produces locked TODO plan (Phase 0)
- Implements deterministically (Phases 1–6)
- Produces 10-section report + final declaration per stage

**Human Role**: Sequencer
- Opens L9 repo in Cursor
- Selects stage GMP from `prompts/GMP-Cursor-Stage-<N>-*.md`
- Runs stage in Cursor per instructions in runbook
- Validates stage report before moving to next

---

## STAGE SEQUENCE

### **Stage 1: Foundation Setup**
**GMP File**: `prompts/GMP-Cursor-Stage-1-Foundation-Setup-v1.0.md`
**Purpose**: Initialize PostgreSQL schema, storage layer scaffolding, environment config
**Dependencies**: None (prerequisite)
**Produces**: Database migrations, config files, baseline schema
**Duration**: ~1 hour
**Prerequisites Check**:
- [ ] PostgreSQL connection verified
- [ ] `memory/substratemodels.py` accessible
- [ ] `.env` template available

---

### **Stage 2: Core Persistence Methods**
**GMP File**: `prompts/GMP-Cursor-Stage-2-Core-Methods-v1.0.md`
**Purpose**: Implement 7 required checkpoint methods (create, restore, list, delete, serialize, deserialize, validate)
**Dependencies**: Stage 1 (database schema exists)
**Produces**: `memory/agent_persistence.py` with full method implementations
**Duration**: ~4 hours
**Prerequisites Check**:
- [ ] Stage 1 report reviewed
- [ ] Database migrations applied
- [ ] Pydantic models scaffolded

---

### **Stage 3: Integration Wiring**
**GMP File**: `prompts/GMP-Cursor-Stage-3-Integration-Wiring-v1.0.md`
**Purpose**: Connect persistence to 6 integration points (executor, server, approval, ingestion)
**Dependencies**: Stage 2 (core methods exist and tested)
**Produces**: Wired integration points with hook methods
**Duration**: ~3 hours
**Prerequisites Check**:
- [ ] Stage 2 report reviewed
- [ ] Core methods passing unit tests
- [ ] Integration point targets identified

---

### **Stage 4: Retention & Lifecycle**
**GMP File**: `prompts/GMP-Cursor-Stage-4-Retention-Lifecycle-v1.0.md`
**Purpose**: Add retention policies, cleanup automation, lifecycle event hooks
**Dependencies**: Stage 3 (integration wired)
**Produces**: Retention policy engine, lifecycle coordinator
**Duration**: ~2 hours
**Prerequisites Check**:
- [ ] Stage 3 report reviewed
- [ ] Integration tests passing
- [ ] Governance pattern review complete

---

### **Stage 5: Integrity & Security**
**GMP File**: `prompts/GMP-Cursor-Stage-5-Integrity-Security-v1.0.md`
**Purpose**: Add checksums, schema versioning, encrypted storage, compliance logging
**Dependencies**: Stage 4 (lifecycle complete)
**Produces**: Cryptographic validation layer, schema versioning system
**Duration**: ~3 hours
**Prerequisites Check**:
- [ ] Stage 4 report reviewed
- [ ] Retention tests passing
- [ ] Encryption key management design approved

---

### **Stage 6: Observability & Metrics**
**GMP File**: `prompts/GMP-Cursor-Stage-6-Observability-Metrics-v1.0.md`
**Purpose**: Add Prometheus metrics, structured logging, audit trails
**Dependencies**: Stage 5 (security layer complete)
**Produces**: Metrics definitions, audit log schema, observability integration
**Duration**: ~2 hours
**Prerequisites Check**:
- [ ] Stage 5 report reviewed
- [ ] Security tests passing
- [ ] Prometheus/structlog patterns available

---

### **Stage 7: Testing & Validation**
**GMP File**: `prompts/GMP-Cursor-Stage-7-Testing-Validation-v1.0.md`
**Purpose**: Comprehensive unit, integration, and chaos tests
**Dependencies**: Stage 6 (full implementation complete)
**Produces**: Test suite covering all methods, integration points, failure modes
**Duration**: ~4 hours
**Prerequisites Check**:
- [ ] Stage 6 report reviewed
- [ ] All observability tests passing
- [ ] Test framework scaffolding complete

---

### **Stage 8: Deployment & Runbook**
**GMP File**: `prompts/GMP-Cursor-Stage-8-Deployment-Runbook-v1.0.md`
**Purpose**: Production migration guide, ops runbook, final validation
**Dependencies**: Stage 7 (full test suite passing)
**Produces**: Migration guide, ops playbook, final checklist
**Duration**: ~2 hours
**Prerequisites Check**:
- [ ] Stage 7 report reviewed
- [ ] All tests passing
- [ ] Production environment readiness

---

## EXECUTION INSTRUCTIONS FOR CURSOR

### For Human (Repo Owner)

1. **Open repo in Cursor**
   ```bash
   cd /path/to/l9
   cursor .
   ```

2. **Open this file**
   ```
   prompts/GMP-Cursor-Master-Integration-v1.0.md
   ```

3. **For each stage (1–8, in order)**:
   - Open corresponding stage GMP file from `prompts/GMP-Cursor-Stage-<N>-*.md`
   - Copy the entire prompt into a new Cursor chat
   - Run to completion (Cursor will STOP when Phase 0 plan is locked)
   - Review Phase 0 plan (TODOs, scope, line ranges)
   - If approved, continue in same chat (Cursor resumes Phases 1–6)
   - When complete, save stage report to `reports/GMP-Stage-<N>-Report.md`
   - **STOP** before moving to next stage
   - Review stage report against 10-section checklist and final declaration
   - Only proceed to Stage N+1 if Stage N report shows ✅ COMPLETE

4. **Track progress**:
   - Use `docs/CURSOR-INTEGRATION-RUNBOOK-v1.0.md` as sequential guide
   - Each stage has prerequisites listed above
   - Do not skip stages or run out of order

### For Cursor (Agent)

Each stage GMP will:
1. **Phase 0**: Audit scope, read target files, lock TODO plan, STOP for human approval
2. **Phase 1**: Verify baselines, confirm targets exist, record signatures
3. **Phase 2**: Implement changes per TODO plan
4. **Phase 3**: Add enforcement (guards, tests)
5. **Phase 4**: Validate functionality, integration tests
6. **Phase 5**: Verify no scope drift, check invariants
7. **Phase 6**: Finalize, generate 10-section report, emit final declaration

---

## MODIFICATION LOCKS (L9 INVARIANTS)

**PROTECTED** (requires explicit TODO approval):
- `websocket_orchestrator.py`
- `docker-compose.yml`
- `kernel_loader.py`
- Agent authority model (L=CTO, CA=executor, Critic=evaluator)
- Memory substrate bindings (Postgres/Redis/Neo4j/Qdrant)
- Packet protocol (PacketEnvelope)

**ALLOWED** (per stage GMP scope):
- New files in `memory/`, `core/`, `api/`
- Config files (`config/`, `.env`)
- Tests and documentation
- Feature flags (`L9_ENABLE_*`)

---

## RISK MITIGATION

### Stage Interdependencies
- Each stage depends on previous stage's report showing ✅ COMPLETE
- Stage GMPs validate prerequisites before Phase 0 completes
- If prerequisite stage fails, halt sequence and diagnose

### Rollback Strategy
- Stage reports include all file diffs
- If a stage fails Phase 4 (Validation), revert and re-run Phase 0
- Root-cause analysis logged in stage report

### Divergence Detection
- Phase 5 (Recursive Verification) checks for scope drift
- Phase 6 (Finalization) produces checksum of all changes
- Final declaration must state "No drift" or stage fails

---

## SUCCESS CRITERIA (MASTER LEVEL)

✅ All 8 stages complete with FINAL DECLARATION: "All phases 0–6 complete. No assumptions. No drift."
✅ 7 required methods implemented and tested
✅ 6 integration points wired and validated
✅ Production-grade code ready to merge
✅ Ops runbook and migration guide delivered
✅ All tests passing (unit, integration, chaos)
✅ Zero manual edits outside GMP TODO plans

---

## APPENDIX: Stage GMP Quick Reference

| Stage | File | Phase 0 TODOs | Expected Changes | Report Path |
|-------|------|--------------|------------------|-------------|
| 1 | Stage-1-Foundation | DB schema, config | 3 files | `reports/GMP-Stage-1-Report.md` |
| 2 | Stage-2-Core-Methods | 7 methods + models | 2 files | `reports/GMP-Stage-2-Report.md` |
| 3 | Stage-3-Integration | 6 wiring points | 6 files | `reports/GMP-Stage-3-Report.md` |
| 4 | Stage-4-Retention | Retention policies | 2 files | `reports/GMP-Stage-4-Report.md` |
| 5 | Stage-5-Integrity | Checksums + versioning | 2 files | `reports/GMP-Stage-5-Report.md` |
| 6 | Stage-6-Observability | Metrics + logging | 2 files | `reports/GMP-Stage-6-Report.md` |
| 7 | Stage-7-Testing | Test suite | 3 files | `reports/GMP-Stage-7-Report.md` |
| 8 | Stage-8-Deployment | Runbook + checklist | 3 files | `reports/GMP-Stage-8-Report.md` |

---

## NEXT STEP

→ **Open `prompts/GMP-Cursor-Stage-1-Foundation-Setup-v1.0.md`**
→ **Copy into Cursor chat**
→ **Follow Stage 1 instructions to Phase 0 STOP**
