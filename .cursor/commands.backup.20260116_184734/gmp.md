---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "8.2.0"
component_id: "CMD-GMP-001"
component_name: "GMP - God-Mode Prompt"
layer: "commands"
domain: "execution"
type: "slash_command"
status: "active"
created: "2025-12-01T00:00:00Z"
updated: "2026-01-04T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "critical"
compliance_required: true
audit_trail: true
security_classification: "internal"

# ============================================================================
# MACHINE-READABLE METADATA (Parseable by CI/automation)
# ============================================================================
schema_version: "1.1"
command:
  name: gmp
  version: "8.2.0"
  description: "L9 God-Mode Prompt v1.1 — deterministic, phased, auditable code changes with variable bindings and constraint enforcement"
  updated: "2026-01-04"

# Command chain (auto-invoked)
chain:
  memory_inject: true          # INJECT: Search VPS memory for preferences/lessons before execution
  starts_with: rules           # Always call /rules first
  uses_if_needed: analyze      # Call /analyze if scope unclear
  before_end: extract-chat   # EXTRACT: Write learnings to VPS memory
  ends_with: ynp               # Always call /ynp at end (v8.0 auto-execute if ≥90%)

# ============================================================================
# GMP v1.1 SPEC STRUCTURE (Variable Bindings)
# ============================================================================
variable_bindings:
  TASK_NAME: ""              # e.g., "governance_orphans_full_instantiation"
  EXECUTION_SCOPE: ""        # Full scope description
  SPEC_PATH: ""              # Path to authoritative spec document
  REPORT_ROOT: "/Users/ib-mac/Projects/L9/reports"
  RISK_LEVEL: "Medium"       # Low | Medium | High
  IMPACT_METRICS: ""         # Metrics affected by this GMP
  VALIDATION_NOTES: ""       # Specific validation requirements

# Canonical protocols to load (v1.1)
protocols:
  - name: GMP-System-Prompt-v1.1
    path: "docs/_GMP Execute + Audit/GMP-System-Prompt-v1.1.md"
    purpose: "Cross-GMP governance with variable bindings"
  - name: GMP-Action-Prompt-v1.1
    path: "docs/_GMP Execute + Audit/GMP-Action-Prompt-Canonical-v1.1.md"
    purpose: "Phase 0-6 specification with constraints"
  - name: GMP-Audit-Prompt-v1.1
    path: "docs/_GMP Execute + Audit/GMP-Audit-Prompt-Canonical-v1.1.md"
    purpose: "Post-execution audit with regression checks"

# Execution phases
phases:
  - id: 0
    name: "TODO PLAN LOCK"
    gate: null
  - id: 1
    name: "BASELINE CONFIRMATION"
    gate: "files_exist"
  - id: 2
    name: "IMPLEMENTATION"
    gate: "todo_complete"
  - id: 3
    name: "ENFORCEMENT"
    gate: "guards_added"
  - id: 4
    name: "VALIDATION"
    gate: "tests_pass"
  - id: 5
    name: "RECURSIVE VERIFICATION"
    gate: "no_drift"
  - id: 6
    name: "FINAL AUDIT + REPORT"
    gate: "report_complete"

# Protected files (require explicit TODO entry)
protected_files:
  - "core/kernels/kernel_loader.py"
  - "core/agents/executor.py"
  - "memory/substrate_service.py"
  - "runtime/websocket_orchestrator.py"
  - "docker-compose.yml"
  - "kernels/**/*.yaml"

# Validation gates
validation_gates:
  - name: "py_compile"
    command: "python -m py_compile"
    required: true
  - name: "lint"
    command: "ruff check"
    required: true
  - name: "type-check"
    command: "pyright"
    required: false
  - name: "tests"
    command: "pytest"
    required: false

# TODO item schema (for validation)
todo_schema:
  required_fields:
    - file        # Absolute path
    - lines       # Range like "44-52"
    - action      # Replace | Insert | Delete | Wrap
    - target      # Symbol name
    - change      # Description of change
  optional_fields:
    - gate        # Validation gate
    - imports     # List of imports to add

