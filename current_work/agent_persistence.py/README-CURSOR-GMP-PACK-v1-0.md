# README: Cursor GMP Pack for L9 Agent Persistence v1.0

**Purpose**: Production-grade implementation of agent_persistence.py for L9 OS  
**Format**: God-Mode Prompt (GMP) pack with 8 sequential stages  
**Quality**: Frontier AI lab standards (OpenAI/DeepMind/Anthropic)  
**Status**: Ready to execute in Cursor  

---

## WHAT IS THIS?

This is a complete orchestration pack to implement checkpoint/recovery for L9 agents:
- **7 required methods** (create, restore, list, delete, serialize, deserialize, validate)
- **6 integration points** (executor, server startup/shutdown, ingestion, approval, instance)
- **Frontier-grade features** (distributed checkpointing, integrity validation, retention policies, observability)

All delivered via deterministic GMP execution with human checkpoints at each stage.

---

## FILES IN THIS PACK

| File | Purpose |
|------|---------|
| `prompts/GMP-Cursor-Master-Integration-v1.0.md` | Master orchestration: stage sequence, dependencies, risk mitigation |
| `prompts/GMP-Cursor-Stage-1-Foundation-Setup-v1.0.md` | Database schema + Pydantic models + config |
| `prompts/GMP-Cursor-Stage-2-Core-Methods-v1.0.md` | Implement all 7 checkpoint methods |
| `prompts/GMP-Cursor-Stage-3-Integration-Wiring-v1.0.md` | Wire to 6 system integration points |
| `prompts/GMP-Cursor-Stage-4-Retention-Lifecycle-v1.0.md` | Retention policies + cleanup automation |
| `prompts/GMP-Cursor-Stage-5-Integrity-Security-v1.0.md` | Checksums + schema versioning + encryption |
| `prompts/GMP-Cursor-Stage-6-Observability-Metrics-v1.0.md` | Prometheus metrics + audit logging |
| `prompts/GMP-Cursor-Stage-7-Testing-Validation-v1.0.md` | Unit + integration + chaos tests |
| `prompts/GMP-Cursor-Stage-8-Deployment-Runbook-v1.0.md` | Migration guide + ops runbook |
| `docs/CURSOR-INTEGRATION-RUNBOOK-v1.0.md` | Human-readable step-by-step guide (START HERE) |
| `prompts/README-CURSOR-GMP-PACK-v1.0.md` | This file |

---

## HOW TO USE (TLDR)

1. **Open L9 repo in Cursor**
   ```bash
   cd /path/to/l9
   cursor .
   ```

2. **Read the runbook**
   ```
   Open: docs/CURSOR-INTEGRATION-RUNBOOK-v1.0.md
   (10 min read, explains all 8 stages)
   ```

3. **Start Stage 1**
   ```
   Open: prompts/GMP-Cursor-Stage-1-Foundation-Setup-v1.0.md
   Copy entire content into a new Cursor chat
   Follow prompts
   ```

4. **Continue through Stage 8**
   ```
   Each stage outputs a report file: reports/GMP-Stage-<N>-Report.md
   Review report before proceeding to next stage
   ```

---

## EXECUTIVE SUMMARY: 8 STAGES

| # | Stage Name | Purpose | Time | Reports |
|---|-----------|---------|------|---------|
| 1 | Foundation Setup | DB schema, models, config | ~1h | `GMP-Stage-1-Foundation-Report.md` |
| 2 | Core Methods | 7 checkpoint methods | ~4h | `GMP-Stage-2-Methods-Report.md` |
| 3 | Integration Wiring | 6 system integration points | ~3h | `GMP-Stage-3-Integration-Report.md` |
| 4 | Retention & Lifecycle | Cleanup automation, retention | ~2h | `GMP-Stage-4-Retention-Report.md` |
| 5 | Integrity & Security | Checksums, versioning, encryption | ~3h | `GMP-Stage-5-Integrity-Report.md` |
| 6 | Observability | Prometheus metrics, audit logs | ~2h | `GMP-Stage-6-Observability-Report.md` |
| 7 | Testing | Unit, integration, chaos tests | ~4h | `GMP-Stage-7-Testing-Report.md` |
| 8 | Deployment & Runbook | Migration guide, ops playbook | ~2h | `GMP-Stage-8-Deployment-Report.md` |
| | **TOTAL** | **Production-ready code** | **~21h** | **8 reports** |

---

## KEY FEATURES

### ✅ Canonical GMP Adherence
- Inherits all rules from `GMP-Action-Prompt-Canonical-v1.0.md`
- Phase 0–6 execution model (audit → baseline → implement → enforce → validate → finalize)
- STOP rules: locked TODO plans, no scope expansion, human checkpoints
- Single 10-section report per stage + final declaration

