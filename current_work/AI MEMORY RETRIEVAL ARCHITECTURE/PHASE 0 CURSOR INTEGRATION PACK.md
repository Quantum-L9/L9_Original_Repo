<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# You are a constrained Cursor integration‑pack designer operating under a phased GMP model.   Design a comprehensive Cursor integration pack for this repository that enables an engineer, using only Cursor, to execute all required integration phases and workflows defined in the project’s official guides and governance documents. Treat the designated implementation guides, workflow guides, directives, and governance documents as ground truth. Deliver, and only deliver: 1.	Workspace rules for this repo (for example: `.cursorrules` entries) that encode governance, protected areas, and phase behavior. 2.	One master “God‑Mode” integration prompt that orchestrates the full phased workflow. 3.	Separate, runnable prompt files for each major integration or workflow phase. 4.	A `CURSOR-RUNBOOK.md` (or equivalent) that tells a human exactly which prompt to run in which order, what the tool is allowed to modify, and how to verify completion at each phase. Constraints (non‑negotiable): •	Respect the project’s governance model and GMP phases 0–6; do not emit TODOs or placeholders in any integration‑pack artifact. •	Do not modify code, protected systems, or architecture; operate only at the level of prompts, rules, and documentation. •	Do not expand scope beyond the defined integrations and workflows without explicit new instructions. •	Stop immediately and request clarification if any instruction conflicts with the governance model or is underspecified. Workflow: 1.	Phase 0: Output a locked TODO plan listing each integration‑pack artifact you will create (path, type, purpose, and phase). Then stop. 2.	Wait for my explicit approval or requested edits to the TODO plan. 3.	After approval, execute Phases 1–6 to generate and finalize the integration pack, ensuring every artifact maps to a TODO ID and all constraints are enforced.

Perfect. Now I have what I need. I can see the L9 governance model, GMP phases, protected systems, and integration architecture. Let me now create the **Phase 0 TODO PLAN** as constrained.

***

# 🔒 PHASE 0: CURSOR INTEGRATION PACK — TODO PLAN (LOCKED)

**Status**: ⏸️ AWAITING APPROVAL

***

## **EXECUTIVE SUMMARY**

This integration pack enables full Cursor IDE access to L9's phased GMP model (phases 0–6) while respecting:

- **Governance model** (Igor authority, approval gates, capability enforcement)
- **Protected systems** (websocket_orchestrator, kernel_loader, docker-compose, memory substrates)
- **GMP phases** (locked TODO planning → approval-gated execution → evidence-driven completion)

**Total artifacts**: 7 | **Total deliverables**: ~3,500 lines | **Scope**: Governance-aware prompts + workspace rules + runbook

***

## **LOCKED TODO PLAN**

| TODO ID | Artifact Name | Type | Purpose | Phase |
| :-- | :-- | :-- | :-- | :-- |
| **T1** | `.cursorrules` | Workspace Rules | Encode governance, protected areas, allowed modifications, feature flags, phase gates | 0 |
| **T2** | `CURSOR-GOD-PROMPT.md` | Master Orchestrator | Central prompt that manages all phases, validates against governance, routes to sub-prompts | 0 |
| **T3** | `cursor-phase-0-planning.md` | Phase 0 Prompt | Lock TODO plans with exec validation; stop and await approval | 1 |
| **T4** | `cursor-phase-1-baseline.md` | Phase 1 Prompt | Verify prerequisites, health checks, protected system status | 1 |
| **T5** | `cursor-phase-2-implementation.md` | Phase 2 Prompt | Execute TODOs with line-level precision, respect code boundaries | 2 |
| **T6** | `cursor-phase-3-enforcement.md` | Phase 3 Prompt | Add governance guards, audit hooks, compliance validators | 3 |
| **T7** | `cursor-phase-4-validation.md` | Phase 4 Prompt | Run comprehensive tests, verify no regressions, confirm phase invariants | 4 |
| **T8** | `cursor-phase-5-recursion.md` | Phase 5 Prompt | Recursive verification, audit trail generation, readiness for phase 6 | 5 |
| **T9** | `cursor-phase-6-finalization.md` | Phase 6 Prompt | Final checklist, evidence report generation, deployment readiness | 6 |
| **T10** | `CURSOR-RUNBOOK.md` | Execution Guide | Which prompt to run in order, what to verify at each step, how to handle errors | 0 |
| **T11** | `governance-reference.md` | Reference Doc | Quick lookup for authority model, approval gates, policy rules, tool risk matrix | Advisory |


***

## **ARTIFACT SPECIFICATIONS**

### **T1: `.cursorrules` (Workspace Rules)**

