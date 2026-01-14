# GMP STAGE 1: Foundation Setup v1.0

**Inherits from**: GMP-Action-Prompt-Canonical-v1.0.md  
**Stage Purpose**: Initialize PostgreSQL schema, storage layer, environment configuration  
**Duration**: ~1 hour  
**Produces**: Database migrations, Pydantic models, config scaffolding  

---

## ROLE & AUTHORITY

You are an L9 GMP Stage Executor operating inside the L9 repository.

- **Execute**: Phases 0–6 exactly as defined in canonical GMP
- **Scope**: Database schema, storage configuration, baseline migration files
- **Authority**: Create new files; modify config files; require approval for protected systems
- **Report**: 10 sections + final declaration to `reports/GMP-Stage-1-Foundation-Report.md`

---

## PURPOSE

Create a production-ready PostgreSQL + storage layer foundation for agent persistence:

1. **Database Schema**: Checkpoint table, metadata indices, retention policy tables
2. **Pydantic Models**: Serialization data classes for checkpoint payloads
3. **Environment Config**: Feature flags, connection strings, storage paths
4. **Baseline Migration**: Alembic or raw SQL migrations ready to apply

**Success Criterion**: Human can run migrations and immediately begin Stage 2 (Core Methods).

---

## CANONICAL GMP PHASES

This stage executes canonical phases 0–6:

### **Phase 0: Audit & TODO Plan Lock**

**Actions**:
1. Read existing files to understand current state:
   - `memory/substratemodels.py` (existing data models)
   - `memory/substrateservice.py` (existing substrate patterns)
   - `config/settings.py` or `.env` template (existing config)
   - `memory/migrations/` directory structure (if it exists)

2. **Produce TODO Plan** (locked, machine-verifiable):
   - All TODOs must be atomic and independent
   - Each TODO includes: ID, file path (absolute), line range (or "new file"), action verb, target, expected result
   - No TODOs that depend on unspecified prerequisites

3. **STOP for Human Approval**: Emit Phase 0 plan, wait for human to approve before proceeding to Phase 1.

---

### **Phase 1: Baseline Confirmation**

**Actions**:
1. Verify all TODO target files exist or can be created
2. If files exist, record current signatures (line counts, key function names)
3. If files are new, confirm directory structure ready
4. Document baseline state in report

**Validation**: All Phase 0 TODOs are confirmed feasible.

---

### **Phase 2: Implementation**

**Actions** (per Phase 0 locked TODO plan):
1. Create migration files (Alembic-style or raw SQL)
2. Create Pydantic models for checkpoint metadata
3. Create config scaffolding (env vars, feature flags)
4. Emit full file contents in report

**Pattern**: Database-first; models follow schema.

---

### **Phase 3: Enforcement**

**Actions**:
1. Add schema validation (Pydantic BaseModel constraints)
2. Add database constraints (unique indices, NOT NULL, foreign keys)
3. Add rollback guards (migration reversibility)

---

### **Phase 4: Validation**

**Actions**:
1. Verify migrations can be applied (dry-run if possible)
2. Verify Pydantic models serialize/deserialize correctly
3. Verify config loads from environment
4. Create minimal test to prove schema works

---

### **Phase 5: Recursive Verification**

**Actions**:
1. Confirm all Phase 0 TODOs were addressed
2. Verify no scope drift (only database, config, models created)
3. Verify protected systems untouched

---

### **Phase 6: Finalization**

**Actions**:
1. Produce 10-section report (see below)
2. Emit final declaration: "All phases 0–6 complete. No assumptions. No drift."
3. Save report to `reports/GMP-Stage-1-Foundation-Report.md`

---

## MODIFICATION LOCK

**YOU MAY**:
- Create new migration files in `memory/migrations/`
- Create new Pydantic model files in `memory/`
- Modify `.env.example` to add new config keys
- Modify `config/settings.py` to add new config classes (append-only)
- Create new test fixtures

**YOU MAY NOT**:
- Modify `websocket_orchestrator.py`, `kernel_loader.py`, `docker-compose.yml`
- Change agent authority model
- Modify memory substrate service core logic
- Delete existing config keys

---

## PHASE 0 TODO PLAN SHAPE

Each TODO must follow this format:

```
- **ID**: 1.1
- **File**: /absolute/path/to/memory/migrations/0001_create_checkpoints.sql
- **Action**: Create new migration file
- **Target**: SQL schema for checkpoint table
- **Expected**: 50-100 lines of SQL, includes: checkpoints table, metadata indices, constraints
- **Imports**: None (SQL file)
- **Dependencies**: None (baseline)
```

