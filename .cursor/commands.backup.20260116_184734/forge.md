---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "7.0.0"
component_id: "CMD-FORGE-001"
component_name: "Forge - Autonomous Execution"
layer: "commands"
domain: "execution"
type: "slash_command"
status: "active"
created: "2025-12-01T00:00:00Z"
updated: "2026-01-01T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "operational"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === COMMAND METADATA ===
name: forge
description: "L9 autonomous execution — NO PAUSES, maximum velocity, governance compliant"
memory_inject: true            # INJECT: Search VPS memory for preferences/lessons before execution
before_chain: extract-chat   # EXTRACT: Write learnings to VPS memory
auto_chain: ynp
---

# === L9 FORGE: Autonomous High-Velocity Execution ===
# Cursor Slash Command: /forge
# Version: 7.0.0 (L9-native)
# Updated: 2026-01-01

---

## ⛓️ AUTO-CHAINS TO /extract-chat → /ynp

After delivery:
1. **Runs /extract-chat** — Captures learnings, patterns, decisions to VPS memory
2. **Then runs /ynp** — Recommends next forge, deploy action, or /evaluate

---

## WHAT IT DOES

**Autonomous high-velocity execution** with:

1. **NO PAUSES** — Zero stops for manual approvals
2. **Auto-Fix** — Repairs issues silently, proceeds
3. **Governance Compliant** — Respects all L9 rules automatically
4. **Complete Delivery** — Code + docs + schema + tests in one pass

**Key principle:** Maximum velocity = ZERO PAUSES. Execute autonomously.

---

## ⚡ MAXIMUM VELOCITY RULES

**CRITICAL:** Maximum velocity means **ZERO PAUSES FOR MANUAL APPROVALS**.

**NEVER PAUSE FOR:**
- File moves/renames
- Header updates
- Version bumps
- Naming standardization
- Code generation
- Documentation updates
- Governance fixes
- Import additions

**ONLY PAUSE FOR:**
- Security violations requiring explicit human authorization
- Critical secrets exposure
- Irreversible data loss without confirmation

---

## 🚨 MANDATORY: Pre-Build Questions

**⚠️ BEFORE AUTONOMOUS EXECUTION:** Strategic questions prevent building the wrong thing correctly.

### Minimum Required Questions (Ask BEFORE Building)

**Success Vision (Q1-Q3):**
- Q1: "What does success look like when this is done?"
- Q2: "What job is this system being hired to do?"
- Q3: "How will you measure if it's working?"

**Constraints (Q5-Q6):**
- Q5: "Production-ready or MVP? Are placeholders acceptable?"
- Q6: "What existing systems can this NOT break?"

**Resources (Q7-Q8):**
- Q7: "What data exists vs what are we assuming exists?"
- Q8: "What prior work can we leverage vs build from scratch?"

**Quality (Q14-Q15):**
- Q14: ⚠️ **CRITICAL** "Should this have confidence scores? If yes, calculated how?"
- Q15: "What's the testing/validation plan?"

### Pre-Execution Checklist

- [ ] Success vision clear (Q1-Q3 answered)
- [ ] Governance standards confirmed (Q5 answered)
- [ ] Data availability validated (Q7 answered)
- [ ] Confidence/scoring approach clarified (Q14 answered if applicable)
- [ ] No placeholders will be used without disclosure

**STOP Rule:** If ANY checkbox unchecked → PAUSE and ASK QUESTIONS (this takes precedence over NO PAUSES)

---

## EXECUTION PROTOCOL

### Step 0: QUICK STATE CHECK

```
1. Glance at workflow_state.md (quick, not full sync)
2. Note current PHASE and priority tier
3. Identify target tier (KERNEL/RUNTIME/INFRA/UX)
4. Check if target is in protected files list
```

**If KERNEL_TIER:** Switch to `/gmp` instead of `/forge`

### Step 1: SCOPE & INTEGRITY

- Clarify scope and objective
- Confirm constraints from L9 governance
- Identify dependencies and risks
- Set success criteria
- Load required context
- **NO PAUSES** — Proceed immediately to Step 2

### Step 2: DRAFT & CHAIN

- Produce artifacts (code, docs, configs)
- Chain required sub-operations automatically
- Generate complete packet:
  - Code files
  - Type hints
  - Docstrings
  - Tests (if scope includes)
- Execute research, validation, build in parallel when safe
- **NO PAUSES** — Proceed immediately to Step 3

### Step 3: FINALIZE & DELIVER

- Apply governance checks:
  - [ ] Security (no hardcoded secrets)
  - [ ] Versioning (headers updated)
  - [ ] L9 Patterns (structlog, httpx, async)
  - [ ] Environment (no hardcoded paths)
