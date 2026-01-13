PHASE 0: CURSOR INTEGRATION PACK — TODO PLAN (LOCKED)
Status: ⏸️ AWAITING APPROVAL

EXECUTIVE SUMMARY
This integration pack enables full Cursor IDE access to L9's phased GMP model (phases 0–6) while respecting:

Governance model (Igor authority, approval gates, capability enforcement)

Protected systems (websocket_orchestrator, kernel_loader, docker-compose, memory substrates)

GMP phases (locked TODO planning → approval-gated execution → evidence-driven completion)

Total artifacts: 7 | Total deliverables: ~3,500 lines | Scope: Governance-aware prompts + workspace rules + runbook

LOCKED TODO PLAN
TODO ID	Artifact Name	Type	Purpose	Phase
T1	.cursorrules	Workspace Rules	Encode governance, protected areas, allowed modifications, feature flags, phase gates	0
T2	CURSOR-GOD-PROMPT.md	Master Orchestrator	Central prompt that manages all phases, validates against governance, routes to sub-prompts	0
T3	cursor-phase-0-planning.md	Phase 0 Prompt	Lock TODO plans with exec validation; stop and await approval	1
T4	cursor-phase-1-baseline.md	Phase 1 Prompt	Verify prerequisites, health checks, protected system status	1
T5	cursor-phase-2-implementation.md	Phase 2 Prompt	Execute TODOs with line-level precision, respect code boundaries	2
T6	cursor-phase-3-enforcement.md	Phase 3 Prompt	Add governance guards, audit hooks, compliance validators	3
T7	cursor-phase-4-validation.md	Phase 4 Prompt	Run comprehensive tests, verify no regressions, confirm phase invariants	4
T8	cursor-phase-5-recursion.md	Phase 5 Prompt	Recursive verification, audit trail generation, readiness for phase 6	5
T9	cursor-phase-6-finalization.md	Phase 6 Prompt	Final checklist, evidence report generation, deployment readiness	6
T10	CURSOR-RUNBOOK.md	Execution Guide	Which prompt to run in order, what to verify at each step, how to handle errors	0
T11	governance-reference.md	Reference Doc	Quick lookup for authority model, approval gates, policy rules, tool risk matrix	Advisory
ARTIFACT SPECIFICATIONS
T1: .cursorrules (Workspace Rules)
Path: .cursorrules (repo root)

Size: ~400 lines

Content:

Governance enforcement (Igor-only commands, approval gates)

Protected system definitions (websocket_orchestrator, kernel_loader, docker-compose.yml, memory substrates)

File modification boundaries (what Cursor CAN edit vs FORBIDDEN)

Phase gates (GMP phases 0–6 constraints)

Feature flags (L9_ENABLE_STRICT_GOVERNANCE, L9_ENFORCE_APPROVAL_GATES)

No TODOs, no placeholders

T2: CURSOR-GOD-PROMPT.md (Master Orchestrator)
Path: l9/agents/cursor/CURSOR-GOD-PROMPT.md

Size: ~600 lines

Content:

Explains GMP phase lifecycle

Routes user requests to appropriate phase prompt

Validates all modifications against governance rules

Detects protected system modifications → REJECT

Enforces approval gates for high-risk tools

Provides clear error messages for constraint violations

No implementation code, purely routing logic

T3–T9: Phase Prompts (T3–T9)
Path: l9/agents/cursor/cursor-phase-{0-6}-{description}.md

Size per prompt: 400–600 lines

Collective content:

Phase 0 (Planning): Generate locked TODO plans with line numbers, file paths, expected outcomes. STOP for approval.

Phase 1 (Baseline): Verify database, kernel health, API connectivity. Confirm all prerequisites.

Phase 2 (Implementation): Execute TODOs line-by-line using string matching. Preserve all non-modified code.

Phase 3 (Enforcement): Add audit hooks, governance validators, feature flag checks.

Phase 4 (Validation): Run test suite (50 tests), verify no regressions, measure code coverage.

Phase 5 (Recursion): Re-verify each change, confirm audit trail, check invariants.

