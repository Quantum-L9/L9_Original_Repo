---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "7.0.0"
component_id: "CMD-EVALUATE-001"
component_name: "Evaluate - Deep Analysis"
layer: "commands"
domain: "evaluation"
type: "slash_command"
status: "active"
created: "2025-12-01T00:00:00Z"
updated: "2026-01-01T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "informational"
compliance_required: false
audit_trail: false
security_classification: "internal"

# === COMMAND METADATA ===
name: evaluate
description: "L9-native deep evaluation — project status, code health, GMP gaps, and actionable TODOs"
memory_inject: true            # INJECT: Search VPS memory for preferences/lessons before execution
before_chain: extract-chat   # EXTRACT: Write learnings to VPS memory
auto_chain: ynp
---

# === L9 EVALUATE: Deep Project & Code Evaluation ===
# Cursor Slash Command: /evaluate
# Version: 7.0.0 (L9-native)
# Updated: 2026-01-01

---

## ⛓️ AUTO-CHAINS TO /ynp

This command **automatically runs /ynp at the end** to provide the highest-leverage next action based on evaluation findings.

---

## WHAT IT DOES

Performs comprehensive L9 project evaluation across 6 dimensions:

1. **Workflow State** — Current phase, active TODOs, blockers
2. **Tier Health** — KERNEL/RUNTIME/INFRA/UX compliance
3. **GMP Compliance** — Phase completion, missing gates
4. **Code Quality** — L9 patterns, anti-patterns, coverage
5. **Dependency Graph** — Imports, circular refs, orphans
6. **Gap Analysis** — What's missing vs production-ready

Outputs actionable GMP TODOs with priority and scope.

**Key principle:** Evaluate EVERYTHING relevant in one pass. Batch findings into related GMP scopes.

---

## EXECUTION PROTOCOL

### Step 0: STATE_SYNC (Required)

```
1. Read workflow_state.md
2. Extract:
   - Current PHASE (0-6)
   - Active TODO plan
   - Recent changes
   - Open questions
   - Priority queue (🔴/🟠/🟡/🔵)
3. Identify evaluation scope from context or target
```

### Step 1: TIER CLASSIFICATION

Classify all files in scope:

| Tier | Files | Evaluation Rigor |
|------|-------|-----------------|
| **KERNEL_TIER** | kernel_loader, executor, websocket_orchestrator, memory_substrate | FULL — every function traced |
| **RUNTIME_TIER** | task_queue, redis_client, tool_registry, agents | HIGH — public APIs + error paths |
| **INFRA_TIER** | docker-compose, deploy/, k8s/, Caddy | DEPLOYMENT — wiring + env vars |
| **UX_TIER** | React, TS client, docs, scripts | STANDARD — structure + tests |

### Step 2: L9 CODE HEALTH SCAN

For each file, check:

```python
L9_HEALTH_CHECKS = {
    # Required patterns
    "structlog_usage": "Uses structlog, not logging/print",
    "httpx_usage": "Uses httpx, not requests/aiohttp",
    "async_io": "Async def for all I/O operations",
    "pydantic_v2": "BaseModel with model_config, not Config class",
    "packet_logging": "Critical ops emit PacketEnvelope to memory",
    "error_handling": "Explicit try/except with recovery action",
    "timeout_config": "External calls have timeout parameter",
    
    # Anti-patterns to flag
    "bare_except": "No bare except: clauses",
    "sync_in_async": "No time.sleep() in async functions",
    "global_state": "No mutable global state",
    "hardcoded_secrets": "No hardcoded credentials",
    "missing_type_hints": "Public functions have type hints",
    
    # Tier-specific
    "kernel_approval_gates": "High-risk tools check Igor approval",
    "kernel_packet_audit": "All decisions logged as packets",
    "infra_env_vars": "Config via env vars, not hardcoded",
}
```

### Step 3: GMP COMPLIANCE AUDIT

For each active/recent GMP:

```
GMP PHASE GATES:
├── Phase 0: TODO plan locked? Hash recorded?
├── Phase 1: Baseline captured? Line anchors verified?
├── Phase 2: Implementation complete? All TODOs addressed?
├── Phase 3: Guards/tests added? Deterministic validation?
├── Phase 4: Positive/negative/regression tests pass?
├── Phase 5: Recursive verify — no scope drift?
└── Phase 6: Report complete? Definition of Done signed?

FLAG IF:
- Phase 2 started but Phase 0 not locked
- Phase 6 claimed but Phase 4 tests missing
- TODO items marked done but no test coverage
- Scope expanded beyond original plan
```

### Step 4: DEPENDENCY GRAPH ANALYSIS

```
CHECK FOR:
├── Circular imports (A → B → C → A)
├── Orphan modules (imported by nothing)
├── Missing __init__.py exports
├── Import from deprecated paths
├── Cross-tier violations (UX importing KERNEL)
└── Unused imports (dead code)
```

### Step 5: GAP ANALYSIS

Compare current state vs production-ready:

