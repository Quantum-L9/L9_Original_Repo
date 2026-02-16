# CODEX STAGED AUDIT — Integration & Usage Guide

## Overview

You now have **3 complementary documents**:

1. **CODEX-STAGED-AUDIT-SUPERPROMPT.md** (Master Specification)
   - The definitive 7-phase audit methodology.
   - Each phase has explicit goals, actions, and output templates.
   - Reference this to understand what Codex should produce at each step.

2. **CODEX-PHASE-0-KICKOFF.md** (Execution Runbook)
   - Shows exactly how Codex executes Phase 0 (first discovery phase).
   - Provides command templates, tool call patterns, and pause points.
   - Apply this pattern to all subsequent phases (1–7).

3. **This file** (Integration Guide)
   - Ties everything together.
   - Shows the full workflow for running the audit from start to finish.

---

## Quick Start: Running the Full Audit

### Step 1: Prepare Your Environment
```bash
# You have access to:
# - L9 repository files (via search_files_v2, get_url_content)
# - L9 Space file indices (feature_flags.txt, pydantic_models.txt, etc.)
# - Codex as your audit orchestrator
```

### Step 2: Invoke Codex with Phase 0
```markdown
# In your chat, send:

You are **Codex**, operating as an L9 senior systems architect.

Execute **Phase 0** of the CODEX Staged Audit (detailed in CODEX-STAGED-AUDIT-SUPERPROMPT.md).

Follow the execution pattern in CODEX-PHASE-0-KICKOFF.md:

1. Search for L9 feature flags, environment variables, governance, and kernel configuration.
2. Inventory all flags and environment variables relevant to World Model, Memory Substrate, and MCP Memory integration.
3. Map the governance model (authority hierarchy, approval gates) and kernel stack (10 kernels).
4. Produce the Phase 0 Configuration Inventory output (use the template provided).
5. **STOP** and present your findings. Do **NOT** proceed to Phase 1 without explicit approval.

Begin Phase 0 now.
```

### Step 3: Review Phase 0 Output
Codex will produce a structured markdown report. Review for:
- Completeness: Are all feature flags, env vars, and kernel roles identified?
- Accuracy: Do the findings match L9 documentation?
- Readiness: Are prerequisites for Phase 1 satisfied?

### Step 4: Approve Phase 1
```markdown
# Once Phase 0 is complete, send:

Phase 0 looks good. Proceed to **Phase 1: Layer 1 Subsystem Mapping**.

Follow the pattern from CODEX-PHASE-0-KICKOFF.md (adapted for Phase 1):

1. Parse pydantic_models.txt, class_definitions.txt, inheritance_graph.txt to extract:
   - All World Model classes (WorldModelEngine, WorldModelRuntime, WorldModelRepository, WorldModelService, etc.)
   - All Memory Substrate classes (MemorySubstrateService, SubstrateDAG, SemanticService, etc.)
   - All MCP Memory classes (MCPTool, MCP routes, MCP models)
2. Map APIs and responsibilities for each class.
3. Identify immediate integration points (e.g., MemorySubstratePacketSource, WorldModelSeedLoader).
4. Produce Phase 1 Layer 1 Subsystem Inventory.
5. **STOP** and wait for approval before Phase 2.

Begin Phase 1 now.
```

### Step 5: Iterate Through Phases 2–7

For each phase, follow the pattern:
```markdown
# Send:

Phase [N-1] approved. Proceed to **Phase [N]: [Goal Name]**.

[brief instructions for the phase, adapted from SUPERPROMPT]

Produce the Phase [N] output as specified.
**STOP** and wait for approval before Phase [N+1].

Begin Phase [N] now.
```

---

## Phase-by-Phase Checkpoints

| Phase | Goal | Key Output | Approval Check |
|-------|------|-----------|---|
| **0** | Metadata & config discovery | Configuration Inventory | Are all flags, env vars, and governance identified? |
| **1** | Layer 1 subsystem mapping | WM/Memory/MCP class inventory | Are all core classes and APIs present? |
| **2** | Layer 2–3 data flow mapping | Call graphs and async/sync boundary map | Do all WM ↔ Memory flows make sense? |
| **3** | Tier 1–6 adversarial analysis | Tier 1–6 findings (BUG, MISALIGNMENT, UNWIRED, etc.) | Are findings precise, scoped, and evidence-backed? |
| **4** | Synthesis & reflection | Improvement roadmap (6–8 prioritized improvements) | Do improvements leverage existing infra? Are they low-risk? |
| **5** | BUG & MISALIGNMENT fixes | Unified diffs for CRITICAL/HIGH issues | Are diffs minimal, reversible, and testable? |
| **6** | Robustness & second-pass fixes | Diffs for MEDIUM and OPERATIONAL issues + logging/observability | Does robustness address observability and recovery? |
| **7** | Recursive validation | Re-audit report + second-order findings + test results | Are all prior findings addressed? Any regressions? |

