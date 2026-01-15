# CURSOR INTEGRATION RUNBOOK v1.0

**For**: L9 Engineers running Agent Persistence GMP stages in Cursor  
**Quality**: Production-grade agent_persistence.py implementation  
**Timeline**: 8 sequential stages, ~20 hours total (~2.5 hours per stage average)  

---

## QUICK START

### Prerequisites
- [ ] L9 repository cloned and up-to-date
- [ ] Cursor IDE installed and L9 repo opened
- [ ] Access to PostgreSQL (dev or production)
- [ ] `.env` file with database credentials
- [ ] Python 3.11+, pytest available

### To Begin
1. Open L9 repo in Cursor
2. Navigate to `prompts/GMP-Cursor-Master-Integration-v1.0.md`
3. Read "Orchestration Model" section (10 min)
4. Follow Stage sequence below

---

## STAGE-BY-STAGE EXECUTION

### **STAGE 1: Foundation Setup** (~1 hour)

**What It Does**: Creates database schema, Pydantic models, config scaffolding

**Step 1.1: Open Stage GMP**
```
File: prompts/GMP-Cursor-Stage-1-Foundation-Setup-v1.0.md
```
Copy entire file into a new Cursor chat.

**Step 1.2: Wait for Phase 0 STOP**
Cursor will:
- Audit L9 repository current state
- Generate locked TODO plan (5–8 atomic TODOs)
- Print TODO plan to chat
- **STOP and wait for your approval**

**Step 1.3: Review Phase 0 Plan**
Check the TODO plan against this checklist:
- [ ] All TODOs have IDs (1.1, 1.2, etc.)
- [ ] All TODOs have absolute file paths
- [ ] All TODOs have action verbs (Create, Append, Modify)
- [ ] All TODOs have expected outcomes (not vague)
- [ ] Database schema includes: checkpoint table, metadata indices, retention tables
- [ ] Pydantic models include: CheckpointMetadata, CheckpointPayload
- [ ] Config variables use `L9_CHECKPOINT_*` naming
- [ ] No TODOs depend on unstated prerequisites

**If any check fails**:
- Reply: "Revise TODO plan. [Specific issue]"
- Cursor will re-generate and STOP again

**If all checks pass**:
- Reply: "Approved. Continue to Phase 1."
- Cursor will execute Phases 1–6 and emit report

**Step 1.4: After Phase 6 Complete**
Cursor will emit:
```
All phases 0–6 complete. No assumptions. No drift.
Report: reports/GMP-Stage-1-Foundation-Report.md
```

Save the report and open it.

**Step 1.5: Validate Stage 1 Report**
Open `reports/GMP-Stage-1-Foundation-Report.md` and verify:
- [ ] Section 1: Foundation scope clearly stated
- [ ] Section 2: All TODOs show "✅ COMPLETED"
- [ ] Section 3: Baseline files verified
- [ ] Section 4: New files listed (migrations, models, config)
- [ ] Section 5: Validation results show success
- [ ] Section 7: No scope drift detected
- [ ] Section 10: Database schema ready for Stage 2
- [ ] Final declaration includes "All phases 0–6 complete"

**If validation passes**:
→ **Proceed to Stage 2**

**If validation fails**:
- Identify specific issue from report (Section 9: Risk Assessment)
- Revert changes (git revert or manual rollback)
- Re-run Stage 1 with revised TODO plan

---

### **STAGE 2: Core Persistence Methods** (~4 hours)

**What It Does**: Implements all 7 required checkpoint methods

**Step 2.1: Prerequisites**
- [ ] Stage 1 report shows COMPLETE
- [ ] Database migrations applied: `alembic upgrade head` or equivalent
- [ ] Pydantic models import successfully: `python -c "from memory.models import CheckpointMetadata"`

**Step 2.2: Open Stage 2 GMP**
```
File: prompts/GMP-Cursor-Stage-2-Core-Methods-v1.0.md
```
Copy entire file into new Cursor chat.

**Step 2.3: Wait for Phase 0 STOP**
Cursor will generate locked TODO plan for 7 methods + models + tests.