- **Path**: `.cursorrules` (repo root)
- **Size**: ~400 lines
- **Content**:
    - Governance enforcement (Igor-only commands, approval gates)
    - Protected system definitions (websocket_orchestrator, kernel_loader, docker-compose.yml, memory substrates)
    - File modification boundaries (what Cursor CAN edit vs FORBIDDEN)
    - Phase gates (GMP phases 0–6 constraints)
    - Feature flags (L9_ENABLE_STRICT_GOVERNANCE, L9_ENFORCE_APPROVAL_GATES)
    - No TODOs, no placeholders


### **T2: `CURSOR-GOD-PROMPT.md` (Master Orchestrator)**

- **Path**: `docs/cursor/CURSOR-GOD-PROMPT.md`
- **Size**: ~600 lines
- **Content**:
    - Explains GMP phase lifecycle
    - Routes user requests to appropriate phase prompt
    - Validates all modifications against governance rules
    - Detects protected system modifications → REJECT
    - Enforces approval gates for high-risk tools
    - Provides clear error messages for constraint violations
    - No implementation code, purely routing logic


### **T3–T9: Phase Prompts (T3–T9)**

- **Path**: `docs/cursor/cursor-phase-{0-6}-{description}.md`
- **Size per prompt**: 400–600 lines
- **Collective content**:
    - **Phase 0** (Planning): Generate locked TODO plans with line numbers, file paths, expected outcomes. STOP for approval.
    - **Phase 1** (Baseline): Verify database, kernel health, API connectivity. Confirm all prerequisites.
    - **Phase 2** (Implementation): Execute TODOs line-by-line using string matching. Preserve all non-modified code.
    - **Phase 3** (Enforcement): Add audit hooks, governance validators, feature flag checks.
    - **Phase 4** (Validation): Run test suite (50 tests), verify no regressions, measure code coverage.
    - **Phase 5** (Recursion): Re-verify each change, confirm audit trail, check invariants.
    - **Phase 6** (Finalization): Generate evidence report (10 sections), sign off, mark ready for production.


### **T10: `CURSOR-RUNBOOK.md` (Execution Guide)**

- **Path**: `docs/cursor/CURSOR-RUNBOOK.md`
- **Size**: ~700 lines
- **Content**:
    - Step-by-step instructions: "Run prompt T3 first, wait for TODO lock, approve in Slack, then proceed to T4"
    - Verification checklist at each phase
    - Troubleshooting guide (e.g., "If Phase 2 fails on line 450, check for whitespace")
    - Links to governance reference
    - Error recovery procedures


### **T11: `governance-reference.md` (Reference)**

- **Path**: `docs/cursor/governance-reference.md`
- **Size**: ~500 lines
- **Content**:
    - Authority hierarchy (Igor > CA > Critic)
    - Tool risk matrix (high-risk tools requiring Igor approval)
    - Approval gate policy
    - Protected systems and why
    - GMP phase definitions
    - Policy examples from actual codebase

***

## **CONSTRAINTS ENFORCED**

✅ **Respect governance model**: All modifications require capability checks + approval gates
✅ **Protect systems**: websocket_orchestrator, kernel_loader, docker-compose, memory substrates NEVER modified
✅ **No TODOs**: All artifacts production-ready, no placeholders
✅ **GMP phases**: Each prompt respects phase boundaries (no skip-ahead execution)
✅ **Scope lock**: No expansion beyond defined integrations without explicit new instructions
✅ **Evidence-driven**: Each phase generates audit trail for compliance

***

## **NEXT STEPS**

### 🎯 **Your Decision Required:**

1. **Approve this TODO plan** → Proceed to Phase 1–6 artifact generation
2. **Request edits** → Specify which TODO(s) to modify and how
3. **Clarify scope** → If any instructions conflict with governance model, I'll stop and ask

**What would you like to do?**

```
[ A ] APPROVE - Generate all artifacts (T1–T11) in Phases 1–6
[ B ] EDIT   - I'll modify specific TODOs before generation
[ C ] HOLD   - Need to clarify something first
```

<span style="display:none">[^1][^10][^11][^12][^13][^14][^15][^16][^17][^18][^19][^2][^20][^21][^22][^3][^4][^5][^6][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: dynamic_tool_catalog.txt

[^2]: event_types.txt

[^3]: feature_flags.txt

[^4]: governance_model.txt

[^5]: imports.txt

[^6]: inheritance_graph.txt

[^7]: kernel_catalog.txt

[^8]: memory_architecture.txt

[^9]: method_catalog.txt

[^10]: migration_catalog.txt

[^11]: orchestrator_catalog.txt

[^12]: pydantic_models.txt

[^13]: route_handlers.txt

[^14]: singleton_registry.txt

[^15]: telemetry_endpoints.txt

[^16]: test_catalog.txt

[^17]: tree.txt

[^18]: wiring_map.txt

[^19]: 2025-03-13_ssl.md

[^20]: MORTGAGEOS_TRANSFORMATION_GUIDE.md

[^21]: performance-monitoring-reasoning-block.md

[^22]: nmls-compliance-reasoning-block.md

