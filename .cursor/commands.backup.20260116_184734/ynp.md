---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "8.1.0"
component_id: "CMD-YNP-001"
component_name: "YNP - Your Next Play"
layer: "commands"
domain: "decision_navigation"
type: "slash_command"
status: "active"
created: "2025-12-01T00:00:00Z"
updated: "2026-01-05T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "operational"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === COMMAND METADATA ===
name: ynp
description: "L9 decision navigator — reasoning-synthesized, confidence-scored, auto-executing next action engine (LOCAL CURSOR SCOPE ONLY)"
auto_chain: null

# === SCOPE BOUNDARY ===
scope: "local_cursor_only"
includes:
  - "Local file operations (read, write, edit)"
  - "Local test execution (pytest, npm test)"
  - "GMP execution and reporting"
  - "Slash command chaining"
  - "workflow_state.md updates"
excludes:
  - "VPS/SSH operations"
  - "Docker container management"
  - "Production deployments"
  - "Remote environment changes"
  - "Feature flag modifications on servers"
---

# === L9 YNP (Your Next Play) ===
# Cursor Slash Command: /ynp
# Version: 8.1.0 (Reasoning-Enhanced + Auto-Execute + Local Scope)
# Updated: 2026-01-05

---

## 🚀 VERSION 8.1: LOCAL CURSOR SCOPE + REASONING + AUTO-EXECUTE

**What's New in 8.1:**
- **Scope Boundary** — Explicitly LOCAL CURSOR ONLY (no VPS, Docker, or remote ops)
- **GOVERNANCE_TIER** — Added tier for commands, rules, protocols