**Step 2.4: Review & Approve**
Checklist:
- [ ] All 7 methods have TODOs (create_checkpoint, restore_checkpoint, list_checkpoints, etc.)
- [ ] Each method TODO specifies lines in `memory/agent_persistence.py`
- [ ] Test file TODO included (`tests/test_agent_persistence.py`)
- [ ] All methods marked as async
- [ ] Serialization strategy includes schema versioning
- [ ] Error handling strategy documented

Reply: "Approved" → Cursor continues to Phases 1–6.

**Step 2.5: After Phase 6 Complete**
Report: `reports/GMP-Stage-2-Methods-Report.md`

Validate:
- [ ] All 7 methods implemented
- [ ] Unit tests passing (section 6)
- [ ] Method signatures match spec (Args, Returns types correct)
- [ ] No TODOs in implementation code
- [ ] Logging uses structlog with context
- [ ] PacketEnvelope emission designed

**If validation passes**:
→ **Proceed to Stage 3**

---

### **STAGE 3: Integration Wiring** (~3 hours)

**What It Does**: Connects AgentPersistence to 6 system integration points

**Integration Points Wired**:
1. `core/agents/executor.py` → `AgentExecutorService.shutdown()`
2. `core/agents/agent_instance.py` → `AgentInstance.restore_state()`
3. `api/server.py` → Startup phase (restore all agents)
4. `memory/ingestion.py` → Critical decision checkpointing
5. `core/governance/approval_manager.py` → Post-approval checkpointing
6. `api/server.py` → Shutdown phase (save all agent states)

**Step 3.1: Prerequisites**
- [ ] Stage 2 report shows COMPLETE
- [ ] `memory/agent_persistence.py` imports cleanly
- [ ] Target files (executor, server, approval_manager, ingestion) readable

**Step 3.2: Open Stage 3 GMP**
```
File: prompts/GMP-Cursor-Stage-3-Integration-Wiring-v1.0.md
```

**Step 3.3: Review Phase 0 Plan**
Should show 6 TODOs, one per integration point, each specifying:
- Target file and method
- Line range for hook injection
- AgentPersistence method to call

Approve and continue.

**Step 3.4: Validate Stage 3 Report**
- [ ] All 6 integration points wired
- [ ] Integration tests passing (section 6)
- [ ] No import errors after wiring
- [ ] Lifecycle hooks properly ordered

**If validation passes**:
→ **Proceed to Stage 4**

---

### **STAGE 4: Retention & Lifecycle** (~2 hours)

**What It Does**: Adds automatic cleanup, retention policies, lifecycle coordination

**Phase 0 TODOs** (you will see 3–4):
- Retention policy rules engine
- Cleanup scheduler
- Lifecycle event coordinator

**Step 4.1: Prerequisites**
- [ ] Stage 3 report shows COMPLETE
- [ ] Integration tests passing

**Step 4.2: Open Stage 4 GMP**
```
File: prompts/GMP-Cursor-Stage-4-Retention-Lifecycle-v1.0.md
```

**Step 4.3: Validate Stage 4 Report**
- [ ] Retention policies configurable (via config, not hardcoded)
- [ ] Cleanup scheduler integrated with event loop
- [ ] Lifecycle hooks called at right times
- [ ] Tests verify retention rules work

**If validation passes**:
→ **Proceed to Stage 5**

---

### **STAGE 5: Integrity & Security** (~3 hours)

**What It Does**: Adds checksums, schema versioning, encryption support

**Features Added**:
- SHA-256 checksum validation
- Schema version detector (handles v1 ↔ v2 migrations)
- Encrypted storage option (KMS/Vault integration)
- Compliance logging

**Step 5.1: Prerequisites**
- [ ] Stage 4 report shows COMPLETE
- [ ] Retention tests passing

**Step 5.2: Open Stage 5 GMP**
```
File: prompts/GMP-Cursor-Stage-5-Integrity-Security-v1.0.md
```