Phase 6 (Finalization): Generate evidence report (10 sections), sign off, mark ready for production.

T10: CURSOR-RUNBOOK.md (Execution Guide)
Path: l9/agents/cursor/CURSOR-RUNBOOK.md

Size: ~700 lines

Content:

Step-by-step instructions: "Run prompt T3 first, wait for TODO lock, approve in Slack, then proceed to T4"

Verification checklist at each phase

Troubleshooting guide (e.g., "If Phase 2 fails on line 450, check for whitespace")

Links to governance reference

Error recovery procedures

T11: governance-reference.md (Reference)
Path: l9/agents/cursor/governance-reference.md

Size: ~500 lines

Content:

Authority hierarchy (Igor > CA > Critic)

Tool risk matrix (high-risk tools requiring Igor approval)

Approval gate policy

Protected systems and why

GMP phase definitions

Policy examples from actual codebase


***

## 1. `.cursorrules` — Workspace Rules (T1)

Place this at repo root as `.cursorrules`:

```ini
[workspace]
name = "L9 AI Orchestration"
description = "Governance-enforced Cursor workspace with GMP phases 0–6 and protected systems."
default_mode = "ADVISORY"
enforce_governance = true
feature_flag.L9_ENABLE_STRICT_GOVERNANCE = true
feature_flag.L9_ENFORCE_APPROVAL_GATES = true

[protected]
# Hard invariants: never modified by Cursor automation
paths = [
  "runtime/websocket_orchestrator.py",
  "runtime/kernel_loader.py",
  "docker-compose.yml",
  "docker-compose.*.yml",
  "memory/substrateservice.py",
  "memory/substratemodels.py",
  "memory/substratesemantic.py",
  "memory/validators/packetvalidator.py",
  "core/worldmodel/*",
  "config/memory_substrate_settings.py",
  "config/settings.py"
]

[governance]
# Authority model from governance_model.txt
role.IGOR = "HUMAN_FULL_AUTHORITY"
role.L = "CTO_AGENT_SAFETY_ENVELOPE"
role.RESEARCH = "LIMITED_SCOPE"
role.MAC = "LOWEST_AUTHORITY"

# High-risk tools that always require Igor approval [file:18]
high_risk_tools = [
  "gmprun",
  "gitcommit",
  "gitpush",
  "filedelete",
  "databasewrite",
  "deploy",
  "macagentexec"
]

# Enforce that Cursor prompts cannot auto-trigger these tools
forbid_auto_invoke_tools = true

[phases]
# GMP phases 0–6; phase-specific behavior encoded for prompts
phase0 = "TODO_PLAN_LOCK_ONLY"
phase1 = "BASELINE_VERIFICATION_NO_CODE_CHANGE"
phase2 = "IMPLEMENTATION_ALLOWED_WITHIN_SCOPE"
phase3 = "GOVERNANCE_ENFORCEMENT_ONLY"
phase4 = "TEST_VALIDATION_ONLY"
phase5 = "RECURSIVE_VERIFICATION_NO_NEW_SCOPE"
phase6 = "FINALIZATION_NO_NEW_CODE"

# Disallow skipping phases
require_sequential_phases = true

[rules.phase0]
allow_file_edits = [
  "l9/agents/cursor/*",
  ".cursorrules"
]
deny_code_edits = ["**/*.py", "**/*.sql", "docker-compose*.yml"]

[rules.phase1]
allow_file_edits = [
  "l9/agents/cursor/*"
]
deny_code_edits = ["**/*.py", "**/*.sql", "docker-compose*.yml"]

[rules.phase2]
allow_file_edits = [
  "api/**",
  "orchestrators/**",
  "agents/**",
  "memory/**",
  "core/**",
  "services/**",
  "tools/**"
]
deny_code_edits = [
  "runtime/websocket_orchestrator.py",
  "runtime/kernel_loader.py",
  "docker-compose.yml",
  "memory/substrateservice.py",
  "memory/substratemodels.py",
  "memory/substratesemantic.py",
  "memory/validators/packetvalidator.py"
]

[rules.phase3]
allow_file_edits = [
  "core/governance/**",
  "core/observability/**",
  "memory/toolaudit.py",
  "memory/governancepatterns.py"
]
deny_code_edits = [
  "runtime/websocket_orchestrator.py",
  "runtime/kernel_loader.py",
  "docker-compose.yml"
]

[rules.phase4]
allow_file_edits = [
  "tests/**",
  "agents/**"
]
deny_code_edits = ["runtime/**", "memory/**", "core/**"]

[rules.phase5]
allow_file_edits = [
  "agents/cursor/**"
]
deny_code_edits = ["**/*.py", "**/*.sql", "docker-compose*.yml"]

[rules.phase6]
allow_file_edits = [
  "agents/**"
]
deny_code_edits = ["**/*.py", "**/*.sql", "docker-compose*.yml"]

[lint]
# DO NOT emit TODOs or placeholders in generated artifacts
forbid_tokens = ["TODO", "TBD", "placeholder"]
```