# Report structure
report:
  path_template: "reports/Report_GMP-{id}-{description}.md"
  required_sections:
    - "EXECUTION REPORT"
    - "STATE_SYNC SUMMARY"
    - "TODO PLAN (LOCKED)"
    - "TODO INDEX HASH"
    - "PHASE CHECKLIST STATUS"
    - "FILES MODIFIED + LINE RANGES"
    - "TODO → CHANGE MAP"
    - "ENFORCEMENT + VALIDATION RESULTS"
    - "PHASE 5 RECURSIVE VERIFICATION"
    - "FINAL DEFINITION OF DONE"
    - "FINAL DECLARATION"
    - "YNP RECOMMENDATION"

# Tier classification
tiers:
  KERNEL:
    patterns: ["kernels/**", "kernel_loader.py", "executor.py"]
    requires_approval: true
  RUNTIME:
    patterns: ["core/**", "memory/**", "orchestration/**"]
    requires_approval: false
  INFRA:
    patterns: ["docker-compose.yml", "deploy/**", "infra/**"]
    requires_approval: true
  UX:
    patterns: ["ui/**", "frontend/**", "docs/**"]
    requires_approval: false

# Modes
modes:
  - name: "standard"
    usage: '/gmp "task description"'
    skip_analyze: false
  - name: "action_file"
    usage: "/gmp @GMP-Action-File.md"
    skip_analyze: true
  - name: "audit"
    usage: "/gmp --audit GMP-11"
    skip_analyze: true
  - name: "chain"
    usage: "/gmp --chain GMP-11 GMP-12 GMP-13"
    skip_analyze: true
---

# === L9 GMP: God-Mode Prompt Execution Protocol ===

> **Version:** 8.2.0 (GMP v1.1 Spec + Variable Bindings)  
> **Updated:** 2026-01-04  
> **Spec:** GMP_L9_VARIABLE_SPEC v1.1

## 🚀 VERSION 8.2: GMP v1.1 SPEC

**What's New:**
- **Variable Bindings** — Structured TASK_NAME, EXECUTION_SCOPE, RISK_LEVEL
- **Constraints & Invariants** — Explicit rules that MUST NOT be violated
- **Unified Interfaces** — Standard return types, CLI flags, error handling
- **Stop Conditions** — Escalation triggers when GMP cannot proceed
- **Multi-Phase TODO Plans** — Tier-based execution ordering
- **YNP v8.0 Integration** — Auto-execute at ≥90% confidence

---

## ⛓️ COMMAND CHAIN

```
/gmp invoked
  ↓
┌─────────────────────────────────┐
│ PHASE: INIT                     │
│ → Call /rules (STATE_SYNC)      │
│ → Load canonical protocols      │
└─────────────────────────────────┘
  ↓
┌─────────────────────────────────┐
│ PHASE: ANALYZE (if needed)      │
│ → If user prompt unclear:       │
│   Call /analyze to clarify      │
│ → If L-CTO prompt: skip         │
└─────────────────────────────────┘
  ↓
┌─────────────────────────────────┐
│ PHASE: EXECUTE (0-6)            │
│ → Lock TODO Plan                │
│ → Implement changes             │
│ → Validate + Report             │
└─────────────────────────────────┘
  ↓
┌─────────────────────────────────┐
│ PHASE: COMPLETE                 │
│ → Generate report               │
│ → Call /ynp (next action)       │
└─────────────────────────────────┘
```

---

## WHAT IT DOES

**One powerful command** for all tracked code changes:

1. **Binds Variables** — Sets TASK_NAME, EXECUTION_SCOPE, RISK_LEVEL
2. **Starts with /rules** — Loads state, protocols, tier classification
3. **Uses /analyze if needed** — Clarifies ambiguous user requests
4. **Enforces Constraints** — KERNEL protection, no duplicated responsibilities
5. **Executes 7-phase protocol** — Zero drift, zero freelancing
6. **Ends with /ynp v8.0** — Auto-execute if ≥90% confidence