**Step 5.3: Validate Stage 5 Report**
- [ ] Checksum validation tests pass
- [ ] Schema versioning tests pass (backward compatibility verified)
- [ ] Encryption configuration documented
- [ ] Compliance logging enabled

**If validation passes**:
→ **Proceed to Stage 6**

---

### **STAGE 6: Observability & Metrics** (~2 hours)

**What It Does**: Adds Prometheus metrics, audit trails, observability

**Metrics Added** (8–10 key metrics):
- `checkpoint_create_latency_ms` (Histogram)
- `checkpoint_restore_success_rate` (Gauge)
- `checkpoint_size_bytes` (Histogram)
- `checkpoint_corruption_detected` (Counter)
- Plus 4–6 more

**Step 6.1: Prerequisites**
- [ ] Stage 5 report shows COMPLETE
- [ ] Integrity tests passing

**Step 6.2: Open Stage 6 GMP**
```
File: prompts/GMP-Cursor-Stage-6-Observability-Metrics-v1.0.md
```

**Step 6.3: Validate Stage 6 Report**
- [ ] All metrics defined (names, types, labels)
- [ ] Audit log schema created
- [ ] Structured logging confirms (check for `self.logger.info(...)` calls)
- [ ] Observability tests pass

**If validation passes**:
→ **Proceed to Stage 7**

---

### **STAGE 7: Testing & Validation** (~4 hours)

**What It Does**: Comprehensive test coverage (unit, integration, chaos)

**Test Coverage**:
- **Unit Tests** (all 7 methods in isolation)
- **Integration Tests** (all 6 wiring points)
- **Chaos Tests** (failures, recovery, edge cases)
- **Load Tests** (concurrent checkpoints, stress)

**Step 7.1: Prerequisites**
- [ ] Stage 6 report shows COMPLETE
- [ ] All observability working

**Step 7.2: Open Stage 7 GMP**
```
File: prompts/GMP-Cursor-Stage-7-Testing-Validation-v1.0.md
```

**Step 7.3: Validate Stage 7 Report**
- [ ] All tests passing (Unit ✅, Integration ✅, Chaos ✅)
- [ ] Code coverage reported (target: >85%)
- [ ] Edge cases documented (what happens if DB is down, etc.)

Run tests locally to confirm:
```bash
python -m pytest tests/test_agent_persistence.py -v
python -m pytest tests/integration/test_agent_persistence_integration.py -v
```

**If all tests pass**:
→ **Proceed to Stage 8**

---

### **STAGE 8: Deployment & Runbook** (~2 hours)

**What It Does**: Migration guide, ops runbook, production checklist

**Produces**:
- Migration script (for existing L9 deployments)
- Ops runbook (troubleshooting, monitoring, scaling)
- Pre-production validation checklist
- Final audit

**Step 8.1: Prerequisites**
- [ ] Stage 7 report shows ALL TESTS PASS
- [ ] All observability verified

**Step 8.2: Open Stage 8 GMP**
```
File: prompts/GMP-Cursor-Stage-8-Deployment-Runbook-v1.0.md
```

**Step 8.3: Validate Stage 8 Report**
- [ ] Migration script provided
- [ ] Runbook includes troubleshooting section
- [ ] Production checklist complete
- [ ] Final audit shows no drift, no scope violations

**Step 8.4: Post-Stage 8 Actions**
1. **Review migration script**: Ensure it's backward-compatible
2. **Stage to production**: Apply script to staging environment
3. **Monitor for 24 hours**: Check logs, metrics, recovery behavior
4. **Get final approval**: From L (CTO) or governance team
5. **Deploy to production**: Run migration script on prod

---

## RECOVERY & TROUBLESHOOTING

### If a Stage Fails Phase 0 (TODO plan approval)
- Cursor generates locked TODO plan
- You review and find issues (ambiguous targets, missing dependencies)
- Reply with specific revision request: "Revise TODO 2.3: Add error handling for missing DB"
- Cursor regenerates Phase 0 plan
- **Do NOT proceed to Phase 1 without approving Phase 0**