```
PRODUCTION CHECKLIST:
├── Core functionality
│   ├── Agent executor working? ✅/❌
│   ├── Memory substrate ingesting? ✅/❌
│   ├── Tool dispatch functioning? ✅/❌
│   └── Governance gates enforced? ✅/❌
├── Integration points
│   ├── Slack webhook receiving? ✅/❌
│   ├── API routes registered? ✅/❌
│   ├── WebSocket connected? ✅/❌
│   └── MCP server responding? ✅/❌
├── Observability
│   ├── Structured logging? ✅/❌
│   ├── Error packets emitted? ✅/❌
│   ├── Metrics exportable? ✅/❌
│   └── Health endpoints live? ✅/❌
├── Testing
│   ├── Unit tests exist? ✅/❌
│   ├── Integration tests exist? ✅/❌
│   ├── Critical path tests? ✅/❌
│   └── CI pipeline configured? ✅/❌
└── Deployment
    ├── Docker builds? ✅/❌
    ├── Env vars documented? ✅/❌
    ├── Migrations ready? ✅/❌
    └── Rollback plan exists? ✅/❌
```

### Step 6: GENERATE ACTIONABLE OUTPUT

---

## OUTPUT FORMAT

```
## 🔍 L9 EVALUATION REPORT

### 📍 STATE_SYNC
- **PHASE:** [0-6] — [phase name]
- **Priority Tier:** [🔴/🟠/🟡/🔵]
- **Active GMPs:** [list]
- **Last Action:** [from recent changes]

---

### 📊 EXECUTIVE SUMMARY

| Dimension | Score | Status |
|-----------|-------|--------|
| Workflow Health | 85% | 🟢 Good |
| Tier Compliance | 72% | 🟡 Needs work |
| GMP Gates | 60% | 🟠 Gaps found |
| Code Quality | 88% | 🟢 Good |
| Test Coverage | 45% | 🔴 Critical |
| Deploy Ready | 70% | 🟡 Almost |

**Overall:** [X]% production-ready

---

### 🏗️ TIER HEALTH

#### KERNEL_TIER (Critical)
| File | Health | Issues |
|------|--------|--------|
| executor.py | 🟢 92% | None |
| kernel_loader.py | 🟢 95% | None |
| memory_substrate_service.py | 🟡 78% | Missing timeout on external call L:234 |

#### RUNTIME_TIER
| File | Health | Issues |
|------|--------|--------|
| task_queue.py | 🟢 88% | None |
| tool_registry.py | 🟡 75% | Bare except L:156 |

#### INFRA_TIER
| File | Health | Issues |
|------|--------|--------|
| docker-compose.yml | 🟢 90% | None |
| deploy.sh | 🟡 70% | Hardcoded path L:12 |

---

### 🚦 GMP COMPLIANCE

#### Active GMPs
| GMP | Phase | Status | Missing Gates |
|-----|-------|--------|---------------|
| GMP-11 Igor Commands | 6 | ✅ Complete | None |
| GMP-16 Closed Loop | 0 | 🔴 Not Started | All |
| Wire-Orchestrators | 2 | 🟡 Partial | Phase 4 tests |

#### Phase Gate Violations
- ⚠️ **GMP-16**: Phase 0 plan not locked, cannot start Phase 2
- ⚠️ **Wire-Orchestrators**: Phase 2 done but Phase 4 tests missing

---

### 🧬 CODE QUALITY

#### Anti-Patterns Found
| File | Line | Issue | Severity |
|------|------|-------|----------|
| api/routes/commands.py | 45 | Bare except | 🟡 Medium |
| services/research.py | 123 | sync sleep in async | 🔴 High |
| tools/shell.py | 89 | Missing timeout | 🟡 Medium |

#### L9 Pattern Compliance
- ✅ structlog usage: 95% compliant
- ✅ httpx usage: 100% compliant
- ⚠️ Packet logging: 72% (missing in 8 critical paths)
- ⚠️ Type hints: 68% (12 public functions missing)

---

### 🔗 DEPENDENCY ANALYSIS

#### Circular Imports
- None found ✅

#### Cross-Tier Violations
- ⚠️ `api/routes/tools.py` imports from `core/kernels/` (UX → KERNEL)

#### Orphan Modules
- `services/legacy_adapter.py` — not imported anywhere

---

### 🎯 GAP ANALYSIS

#### Critical Gaps (Blocking Deploy)
1. **GMP-16 not started** — Closed-loop learning required for L autonomy
2. **Integration tests missing** — Wire-Orchestrators needs Phase 4
3. **Slack DM not wired** — Feature flag needs flip on VPS

#### High Priority Gaps
4. **Packet logging incomplete** — 8 critical paths not audited
5. **Type hints missing** — 12 public functions undocumented

#### Medium Priority
6. **Orphan module** — `legacy_adapter.py` should be archived
7. **Bare excepts** — 3 instances need specific exception types

---

### 📋 GENERATED GMP TODOs

#### 🔴 URGENT (Block Deploy)
| TODO | Scope | Files | Priority |
|------|-------|-------|----------|
| T1: Lock GMP-16 Phase 0 | RUNTIME | orchestration/, memory/ | 🔴 |
| T2: Add Wire-Orchestrators tests | RUNTIME | tests/integration/ | 🔴 |
| T3: Flip Slack DM flag on VPS | INFRA | .env, deploy.sh | 🔴 |

#### 🟠 HIGH (Before Stabilize)
| TODO | Scope | Files | Priority |
|------|-------|-------|----------|
| T4: Add packet logging to 8 paths | KERNEL | executor.py, task_router.py | 🟠 |
| T5: Add type hints to public APIs | RUNTIME | 12 files | 🟠 |

#### 🟡 MEDIUM (Cleanup)
| TODO | Scope | Files | Priority |
|------|-------|-------|----------|
| T6: Archive legacy_adapter.py | RUNTIME | services/ | 🟡 |
| T7: Fix bare excepts | RUNTIME | 3 files | 🟡 |

---

### 📦 BATCH OPPORTUNITIES

These TODOs can be chained in single GMP runs:

**Batch 1: RUNTIME Packet Logging (T4 + T5)**
- Scope: executor.py, task_router.py, tool_dispatch.py
- Add packet logging + type hints in same pass
- Estimated: 1 GMP run

**Batch 2: INFRA Deploy Prep (T3 + env cleanup)**
- Scope: .env, deploy.sh, docker-compose.yml
- Flip flags + fix hardcoded paths
- Estimated: 1 quick action

---

### 🎯 YNP (Your Next Play)

**Primary:** Lock GMP-16 Phase 0 plan — highest leverage unblock
**Why:** Closed-loop learning is prerequisite for autonomous L; blocking all downstream GMPs

**Batch opportunity:** Chain T1 (GMP-16 plan) + T2 (Wire-Orchestrators tests) — both RUNTIME tier

**Alternates:**
1. T3 (Slack DM flag) if deploy is imminent
2. T4 (packet logging) if GMP-16 blocked

---

### 📝 EVALUATION METADATA

```yaml
evaluation:
  timestamp: 2026-01-01T12:00:00Z
  scope: full_workspace
  files_scanned: 247
  issues_found: 18
  critical: 3
  high: 5
  medium: 10
  generated_todos: 7
  batch_opportunities: 2