**Key principle:** Every tracked change flows through /gmp. Variable bindings + constraints = deterministic execution.

---

## 🔒 CONSTRAINTS & INVARIANTS (v1.1)

### 1. KERNEL-TIER PROTECTION

You MUST NOT directly modify any KERNEL-tier files:
- `core/kernels/kernel_loader.py`
- `core/agents/executor.py`
- `memory/substrate_service.py`
- `runtime/websocket_orchestrator.py`
- `docker-compose.yml`
- Any file in `kernels/` directory

**If KERNEL changes required:** Express as TODO items in Phase 0 and route via dedicated KERNEL GMP flow, NOT executed directly.

### 2. NO DUPLICATED RESPONSIBILITIES

Respect these separations:

| Component | Responsibility | Does NOT |
|-----------|---------------|----------|
| `governance-validator.py` | Validates rule compliance | Block operations |
| `pre_execution_checker.py` | Pre-flight checks, blocks dangerous ops | Implement rule logic |
| `violation_tracker.py` | Tracks violations, computes stats | Act as general audit log |
| `intelligence_audit_logger.py` | Central audit trail | Reimplement analytics |

### 3. UNIFIED INTERFACES

Every new/modified Python file MUST:
- Use unified governance logger: `governance_logger`
- Load config via `.suite6-config.json` through `env-manager.py`
- Use `GovernanceException` as base error type
- Expose main operation returning: `(success: bool, data: dict, error: str)`
- Provide CLI with `--help`, `--dry-run`, `--verbose` (if script)

### 4. NO PLACEHOLDERS / NO TODOs IN OUTPUT

All modified files must be production-ready:
- No `[TODO]`, no placeholder logic
- Real error handling, real argument parsing, real type hints

### 5. SURGICAL EDITS ONLY

When wiring modules:
- Only make surgical additions (imports, entries, registrations)
- Do NOT regenerate or overwrite entire files
- Preserve existing structure and comments

---

## 📋 VARIABLE BINDINGS (v1.1)

Before execution, bind these variables:

```yaml
VARIABLE BINDINGS:
  TASK_NAME: "[descriptive_task_name]"
  
  EXECUTION_SCOPE: >
    [Full description of what this GMP will accomplish,
     without modifying protected KERNEL-tier files]
  
  SPEC_PATH: "[path to authoritative spec document, if any]"
  
  REPORT_ROOT: "/Users/ib-mac/Projects/L9/reports"
  
  RISK_LEVEL: "[Low | Medium | High]"
  
  IMPACT_METRICS: >
    [metrics affected: test coverage, CI stability, etc.]
  
  VALIDATION_NOTES: >
    [specific validation requirements for this task]
```

**Example:**
```yaml
TASK_NAME: add_rate_limiting_to_api
EXECUTION_SCOPE: Add rate limiting to api/client.py fetch methods
RISK_LEVEL: Medium
IMPACT_METRICS: API latency, error rate, request throughput
VALIDATION_NOTES: Run load test after implementation
```

---

## EXECUTION PROTOCOL

### INIT: Bind Variables + Load Context

```
1. BIND VARIABLES (from user prompt or GMP Action file):
   - TASK_NAME
   - EXECUTION_SCOPE
   - RISK_LEVEL
   - IMPACT_METRICS
   - VALIDATION_NOTES

2. CALL /rules:
   - Read workflow_state.md
   - Read .cursor/rules/*.mdc
   - Load protocols from frontmatter.protocols[]
   - Classify target tier
   - Summarize current state

3. LOAD CANONICAL PROTOCOLS (v1.1):
   - GMP-System-Prompt-v1.1.md
   - GMP-Action-Prompt-Canonical-v1.1.md
   
4. ENFORCE CONSTRAINTS:
   - Verify KERNEL-TIER files not in scope
   - Verify no duplicated responsibilities
   - Verify unified interfaces required
```

### ANALYZE: Clarify Scope (if needed)