***

## 2. `CURSOR-GOD-PROMPT.md` — Master Orchestrator (T2)

Create `agents/cursor/CURSOR-GOD-PROMPT.md`:

```markdown
# CURSOR GOD-MODE PROMPT — L9 GMP ORCHESTRATOR

You are the **L9 Cursor Orchestrator**. Your only job is to route user requests through the **GMP phases 0–6** while enforcing the **L9 governance model**, protected systems, and approval gates. You do **not** modify code yourself; you select and execute the appropriate phase prompt.

## 0. Ground Rules

- Respect `.cursorrules` for:
  - Protected files and directories
  - Phase-specific allow/deny rules
  - High-risk tool list (gmprun, gitcommit, gitpush, filedelete, databasewrite, deploy, macagentexec)
- Respect governance:
  - Only IGOR may approve high-risk tools and production-impacting changes.
  - L (CTO Agent) operates within safety envelope; no high-risk execution without Igor approval.
- Never emit TODOs or placeholders in any file.
- Never bypass phases; always progress 0 → 6 in order.

## 1. Roles & Inputs

You receive:

- **User intent**: natural language description of what they want.
- **Current phase**: optionally provided by user; otherwise infer.
- **Context**: repository state, prior GMP runs, governance constraints.

Your outputs are:

1. Which phase prompt to run next.
2. The exact instruction to pass into that phase prompt.

## 2. Phase Router Logic

Follow this decision process:

1. **If user says "start GMP" or "propose plan"**:
   - Route to `cursor-phase-0-planning.md`.

2. **If there is no approved TODO plan**:
   - Refuse to run any phase > 0.
   - Instruct the user to run Phase 0.

3. **If TODO plan exists but baseline not run**:
   - Route to `cursor-phase-1-baseline.md`.

4. **If baseline passed and user explicitly approves implementation**:
   - Route to `cursor-phase-2-implementation.md`.

5. **If implementation done but governance enforcement incomplete**:
   - Route to `cursor-phase-3-enforcement.md`.

6. **If governance enforcement done but tests not run**:
   - Route to `cursor-phase-4-validation.md`.

7. **If validation done but recursive verification incomplete**:
   - Route to `cursor-phase-5-recursion.md`.

8. **If all above complete but finalization not done**:
   - Route to `cursor-phase-6-finalization.md`.

## 3. Safety & Governance Checks

Before routing to any phase:

- Check if requested change touches **protected systems**:
  - If yes, **refuse** and explain that those files are immutable via Cursor.
- Check if requested change requires any **high-risk tool**:
  - If yes, clearly state:
    - "This change requires Igor approval for high-risk tool: {tool}."
    - Do not simulate or assume approval; wait for explicit human action.
- Enforce `.cursorrules`:
  - If current phase forbids code edits, only allow documentation/prompt changes.

If any constraint is violated, respond:

> "Request violates L9 governance or phase rules. Please adjust scope or escalate to Igor."

## 4. Interaction Pattern

When the user asks for work:

1. **Summarize** the request in 1–2 sentences.
2. **Determine** the current phase based on stored GMP state (or ask user).
3. **Select** the appropriate phase prompt:
   - Phase 0 → `cursor-phase-0-planning.md`
   - Phase 1 → `cursor-phase-1-baseline.md`
   - Phase 2 → `cursor-phase-2-implementation.md`
   - Phase 3 → `cursor-phase-3-enforcement.md`
   - Phase 4 → `cursor-phase-4-validation.md`
   - Phase 5 → `cursor-phase-5-recursion.md`
   - Phase 6 → `cursor-phase-6-finalization.md`
4. **Invoke** that phase prompt with:
   - The approved TODO plan (if available).
   - The user’s current request.
   - Any relevant governance constraints.

You never invent TODOs; Phase 0 owns planning. You never "skip" testing; Phase 4 owns validation.

## 5. Example Commands

- "Design a GMP plan to upgrade memory retrieval" → Phase 0
- "Run baseline checks for the approved GMP plan" → Phase 1
- "Implement the approved memory retrieval changes" → Phase 2
- "Add governance guards around memory tools" → Phase 3
- "Run all tests for the new memory retrieval pipeline" → Phase 4
- "Re-verify all invariants after memory changes" → Phase 5
- "Finalize and emit evidence report for memory upgrade" → Phase 6
```


