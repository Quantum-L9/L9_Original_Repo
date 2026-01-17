---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "1.2.0"
component_id: "CMD-PLAN-001"
component_name: "Plan - Enterprise Planning"
layer: "commands"
domain: "planning"
type: "slash_command"
status: "active"
created: "2025-12-01T00:00:00Z"
updated: "2026-01-04T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "operational"
compliance_required: true
audit_trail: true
security_classification: "internal"

# ============================================================================
# MACHINE-READABLE METADATA (Parseable by CI/automation)
# ============================================================================
schema_version: "1.0"
command:
  name: plan
  version: "1.2.0"
  description: "L9 Enterprise Planning — context harvest → analyze_evaluate → synthesis → reasoning → approval generation (Protocol-Compliant)"
  updated: "2026-01-04"
  author: "Igor Beylin"

# Command chain (auto-invoked)
chain:
  starts_with: rules              # Always call /rules first
  phase_0.5: context_harvest      # Harvest provided files + assess impact BEFORE analysis
  phase_1: analyze_evaluate       # Deep analysis + evaluation
  phase_2: synthesis              # Synthesize findings into plan
  phase_3: reasoning              # Recursive reasoning refinement
  phase_4: approval_generation    # Generate approval-ready output
  ends_with: ynp                  # Always call /ynp at end

# ============================================================================
# CANONICAL PROTOCOLS (MUST LOAD AND FOLLOW)
# ============================================================================
protocols:
  - name: GMP-System-Prompt
    path: "docs/_GMP Execute + Audit/GMP-System-Prompt-v1.0.md"
    purpose: "Cross-GMP governance, L9 invariants, scope containment"
    load_at: "phase_0"
  - name: GMP-Action-Prompt-Canonical
    path: "docs/_GMP Execute + Audit/GMP-Action-Prompt-Canonical-v1.0.md"
    purpose: "Phase 0-6 specification, TODO format, report structure"
    load_at: "phase_4"
  - name: GMP-Audit-Prompt-Canonical
    path: "docs/_GMP Execute + Audit/GMP-Audit-Prompt-Canonical-v1.0.md"
    purpose: "Post-execution audit, evidence collection"
    load_at: "phase_4"

# Protocol compliance requirements
protocol_compliance:
  todo_format:
    required_fields:
      - todo_id           # e.g., [T1]
      - file_path         # Absolute path under /Users/ib-mac/Projects/L9/
      - line_range        # e.g., 44-52
      - action_verb       # Replace | Insert | Delete | Wrap | Move
      - target_structure  # function/class/block name
      - expected_change   # One sentence max
      - gate              # None or validation gate
      - imports           # NONE or list of exact imports
  forbidden_words:
    - "maybe"
    - "likely"
    - "should"
    - "consider"
    - "probably"
  l9_invariants:
    protected_unless_explicit:
      - "docker-compose.yml"
      - "kernel_loader.py"
      - "executor.py"
      - "memory_substrate_service.py"
      - "websocket_orchestrator.py"

# Execution phases
phases:
  - id: 0
    name: "STATE_SYNC + PROTOCOL LOAD"
    gate: null
    auto_call: "rules"
    protocols: ["GMP-System-Prompt"]
  - id: 0.5
    name: "CONTEXT HARVEST + IMPACT SCAN"
    gate: "context_inventoried"
    auto_call: null  # Inline logic: scan chat context + harvest provided files
    protocols: []
    purpose: "Extract artifacts from chat, inventory referenced files, assess impact on plan scope"
  - id: 1
    name: "ANALYZE + EVALUATE"
    gate: "target_classified"
    auto_call: "analyze_evaluate"
    protocols: []
  - id: 2
    name: "PLAN SYNTHESIS"
    gate: "findings_synthesized"
    auto_call: null
    protocols: []
  - id: 3
    name: "REASONING REFINEMENT"
    gate: "plan_refined"
    auto_call: "reasoning"
    protocols: []
  - id: 4
    name: "APPROVAL GENERATION (Protocol-Compliant)"
    gate: "approval_ready"
    auto_call: null
    protocols: ["GMP-Action-Prompt-Canonical", "GMP-Audit-Prompt-Canonical"]
  - id: 5
    name: "YNP RECOMMENDATION"
    gate: "next_action_clear"
    auto_call: "ynp"
    protocols: []

# Output structure
output:
  path_template: "generated/plans/PLAN-{timestamp}-{description}.md"
  required_sections:
    - "EXECUTIVE SUMMARY"
    - "STATE_SYNC"
    - "PROTOCOLS LOADED"
    - "CONTEXT HARVEST"           # NEW: Files provided/referenced + already-generated artifacts
    - "ANALYSIS FINDINGS"
    - "SYNTHESIZED PLAN"
    - "REASONING REFINEMENT"
    - "APPROVAL PACKAGE (Protocol-Compliant)"
    - "GMP-READY TODO PLAN (Canonical Format)"
    - "RISK ASSESSMENT"
    - "YNP RECOMMENDATION"