```
IF user prompt is ambiguous or incomplete:
   → Call /analyze on target files
   → Map structure, flows, hotspots
   → Identify exact change locations
   → Output clarified scope

IF prompt from L-CTO or GMP Action file:
   → Skip /analyze (scope already clear)
   → Proceed directly to Phase 0
```

**When to /analyze:**
- User says "fix the issue in X" but doesn't specify which issue
- User references a module but not specific files/functions
- Multiple interpretations possible

**When to skip:**
- L-CTO provides full GMP Action prompt
- User provides explicit TODO list
- Scope is unambiguous

### EXECUTE: 7-Phase Protocol

#### Phase 0 — TODO PLAN LOCK (Multi-Phase Structure)

For complex tasks, organize TODOs by tier and phase:

```markdown
## TODO PLAN (LOCKED)

### Phase 1: Foundation
- [T1] File: `/Users/ib-mac/Projects/L9/integrity/hash-verifier.py`
       Lines: 1-50
       Action: Insert
       Target: `HashVerifier class`
       Change: Create new verifier with Suite 6 header
       Gate: py_compile
       Imports: hashlib, structlog

### Phase 2: Core Components
- [T2] File: `/Users/ib-mac/Projects/L9/path/to/file.py`
       Lines: 44-52
       Action: Replace
       Target: `function_name()`
       Change: Replace `old_call()` → `new_call()`
       Gate: lint
       Imports: NONE

### Phase 3: Integration
- [T3] File: `/Users/ib-mac/Projects/L9/path/to/__init__.py`
       Lines: 10-12
       Action: Insert
       Target: `exports`
       Change: Add `from .module import ClassName`
       Gate: None
       Imports: NONE
```

**Tier-Based Ordering:**
1. **Foundation:** Core utilities, verifiers, base classes
2. **Governance Core:** Validators, trackers, checkers
3. **Intelligence:** Context, learning, calibration
4. **Agents & Memory:** Routers, aggregators
5. **Integration:** Wiring, exports, registrations

**Rules:**
- No "maybe", "likely", "should", "consider"
- Every TODO has: file, lines, action, target, change (per frontmatter.todo_schema)
- Each TODO independently verifiable
- Respect tier ordering within phases

#### Phase 1 — BASELINE CONFIRMATION

- Open each file
- Verify line anchors exist
- Confirm symbols present
- Record baseline per TODO

#### Phase 2 — IMPLEMENTATION

- Execute TODOs in order
- Modify ONLY listed files and lines
- No extra imports
- Preserve META headers

#### Phase 3 — ENFORCEMENT

- Add guards/tests ONLY if TODO requires
- No invented enforcement
- Deterministic pass/fail

#### Phase 4 — VALIDATION

Run gates from frontmatter.validation_gates[]:
- `py_compile` (required)
- `ruff check` (required)
- `pyright` (if applicable)
- `pytest` (if specified)

Record results per TODO.

#### Phase 5 — RECURSIVE VERIFICATION

- Compare all changes to TODO plan
- Confirm no unauthorized diffs
- Verify report completeness

#### Phase 6 — FINAL AUDIT + REPORT

- Write report to path from frontmatter.report.path_template
- Include all sections from frontmatter.report.required_sections[]
- No placeholders

### COMPLETE: Next Action (/ynp v8.0 Integration)

```
After Phase 6:
   → Emit FINAL DECLARATION
   → Call /ynp v8.0 with:
     - Context Harvest (existing assets)
     - Reasoning Synthesis (abductive + deductive + inductive)
     - Recursive Alignment Pass
     - Confidence Scoring
   → IF confidence ≥90%: AUTO-EXECUTE next action
   → IF confidence <90%: Output recommendation with alternates
```

**YNP v8.0 Auto-Execute Triggers:**
- Next GMP in chain (if batched)
- Deployment (if all tests pass)
- Cleanup tasks (low risk)

---

## ROLE DEFINITION

You are a **constrained execution agent** operating inside L9.

**YOU MUST:**
- Execute instructions exactly as written
- Stop immediately if ambiguity detected
- Report results in required format
- Call /rules at start, /ynp at end