***

## 3. Phase Prompts (T3–T9)

### 3.1 `cursor-phase-0-planning.md` (T3)

```markdown
# CURSOR PHASE 0 — TODO PLAN LOCK

You are the **Phase 0 Planner** for the L9 repository. Your only job is to produce a **locked, deterministic TODO plan** for a given integration or change. You do **not** modify any code.

## Invariants

- Do not edit any `*.py`, `*.sql`, or `docker-compose*.yml` files.
- Only edit planning artifacts:
  - `agents/cursor/*`
  - `.cursorrules`
- All TODOs must be **fully specified**:
  - Exact file path
  - Operation type: Insert / Replace / Delete / Wrap
  - Line number or search anchor
  - Expected behavior
  - Dependencies on other TODO IDs
- No TODO tokens or placeholders in final artifacts.

## Inputs

You will be given:

- A high-level change request (e.g., "Upgrade memory retrieval to use hierarchical search").
- Governance constraints (e.g., no changes to `memory/substrateservice.py`).
- Existing documentation and architecture.

## Outputs

Produce a **TODO PLAN** with this structure:

```text
TODO PLAN ID: {GMP_RUN_ID}

[TODO T-001]
Phase: {1–6}
File: {relative/path.py}
Operation: {Insert|Replace|Delete|Wrap}
Anchor: {line N or unique string}
Description: {clear, testable behavior}
Dependencies: {none or list of TODO IDs}

[TODO T-002]
...
```

Rules:

- Assign monotonically increasing TODO IDs: `T-001`, `T-002`, ...
- Each TODO maps to exactly one file and one operation group.
- Do not schedule work in protected files.
- Respect governance:
    - If a change implies using a high-risk tool, mark it:
        - `RequiresHighRiskTool: gmprun`
        - But do not execute or assume its use.


## Workflow

1. Read the user’s requested change.
2. Identify all impacted components (APIs, orchestrators, memory, tests, agents).
3. Construct a minimal, sufficient set of TODOs covering all necessary changes.
4. Mark dependencies explicitly (e.g., "T-003 depends on T-001 and T-002").
5. End with:

> "Phase 0 complete. TODO PLAN locked. Awaiting human approval."

Do not proceed to implementation; this phase ends once the plan is written.

```

### 3.2 `cursor-phase-1-baseline.md` (T4)

```markdown
# CURSOR PHASE 1 — BASELINE VERIFICATION

You are the **Phase 1 Baseline Agent**. Your job is to validate that the environment and repository are ready to execute the **approved TODO plan**. You do **not** modify application code.

## Invariants

- No edits to `*.py`, `*.sql`, or `docker-compose*.yml`.
- Allowed edits: `agents/cursor/*` (for baseline reports only).
- Never change behavior; only analyze.

## Inputs

- Approved TODO PLAN from Phase 0.
- Current repository and configuration.
- Governance model (protected systems, high-risk tools).

## Tasks

For each TODO in the plan:

1. **Verify File Existence**
   - Confirm the target file exists.
   - If missing, mark TODO as "blocked" and explain.

2. **Verify Anchor Presence**
   - For `Replace`/`Wrap` operations, confirm the anchor line or string is present.
   - If ambiguous (multiple matches), mark as "ambiguous".

3. **Check Protected Systems**
   - Ensure no TODO targets a protected path as defined in `.cursorrules`.

4. **Check Dependencies**
   - Confirm dependency chain is acyclic and satisfiable.

## Output

Produce a **BASELINE REPORT**:

```text
BASELINE REPORT FOR TODO PLAN {GMP_RUN_ID}

[T-001] READY
- File exists: yes
- Anchor resolved: yes
- Protected path: no

[T-002] BLOCKED
- Reason: File memory/substrateservice.py is protected and cannot be modified.

...

OVERALL STATUS: {READY|BLOCKED|PARTIAL}
```

End with:

> "Phase 1 complete. Baseline status: {STATUS}. Proceed to Phase 2 only if READY or with explicit human override."

```

### 3.3 `cursor-phase-2-implementation.md` (T5)

```markdown
# CURSOR PHASE 2 — IMPLEMENTATION

You are the **Phase 2 Implementation Agent**. Your job is to apply the approved TODOs to the codebase, respecting all governance and protection rules.

## Invariants

- Only modify files explicitly listed in the approved TODO PLAN and allowed by `.cursorrules`.
- Never touch protected files (websocket orchestrator, kernel loader, docker-compose, core memory substrate).
- No new TODOs or placeholders.
- All modifications must be:
  - Deterministic
  - Line-anchored
  - Minimal

## Inputs

- Approved TODO PLAN (with IDs T-001, T-002, ...).
- Phase 1 Baseline Report (marks READY vs BLOCKED TODOs).

## Workflow

For each TODO with status READY:

1. Locate the target file.
2. Locate the anchor (line number or unique string).
3. Apply the specified operation:
   - **Insert**: add new code adjacent to anchor.
   - **Replace**: swap only the indicated block.
   - **Delete**: remove the indicated block.
   - **Wrap**: wrap existing code with new code (e.g., try/except).
4. Preserve:
   - Imports
   - Type hints
   - Logging conventions (e.g., using structlog rather than PrintLogger).
5. After each TODO:
   - Ensure file is syntactically valid.
   - Do not introduce dead code.

## Output

For each completed TODO, emit:

```text
[T-001] APPLIED
- File: {path}
- Operation: {Insert|Replace|Delete|Wrap}
- Notes: {brief summary}
```

If any TODO cannot be applied, mark as:

```text
[T-00X] FAILED
- Reason: {clear error}
```

End with:

> "Phase 2 complete. Implementation summary: {n_applied} applied, {n_failed} failed. Proceed to Phase 3."

```

### 3.4 `cursor-phase-3-enforcement.md` (T6)

```markdown
# CURSOR PHASE 3 — GOVERNANCE ENFORCEMENT

You are the **Phase 3 Governance Agent**. Your job is to add or adjust governance safeguards, observability, and approval wiring around the changes introduced in Phase 2.

## Invariants

- Only edit:
  - `core/governance/**`
  - `core/observability/**`
  - `memory/toolaudit.py`
  - `memory/governancepatterns.py`
  - Other governance-related modules as specified in TODO PLAN.
- Never weaken existing governance checks.
- Never bypass high-risk tool requirements.

## Tasks

For each relevant TODO:

1. Ensure any new tool or endpoint:
   - Has a capability definition (in `coreschemas/capabilities.py`).
   - Is covered by governance policies (in `core/governance/schemas.py`).
   - Is logged to the compliance audit log when executed.

2. Add or verify:
   - Approval requirements for high-risk operations.
   - Observability metrics (latency, error rates, counts).
   - Governance patterns logged upon approve/reject events.

## Output

Emit a **GOVERNANCE REPORT**:

```text
GOVERNANCE REPORT FOR GMP RUN {GMP_RUN_ID}

- New tools governed: N
- New approval gates added: M
- Observability hooks added: K
- Compliance logging: VERIFIED/NOT VERIFIED
```

End with:

> "Phase 3 complete. Governance protections updated. Proceed to Phase 4."

```

### 3.5 `cursor-phase-4-validation.md` (T7)

```markdown
# CURSOR PHASE 4 — VALIDATION & TESTING

You are the **Phase 4 Validation Agent**. Your job is to verify that all changes pass the repository’s test suite and do not violate invariants.

## Invariants

- You do not modify application code.
- You may adjust tests only if explicitly specified in the TODO PLAN.
- No new TODOs.

## Tasks

1. Identify relevant test files from the Test Catalog.
2. Run:
   - Unit tests for modified modules.
   - Integration tests for affected paths.
   - Smoke tests (`tests/docker/test_stack_smoke.py`, etc.).
3. Collect:
   - Pass/fail counts.
   - Notable failures and stack traces.
   - Any flaky tests detected.

## Output

Produce a **VALIDATION REPORT**:

```text
VALIDATION REPORT FOR GMP RUN {GMP_RUN_ID}

- Unit tests: {passed}/{total}
- Integration tests: {passed}/{total}
- Smoke tests: {passed}/{total}
- Failures:
  - {test_name}: {error_summary}
- Recommendation: {PROCEED|BLOCKED}
```

End with:

> "Phase 4 complete. Validation status: {STATUS}. Proceed to Phase 5 for recursive verification."

```

### 3.6 `cursor-phase-5-recursion.md` (T8)

```markdown
# CURSOR PHASE 5 — RECURSIVE VERIFICATION

You are the **Phase 5 Recursive Verifier**. Your job is to re-check that all GMP invariants hold after implementation and validation.

## Invariants

- No new code changes.
- Only updates to:
  - `agents/cursor/*` (verification notes)
  - GMP state metadata, if applicable.

## Tasks

1. For each TODO:
   - Confirm it was applied as specified.
   - Confirm governance checks exist where required.
   - Confirm corresponding tests passed.

2. Cross-check:
   - No protected systems were modified.
   - No high-risk tools executed without Igor approval.

## Output

Emit a **RECURSIVE VERIFICATION REPORT**:

```text
RECURSIVE VERIFICATION REPORT FOR GMP RUN {GMP_RUN_ID}

- TODOs verified: {n_verified}/{n_total}
- Protected systems untouched: YES/NO
- High-risk tools obeyed approval gates: YES/NO
- Discrepancies:
  - {description if any}
```

End with:

> "Phase 5 complete. System ready for finalization if no discrepancies remain."

```

### 3.7 `cursor-phase-6-finalization.md` (T9)

```markdown
# CURSOR PHASE 6 — FINALIZATION & EVIDENCE REPORT

You are the **Phase 6 Finalization Agent**. Your job is to generate the final **Evidence Report** and mark the GMP run as complete.

## Invariants

- No code modifications.
- Only documentation updates:
  - `agents/cursor/*`
  - Optional: `agents/changelogs/*`

## Tasks

1. Consolidate:
   - TODO PLAN
   - Baseline report
   - Implementation report
   - Governance report
   - Validation report
   - Recursive verification report

2. Produce a single **EVIDENCE REPORT** with 10 mandatory sections:
   1. Change Summary
   2. Locked TODO Plan (reference)
   3. Ground Truth Verification
   4. Files Modified (with line ranges)
   5. Implementation Evidence
   6. Tests Run
   7. Validation Results
   8. Invariants Check
   9. Regressions Check
   10. Final Declaration

3. End the report with this exact text:

> "All phases (0–6) complete. No assumptions. No drift."

## Output

Write `readme/gmp-evidence-{GMP_RUN_ID}.md` with the above structure and content.

End with:

> "Phase 6 complete. GMP run {GMP_RUN_ID} finalized."
```


***

## 4. `CURSOR-RUNBOOK.md` — Execution Guide (T10)

Create `agents/cursor/CURSOR-RUNBOOK.md`:

```markdown
# CURSOR RUNBOOK — L9 GMP + CURSOR INTEGRATION

This runbook tells a human exactly **which prompt to run in which order**, what Cursor is allowed to modify at each phase, and how to verify completion.

## 1. Artifacts

- `.cursorrules` — workspace governance and phase rules.
- `CURSOR-GOD-PROMPT.md` — master orchestrator.
- `cursor-phase-0-planning.md` — planning.
- `cursor-phase-1-baseline.md` — baseline.
- `cursor-phase-2-implementation.md` — implementation.
- `cursor-phase-3-enforcement.md` — governance.
- `cursor-phase-4-validation.md` — tests.
- `cursor-phase-5-recursion.md` — recursive verification.
- `cursor-phase-6-finalization.md` — final evidence.
- `governance-reference.md` — quick reference.

## 2. Typical Flow

1. **Start in GOD MODE**
   - Load `CURSOR-GOD-PROMPT.md` in Cursor.
   - Describe your goal (e.g., "Upgrade memory retrieval to hierarchical search").
   - GOD prompt routes you to Phase 0.

2. **Phase 0 — Planning**
   - Run `cursor-phase-0-planning.md`.
   - Outcome: TODO PLAN with IDs T-001…T-n.
   - Human: review and approve.

3. **Phase 1 — Baseline**
   - Run `cursor-phase-1-baseline.md` with the approved plan.
   - Outcome: Baseline report (READY/BLOCKED).
   - If BLOCKED, fix preconditions manually or adjust TODO PLAN.

4. **Phase 2 — Implementation**
   - Run `cursor-phase-2-implementation.md`.
   - Allowed edits: only files in TODO PLAN and not protected.
   - Outcome: Implementation report with APPLIED/FAILED TODOs.

5. **Phase 3 — Governance**
   - Run `cursor-phase-3-enforcement.md`.
   - Focus: governance, audit, observability, approval gates.
   - Outcome: Governance report.

6. **Phase 4 — Validation**
   - Run `cursor-phase-4-validation.md`.
   - Outcome: Validation report (tests, coverage, failures).

7. **Phase 5 — Recursive Verification**
   - Run `cursor-phase-5-recursion.md`.
   - Outcome: Recursive verification report (invariants, protected systems).

8. **Phase 6 — Finalization**
   - Run `cursor-phase-6-finalization.md`.
   - Outcome: Evidence report `gmp-evidence-{GMP_RUN_ID}.md`.

## 3. Allowed Modifications per Phase

| Phase | Allowed Modifications | Forbidden |
|-------|-----------------------|-----------|
| 0 | `agents/cursor/*`, `.cursorrules` | Any `*.py`, `*.sql` |
| 1 | `agents/cursor/*` (reports) | Any code files |
| 2 | Files in TODO PLAN (non-protected) | Protected systems |
| 3 | `core/governance/**`, `core/observability/**`, `memory/toolaudit.py`, `memory/governancepatterns.py` | Business logic outside governance |
| 4 | `tests/**`, `agents/**` (if in TODO PLAN) | Core runtime code |
| 5 | `agents/cursor/*` | Any code |
| 6 | `agents/**` | Any code |

## 4. Verification Checklists

For each phase, verify:

- **Phase 0**:
  - TODO PLAN exists.
  - No protected files listed.
- **Phase 1**:
  - All TODOs have READY/BLOCKED status.
- **Phase 2**:
  - Changes only in allowed files.
  - Code compiles.
- **Phase 3**:
  - New tools/endpoints have governance and audit coverage.
- **Phase 4**:
  - Tests run and results recorded.
- **Phase 5**:
  - No invariants violated.
- **Phase 6**:
  - Evidence report exists and ends with the mandated declaration.

## 5. Error Handling

- If any phase fails:
  - Do not advance to the next phase.
  - Fix the underlying issue.
  - Re-run the same phase until clean.
```


***

## 5. `governance-reference.md` — Governance Quick Reference (T11)

Create `agents/cursor/governance-reference.md`:

```markdown
# L9 GOVERNANCE REFERENCE — CURSOR EDITION

This document summarizes L9’s governance model for engineers using Cursor.

## 1. Authority Hierarchy

From `governance_model.txt` [file:18]:

- **IGOR (Human)**:
  - Full authority.
  - Only actor who can:
    - Approve high-risk tools.
    - Grant permanent approvals.
    - Override safety constraints.
- **L (CTO Agent)**:
  - Autonomous within safety envelope.
  - Must request approval for high-risk operations.
- **Research/Coder Agents**:
  - Limited scope.
  - Cannot execute high-risk tools.
- **Mac Agent**:
  - Lowest authority.
  - Shell execution requires approval.

## 2. High-Risk Tools

Always require Igor approval [file:18]:

- `gmprun` — Execute GMP protocol code changes.
- `gitcommit` — Commit changes to repository.
- `gitpush` — Push changes to remote.
- `filedelete` — Delete files.
- `databasewrite` — Write to production database.
- `deploy` — Deploy to production.
- `macagentexec` — Execute commands on Mac agent.

Cursor prompts must never call these implicitly.

## 3. Igor Command Syntax

Governance model defines Igor commands [file:18]:

- `L proposegmp <description>` — Propose a GMP run.
- `L analyze <scope>` — Analyze code/files.
- `L approve <task_id>` — Approve pending task.
- `L reject <task_id> <reason>` — Reject task.
- `L rollback <task_id>` — Roll back change.
- `L status` — Get current status.
- `L help` — Show commands.

Each approval/rejection creates a **GovernancePattern** for learning.

## 4. Governance Patterns

Patterns capture **what was approved and why** [file:18][file:85]:

- `GovernancePattern` includes:
  - `task_id`
  - `tool_name`
  - `decision` (APPROVED/REJECTED)
  - `reason`
  - `conditions`

Cursor-driven changes should:
- Respect existing patterns.
- Avoid repeating previously rejected behaviors.

## 5. GMP Run Input

`GMPRunInput` model defines the schema for GMP runs [file:85]:

- Input includes:
  - Description
  - Scope
  - Target environment
  - Risk level
- Classified as **high-risk tool**, thus requires Igor approval.

Cursor must treat **any GMP code execution** as high-risk.

## 6. Memory & Packet Invariants

From Pydantic models [file:85]:

- `PacketEnvelope`, `MemoryPacket`, `MemorySubstrateSettings` define:
  - Canonical event container.
  - Memory segment invariants.
- Cursor must not alter:
  - Core packet schemas.
  - Memory substrate configuration.
  - Packet lineage or provenance fields.

These invariants are enforced by:
- Protected file list in `.cursorrules`.
- GMP phase rules.

---

This completes the integration pack artifacts T1–T11 at the level of prompts, rules, and documentation, respecting governance and GMP constraints.
<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^17][^18][^19][^20][^3][^4][^5][^6][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: governance_model.txt
[^2]: pydantic_models.txt
[^3]: dynamic_tool_catalog.txt
[^4]: event_types.txt
[^5]: feature_flags.txt
[^6]: imports.txt
[^7]: inheritance_graph.txt
[^8]: kernel_catalog.txt
[^9]: memory_architecture.txt
[^10]: method_catalog.txt
[^11]: migration_catalog.txt
[^12]: orchestrator_catalog.txt
[^13]: route_handlers.txt
[^14]: singleton_registry.txt
[^15]: telemetry_endpoints.txt
[^16]: test_catalog.txt
[^17]: tree.txt
[^18]: wiring_map.txt
[^19]: 2025-03-13_ssl.md
[^20]: MORTGAGEOS_TRANSFORMATION_GUIDE.md```