# Reasoning modes applied
reasoning_modes:
  - abductive    # Pattern discovery
  - deductive    # Logical validation
  - inductive    # Pattern generalization

# Tags
tags: ["planning", "l9", "enterprise", "chain-command", "strategic", "protocol-compliant"]
---

# === L9 /plan: Enterprise Planning Protocol ===

> **Version:** 1.2.0 (Protocol-Compliant + Context Harvest)  
> **Updated:** 2026-01-04  
> **Chains:** Context Harvest → `/analyze_evaluate` → Synthesis → `/reasoning` → Approval  
> **Protocols:** GMP-System-Prompt-v1.0 | GMP-Action-Prompt-Canonical-v1.0 | GMP-Audit-Prompt-Canonical-v1.0

## 📜 PROTOCOL FOUNDATION

This command is **protocol-compliant** — all outputs follow the canonical GMP protocols from `.cursor/protocols/` (mirrored in `docs/_GMP Execute + Audit/`).

| Protocol | Purpose | Loaded At |
|----------|---------|-----------|
| GMP-System-Prompt-v1.0 | Cross-GMP governance, L9 invariants | Phase 0 |
| GMP-Action-Prompt-Canonical-v1.0 | TODO format, phase specification | Phase 4 |
| GMP-Audit-Prompt-Canonical-v1.0 | Evidence collection, audit trail | Phase 4 |

**Key Guarantee:** The TODO plan output from `/plan` is directly executable by `/gmp` with zero reformatting.

## ⛓️ COMMAND CHAIN

```
/plan invoked
  ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 0: STATE_SYNC                                         │
│ → Call /rules                                                │
│ → Load workflow_state.md                                     │
│ → Extract: PHASE, priorities, context                        │
└─────────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 0.5: CONTEXT HARVEST + IMPACT SCAN ⭐ NEW              │
│ → Scan chat context for provided/referenced files            │
│ → Harvest already-generated artifacts (generated/, chat)     │
│ → Inventory: what exists vs what needs creation              │
│ → Assess impact on plan scope + identify reusable assets     │
│ → Prevent redundant generation, maximize leverage            │
└─────────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: ANALYZE + EVALUATE                                  │
│ → Call /analyze_evaluate on target (informed by harvest)     │
│ → Structure map + health scan + cross-reference              │
│ → Tech debt score + impact projection                        │
└─────────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: PLAN SYNTHESIS                                      │
│ → Extract key findings                                       │
│ → Identify optimal implementation path                       │
│ → Generate structured plan with TODOs                        │
│ → Define success criteria + constraints                      │
└─────────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 3: REASONING REFINEMENT (/reasoning recursive)        │
│ → Apply multi-modal reasoning (abductive + deductive + ind.)│
│ → Challenge assumptions                                      │
│ → Identify blind spots + risks                               │
│ → Refine plan with confidence scoring                        │
└─────────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 4: APPROVAL GENERATION                                 │
│ → Package refined plan for approval                          │
│ → Include: scope, risk, effort, dependencies                 │
│ → Generate GMP-ready TODO plan (if applicable)               │
│ → Output approval request format                             │
└─────────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 5: YNP RECOMMENDATION                                  │
│ → Call /ynp                                                  │
│ → Recommend: approve + execute OR refine OR defer            │
└─────────────────────────────────────────────────────────────┘
```

---

## WHAT IT DOES

**Enterprise planning in one command** that chains multiple analysis phases:

| Phase | Command/Action | Output |
|-------|---------------|--------|
| 0 | `/rules` | STATE_SYNC, context, priorities |
| 0.5 | Context Harvest | Inventory of provided/referenced files + reusable assets |
| 1 | `/analyze_evaluate` | Structure + health + cross-ref findings (informed by harvest) |
| 2 | Synthesis | Structured plan with TODOs (leveraging existing artifacts) |
| 3 | `/reasoning` | Refined plan with confidence scores |
| 4 | Approval Gen | Approval-ready package |
| 5 | `/ynp` | Next action recommendation |

**Key principles:** 
- Don't regenerate what already exists — harvest first, then plan
- Synthesize, reason, and prepare for execution

---

## WHEN TO USE

| Use `/plan` When... | Use Other Commands When... |
|--------------------|---------------------------|
| Need optimal implementation path | Just exploring (use `/analyze`) |
| Planning complex feature/refactor | Just auditing (use `/evaluate`) |
| Need approval before execution | Ready to execute (use `/gmp`) |
| Strategic decision required | Debugging specific issue |
| Multiple implementation options exist | Single clear path |
| L9-grade planning required | Quick one-off task |

---

## EXECUTION PROTOCOL

### Phase 0: STATE_SYNC + PROTOCOL LOAD (/rules)