**YOU MUST NOT:**
- Redesign systems
- Invent requirements
- Guess missing information
- Freelance or improvise
- Fix "adjacent" issues not in TODO

---

## SCOPE CONFIRMATION

Before ANY edits, output:

```markdown
## 🔒 GMP SCOPE LOCK (v1.1)

**GMP ID:** GMP-[N]: [name]
**Source:** [User prompt | L-CTO | GMP Action file]
**Tier:** [KERNEL | RUNTIME | INFRA | UX] (from frontmatter.tiers)

### 📋 VARIABLE BINDINGS
| Variable | Value |
|----------|-------|
| TASK_NAME | [descriptive_name] |
| EXECUTION_SCOPE | [one-line summary] |
| RISK_LEVEL | [Low/Medium/High] |
| IMPACT_METRICS | [affected metrics] |

### 📍 STATE_SYNC (from /rules)
- Phase: [current phase]
- Context: [one line]
- Priority: [🔴/🟠/🟡/🔵]

### 🔍 ANALYSIS (from /analyze if run)
- [summary of findings]

### 🔒 CONSTRAINT CHECK
- [ ] KERNEL-TIER files NOT in scope
- [ ] No duplicated responsibilities
- [ ] Unified interfaces will be used
- [ ] No placeholders in output

### 📁 FILE BUDGET
- MAY modify: [list]
- MAY NOT modify: [list] + frontmatter.protected_files[]

### ✅ VALIDATION GATES (from frontmatter.validation_gates)
- [ ] py_compile
- [ ] lint (ruff)
- [ ] type-check (if applicable)
- [ ] tests (if specified)

⏸️ AWAITING: "CONFIRM SCOPE" or proceed if scope clear
```

---

## PROTECTED FILES

From frontmatter.protected_files[] — require explicit TODO plan entries:

- `core/kernels/kernel_loader.py`
- `core/agents/executor.py`
- `memory/substrate_service.py`
- `runtime/websocket_orchestrator.py`
- `docker-compose.yml`
- Any file matching `kernels/**/*.yaml`

---

## REPORT STRUCTURE

Path template: `reports/Report_GMP-{id}-{description}.md`

Required sections (from frontmatter.report.required_sections):
1. `# EXECUTION REPORT — <task>`
2. `## STATE_SYNC SUMMARY` (from /rules)
3. `## ANALYSIS SUMMARY` (from /analyze, if run)
4. `## TODO PLAN (LOCKED)`
5. `## TODO INDEX HASH`
6. `## PHASE CHECKLIST STATUS (0-6)`
7. `## FILES MODIFIED + LINE RANGES`
8. `## TODO → CHANGE MAP`
9. `## ENFORCEMENT + VALIDATION RESULTS`
10. `## PHASE 5 RECURSIVE VERIFICATION`
11. `## FINAL DEFINITION OF DONE`
12. `## FINAL DECLARATION`
13. `## YNP RECOMMENDATION` (from /ynp)

---

## FINAL DECLARATION

```
> All phases (0-6) complete. No assumptions. No drift. Scope locked.
> Report: /Users/ib-mac/Projects/L9/reports/Report_GMP-##-Description.md
> No further changes permitted.
```

---

## USAGE

### Standard Execution (v1.1)
```
/gmp "Add rate limiting to api/client.py"

Variable Bindings (auto-inferred):
  TASK_NAME: add_rate_limiting_api
  EXECUTION_SCOPE: Add rate limiting to api/client.py
  RISK_LEVEL: Medium

Flow:
1. Bind variables
2. /rules → STATE_SYNC
3. /analyze @api/client.py → clarify scope
4. Constraint check → verify KERNEL-TIER not touched
5. Phase 0-6 → execute
6. /ynp v8.0 → auto-execute if ≥90% confidence
```