### If a Stage Fails Phase 4 (Validation)
- Report shows validation failures in Section 6
- Identify root cause (missing import, test failure, etc.)
- Options:
  1. **Revert & re-run**: `git revert <commit>` + re-run stage
  2. **Quick fix**: Manually fix and re-run validation (Phases 4–6 only)
- If quick fix chosen, document in stage report

### If Multiple Stages Fail
- Halt sequence immediately
- Schedule sync with L (CTO) to diagnose
- Likely causes: database issues, environment not ready, schema conflicts
- Restart from failing stage after fixes applied

---

## STAGE SUCCESS INDICATORS

After each stage, verify these signals before proceeding to next:

| Stage | Report File | Key Checkpoints |
|-------|------------|-----------------|
| 1 | GMP-Stage-1-Foundation-Report.md | ✅ All migrations generated, config keys added, Pydantic models created |
| 2 | GMP-Stage-2-Methods-Report.md | ✅ All 7 methods implemented, unit tests pass, 0 TODOs in code |
| 3 | GMP-Stage-3-Integration-Report.md | ✅ All 6 integration points wired, integration tests pass |
| 4 | GMP-Stage-4-Retention-Report.md | ✅ Retention scheduler running, cleanup tests pass |
| 5 | GMP-Stage-5-Integrity-Report.md | ✅ Checksum validation working, schema versioning tested |
| 6 | GMP-Stage-6-Observability-Report.md | ✅ Metrics exported, audit logs working |
| 7 | GMP-Stage-7-Testing-Report.md | ✅ All tests passing, >85% code coverage |
| 8 | GMP-Stage-8-Deployment-Report.md | ✅ Migration script ready, ops runbook complete, pre-prod checklist approved |

---

## FINAL CHECKLIST (Before Production Deploy)

- [ ] All 8 stages completed with ✅ COMPLETE status
- [ ] No TODO comments remaining in code
- [ ] All tests passing locally and in CI/CD
- [ ] Monitoring/alerting configured for new metrics
- [ ] Runbook reviewed by ops team
- [ ] L (CTO) approval obtained
- [ ] Migration script tested on staging
- [ ] Backup of checkpoint data verified
- [ ] Rollback plan documented
- [ ] Post-deployment monitoring plan written

---

## APPENDIX: GMP File Locations

```
prompts/GMP-Cursor-Master-Integration-v1.0.md           (Master orchestration)
prompts/GMP-Cursor-Stage-1-Foundation-Setup-v1.0.md     (Database + config)
prompts/GMP-Cursor-Stage-2-Core-Methods-v1.0.md         (7 methods)
prompts/GMP-Cursor-Stage-3-Integration-Wiring-v1.0.md   (6 integration points)
prompts/GMP-Cursor-Stage-4-Retention-Lifecycle-v1.0.md  (Cleanup automation)
prompts/GMP-Cursor-Stage-5-Integrity-Security-v1.0.md   (Checksums + encryption)
prompts/GMP-Cursor-Stage-6-Observability-Metrics-v1.0.md (Prometheus + audit)
prompts/GMP-Cursor-Stage-7-Testing-Validation-v1.0.md   (Full test suite)
prompts/GMP-Cursor-Stage-8-Deployment-Runbook-v1.0.md   (Ops + migration)

docs/CURSOR-INTEGRATION-RUNBOOK-v1.0.md                 (This file)
prompts/README-CURSOR-GMP-PACK-v1.0.md                  (Index)
```

---

## QUESTIONS & SUPPORT

- **GMP questions**: Refer to `GMP-Action-Prompt-Canonical-v1.0.md`
- **L9 architecture questions**: See `docs/architecture.md` + `INTEGRATION_GUIDE.md`
- **Stage-specific issues**: Review stage GMP file Section "Risk Mitigation" + "Known Edge Cases"
- **Stuck?**: Halt sequence, save current state, sync with L9 engineering team

---

**Ready?** → Open `prompts/GMP-Cursor-Master-Integration-v1.0.md` in Cursor and begin Stage 1.
