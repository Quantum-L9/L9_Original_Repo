# L9 GOVERNANCE REFERENCE — CURSOR EDITION

**Version:** 3.1.0
**Purpose:** Quick reference for L9 governance model

---

This document summarizes L9's governance model for engineers using Cursor.

## 1. Authority Hierarchy

From `governance_model.txt`:

| Role                      | Authority        | Can Do                                                                          |
| ------------------------- | ---------------- | ------------------------------------------------------------------------------- |
| **IGOR (Human)**          | Full authority   | Approve high-risk tools, grant permanent approvals, override safety constraints |
| **L (CTO Agent)**         | Safety envelope  | Autonomous within envelope, must request approval for high-risk                 |
| **Research/Coder Agents** | Limited scope    | Cannot execute high-risk tools                                                  |
| **Mac Agent**             | Lowest authority | Shell execution requires approval                                               |

## 2. High-Risk Tools

**Always require Igor approval:**

| Tool            | Risk | Purpose                           |
| --------------- | ---- | --------------------------------- |
| `gmprun`        | High | Execute GMP protocol code changes |
| `gitcommit`     | High | Commit changes to repository      |
| `gitpush`       | High | Push changes to remote            |
| `filedelete`    | High | Delete files                      |
| `databasewrite` | High | Write to production database      |
| `deploy`        | High | Deploy to production              |
| `macagentexec`  | High | Execute commands on Mac agent     |

Cursor prompts must **never** call these implicitly.

## 3. Igor Command Syntax

| Command                       | Purpose              |
| ----------------------------- | -------------------- |
| `L proposegmp <description>`  | Propose a GMP run    |
| `L analyze <scope>`           | Analyze code/files   |
| `L approve <task_id>`         | Approve pending task |
| `L reject <task_id> <reason>` | Reject task          |
| `L rollback <task_id>`        | Roll back change     |
| `L status`                    | Get current status   |
| `L help`                      | Show commands        |

Each approval/rejection creates a **GovernancePattern** for learning.

## 4. Governance Patterns

Patterns capture **what was approved and why**:

```python
GovernancePattern(
    task_id="...",
    tool_name="...",
    decision="APPROVED|REJECTED",
    reason="...",
    conditions=["..."]
)
```

Cursor-driven changes should:

- Respect existing patterns
- Avoid repeating previously rejected behaviors

## 5. GMP Run Input

`GMPRunInput` model defines the schema for GMP runs:

| Field              | Type | Purpose                |
| ------------------ | ---- | ---------------------- |
| description        | str  | What the GMP does      |
| scope              | str  | Files/modules affected |
| target_environment | str  | dev/staging/prod       |
| risk_level         | enum | Low/Medium/High        |

Classified as **high-risk tool**, thus requires Igor approval.

## 6. Memory & Packet Invariants

Core memory invariants:

| Model                     | Purpose                   | Protected |
| ------------------------- | ------------------------- | --------- |
| `PacketEnvelope`          | Canonical event container | Yes       |
| `MemoryPacket`            | Memory segment invariants | Yes       |
| `MemorySubstrateSettings` | Configuration             | Yes       |

Cursor must **not** alter:

- Core packet schemas
- Memory substrate configuration
- Packet lineage or provenance fields

## 7. Protected Systems

**NEVER modified by Cursor automation:**

```
runtime/websocket_orchestrator.py
core/kernels/kernel_loader.py
core/agents/executor.py
docker-compose.yml
memory/substrate_service.py
memory/substrate_models.py
memory/substrate_semantic.py
memory/validators/packet_validator.py
config/kernels/*.yaml
config/agents/*.yaml
```

## 8. GMP Phases

| Phase | Name           | Purpose                 |
| ----- | -------------- | ----------------------- |
| 0     | TODO PLAN LOCK | Lock deterministic plan |
| 1     | BASELINE       | Verify prerequisites    |
| 2     | IMPLEMENTATION | Execute TODOs           |
| 3     | ENFORCEMENT    | Add governance          |
| 4     | VALIDATION     | Run tests               |
| 5     | RECURSION      | Verify invariants       |
| 6     | FINALIZATION   | Evidence report         |

**Sequential only** — cannot skip phases.

## 9. Memory Tiers (v3.1)

| Tier     | Purpose                      | Retention        |
| -------- | ---------------------------- | ---------------- |
| Identity | Core facts, user preferences | Permanent        |
| Project  | Project-scoped knowledge     | Project lifetime |
| Session  | Conversation context         | Session          |
| General  | Default tier                 | Standard decay   |

## 10. Feature Flags

| Flag                           | Default | Purpose                          |
| ------------------------------ | ------- | -------------------------------- |
| `L9_ENABLE_STRICT_GOVERNANCE`  | true    | Enforce governance checks        |
| `L9_ENFORCE_APPROVAL_GATES`    | true    | Block high-risk without approval |
| `GOVERNANCE_HARDENING_ENABLED` | true    | Full governance stack            |

## 11. Quick Decision Matrix

| Scenario                      | Action                       |
| ----------------------------- | ---------------------------- |
| Need to modify protected file | STOP — escalate to Igor      |
| Need high-risk tool           | STOP — request Igor approval |
| Test failure                  | STOP — fix before proceeding |
| Governance check missing      | Add before Phase 4           |
| Scope drift detected          | STOP — revise TODO plan      |

---

**End governance-reference.md**