### With GMP Action File (v1.1)
```
/gmp @docs/_GMP Execute + Audit/GMP-Action-Wire-Orchestrators.md

Variable Bindings (from file):
  TASK_NAME: wire_orchestrators
  EXECUTION_SCOPE: [from file]
  RISK_LEVEL: [from file]

Flow:
1. Load variable bindings from file
2. /rules → STATE_SYNC
3. Skip /analyze (scope in file)
4. Constraint check
5. Phase 0-6 → execute
6. /ynp v8.0 → next action
```

### With Explicit Variables
```
/gmp --task "governance_orphans_instantiation" \
     --scope "Instantiate all orphaned governance files" \
     --risk High \
     --spec docs/Governance\ Audit/Audit-Notes-Cursor.md

Flow:
1. Bind explicit variables
2. /rules → STATE_SYNC
3. Constraint check (KERNEL protection)
4. Phase 0-6 → multi-phase execution
5. /ynp v8.0 → next action
```

### From L-CTO
```
L-CTO generates GMP Action prompt → /gmp executes

Flow:
1. Load variable bindings from L-CTO
2. /rules → STATE_SYNC
3. Skip /analyze (L-CTO clarified)
4. Constraint check
5. Phase 0-6 → execute
6. /ynp v8.0 → auto-execute if ≥90%
```

### Audit Mode
```
/gmp --audit GMP-11

Runs post-execution audit:
- Verifies all TODOs implemented
- Verifies constraints not violated
- Verifies unified interfaces used
- Detects scope creep
- Produces audit report
```

### Chain Mode
```
/gmp --chain GMP-11 GMP-12 GMP-13

Executes in sequence with:
- Prerequisite validation
- Constraint inheritance
- YNP v8.0 auto-continue if ≥90% confidence
```

---

## 🛑 STOP CONDITIONS (v1.1)

The GMP engine MUST STOP and escalate if:

| Condition | Action |
|-----------|--------|
| TASK_NAME or EXECUTION_SCOPE missing/empty | STOP: Request clarification |
| REPORT_ROOT invalid (outside repo) | STOP: Request valid path |
| File cannot be uniquely identified | STOP: Request exact path |
| Variable contradicts KERNEL protection | STOP: Explain conflict |
| Variable contradicts Suite 6 invariants | STOP: Explain conflict |
| Implementing TODO requires KERNEL changes | STOP: Route to KERNEL GMP |

**When stopping, the report MUST:**
1. Name the conflicting variable(s) and file(s)
2. Explain why this cannot proceed under L9 invariants
3. Suggest whether a separate dedicated GMP is needed

---

## FAILURE & RECOVERY

### If GMP Fails:

```
GMP-[ID] EXECUTION FAILED
Phase: [0-6]
Checklist Item: [specific item]
Failure Reason: [specific]
Evidence: [code snippet or path]
Constraint Violated: [if applicable]
```

**Recovery:**
1. User reviews failure
2. User fixes issue OR modifies TODO plan
3. If constraint violation: Route to appropriate GMP tier
4. Re-execute from Phase 0

---

## INTEGRATION

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│ /rules  │────▶│/analyze │────▶│ /gmp    │────▶│  /ynp   │
│ (init)  │     │(clarify)│     │(execute)│     │ (next)  │
└─────────┘     └─────────┘     └─────────┘     └─────────┘
     ↑              ↑
     │              │
     │   Optional   │
     │   if scope   │
     │   unclear    │
     └──────────────┘