### ✅ Frontier AI Lab Quality
- Distributed, fault-tolerant checkpoint system (OpenAI pattern)
- Time-travel debugging support (DeepMind pattern)
- Schema versioning with backward compatibility (Google pattern)
- Cryptographic integrity validation (Anthropic pattern)
- Automated retention + cost optimization

### ✅ Production-Ready
- Zero TODOs or placeholders in implementation
- Complete error handling + graceful degradation
- Comprehensive observability (metrics + audit trails)
- Full test coverage (unit + integration + chaos)
- Migration guide + ops runbook included

### ✅ Deterministic Execution
- Every stage locks Phase 0 TODO plan before implementation
- No assumptions or manual interpolation
- Clear success criteria for each stage
- Recovery procedures for stage failures

---

## PREREQUISITES

Before starting:

- [ ] **L9 repo**: Cloned and up-to-date (git pull)
- [ ] **PostgreSQL**: Running and accessible (dev or prod)
- [ ] **Python 3.11+**: Installed with venv active
- [ ] **Cursor IDE**: Opened with L9 repo
- [ ] **.env file**: Has database credentials set
- [ ] **Migrations tool**: Alembic or equivalent (for Stage 1)
- [ ] **pytest**: Installed (for Stage 7)

---

## EXECUTION RULES

1. **Sequential Only**: Run stages 1→2→3→...→8 (no skipping, no reordering)
2. **Human Approval**: Each stage STOPS at Phase 0 for your TODO plan approval
3. **Report Validation**: Review each stage report before proceeding to next
4. **No Manual Edits**: Outside changes will cause scope drift detection to fail
5. **Protected Systems**: websocket_orchestrator.py, kernel_loader.py, docker-compose.yml cannot be modified

---

## TROUBLESHOOTING

### Stage Phase 0 Approval Takes Too Long?
- Cursor has generated locked TODO plan
- You must review it thoroughly (use checklist in runbook)
- Reply "Approved" (or specific revisions) to continue
- Typically 5–10 min per stage

### Tests Fail in Stage 7?
- Check Stage 7 report Section 6 (validation results)
- Root cause listed in Section 9 (risk assessment)
- Options: revert + re-run, or quick fix + continue
- Document decision in stage notes

### Multiple Stages Fail?
- Stop sequence immediately
- Sync with L (CTO) to diagnose
- Most common: DB connectivity, environment not ready, schema conflicts
- Restart after fixing underlying issue

### Need to Revert All Changes?
```bash
git log --oneline | head -20  # Find commit before Stage 1
git revert <commit-hash> -m 1 --no-edit
# Then re-run stages
```

---

## AFTER COMPLETION (Post-Stage 8)

When all 8 stages complete successfully:

1. **Review final ops runbook** (in Stage 8 report)
2. **Test on staging environment** (run migration script)
3. **Monitor for 24 hours** (check metrics, logs, recovery)
4. **Get final approval** from L (CTO) / governance team
5. **Deploy to production** (run migration script on prod)
6. **Post-deployment monitoring** (per ops runbook)

---

## FAQ

**Q: Can I run multiple stages in parallel?**  
A: No. Each stage depends on previous stage's report showing COMPLETE.

**Q: What if I need to stop mid-stage?**  
A: All stages use git commits (via Phase 2 implementation). Revert to last good commit and re-run.

**Q: Who should approve Phase 0 plans?**  
A: Any engineer with L9 write access. Recommended: L (CTO) or senior engineer for early stages.

**Q: How long will this take?**  
A: ~20 hours total, spread over 1–2 weeks (assuming 2–3 hours per day).

**Q: Is this production-ready?**  
A: Yes. Stage 8 includes migration guide + pre-production validation. Follow ops runbook.

**Q: What if we need to modify L9 protected systems?**  
A: Stage GMPs require explicit TODO approval for protected systems. Unlikely unless L9 core architecture changes.

---

## SUPPORT

- **Questions about a stage?** Read that stage's GMP file (includes "Risk Mitigation" + "Known Edge Cases")
- **Questions about GMP format?** See `GMP-Action-Prompt-Canonical-v1.0.md`
- **Questions about L9 architecture?** See `docs/architecture.md` + `INTEGRATION_GUIDE.md`
- **Stuck?** Save current state, sync with L9 engineering team

---

## QUICK LINKS

| Document | Purpose |
|----------|---------|
| **START HERE** → | `docs/CURSOR-INTEGRATION-RUNBOOK-v1.0.md` |
| **Then** → | `prompts/GMP-Cursor-Master-Integration-v1.0.md` |
| **For Stage N** → | `prompts/GMP-Cursor-Stage-<N>-<Name>-v1.0.md` |
| **Reference** → | `GMP-Action-Prompt-Canonical-v1.0.md` |

---

**Ready?** Open the runbook and begin Stage 1. ✅