- Run recursive self-check
- Fix issues automatically (don't pause)
- Self-verify: Plan A vs Plan B, risk scan
- Deliver artifact + delivery log + YNP
- **NO PAUSES** — Complete immediately

---

## L9-NATIVE PATTERNS

### Automatic Pattern Application

```python
# ✅ FORGE AUTO-APPLIES:
import structlog  # NOT logging
import httpx      # NOT requests
from pydantic import BaseModel, Field  # Pydantic v2

logger = structlog.get_logger(__name__)

async def fetch_data(url: str, timeout: float = 30.0) -> dict:
    """Fetch data with timeout (L9 pattern)."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
```

### Tier-Aware Behavior

| Tier | Forge Behavior |
|------|----------------|
| **KERNEL_TIER** | ❌ Redirect to /gmp — too critical for autonomous |
| **RUNTIME_TIER** | ⚠️ Forge with extra validation, run tests |
| **INFRA_TIER** | ✅ Forge freely, focus on env vars |
| **UX_TIER** | ✅ Full autonomous execution |

---

## OUTPUT FORMAT

### Delivery Log (Required)

```markdown
## 📋 FORGE DELIVERY LOG

### 🎯 Objective
[What was built]

### ✅ Actions Taken
1. [Action 1]
2. [Action 2]
3. [Action 3]

### 🔧 Auto-Fixes Applied
- [Fix 1]: [What was wrong → how it was fixed]
- [Fix 2]: [What was wrong → how it was fixed]

### 🧠 Decisions Made
| Decision | Rationale |
|----------|-----------|
| [Decision 1] | [Why this choice] |
| [Decision 2] | [Why this choice] |

### 🔒 Governance Checks
- [x] Security: No hardcoded secrets
- [x] Patterns: structlog, httpx, async
- [x] Headers: Updated with timestamp
- [x] Env: No hardcoded paths

### ⏱️ Execution
- **No Pauses:** ✅ Confirmed
- **Time:** [duration]
- **Files Created:** [count]
- **Files Modified:** [count]

### 🎯 YNP (Your Next Play)
**Primary:** [Recommended next action]
**Alternates:** [1-2 alternatives]
```

---

## USAGE

### Standard Forge
```
/forge [objective]

Examples:
/forge Add retry logic to api/client.py
/forge Create new endpoint for user preferences
/forge Implement caching layer for research results
```

### Forge with Target
```
/forge @core/tools/ add new tool registration pattern

Focuses on specific directory, applies L9 tool patterns.
```

### Forge Pipeline
```
/forge analyze @module/ then implement improvements

Chains analysis → implementation in single autonomous run.
```

---

## PRECEDENCE RULES (Auto-Resolve Conflicts)

When conflicts arise, resolve automatically using this hierarchy:

1. **Security & Access** (secrets, auth, least privilege)
2. **Operational Health** (preflight, env sync, checkpoints)
3. **Versioning** (headers, naming, archiving)
4. **Workflow Governance** (validation, deploy, test)
5. **Reasoning** (self-verification, evidence)

Document resolution in delivery log.

---

## EXCEPTIONS (Security-Critical Only)

**PAUSE FOR:**
```
❗ Security violation detected: [description]
   Requires explicit human authorization to proceed.
   
   Options:
   1. Authorize: "proceed with [action]"
   2. Abort: "cancel forge"
   3. Modify: "change approach to [alternative]"
```

**NEVER PAUSE FOR:**
- Missing imports → auto-add
- Wrong patterns → auto-fix
- Formatting issues → auto-format
- Missing docstrings → auto-generate
- Version mismatches → auto-bump

---

## COMPLETION GATE

Task is complete only after:

1. ✅ Security and env checks pass (auto-repair)
2. ✅ Headers + versioning correct (auto-fix)
3. ✅ Workflow governance satisfied (auto-validate)
4. ✅ Reasoning self-check recorded (auto-record)
5. ✅ Delivery log generated
6. ✅ /ynp runs for next action

**Then deliver immediately — NO PAUSES.**

---

## INTEGRATION

- **Chains from:** `/analyze` (findings), `/evaluate` (TODOs)
- **Chains to:** `/ynp` (always), `/evaluate` (for verification)
- **Redirects to:** `/gmp` (for KERNEL_TIER)
- **Updates:** `workflow_state.md` with completion

---

## ANTI-PATTERNS

❌ **DON'T:** Pause for confirmation on non-security items
❌ **DON'T:** Use /forge for KERNEL_TIER changes
❌ **DON'T:** Skip pre-build questions for complex builds
❌ **DON'T:** Leave placeholders without disclosure
❌ **DON'T:** Skip the delivery log

✅ **DO:** Execute entire chain without stopping
✅ **DO:** Auto-fix issues silently
✅ **DO:** Apply L9 patterns automatically
✅ **DO:** Generate complete delivery log
✅ **DO:** Run /ynp at completion

---

## EXAMPLES

### Example 1: Simple File Addition
```
/forge Add rate limiting to api/routes/commands.py

FORGE DELIVERY LOG:

🎯 Objective: Add rate limiting to commands endpoint

✅ Actions Taken:
1. Added RateLimiter import from runtime.rate_limiter
2. Created rate limiter instance: commands_limiter = RateLimiter(max_requests=100, window_seconds=60)
3. Added @commands_limiter.limit decorator to execute_command()
4. Added rate limit exceeded error handling

🔧 Auto-Fixes Applied:
- Missing import → Added `from runtime.rate_limiter import RateLimiter`

🔒 Governance Checks: All passed

⏱️ No Pauses: ✅ | Time: 45s | Files Modified: 1

🎯 YNP: /evaluate @api/routes/commands.py to verify rate limiting works
```

### Example 2: New Module Creation
```
/forge Create observability module at core/observability/

FORGE DELIVERY LOG:

🎯 Objective: Create observability module with tracing and metrics

✅ Actions Taken:
1. Created core/observability/__init__.py
2. Created core/observability/models.py (TraceContext, Span, etc.)
3. Created core/observability/instrumentation.py (decorators)
4. Created core/observability/aggregation.py (metrics)
5. Created tests/core/observability/test_instrumentation.py

🧠 Decisions Made:
| Use OpenTelemetry-compatible span format | Industry standard, future-proof |
| Decorator-based instrumentation | Minimal code changes needed |

🔒 Governance Checks: All passed

⏱️ No Pauses: ✅ | Time: 3m 20s | Files Created: 5

🎯 YNP: /wire to integrate into executor
```

---

## REFERENCE

- **Pre-Build Questions:** `.cursor-commands/intelligence/pre-build-question-framework.md`
- **L9 Patterns:** `.cursor/rules/20-lang-python.mdc`
- **Protected Files:** `.cursor/rules/90-protected-core.mdc`