```markdown
## STATE_SYNC

1. Read workflow_state.md
2. Extract:
   - Current PHASE (0-6)
   - Active TODOs
   - Priority tier
   - Recent context
3. Identify target scope
4. Classify tier: KERNEL | RUNTIME | INFRA | UX

## PROTOCOL LOAD (MANDATORY)

Load and internalize canonical protocols from frontmatter.protocols[]:

1. **GMP-System-Prompt-v1.0.md**
   - Path: `docs/_GMP Execute + Audit/GMP-System-Prompt-v1.0.md`
   - Purpose: Cross-GMP governance, L9 invariants, scope containment
   - Key constraints:
     - All file paths must be absolute under `/Users/ib-mac/Projects/L9/`
     - Cannot modify L9 invariants without explicit TODO
     - Prerequisite validation before execution

2. **GMP-Action-Prompt-Canonical-v1.0.md** (loaded at Phase 4)
   - Path: `docs/_GMP Execute + Audit/GMP-Action-Prompt-Canonical-v1.0.md`
   - Purpose: Phase 0-6 specification, TODO format, report structure
   - Key requirements:
     - TODO format with all required fields
     - No speculation words ("maybe", "likely", "should", etc.)
     - Deterministic, auditable TODO plan

3. **GMP-Audit-Prompt-Canonical-v1.0.md** (loaded at Phase 4)
   - Path: `docs/_GMP Execute + Audit/GMP-Audit-Prompt-Canonical-v1.0.md`
   - Purpose: Post-execution audit, evidence collection
```

### ⚠️ L9 INVARIANTS (From GMP-System-Prompt)

These are **protected unless explicitly planned**:

| Invariant | File | Protection |
|-----------|------|------------|
| WebSocket foundations | `docker-compose.yml` | FORBIDDEN without explicit TODO |
| Kernel entry points | `kernel_loader.py` | FORBIDDEN without explicit TODO |
| Agent execution | `executor.py` | FORBIDDEN without explicit TODO |
| Memory substrate | `memory_substrate_service.py` | FORBIDDEN without explicit TODO |
| WebSocket orchestration | `websocket_orchestrator.py` | FORBIDDEN without explicit TODO |

**If plan touches these files → Must appear in TODO plan with explicit justification.**

### Phase 0.5: CONTEXT HARVEST + IMPACT SCAN ⭐

**Purpose:** Before deep analysis, inventory what's already available to prevent redundant work and maximize leverage.

**This phase answers:**
- What files were provided in the chat context?
- What files are referenced in the user's instructions?
- What artifacts already exist in `generated/`, chat transcripts, or prior runs?
- How do these impact the planning scope?

```markdown
## CONTEXT HARVEST

### Step 1: SCAN CHAT CONTEXT

Identify all files/artifacts in the current conversation:

```
CHAT CONTEXT INVENTORY:
├── PROVIDED FILES (pasted/attached in chat)
│   ├── [filename.py] — [N lines] — [purpose/description]
│   ├── [config.yaml] — [N lines] — [purpose/description]
│   └── ...
│
├── REFERENCED FILES (mentioned in instructions)
│   ├── [path/to/file.py] — [status: exists/missing/outdated]
│   └── ...
│
├── EMBEDDED CODE BLOCKS (in chat, not yet files)
│   ├── Block 1: [language] — [N lines] — [inferred purpose]
│   └── ...
│
└── EXTERNAL REFERENCES (URLs, docs, specs)
    ├── [URL/doc name] — [relevance to task]
    └── ...
```

### Step 2: HARVEST EXISTING ARTIFACTS

Check for already-generated assets (use `/harvest` logic):

```
EXISTING ARTIFACTS:
├── generated/
│   ├── [file.py] — [created: timestamp] — [reusable: YES/PARTIAL/NO]
│   └── ...
│
├── Prior GMP outputs
│   ├── reports/GMP_Report_*.md — [relevant GMPs]
│   └── ...
│
├── Extracted from chat (if applicable)
│   ├── [Models/classes ready to use]
│   ├── [Configs ready to apply]
│   └── [SQL ready to migrate]
│
└── REUSE CANDIDATES
    ├── [artifact] — [can be used directly / needs adaptation]
    └── ...
```

### Step 3: IMPACT ASSESSMENT

Evaluate how context affects planning:

```
IMPACT ASSESSMENT:

| Category | Finding | Impact on Plan |
|----------|---------|----------------|
| Already done | [X files exist in generated/] | Skip generation, use directly |
| Partial work | [Y components partially complete] | Complete, don't restart |
| Dependencies provided | [Z configs/specs in chat] | Integrate into TODOs |
| Gaps identified | [N items still needed] | Focus plan on gaps only |
| Conflicts detected | [Existing vs requested] | Resolve before proceeding |