Example TODOs for Stage 1 (illustrative; you will generate the actual list):

```
- **ID**: 1.1
- **File**: /memory/migrations/0001_checkpoint_schema.sql
- **Action**: Create new migration
- **Target**: Checkpoint table schema
- **Expected**: CREATE TABLE checkpoints (id UUID PK, agent_id VARCHAR, state JSONB, created_at TIMESTAMP, updated_at TIMESTAMP, checksum VARCHAR, reason VARCHAR, metadata JSONB); CREATE INDEX idx_agent_id ON checkpoints(agent_id); CREATE INDEX idx_created_at ON checkpoints(created_at);
- **Imports**: None

- **ID**: 1.2
- **File**: /memory/models.py
- **Action**: Create new file
- **Target**: Pydantic models for checkpoint serialization
- **Expected**: CheckpointMetadata (agent_id, checkpoint_id, created_at, reason, state_size), CheckpointPayload (state dict, metadata dict)
- **Imports**: pydantic.BaseModel, datetime, uuid

- **ID**: 1.3
- **File**: /.env.example
- **Action**: Append new lines
- **Target**: Environment variables for agent persistence
- **Expected**: L9_CHECKPOINT_DB_URL, L9_CHECKPOINT_RETENTION_DAYS, L9_ENABLE_CHECKPOINT_COMPRESSION
- **Imports**: None (env template)

- **ID**: 1.4
- **File**: /config/settings.py
- **Action**: Append new class
- **Target**: CheckpointSettings config class
- **Expected**: class CheckpointSettings(BaseSettings): db_url, retention_days, compression_enabled
- **Imports**: pydantic_settings
```

---

## SUCCESS INDICATORS (CHECKLIST FOR HUMAN)

After Phase 0 STOP, human must verify:

- [ ] TODO plan is locked (no "TBD" or "TBD" placeholders)
- [ ] Each TODO has file path, action, expected result
- [ ] Database schema is normalized (no redundant columns)
- [ ] Pydantic models cover checkpoint metadata + state
- [ ] Config keys use L9_CHECKPOINT_ naming convention
- [ ] Migration files are reversible (down() methods or rollback SQL)
- [ ] No breaking changes to existing tables/schemas

If all checked, approve and Cursor continues Phases 1–6.  
If not, Cursor stops and waits for revised TODO plan.

---

## 10-SECTION REPORT STRUCTURE

When Phase 6 completes, emit report with these 10 sections:

1. **Stage Purpose & Scope** (1 paragraph)
2. **Phase 0 Locked TODO Plan** (full table: ID, file, action, expected)
3. **Phase 1 Baseline Verification** (file signatures, directory structure confirmed)
4. **Phase 2 Implementation Summary** (what was created, line counts, file diffs)
5. **Phase 3 Enforcement Additions** (constraints, validation rules added)
6. **Phase 4 Validation Results** (migration test results, model serialization test, config load test)
7. **Phase 5 Recursive Verification** (TODO coverage check, scope drift audit, protected system audit)
8. **Files Modified/Created** (complete list with line ranges and checksums)
9. **Risk Assessment** (any concerns, mitigation steps)
10. **Artifacts Ready for Stage 2** (what Stage 2 will consume: schema, models, config)

---

## FINAL DECLARATION

At end of Phase 6, emit exactly:

```
All phases 0–6 complete. No assumptions. No drift. Scope locked. Execution terminated. Output verified.
Report: reports/GMP-Stage-1-Foundation-Report.md
Stage 1 Foundation Setup complete. Ready for Stage 2: Core Methods.
```

---

## EXECUTION START: PHASE 0

**BEGIN PHASE 0**

Read current state of L9 repository:

1. Check if `memory/migrations/` directory exists. If not, note that migrations will be new.
2. Check if `memory/models.py` exists. If yes, record current content length.
3. Check if `.env.example` exists. If yes, record current keys.
4. Check if `config/settings.py` exists. If yes, record current classes.
5. Read `memory/substratemodels.py` to understand existing table patterns (SQLAlchemy models).
6. Read `memory/substrateservice.py` to understand how existing tables are created and accessed.

**After confirming above**:
- Generate Phase 0 TODO Plan (5–8 atomic TODOs)
- Emit TODO Plan in structured format above
- **STOP: AWAIT HUMAN APPROVAL**

Do not proceed to Phase 1 until human explicitly approves Phase 0 plan.