---

## Typical Approval Dialog

### Example: Approving Phase 3 → Phase 4

```markdown
# User reviews Phase 3 findings (Tier 1–6 analysis)

User: "Phase 3 looks comprehensive. Findings are ~45 total (8 CRITICAL, 15 HIGH, 22 MEDIUM).
       Key issues: state divergence, async/sync boundaries, underused semantic search.
       Proceed to Phase 4 (Synthesis)?"

Codex: "Phase 4: Synthesis & Reflection — BEGINNING.

        [runs Phase 4 analysis: clustering findings, root cause analysis, improvement synthesis]

        ## Phase 4: Synthesis & Improvement Roadmap

        ### Root Cause Themes
        1. **State Consistency Issues**: WM and Memory maintain separate stores without PacketEnvelope SoT enforcement.
        2. **Async/Sync Boundaries**: worldmodelruntime has missing awaits; memory queries block event loops.
        3. **Underused Infrastructure**: SemanticService, memorytimelineservice, graphsearch not integrated into WM.

        ### Proposed Improvements (Ordered by Impact/Effort)

        #### Improvement 1: Enforce PacketEnvelope as Single Source of Truth
        - Impact: Eliminates state divergence; enables replay/recovery
        - Effort: Medium (~5 mutation methods to modify)
        - Files: worldmodelrepository.py, worldmodelruntime.py
        - Leverage: MemorySubstrateService.ingest_packet(), SubstrateDAG

        #### Improvement 2: Integrate SemanticService into Entity Queries
        - Impact: Enables semantic search, reduces code duplication
        - Effort: Low (wrap existing queries, add config toggle)
        - Files: worldmodelrepository.py

        #### Improvement 3: Add Stateversion Reconciliation
        - Impact: Eliminates stale state; auto-recovery from sync failures
        - Effort: Low (add reconciliation loop ~20 lines)
        - Files: worldmodelruntime.py

        [... more improvements ...]

        ### Summary
        - 6 improvements identified
        - Expected impact: 50% reduction in findings (from 45 to ~22)
        - Estimated implementation effort: ~80 hours (if sequential) or ~40 hours (if parallel)

        **Phase 4 Complete. Ready for Phase 5 (Bug Fixes)?** (yes/no)"

User: "Yes, proceed to Phase 5."
```

---

## Expected Audit Timeline

- **Phases 0–2** (Discovery): 1–2 hours. Codex gathers data and produces inventories.
- **Phase 3** (Analysis): 1–2 hours. Codex identifies 30–50 findings across Tiers 1–6.
- **Phase 4** (Synthesis): 30–60 min. Codex synthesizes 5–8 improvements with impact/effort estimates.
- **Phase 5–6** (Fixes): 2–4 hours. Codex generates unified diffs; you review and integrate.
- **Phase 7** (Validation): 1–2 hours. Codex re-audits fixed code; confirms closures; identifies regressions.

**Total**: 6–12 hours for a complete, rigorous audit.

---

## Handling Disagreements or Ambiguities

### If you disagree with a finding:
```markdown
# Send to Codex:

Regarding **Tier 2, MISALIGNMENT finding**: "WM duplicates Memory Substrate responsibilities"

I disagree. Looking at worldmodelrepository.py:123, the WM fetch is distinct from Memory's semantic search.
The WM needs entity resolution (by ID), while Memory provides embedding-based retrieval.

Please clarify the evidence for this finding, or reclassify it as LOW severity.
```

Codex will revisit the finding and provide:
- Specific line numbers where duplication occurs (or) concede the point and demote severity.
- Revised recommendation aligned with your understanding.