```

- **Starts with:** `/rules` (always) — per frontmatter.chain.starts_with
- **Uses:** `/analyze` (if needed) — per frontmatter.chain.uses_if_needed
- **Ends with:** `/ynp` (always) — per frontmatter.chain.ends_with
- **Produces:** Report at path from frontmatter.report.path_template
- **Updates:** `workflow_state.md` with results

---

## ANTI-PATTERNS

### Critical Violations (v1.1)
❌ **DON'T:** Modify KERNEL-TIER files without dedicated KERNEL GMP
❌ **DON'T:** Skip variable bindings (TASK_NAME, EXECUTION_SCOPE required)
❌ **DON'T:** Ignore constraint checks before execution
❌ **DON'T:** Leave placeholders or TODOs in output files
❌ **DON'T:** Rewrite entire files (use surgical edits)

### Execution Violations
❌ **DON'T:** Skip /rules at start
❌ **DON'T:** Proceed with ambiguous scope (use /analyze)
❌ **DON'T:** Fix issues not in TODO
❌ **DON'T:** Skip phases or combine them
❌ **DON'T:** Skip /ynp at end
❌ **DON'T:** Proceed when stop conditions triggered

### Best Practices
✅ **DO:** Bind variables before execution
✅ **DO:** Check constraints at INIT phase
✅ **DO:** Use tier-based TODO ordering
✅ **DO:** Always call /rules first
✅ **DO:** Use /analyze when user prompt unclear
✅ **DO:** Trace every change to a TODO ID
✅ **DO:** Use unified interfaces (governance_logger, GovernanceException)
✅ **DO:** Always call /ynp at end (v8.0 with auto-execute)
✅ **DO:** Generate complete report with variable bindings

---

## EXAMPLES

### Example 1: User Prompt (needs /analyze)
```
User: /gmp "fix the timeout issue in the API"

Variable Bindings:
  TASK_NAME: fix_api_timeout
  RISK_LEVEL: Medium

1. Bind variables (auto-inferred)
2. /rules → STATE_SYNC complete
3. Constraint check → ✅ KERNEL not touched
4. /analyze @api/ → Found timeout issue in client.py:45
5. Phase 0 → TODO PLAN locked
6. Phase 1-6 → Execute
7. /ynp v8.0 → Confidence: 92% → AUTO-EXECUTE: test deployment
```

### Example 2: Governance Orphan Instantiation (v1.1 Multi-Phase)
```
/gmp @governance-upgrade-prompt-1.md

Variable Bindings (from file):
  TASK_NAME: governance_orphans_full_instantiation
  EXECUTION_SCOPE: Instantiate all orphaned governance files
  RISK_LEVEL: High
  SPEC_PATH: docs/Governance Audit/Audit-Notes-Cursor.md

1. Load variable bindings
2. /rules → STATE_SYNC complete
3. Constraint check → ✅ KERNEL protected, unified interfaces required
4. Phase 0 → Multi-phase TODO PLAN:
   - Phase 1: Foundation (hash-verifier, hybrid_kernel, telemetry)
   - Phase 2: Governance Core (validator, tracker, checker)
   - Phase 3: Intelligence (context, learning, calibrator)
   - Phase 4: Agents & Memory (escalation, aggregator)
5. Phase 1-6 → Execute per phase
6. /ynp v8.0 → Confidence: 85% → Recommend: Run integration tests
```

### Example 3: Active File Normalization (v1.1)
```
/gmp @governance-upgrade-prompt-2.md

Variable Bindings:
  TASK_NAME: governance_active_files_normalization
  EXECUTION_SCOPE: Normalize all ACTIVE governance files to Suite 6 v9.0.0
  RISK_LEVEL: High

1. Load variable bindings
2. /rules → STATE_SYNC complete
3. Constraint check → ✅ Behavioral equivalence required
4. Phase 0 → TODO PLAN with file clusters:
   - Phase A1: Core Python Scripts
   - Phase A2: Startup & Learning Docs
   - Phase A3: Profiles & Commands
   - Phase A4: Feature & Rule Core
5. Phase 1-6 → Execute with regression safety
6. /ynp v8.0 → Recommend: Run existing tests
```

### Example 4: L-CTO Prompt (skip /analyze)
```
L-CTO provides:
  GMP-22: Add retry logic to fetch_data()
  File: api/client.py:45-60
  Change: Wrap in retry decorator
  RISK_LEVEL: Low

1. Bind variables from L-CTO
2. /rules → STATE_SYNC complete
3. Constraint check → ✅ Pass
4. Skip /analyze (scope clear)
5. Phase 0-6 → Execute
6. /ynp v8.0 → Confidence: 95% → AUTO-EXECUTE: next GMP
```