**Core Features (from 8.0):**
- **Reasoning Synthesis** — Uses `/reasoning` multi-modal analysis to synthesize Primary YNP
- **Recursive Alignment** — Validates recommendation against context before locking
- **Auto-Execute** — If confidence ≥90%, EXECUTES action (doesn't just recommend)
- **Context Harvest** — Scans chat for provided files before recommending
- **Confidence Scoring** — Every YNP has a calibrated confidence score
- **Time Estimation** — Includes effort estimate for session planning

**⚠️ SCOPE BOUNDARY:**
- ✅ Local file operations, tests, GMP, slash commands
- ❌ VPS/SSH, Docker, deployments, remote environment changes

---

## WHAT IT DOES

Reads current L9 state, **applies multi-modal reasoning** to synthesize the highest-leverage next action, **validates with recursive alignment**, and **auto-executes if confidence ≥90%**.

**Key principles:**
1. **Batch aggressively** — 3 related TODOs in one GMP > 3 separate runs
2. **Reason before recommending** — Use abductive/deductive/inductive analysis
3. **Execute, don't just recommend** — If ≥90% confident, DO IT
4. **Harvest context first** — Check what's already available in chat

---

## EXECUTION PROTOCOL

### Step 0: CONTEXT HARVEST ⭐ NEW

Before any analysis, inventory what's already available:

```
CONTEXT SCAN:
├── Chat context
│   ├── Files provided (pasted/attached)
│   ├── Files referenced in instructions
│   └── Embedded code blocks
├── Existing artifacts
│   ├── generated/ directory
│   └── Prior GMP outputs
└── Reusable assets
    └── What can be leveraged vs created

IMPACT: Recommendations account for existing assets.
        Don't recommend creating what already exists.
```

### Step 1: STATE_SYNC (Required)

Read and summarize:

```
1. Open workflow_state.md
2. Extract:
   - PHASE (0-6)
   - Active TODO Plan items
   - Recent changes (last 3)
   - Open questions
   - Next steps queue
3. Identify current priority tier:
   - 🔴 BLOCKING (critical path blocker)
   - 🟠 PARTIAL (needs completion)
   - 🟡 QUEUED (ready for next)
   - 🔵 BACKLOG (lower priority)
```

### Step 2: SITUATION ANALYSIS

Assess:
- What phase are we in? (Phase 0 = planning, Phase 2 = implementing, Phase 6 = finalizing)
- What's blocking? (open questions, missing approvals, incomplete GMPs)
- What scope is active? (files in scope, tier classification)
- What can be batched? (related TODOs that share scope)
- What context is available? (from Step 0 harvest)

### Step 3: REASONING SYNTHESIS ⭐ NEW (Multi-Modal)

Apply `/reasoning` multi-modal analysis to identify the PRIMARY YNP:

```
ABDUCTIVE ANALYSIS (Pattern Discovery):
├── What patterns suggest the best next action?
├── What's the most likely high-leverage move?
└── Hypothesis: [candidate action] with [evidence]

DEDUCTIVE ANALYSIS (Logical Validation):
├── Does this action follow from current state?
├── Are prerequisites met?
├── Is this consistent with GMP phase gates?
└── Validation: PASS/FAIL

INDUCTIVE ANALYSIS (Pattern Generalization):
├── What worked in similar past situations?
├── What patterns from prior GMPs apply?
└── Generalization: [principle that supports this action]

SYNTHESIS:
├── Candidate actions ranked by reasoning
├── Top candidate with combined confidence score
└── Confidence = weighted(abductive + deductive + inductive)
```

### Step 4: RECURSIVE ALIGNMENT PASS ⭐ NEW

Before locking PRIMARY YNP, validate against all context:

```
ALIGNMENT CHECK:
├── Context alignment
│   ├── Does action leverage available context? ✅/❌
│   ├── Does action avoid redundant work? ✅/❌
│   └── Is scope correctly bounded? ✅/❌
├── State alignment
│   ├── Consistent with workflow_state.md? ✅/❌
│   ├── Respects current PHASE? ✅/❌
│   └── No blockers ignored? ✅/❌
├── Tier alignment
│   ├── Correct tier classification? ✅/❌
│   ├── Appropriate rigor level? ✅/❌
│   └── No cross-tier mixing? ✅/❌
└── Risk alignment
    ├── Rollback path if destructive? ✅/❌
    ├── Approval gates respected? ✅/❌
    └── No silent partial work? ✅/❌

IF ANY ❌ → Adjust recommendation and re-check
IF ALL ✅ → Lock PRIMARY YNP with confidence score
```

### Step 5: CONFIDENCE SCORING ⭐ NEW

Calculate final confidence:

```python
CONFIDENCE_CALCULATION:
  abductive_score = 0.0-1.0  # How strong is the pattern evidence?
  deductive_score = 0.0-1.0  # How logically sound?
  inductive_score = 0.0-1.0  # How well do past patterns support?
  alignment_score = 0.0-1.0  # How many alignment checks passed?
  
  # Weighted combination
  confidence = (
    abductive_score * 0.25 +
    deductive_score * 0.30 +
    inductive_score * 0.20 +
    alignment_score * 0.25
  )
  
  # Convert to percentage
  confidence_pct = round(confidence * 100)

CONFIDENCE THRESHOLDS:
  ≥90% → AUTO-EXECUTE (don't just recommend — DO IT)
  80-89% → HIGH confidence, recommend with strong endorsement
  70-79% → MODERATE, recommend with validation caveat
  60-69% → LOW-MODERATE, recommend but flag uncertainty
  <60% → LOW, investigate further before recommending
```

### Step 6: AUTO-EXECUTE OR OUTPUT ⭐ NEW

```
IF confidence ≥ 90%:
  → AUTO-EXECUTE the action
  → Use appropriate tool (write, run_terminal_cmd, etc.)
  → Show results, not just recommendation
  → Format: "⚡ AUTO-EXECUTED (94% confidence)"

IF confidence < 90%:
  → OUTPUT recommendation
  → Include confidence score and reasoning
  → Format: "🎯 PRIMARY YNP (78% confidence)"

AUTO-EXECUTE CRITERIA (all must be true):
  ✅ Confidence ≥ 90%
  ✅ Not KERNEL_TIER (requires explicit approval)
  ✅ No approval gate required
  ✅ Low/medium risk (not destructive)
  ✅ Clear, unambiguous action

NEVER AUTO-EXECUTE:
  ❌ KERNEL_TIER changes
  ❌ Destructive operations (delete, overwrite production)
  ❌ Operations requiring Igor approval
  ❌ Ambiguous or multi-interpretation actions
```

---

## OUTPUT FORMAT

### Standard Output (Confidence < 90%)

```
## 📍 STATE_SYNC
- PHASE: [0-6] — [phase name]
- Active scope: [files/modules]
- Priority tier: [🔴/🟠/🟡/🔵]
- Last action: [from recent changes]

## 🌾 CONTEXT AVAILABLE
- Provided in chat: [N files — list]
- In generated/: [N artifacts]
- Reusable: [what to leverage]

## 🧠 REASONING SYNTHESIS
### Abductive: [pattern evidence]
### Deductive: [logical validation — PASS/FAIL]
### Inductive: [past pattern support]
### Alignment: [N/N checks passed]

## 🎯 PRIMARY YNP ([confidence]% confidence)
**Action:** [command with full syntax]
**Time:** ~[estimate]
**Unblocks:** [what becomes possible]

## 💡 WHY THIS MOVE
[1-2 sentences synthesized from reasoning]

## 📦 BATCH OPPORTUNITY (if applicable)
Chain in single run:
- TODO-1: [description]
- TODO-2: [description]  
- TODO-3: [description]
Scope: [shared files/tier]
Time saved: ~[estimate]

## 🔄 ALTERNATES (max 2)
1. [Alternative if primary blocked] ([confidence]%)
2. [Lower-priority option] ([confidence]%)
```

### Auto-Execute Output (Confidence ≥ 90%)

```
## 📍 STATE_SYNC
[Same as above]

## 🌾 CONTEXT AVAILABLE
[Same as above]

## 🧠 REASONING SYNTHESIS (LOCKED)
Confidence: [N]% — AUTO-EXECUTE THRESHOLD MET

## ⚡ AUTO-EXECUTED ([confidence]% confidence)
**Action:** [what was executed]
**Result:** [output/confirmation]
**Time taken:** [actual]
**Files affected:** [list]

## ✅ EXECUTION COMPLETE
[Confirmation of what was done]

## 🎯 NEXT YNP
[If there's an obvious follow-up, state it]
[Otherwise: "Awaiting next instruction"]
```

---

## L9 COMMAND VOCABULARY (Local Cursor Scope)

### High-Priority Actions
| Command | When to Recommend |
|---------|------------------|
| `/gmp GMP-N` | Locked TODO plan ready for execution |
| `/wire` | Generated specs need integration |
| `/harvest` | Files in chat to extract to repo |
| `GMP Phase advance` | Current phase complete, gates passed |

### Development Actions  
| Command | When to Recommend |
|---------|------------------|
| `Create GMP Action Prompt` | New feature needs Phase 0 plan |
| `Run tests` | Validation needed before Phase 4 |
| `Batch TODO chain` | Multiple related items, same scope |
| `STATE_SYNC update` | Session ending, need handoff |
| `/analyze+evaluate` | Need full picture before GMP |

### Avoid Recommending
- Phase 2 work when Phase 0 not locked
- KERNEL_TIER changes without explicit plan
- Destructive ops without rollback spec
- Fragmented single-TODO runs (batch instead!)

### OUT OF SCOPE (Require Separate Process)
- ❌ VPS/SSH operations (not Cursor-accessible)
- ❌ Docker container management (requires terminal access)
- ❌ Production deployments (require Igor approval + VPS access)
- ❌ Environment changes on remote servers

---

## TIER CLASSIFICATION (Local Cursor Scope)

Before recommending, classify touched files:

| Tier | Files | GMP Rigor | Auto-Execute? |
|------|-------|-----------|---------------|
| KERNEL_TIER | kernel_loader, executor, websocket_orchestrator, memory_substrate | Full GMP + Audit | ❌ Never |
| RUNTIME_TIER | task_queue, redis_client, tool_registry, agents | GMP Action | ✅ If ≥90% |
| GOVERNANCE_TIER | commands/, rules/, protocols/ | GMP Action | ✅ If ≥90% |
| UX_TIER | React, TS client, docs, generated/ | Unit tests only | ✅ If ≥90% |

**Note:** INFRA_TIER (docker-compose, deploy/, k8s/) is OUT OF SCOPE for YNP auto-execute — requires VPS access and Igor approval.

---

## BATCHING RULES

### DO Batch Together:
- Same file, multiple functions
- Same tier, related behavior
- Same GMP, sequential TODOs
- Tests + implementation (always together)

### DON'T Batch:
- Cross-tier changes (KERNEL + UX)
- Unrelated features
- Changes requiring different approval levels

### Batch Size Guidelines:
- **Ideal:** 3-5 related TODOs per run
- **Maximum:** 7 TODOs (cognitive limit)
- **Minimum viable:** Don't run single-TODO when 3 are ready

---

## EXAMPLES

### Example 1: Auto-Execute (≥90% Confidence)

```
## 📍 STATE_SYNC
- PHASE: 0 — PLAN
- Active scope: core/observability/
- Priority tier: 🟠 PARTIAL
- Last action: User provided models.py in chat

## 🌾 CONTEXT AVAILABLE
- Provided in chat: 1 file (models.py — 450 lines)
- In generated/: 0 artifacts
- Reusable: models.py can be written directly

## 🧠 REASONING SYNTHESIS (LOCKED)
- Abductive: User provided complete file with path → wants it saved (0.95)
- Deductive: File path specified, code complete, no blockers (0.98)
- Inductive: /harvest pattern → write files directly (0.92)
- Alignment: 4/4 checks passed (1.0)
- **Confidence: 94%** — AUTO-EXECUTE THRESHOLD MET

## ⚡ AUTO-EXECUTED (94% confidence)
**Action:** Write core/observability/models.py
**Result:** ✅ File created (450 lines)
**Time taken:** <1s
**Files affected:** core/observability/models.py

## ✅ EXECUTION COMPLETE
models.py written to core/observability/. Ready for use.

## 🎯 NEXT YNP
If more files in context → continue /harvest
Otherwise → awaiting next instruction
```

### Example 2: High Confidence Recommendation (80-89%)

```
## 📍 STATE_SYNC
- PHASE: 6 — FINALIZE
- Active scope: core/agents/executor.py
- Priority tier: 🔴 BLOCKING
- Last action: GMP-16 implementation complete

## 🌾 CONTEXT AVAILABLE
- Provided in chat: 0 files
- In generated/: GMP report ready
- Reusable: Test fixtures exist

## 🧠 REASONING SYNTHESIS
- Abductive: Phase 6 gates passed → final report is next (0.88)
- Deductive: Implementation complete, tests pass, no blockers (0.95)
- Inductive: Prior GMPs required report generation (0.85)
- Alignment: 4/4 checks passed (1.0)
- **Confidence: 87%**

## 🎯 PRIMARY YNP (87% confidence)
**Action:** Generate GMP-16 final report and update workflow_state.md
**Time:** ~5 min
**Unblocks:** Next GMP can begin, session handoff ready

## 💡 WHY THIS MOVE
Reasoning synthesis: Report generation is the logical conclusion of Phase 6.
All prerequisites met. Documentation unblocks next iteration.

## 🔄 ALTERNATES
1. Run additional integration tests — if more validation needed (82%)
```

### Example 3: Batch Opportunity with Reasoning

```
## 📍 STATE_SYNC  
- PHASE: 0 — TODO PLAN LOCK
- Active scope: agents/codegen_agent/
- Priority tier: 🔵 CGA SYSTEM
- Last action: Spec extraction complete

## 🌾 CONTEXT AVAILABLE
- Provided in chat: 3 spec files
- In generated/: specs ready
- Reusable: All specs → direct implementation

## 🧠 REASONING SYNTHESIS
- Abductive: 3 related specs → batch opportunity (0.90)
- Deductive: Same tier, same module, no cross-deps (0.92)
- Inductive: Batching 3+ TODOs = 40% time savings (0.88)
- Alignment: 4/4 checks passed (1.0)
- **Confidence: 91%** — AUTO-EXECUTE THRESHOLD MET

## ⚡ AUTO-EXECUTED (91% confidence)
**Action:** Create GMP Action Prompt with 3 batched TODOs
**Result:** ✅ GMP-CGA-CORE.md created in generated/plans/
**Files affected:** 
- generated/plans/GMP-CGA-CORE.md

## ✅ EXECUTION COMPLETE
GMP Action Prompt created with batched TODOs:
- TODO-1: meta_loader.py — YAML parsing
- TODO-2: file_emitter.py — file writing with rollback
- TODO-3: codegen_agent.py — main agent wiring

## 🎯 NEXT YNP
Run `/gmp @generated/plans/GMP-CGA-CORE.md` to execute
```

### Example 4: Moderate Confidence (Needs Input)

```
## 📍 STATE_SYNC
- PHASE: 2 — IMPLEMENT
- Active scope: memory/substrate_service.py
- Priority tier: 🔴 PRE-DEPLOY
- Last action: GMP-16 Phase 2 started

## 🌾 CONTEXT AVAILABLE
- Provided in chat: 0 files
- In generated/: Partial implementation
- Reusable: None identified

## 🧠 REASONING SYNTHESIS
- Abductive: KERNEL_TIER file in scope → high rigor needed (0.75)
- Deductive: Phase 2 active but open question exists (0.65)
- Inductive: Similar KERNEL changes required clarification (0.70)
- Alignment: 3/4 checks passed (0.75) — ❌ open question not resolved
- **Confidence: 71%**

## 🎯 PRIMARY YNP (71% confidence)
**Action:** Resolve open question before continuing GMP-16
**Time:** ~5 min
**Unblocks:** GMP-16 Phase 2 completion

## ⚠️ UNCERTAINTY
Open question in workflow_state.md: "Should packet dedup use content hash or UUID?"
Recommend: Get clarification before proceeding with implementation.

## 💡 WHY THIS MOVE
Reasoning alignment check failed: Open question must be resolved before 
KERNEL_TIER changes. Proceeding without clarity creates rework risk.

## 🔄 ALTERNATES
1. Proceed with UUID approach (conservative) — 65% confidence
2. Switch to non-KERNEL task while awaiting answer — 78% confidence
```

---

## INTEGRATION

- **Scope:** Local Cursor instance only (no VPS, Docker, or remote operations)
- **Called by:** All slash commands as final step
- **Reads:** workflow_state.md, chat context, generated/, .cursor/rules/*.mdc
- **Applies:** `/reasoning` multi-modal synthesis (abductive + deductive + inductive)
- **Auto-executes:** If confidence ≥90% and criteria met (local operations only)
- **Updates:** workflow_state.md with execution results
- **Chains to:** /gmp, /wire, /harvest, /analyze+evaluate, or EXECUTES directly

---

## AUTO-EXECUTE RULES (Local Cursor Scope)

### When to Auto-Execute (Confidence ≥90%)

| Criteria | Required |
|----------|----------|
| Confidence score | ≥90% |
| Tier | RUNTIME, GOVERNANCE, or UX (not KERNEL) |
| Approval required | No |
| Risk level | Low or Medium |
| Action clarity | Unambiguous |
| Scope | Local Cursor operations only |

### Auto-Executable Actions (Local Only)

| Action Type | Example | Auto-Execute? |
|-------------|---------|---------------|
| Write file from context | User provided code with path | ✅ Yes |
| Run /harvest | Files in chat to extract | ✅ Yes |
| Run local tests | pytest, npm test | ✅ Yes |
| Create GMP plan | Batch opportunity identified | ✅ Yes |
| Update workflow_state.md | Session handoff | ✅ Yes |
| Read/analyze files | /analyze+evaluate | ✅ Yes |
| Generate reports | GMP reports to reports/ | ✅ Yes |

### NEVER Auto-Execute

| Action Type | Reason |
|-------------|--------|
| KERNEL_TIER changes | Requires explicit approval |
| Delete files | Destructive operation |
| Changes needing Igor approval | Governance gate |
| VPS/SSH operations | Out of Cursor scope |
| Docker commands | Requires terminal + approval |
| Production deployments | Requires VPS access + approval |
| Environment variable changes | Affects runtime, needs approval |

---

## ANTI-PATTERNS

### Critical (Efficiency Killers)

❌ **DON'T:** Just recommend when you could AUTO-EXECUTE at 90%+ confidence
❌ **DON'T:** Skip reasoning synthesis — always apply multi-modal analysis
❌ **DON'T:** Ignore chat context — files provided should be leveraged
❌ **DON'T:** Recommend creating what already exists in generated/

### Standard

❌ **DON'T:** Recommend single TODO when 3+ are ready in same scope
❌ **DON'T:** Skip STATE_SYNC — always read workflow_state.md first  
❌ **DON'T:** Recommend Phase 2 when Phase 0 plan not locked
❌ **DON'T:** Mix KERNEL_TIER and UX_TIER in same recommendation
❌ **DON'T:** Ignore open questions — they may be blockers
❌ **DON'T:** Auto-execute KERNEL_TIER changes (always require approval)

### Best Practices

✅ **DO:** Apply reasoning synthesis to every YNP
✅ **DO:** Auto-execute when confidence ≥90% and criteria met (local ops only)
✅ **DO:** Harvest context before recommending
✅ **DO:** Include confidence score in every output
✅ **DO:** Batch related TODOs aggressively
✅ **DO:** Respect GMP phase gates
✅ **DO:** Prioritize blocking items over new features
✅ **DO:** Include rollback path for destructive ops
✅ **DO:** Update workflow_state.md after execution
✅ **DO:** Stay within local Cursor scope (no VPS/Docker recommendations)

---

## CONFIDENCE CALIBRATION

| Score | Meaning | Action |
|-------|---------|--------|
| ≥95% | Extremely High | Auto-execute immediately |
| 90-94% | Very High | Auto-execute with logging |
| 85-89% | High | Recommend with strong endorsement |
| 80-84% | Good | Recommend confidently |
| 70-79% | Moderate | Recommend with validation caveat |
| 60-69% | Low-Moderate | Recommend but flag uncertainty |
| <60% | Low | Investigate further, don't recommend |

**Calibration principle:** If you say 90%, you should be right 90% of the time.
Overconfidence wastes time on wrong actions. Underconfidence wastes time asking.

---

**Remember: YNP = Harvest Context → Reason Multi-Modal → Align Recursively → Auto-Execute (≥90%) or Recommend**

**Scope: LOCAL CURSOR ONLY** — No VPS, Docker, or remote operations. Those require separate approval process.