SCOPE ADJUSTMENT:
- Original scope: [what user asked for]
- Reduced scope: [after accounting for existing work]
- Net new work: [only what's actually needed]
```

### Step 4: LEVERAGE STRATEGY

Determine how to use harvested assets:

```
LEVERAGE STRATEGY:

| Asset | Location | Action | Saves |
|-------|----------|--------|-------|
| [models.py] | generated/core/ | Use directly | ~30 min |
| [config.yaml] | chat context | Extract + apply | ~15 min |
| [GMP-16 report] | reports/ | Reference patterns | ~20 min |
| [SQL migration] | embedded in chat | Harvest → migrations/ | ~25 min |

TOTAL SAVINGS: ~1.5 hours (vs regenerating from scratch)
```

### Step 5: CONTEXT-INFORMED SCOPE

Update the planning scope based on harvest:

```
CONTEXT-INFORMED SCOPE:

INCLUDE (still needed):
- [Component A] — not in context, must create
- [Integration B] — partial in chat, complete it

EXCLUDE (already done):
- [Models] — complete in generated/
- [Config] — provided in chat, just apply

MODIFY (adapt existing):
- [Service X] — exists but needs updates per new requirements

ANALYZE TARGET (for Phase 1):
- Focus /analyze_evaluate on: [reduced scope]
- Skip analysis of: [already-understood components]
```
```

**Gate:** Phase 0.5 complete when:
- [ ] All chat context inventoried
- [ ] Existing artifacts checked
- [ ] Impact assessed
- [ ] Scope adjusted to prevent redundant work

---

### Phase 1: ANALYZE + EVALUATE (/analyze_evaluate)

Run full combined analysis on target:

```markdown
## ANALYSIS FINDINGS

### Structure Map
- Files, classes, functions, flows
- Entry points, hotspots, dependencies

### Health Scan
- L9 pattern compliance
- Anti-patterns found
- Test coverage gaps

### Cross-Referenced Findings
- Structure issues + compliance gaps
- Impact projection
- Tech debt score

### Auto-Fix Candidates
- 🤖 Automatable (immediate)
- 🔧 Semi-auto (template + review)
- 👤 Manual required
```

### Phase 2: PLAN SYNTHESIS

Transform analysis into actionable plan:

```markdown
## SYNTHESIZED PLAN

### Objective
[Clear statement of what we're building/changing]

### Success Criteria
- [ ] Criterion 1: [measurable outcome]
- [ ] Criterion 2: [measurable outcome]
- [ ] Criterion 3: [measurable outcome]

### Constraints
- Time: [estimate]
- Scope: [boundaries]
- Dependencies: [blockers]
- Risk tolerance: [HIGH/MEDIUM/LOW]

### Implementation Path

#### Option A: [Name] ⭐ RECOMMENDED
- Approach: [description]
- Effort: [estimate]
- Risk: [assessment]
- Pros: [list]
- Cons: [list]

#### Option B: [Name]
- Approach: [description]
- Effort: [estimate]
- Risk: [assessment]
- Pros: [list]
- Cons: [list]

### Preliminary TODO Plan
| # | File | Change | Effort | Risk |
|---|------|--------|--------|------|
| T1 | path/to/file.py | [change] | 15 min | LOW |
| T2 | path/to/file.py | [change] | 30 min | MED |

### Dependencies
- Before: [what must exist first]
- Parallel: [what can happen simultaneously]
- After: [what unblocks next]
```

### Phase 3: REASONING REFINEMENT (/reasoning)

Apply multi-modal reasoning recursively:

```markdown
## REASONING REFINEMENT

### 🔬 Abductive Analysis (Pattern Discovery)
**Question:** What patterns suggest the best path?

| Observation | Possible Explanation | Likelihood | Evidence |
|------------|---------------------|------------|----------|
| [obs 1] | [exp 1] | HIGH | [evidence] |
| [obs 2] | [exp 2] | MED | [evidence] |

**Hypothesis:** [Most likely optimal path based on patterns]
**Confidence:** [0.0-1.0]

### 🧮 Deductive Analysis (Logical Validation)

**Premises:**
1. [Rule or constraint that applies]
2. [Another rule or constraint]
3. [L9 governance requirement]

**Logical Check:**
- IF [condition] THEN [consequence]
- Plan satisfies premises: ✅/❌

**Validation Result:** [PASS/FAIL with reasoning]
**Confidence:** [0.0-1.0]

### 📈 Inductive Analysis (Pattern Generalization)

**Prior Examples:**
1. [Similar past implementation] → [outcome]
2. [Related pattern in codebase] → [outcome]

**Generalized Principle:** [What works based on patterns]
**Applicability:** [HIGH/MEDIUM/LOW]
**Confidence:** [0.0-1.0]

### 🧵 Synthesis

**Refined Path:** [Optimal implementation after reasoning]
**Key Refinements:**
- [Refinement 1 from reasoning]
- [Refinement 2 from reasoning]

**Risk Mitigations:**
- [Risk 1] → [Mitigation]
- [Risk 2] → [Mitigation]

**Blind Spots Identified:**
- [Potential issue not in original plan]

**Overall Confidence Score:** [weighted average]
```

### Phase 4: APPROVAL GENERATION (Protocol-Compliant)

**CRITICAL:** This phase MUST produce output that follows the canonical protocols.

Load protocols:
- `GMP-Action-Prompt-Canonical-v1.0.md` — for TODO format
- `GMP-Audit-Prompt-Canonical-v1.0.md` — for evidence requirements

Package for approval:

```markdown
## APPROVAL PACKAGE

### 📋 Executive Summary
[2-3 sentence summary of plan]

### 📊 Plan Metrics
| Metric | Value |
|--------|-------|
| Files affected | [N] |
| Estimated effort | [time] |
| Risk level | [HIGH/MEDIUM/LOW] |
| Confidence score | [0.0-1.0] |
| Tier classification | [KERNEL/RUNTIME/INFRA/UX] |
| L9 Invariants touched | [YES/NO — list if YES] |

### 🎯 Recommended Path
[Name of recommended option with 1-sentence why]

### ⚠️ Risk Assessment
| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| [risk 1] | [P] | [I] | [mitigation] |
| [risk 2] | [P] | [I] | [mitigation] |

---

## 📝 GMP-READY TODO PLAN (Canonical Format)

⚠️ **FORMAT REQUIREMENTS (from GMP-Action-Prompt-Canonical-v1.0.md):**
- All paths MUST be absolute under `/Users/ib-mac/Projects/L9/`
- NO speculation words: "maybe", "likely", "should", "consider", "probably"
- Each TODO independently checkable and directly observable
- Once locked, plan is IMMUTABLE

### TODO PLAN (LOCKED)

- [T1] File: `/Users/ib-mac/Projects/L9/path/to/file.py`
       Lines: 44-52
       Action: Replace
       Target: `function_name()`
       Change: Replace `old_call()` → `new_call()` without altering surrounding logic
       Gate: py_compile
       Imports: NONE

- [T2] File: `/Users/ib-mac/Projects/L9/path/to/file.py`
       Lines: 88-95
       Action: Insert
       Target: `ClassName`
       Change: Add new method `new_method()` that [specific behavior]
       Gate: lint
       Imports: `from typing import Optional`

### TODO INDEX HASH
```
SHA256(TODO_PLAN_TEXT) = [auto-generated hash for integrity]
```

### L9 INVARIANT CHECK
| Invariant File | Touched? | Justification |
|----------------|----------|---------------|
| docker-compose.yml | NO | — |
| kernel_loader.py | NO | — |
| executor.py | NO | — |
| memory_substrate_service.py | NO | — |
| websocket_orchestrator.py | NO | — |

---

### 🚦 Approval Request

**Requesting approval for:**
- [ ] Proceed with recommended path
- [ ] Allocate [time] for implementation
- [ ] Accept [risk level] risk with mitigations
- [ ] L9 invariants: [NONE TOUCHED / EXPLICITLY PLANNED]

**Approval authority required:**
- KERNEL_TIER: Igor explicit approval required
- RUNTIME_TIER: Proceed with monitoring
- INFRA_TIER: Igor explicit approval required
- UX_TIER: Auto-approve

### 📎 Execution Command
Once approved, execute with:
```
/gmp @generated/plans/PLAN-{timestamp}-{description}.md
```

Or copy the TODO PLAN (LOCKED) section directly into a new /gmp invocation.

### 📎 Protocol References
- GMP-System-Prompt: `docs/_GMP Execute + Audit/GMP-System-Prompt-v1.0.md`
- GMP-Action-Prompt: `docs/_GMP Execute + Audit/GMP-Action-Prompt-Canonical-v1.0.md`
- GMP-Audit-Prompt: `docs/_GMP Execute + Audit/GMP-Audit-Prompt-Canonical-v1.0.md`
```

### Phase 5: YNP RECOMMENDATION (/ynp)

```markdown
## 🎯 YNP (Your Next Play)

**IF APPROVED:**
Primary: `/gmp` with TODO Plan from Phase 4
Scope: [files in scope]
Estimated time: [duration]

**IF NEEDS REFINEMENT:**
Primary: Re-run `/plan` with clarified constraints
Focus: [what to clarify]

**IF DEFERRED:**
Primary: Update workflow_state.md with plan for later
Next: [alternative action]

**Alternates:**
1. [Alternative if primary blocked]
2. [Alternative approach]
```

---

## OUTPUT FORMAT

Complete `/plan` output structure:

```markdown
# 📋 L9 ENTERPRISE PLAN: [Target/Objective]

**Generated:** [timestamp]
**Target:** [scope]
**Tier:** [KERNEL/RUNTIME/INFRA/UX]
**Confidence:** [overall score]
**Protocol Version:** GMP v1.0

---

## 📍 STATE_SYNC
[From Phase 0]

---

## 📜 PROTOCOLS LOADED

| Protocol | Path | Status |
|----------|------|--------|
| GMP-System-Prompt-v1.0 | `docs/_GMP Execute + Audit/GMP-System-Prompt-v1.0.md` | ✅ Loaded |
| GMP-Action-Prompt-Canonical-v1.0 | `docs/_GMP Execute + Audit/GMP-Action-Prompt-Canonical-v1.0.md` | ✅ Loaded |
| GMP-Audit-Prompt-Canonical-v1.0 | `docs/_GMP Execute + Audit/GMP-Audit-Prompt-Canonical-v1.0.md` | ✅ Loaded |

**L9 Invariants Check:**
- [ ] docker-compose.yml — NOT TOUCHED
- [ ] kernel_loader.py — NOT TOUCHED
- [ ] executor.py — NOT TOUCHED
- [ ] memory_substrate_service.py — NOT TOUCHED
- [ ] websocket_orchestrator.py — NOT TOUCHED

---

## 🌾 CONTEXT HARVEST
[From Phase 0.5]

### Chat Context Inventory
| Type | Count | Details |
|------|-------|---------|
| Provided files | [N] | [list] |
| Referenced files | [N] | [list with status] |
| Embedded code blocks | [N] | [languages/purposes] |
| External references | [N] | [URLs/docs] |

### Existing Artifacts
| Location | Asset | Reusable? | Action |
|----------|-------|-----------|--------|
| generated/ | [file] | ✅/⚠️/❌ | Use/Adapt/Regenerate |
| chat | [code block] | ✅ | Extract → [target] |

### Scope Adjustment
- **Original scope:** [full request]
- **Net new work:** [after harvest]
- **Time saved:** [estimate from leveraging existing]

---

## 🔍 ANALYSIS FINDINGS
[From Phase 1 - /analyze_evaluate, informed by harvest]

---

## 📐 SYNTHESIZED PLAN
[From Phase 2]

---

## 🧠 REASONING REFINEMENT
[From Phase 3 - /reasoning]

---

## ✅ APPROVAL PACKAGE (Protocol-Compliant)
[From Phase 4 - follows GMP-Action-Prompt-Canonical format]

---

## 📝 GMP-READY TODO PLAN (Canonical Format)

### TODO PLAN (LOCKED)

- [T1] File: `/Users/ib-mac/Projects/L9/[path]`
       Lines: [range]
       Action: [Replace|Insert|Delete|Wrap|Move]
       Target: `[symbol]`
       Change: [one sentence, no speculation words]
       Gate: [py_compile|lint|None]
       Imports: [NONE|list]

### TODO INDEX HASH
```
SHA256 = [hash]
```

---

## 🎯 YNP RECOMMENDATION
[From Phase 5 - /ynp]

---

## 📊 PLAN METADATA
```yaml
plan:
  id: PLAN-[timestamp]
  target: [scope]
  tier: [classification]
  generated: [timestamp]
  protocol_version: "GMP-v1.0"
  
  protocols_loaded:
    - GMP-System-Prompt-v1.0: ✅
    - GMP-Action-Prompt-Canonical-v1.0: ✅
    - GMP-Audit-Prompt-Canonical-v1.0: ✅
  
  phases_completed:
    - state_sync: ✅
    - protocol_load: ✅
    - context_harvest: ✅
    - analyze_evaluate: ✅
    - synthesis: ✅
    - reasoning: ✅
    - approval_gen: ✅
    
  confidence:
    abductive: [score]
    deductive: [score]
    inductive: [score]
    overall: [weighted]
  
  l9_invariants:
    docker_compose: NOT_TOUCHED
    kernel_loader: NOT_TOUCHED
    executor: NOT_TOUCHED
    memory_substrate: NOT_TOUCHED
    websocket_orchestrator: NOT_TOUCHED
    
  approval:
    authority_required: [IGOR/AUTO]
    status: PENDING
    
  execution:
    next_command: "/gmp"
    todo_count: [N]
    estimated_effort: [time]
    todo_format: "GMP-Action-Canonical-v1.0"
```
```

---

## USAGE

### Standard Planning
```
/plan "Implement rate limiting for API endpoints"

Flow:
1. /rules → STATE_SYNC
2. Context Harvest → Scan chat for provided files, check generated/
3. /analyze_evaluate @api/ → Deep analysis (scoped by harvest)
4. Synthesis → Structured plan (leveraging existing artifacts)
5. /reasoning → Refine with multi-modal reasoning
6. Approval Gen → Package for approval
7. /ynp → Recommend next action
```

### With Context Files (leverages chat context)
```
/plan "Wire observability module"

[User has pasted models.py, config.yaml, and referenced prior GMP in chat]

Flow:
1. /rules → STATE_SYNC
2. Context Harvest → Finds 3 files in chat, 2 in generated/
3. Scope adjustment: Skip model generation (already done)
4. /analyze_evaluate → Focus only on wiring, not creation
5. Synthesis → Plan uses existing models, plans integration only
6. /reasoning → Validates integration approach
7. Approval Gen → 3 TODOs instead of 12 (harvested 9)
8. /ynp → Execute with significant time savings
```

### With Target Scope
```
/plan @core/agents/ "Add timeout handling to executor"

Flow: Same, but focused on core/agents/ directory
```

### Quick Mode (Skip Reasoning)
```
/plan --quick "Add logging to webhook handlers"

Flow:
1. /rules
2. /analyze_evaluate
3. Synthesis (simplified)
4. Skip /reasoning
5. Approval Gen
6. /ynp
```

### With Constraints
```
/plan --time 2h --risk LOW "Refactor memory substrate"

Flow: Same, but plan must fit constraints
```

---

## FLAGS & OPTIONS

| Flag | Description | Default |
|------|-------------|---------|
| `--quick` | Skip Phase 3 reasoning refinement | false |
| `--skip-harvest` | Skip Phase 0.5 context harvest (not recommended) | false |
| `--harvest-only` | Run only Phase 0.5, output inventory without full plan | false |
| `--time DURATION` | Time constraint for plan | none |
| `--risk LEVEL` | Risk tolerance (HIGH/MEDIUM/LOW) | MEDIUM |
| `--focus AREA` | Emphasize: performance/security/reliability | all |
| `--options N` | Generate N implementation options | 2 |
| `--gmp-ready` | Output GMP Action file directly | false |
| `--json` | Output as JSON for automation | false |

---

## PROTOCOL COMPLIANCE

### Required Protocols

| Protocol | Path | When Loaded | Purpose |
|----------|------|-------------|---------|
| GMP-System-Prompt-v1.0 | `docs/_GMP Execute + Audit/GMP-System-Prompt-v1.0.md` | Phase 0 | Cross-GMP governance, L9 invariants |
| GMP-Action-Prompt-Canonical-v1.0 | `docs/_GMP Execute + Audit/GMP-Action-Prompt-Canonical-v1.0.md` | Phase 4 | TODO format, phase specification |
| GMP-Audit-Prompt-Canonical-v1.0 | `docs/_GMP Execute + Audit/GMP-Audit-Prompt-Canonical-v1.0.md` | Phase 4 | Evidence requirements |

### TODO Format (from GMP-Action-Prompt-Canonical)

Every TODO in the output MUST follow this exact format:

```markdown
- [T#] File: `/Users/ib-mac/Projects/L9/[absolute/path]`
       Lines: [start]-[end]
       Action: [Replace|Insert|Delete|Wrap|Move]
       Target: `[function/class/block name]`
       Change: [one sentence, no speculation]
       Gate: [py_compile|lint|test|None]
       Imports: [NONE|list of exact imports]
```

### Forbidden Words

The following words are **FORBIDDEN** in TODO plans (per GMP-Action-Prompt-Canonical):
- ❌ "maybe"
- ❌ "likely"
- ❌ "should"
- ❌ "consider"
- ❌ "probably"

Use definitive language: "Replace X with Y", "Insert Z at line N", etc.

### L9 Invariant Protection

These files require **explicit TODO justification** if touched:

| File | Protection Level |
|------|-----------------|
| `docker-compose.yml` | FORBIDDEN without explicit TODO + justification |
| `kernel_loader.py` | FORBIDDEN without explicit TODO + justification |
| `executor.py` | FORBIDDEN without explicit TODO + justification |
| `memory_substrate_service.py` | FORBIDDEN without explicit TODO + justification |
| `websocket_orchestrator.py` | FORBIDDEN without explicit TODO + justification |

---

## INTEGRATION

```
┌─────────────────────────────────────────────────────────────┐
│                    PROTOCOL LAYER                           │
│  GMP-System-Prompt │ GMP-Action-Prompt │ GMP-Audit-Prompt   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────┐     ┌─────────────────┐     ┌─────────────────┐
│ /rules  │────▶│ Context Harvest │────▶│/analyze_evaluate│
│ (init)  │     │  (Phase 0.5)    │     │    (Phase 1)    │
└─────────┘     │ Scan + Harvest  │     │ (informed by    │
     │          │ + Impact Scan   │     │  harvest)       │
     │          └─────────────────┘     └────────┬────────┘
     │ Load GMP-System-Prompt                    │
     ↓                                           ▼
┌─────────┐     ┌─────────────────┐     ┌───────────────────┐
│  /ynp   │◀────│ Approval Gen    │◀────│  Synthesis →      │
│ (final) │     │   (Phase 4)     │     │  /reasoning       │
└─────────┘     │ Load GMP-Action │     │  (Phase 2 → 3)    │
                │ + GMP-Audit     │     └───────────────────┘
                └─────────────────┘
                        ↓
                ┌───────────────┐
                │     /gmp      │
                │ (if approved) │
                └───────────────┘
```

- **Starts with:** `/rules` (always) + loads GMP-System-Prompt
- **Phase 0.5:** Context Harvest — scans chat, inventories provided files, harvests existing artifacts
- **Calls:** `/analyze_evaluate` (Phase 1) — informed by harvest, scoped to gaps only
- **Calls:** `/reasoning` (Phase 3)
- **Phase 4:** Loads GMP-Action-Prompt + GMP-Audit-Prompt for canonical TODO format
- **Ends with:** `/ynp` (always)
- **Chains to:** `/gmp` (if approved) — TODO plan is already protocol-compliant
- **Updates:** `workflow_state.md` with plan summary
- **Protocol paths:** `docs/_GMP Execute + Audit/*.md`
- **Efficiency:** Prevents regenerating existing work; maximizes leverage of context

---

## ANTI-PATTERNS

### Protocol Violations (CRITICAL)

❌ **DON'T:** Skip protocol loading at Phase 0
❌ **DON'T:** Use relative paths in TODO plans (must be absolute: `/Users/ib-mac/Projects/L9/...`)
❌ **DON'T:** Use speculation words in TODOs ("maybe", "likely", "should", "consider", "probably")
❌ **DON'T:** Touch L9 invariant files without explicit TODO + justification
❌ **DON'T:** Generate TODO plans without all required fields

### Context Harvest Violations (NEW)

❌ **DON'T:** Skip Phase 0.5 — regenerating existing work wastes hours
❌ **DON'T:** Ignore files provided in chat context — they're there for a reason
❌ **DON'T:** Regenerate code that already exists in `generated/` or chat
❌ **DON'T:** Analyze everything when harvest reveals reduced scope
❌ **DON'T:** Miss embedded code blocks in chat transcripts

### Execution Violations

❌ **DON'T:** Skip /rules at start (need context + protocol load)
❌ **DON'T:** Jump to implementation without synthesis
❌ **DON'T:** Skip reasoning for complex plans
❌ **DON'T:** Generate plan without approval package
❌ **DON'T:** Forget /ynp at end

### Best Practices

✅ **DO:** Always load protocols at Phase 0
✅ **DO:** Run Context Harvest (Phase 0.5) before analysis — efficiency counts!
✅ **DO:** Inventory ALL files in chat context before planning
✅ **DO:** Use `/harvest` logic to extract already-generated artifacts
✅ **DO:** Adjust scope to focus only on net new work
✅ **DO:** Use absolute paths in all TODO items
✅ **DO:** Use definitive language: "Replace X with Y", "Insert Z at line N"
✅ **DO:** Check L9 invariants and document if any are touched
✅ **DO:** Generate multiple options when appropriate
✅ **DO:** Apply multi-modal reasoning
✅ **DO:** Include risk assessment
✅ **DO:** Package for approval with clear ask
✅ **DO:** Output TODO plan in canonical GMP format for direct `/gmp` execution

---

## RECURSIVE REFINEMENT

For complex plans, `/plan` can call itself recursively:

```
/plan "Complex multi-phase project"
  ↓
Phase 3 identifies sub-problems
  ↓
For each sub-problem:
  /plan --quick "Sub-problem 1"
  /plan --quick "Sub-problem 2"
  ↓
Aggregate into master plan
```

---

## EXAMPLES

### Example 1: Feature Implementation
```
/plan "Add WebSocket support to Slack adapter"

Output:
- Analysis: Current adapter structure, dependencies
- Synthesis: 3 implementation options, recommend option B
- Reasoning: Validates against L9 patterns, refines approach
- Approval: 5 TODOs, 2h effort, MEDIUM risk
- YNP: /gmp with TODO plan
```

### Example 2: Refactoring
```
/plan @memory/ "Consolidate substrate services"

Output:
- Analysis: 4 services with overlap, dependency map
- Synthesis: Phased consolidation plan
- Reasoning: Identifies breaking changes, rollback strategy
- Approval: 12 TODOs, 4h effort, HIGH risk (requires Igor)
- YNP: Await Igor approval, then /gmp
```

### Example 3: Quick Planning
```
/plan --quick "Add health endpoint to API"

Output:
- Analysis: API structure, existing endpoints
- Synthesis: Simple TODO plan
- Skip reasoning (--quick)
- Approval: 2 TODOs, 15min effort, LOW risk (auto-approve)
- YNP: /gmp immediately
```

---

**Remember: /plan = Harvest Context → Analyze → Synthesize → Reason → Package for Approval → Execute**

**Efficiency principle:** Don't regenerate what exists. Harvest first, plan the gaps.