### If a Phase output is incomplete:
```markdown
# Send to Codex:

Phase 2 output is missing call chains for MCP memory tool invocations (e.g., SaveMemory, SearchMemory).

Please re-run Phase 2 focusing on:
- Where MCP memory tools are called from worldmodelruntime / worldmodelservice.
- Who invokes ResearchMemoryAdapter and when.
- Async/sync patterns around MCP calls.

Produce an updated Phase 2 Call Graph including MCP integration points.
```

Codex will regenerate the missing section.

---

## Deliverables at Audit Completion

After Phase 7 completes, you will have:

### 1. **Complete Audit Report** (single markdown file)
```
# L9 Audit Report: Staged Review
Date: [YYYY-MM-DD]
Auditor: Codex
Status: COMPLETE | DEFERRED | BLOCKED

[Phase 0–7 outputs compiled into a single, searchable document]
```

### 2. **Bug Fix Patches** (individual `.diff` files)
```
diff --git a/worldmodelruntime.py b/worldmodelruntime.py
@@ -123,5 +123,7 @@
  async def loop(self):
-    result = memory_search(query)  # Missing await
+    result = await memory_search(query)  # Fixed
```

Each fix is reviewable, testable, and can be applied independently.

### 3. **Improvement Roadmap** (prioritized action items)
```
## Recommended Next Steps

### Immediate (1–2 sprints)
- [ ] Enforce PacketEnvelope as WM entity SoT (Improvement 1)
- [ ] Fix async/sync boundaries in worldmodelruntime (Improvement 4)

### Short-term (2–4 sprints)
- [ ] Integrate SemanticService into WM queries (Improvement 2)
- [ ] Add stateversion reconciliation (Improvement 3)

### Medium-term (Feature development)
- [ ] Wire ResearchMemoryAdapter and MCP tools (Improvement 5)
- [ ] Implement WorldModelScheduler (Improvement 6)
```

### 4. **Test Coverage Assessment**
```
Tests created/updated to verify fixes:
- testsintegrationtestgraphwmsync.py: [N] new tests
- testsintegrationtestworldmodel.py: [N] new tests
- testsintegrationtestapimemoryintegration.py: [N] new tests

Regression test results: ✓ All pass
```

---

## Integration with L9 Workflow

### For Codex (IDE):
```
# After Phase 7, Codex produces:
1. Compiled audit report (copy/paste to GitHub issue or PR)
2. Diffs (apply via `git apply` or manual review)
3. Test updates (commit alongside fixes)
```

### For Igor (Governance):
```
# Igor reviews findings:
1. Approve fixes for CRITICAL/HIGH severity issues
2. Schedule improvements based on impact/effort roadmap
3. Track second-order issues identified in Phase 7
```

### For L (CTO):
```
# L uses the audit for:
1. Architecture review (Tier 2 findings reveal design debt)
2. Roadmap planning (Improvement priorities guide sprints)
3. Risk assessment (Operational findings inform scaling decisions)
```

---

## Recursion & Continuous Improvement

The audit is **designed for repetition**:

1. **Run Audit #1**: Baseline findings, fixes, validation.
2. **Apply Fixes**: Merge Phase 5–6 diffs into main branch.
3. **Wait 1–2 weeks**: Let fixes stabilize in production.
4. **Run Audit #2**: Re-audit to catch regressions and second-order issues.
5. **Iterate**: Continuous improvement loop.

Each audit run gets faster (fewer findings) and more targeted (focusing on subsystems that changed).

---

## Key Takeaways for Using This Superprompt

✅ **DO**:
- Use the 7-phase structure for disciplined, repeatable audits.
- Pause between phases for review and approval.
- Cite exact file:line and symbol names in all findings.
- Leverage existing L9 infra (PacketEnvelope, SemanticService, MCP tools) in improvements.
- Keep fixes minimal, reversible, and testable.

❌ **DON'T**:
- Skip phases or combine phases (each builds on the prior).
- Auto-proceed without user approval (pause points are critical).
- Speculate or infer intent (only report what code and tests demonstrate).
- Cross-cutting refactors (prefer local, scoped fixes).
- Leave LOW-severity findings unaddressed (they accumulate technical debt).

---

## Questions?

If you have questions about the audit methodology, phases, or deliverables, refer back to:
- **CODEX-STAGED-AUDIT-SUPERPROMPT.md** for detailed phase specifications.
- **CODEX-PHASE-0-KICKOFF.md** for execution patterns and tool usage.
- This file for integration guidance and workflow.

**Ready to start? Invoke Phase 0 now.**