```
```

---

## EVALUATION MODES

### Full Workspace (default)
```
/evaluate
```
Scans entire L9 workspace, all tiers.

### Target Directory
```
/evaluate @core/agents/
/evaluate @api/routes/
```
Focuses on specific module.

### Tier-Specific
```
/evaluate --tier KERNEL
/evaluate --tier RUNTIME
```
Only evaluates files in specified tier.

### GMP-Focused
```
/evaluate --gmp GMP-16
/evaluate --gmp Wire-Orchestrators
```
Evaluates specific GMP compliance only.

### Quick Health Check
```
/evaluate --quick
```
Skip deep analysis, just code health + blockers.

---

## FLAGS & OPTIONS

| Flag | Description | Default |
|------|-------------|---------|
| `--tier TIER` | Filter to specific tier | all |
| `--gmp GMP_ID` | Focus on specific GMP | all active |
| `--quick` | Fast mode, skip deep analysis | false |
| `--output FILE` | Write report to file | stdout |
| `--json` | Output as JSON for automation | false |
| `--fix` | Auto-fix simple issues (imports, formatting) | false |

---

## INTEGRATION

### Before Evaluate:
- STATE_SYNC is automatic (reads workflow_state.md)

### After Evaluate:
- Generated TODOs can feed into `/gmp` for execution
- `/ynp` called automatically at end
- Update `workflow_state.md` with findings

### Typical Flow:
```
/evaluate
  ↓
Review findings, identify priority
  ↓
/gmp [highest priority TODO]
  ↓
/evaluate --quick (verify fix)
```

---

## ANTI-PATTERNS

❌ **DON'T:** Evaluate and ignore findings
❌ **DON'T:** Start Phase 2 work based on evaluate without Phase 0 plan
❌ **DON'T:** Fix KERNEL_TIER issues without full GMP process
❌ **DON'T:** Run /evaluate repeatedly — batch your fixes

✅ **DO:** Use evaluate to generate GMP TODO plans
✅ **DO:** Batch related fixes into single GMP runs
✅ **DO:** Respect tier rigor requirements
✅ **DO:** Update workflow_state.md with evaluation results
✅ **DO:** Run /ynp after to get next action

---

## L9-SPECIFIC CHECKS

### Kernel Compliance
- All tool dispatches check approval gates
- All decisions emit PacketEnvelope
- No mutable global state in executor
- Timeout on all external calls

### Memory Substrate
- All ingestion via ingest_packet()
- Dedup keys properly set
- No fire-and-forget logging
- Blob refs for large payloads

### Governance
- High-risk tools require Igor approval
- Destructive ops have rollback spec
- Audit trail immutable
- Authority hierarchy respected

### Orchestration
- TaskRouter and AgentExecutorService wired
- WebSocket connections managed
- Rate limiting in place
- Circuit breakers for repeated failures
