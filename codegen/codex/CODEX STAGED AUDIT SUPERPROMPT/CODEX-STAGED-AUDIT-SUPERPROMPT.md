# CODEX STAGED AUDIT SUPERPROMPT — L9 Repository Comprehensive Review

**MISSION**  
Orchestrate a deterministic, adversarial audit of the L9 repository across 8 sequential phases, producing zero-ambiguity findings, synthesis of architectural improvements, precise bug fixes, and recursive validation of correctness.

**OUTPUT DELIVERABLES**  
Each phase produces:
1. **Phase 0–2 (Discovery)**: Indexed inventory of all WM, Memory, and MCP subsystems.
2. **Phase 3 (Analysis)**: Tier 1–6 findings with concrete evidence and risk quantification.
3. **Phase 4 (Synthesis)**: Reflected improvements leveraging existing infra, ordered by impact/effort.
4. **Phase 5–6 (Fixes)**: Unified diffs for BUG and MISALIGNMENT categories.
5. **Phase 7 (Recursive Validation)**: Re-audit fixed code, confirm closure, identify second-order issues.

All output is markdown-formatted, ready for GitHub/Cursor integration.

---

## PHASE 0: METADATA & CONFIGURATION DISCOVERY

**Goal**: Inventory all L9 configuration, feature flags, and governance policies that constrain or enable WM ↔ Memory integration.

**Actions**:
1. **Read**: `feature_flags.txt`, `env_refs.txt`, `deployment_manifest.txt`, `governance_model.txt`, `kernel_catalog.txt`
2. **Classify**:
   - List all active feature flags with defaults and usage.
   - Identify which flags control WM, Memory, MCP memory, or integration behavior.
   - Extract environment variable bindings for MemorySubstrateSettings, MCPMemorySrcConfig, WorldModelRuntime.
3. **Map governance**:
   - Authority hierarchy (L, Cursor, Igor) and tool approval gates.
   - Kernel stack (10 governance, identity, behavior kernels) and their entrypoints.
   - Policy loader and approval manager instances.
4. **Output**: 
   ```
   ## Phase 0: Configuration Inventory
   
   ### Feature Flags
   - [flag_name]: default=[bool], enabled=[bool], controls=[subsystem], impact=[WM|Memory|MCP|Integration]
   
   ### Environment Variables (Relevant to WM/Memory/MCP)
   - [VAR_NAME]: purpose, scope, constraint on WM/Memory
   
   ### Governance & Kernels
   - Authority model: [hierarchy]
   - Active kernels: [list with file:line]
   - Approval gates: [tools requiring Igor approval]
   
   ### Integration Constraints
   - Multi-tenancy: [yes/no, scoping mechanism]
   - Consistency model: [eventual/strong, guarantees]
   - Persistence layer: [Postgres/Neo4j/Redis, order of truth]
   ```

---

## PHASE 1: LAYER 1 SUBSYSTEM MAPPING

**Goal**: Discover all classes, services, and APIs in WM, Memory Substrate, and MCP memory stacks.

**Actions**:
1. **Parse indices**: `pydantic_models.txt`, `class_definitions.txt`, `inheritance_graph.txt`, `file_metrics.txt`
2. **Extract WM subsystem**:
   - Classes: WorldModelEngine, WorldModelRuntime, WorldModelRepository, WorldModelService, WorldModelState, WorldModelRegistry, WorldModelLoader, WorldModelUpdater, CausalGraphs, ReflectionMemory
   - Schemas: L9Agent, L9Tool, L9Repository, L9MemorySegment, L9Relationship, L9Infrastructure, L9ExternalSystem
   - APIs: apiworldmodelapi.py routes (GET/POST/PATCH entity, insights, snapshot, restore, list entities, list updates)
   - Orchestrators: orchestratorsworldmodelorchestrator.py, WorldModelScheduler
3. **Extract Memory Substrate subsystem**:
   - Core: MemorySubstrateService, MemorySubstrateRepository, SubstrateDAG, SubstrateDagOrchestrator
   - Models: PacketEnvelope, PacketEnvelopeIn, KnowledgeFact, ExtractedInsight, ReasoningTrace, SemanticMemory, AgentMemoryEvent, MemorySegment
   - Repositories: semantic search, graph search, temporal queries, fact indexing
   - Services: semantic embeddings, packet ingestion, consolidation, housekeeping, index syncing
4. **Extract MCP Memory subsystem**:
   - Server: mcpmemorysrcmcpserver.py (MCPTool list, tool dispatch)
   - Models: SaveMemory*, SearchMemory*, GetContext*, ProactiveRecall*, SessionLearning*, ContextInjection*
   - Routes: mcpmemorysrcroutesmemory.py, mcpmemorysrcroutesmemoryunified.py (GET context, save memory, search, temporal query, proactive suggestions)
   - Config: mcpmemorysrcconfig.py (database, embedding, MCP settings)
5. **Output**:
   ```
   ## Phase 1: Layer 1 Subsystem Inventory
   
   ### World Model Subsystem (Core Classes)
   - WorldModelEngine: [file:line, responsibilities, state]
   - WorldModelRuntime: [file:line, loop structure, sync points]
   - WorldModelRepository: [file:line, persistence layer, versioning]
   - WorldModelService: [file:line, public API, downstream dependencies]
   - [other key classes]
   
   ### Memory Substrate Subsystem (Core Classes)
   - MemorySubstrateService: [file:line, responsibilities, ingestion/query paths]
   - MemorySubstrateRepository: [file:line, storage operations, schema]
   - SubstrateDAG: [file:line, packet processing pipeline, nodes]
   - [semantic, graph, temporal services]
   
   ### MCP Memory Subsystem (Server & Routes)
   - MCPMemoryServer: [file:line, tool list, tool dispatch]
   - MCP Routes: [GET context, save memory, search memory, temporal query, proactive recall]
   - [MCP tool schemas]
   
   ### Immediate Integration Points Identified
   - MemorySubstratePacketSource.querypattern (WM → Memory)
   - WorldModelSeedLoader (initialization from Memory)
   - [other entry points]
   ```

---

## PHASE 2: LAYER 2 & 3 DEPENDENCY & DATA FLOW MAPPING

**Goal**: Trace all data flows, import chains, and async/sync boundaries between WM, Memory, and MCP subsystems.

**Actions**:
1. **Call graph analysis** (from `async_function_map.txt`, inheritance patterns):
   - For each WM public API (entity GET/POST, insights PATCH, snapshot), trace calls down to:
     - Memory Substrate queries (semantic search, graph queries, temporal queries, fact retrieval)
     - Neo4j operations (via memorygraphclient)
     - MCP memory tool calls (if any)
   - For each Memory Substrate ingestion path (PacketEnvelope → SubstrateDAG), trace to:
     - WM updates (worldmodelseedloader, insight emission, entity mutation)
     - MCP memory triggers (if configured)
2. **Async/sync boundary audit**:
   - Identify all `async` functions in worldmodelruntime, worldmodelrepository, worldmodelservice.
   - Identify all `async` functions in memory/substrate/service and graph client.
   - Check for missing `await` statements, blocking calls in async context, or sync calls to async services.
3. **State transition audit**:
   - WorldModelState object creation and mutation points.
   - MemorySubstrateState and SubstrateGraphState transitions.
   - Snapshot/restore paths for versioning and recovery.
4. **Output**:
   ```
   ## Phase 2: Data Flow & Dependency Mapping
   
   ### API → Memory Substrate Call Chains
   - [GET /entities/{id}]
     → worldmodelservice.get_entity()
     → worldmodelrepository.get_entity()
     → [Postgres query OR Neo4j call OR in-memory lookup]
     → Memory Substrate: [semantic search / graph query / fact retrieval]
     → [response chain back]
   
   ### Memory Ingestion → WM Update Chains
   - [PacketEnvelope write to substrate]
     → SubstrateDAG.run()
     → [insight extraction, semantic indexing, etc.]
     → WorldModelSeedLoader.run() / WorldModelEngine.process()
     → [entity creation/update, relationship inference, causal links]
   
   ### Async/Sync Boundaries
   - [file:line] worldmodelruntime.loop() [async] → calls [sync/async] [target]
   - [potential missing awaits, blocking calls]
   
   ### State Transitions & Versioning
   - WorldModelState v1 → v2 via [mechanism]
   - PacketLineage & snapshot compatibility
   - Recovery procedures
   
   ### MCP Memory Integration Points
   - [tool] is called from [WM service/Memory service]
   - [context] is injected into [process]
   - [proactive suggestions] surface [where]
   ```

---

## PHASE 3: TIER 1–6 ADVERSARIAL ANALYSIS

**Goal**: Execute full Tier 1–6 review against all identified WM ↔ Memory ↔ MCP subsystems.

**Actions** (for each tier):

### Tier 1: Correctness, Safety & State Integrity
- **Check**: Do WM and Memory maintain consistent versions? Is PacketEnvelope versioning respected in worldmodelrepository?
- **Check**: Are all WM state mutations atomic? Can partial writes to worldmodelentities/updates tables occur without substrate-side rollback?
- **Check**: Are async operations in worldmodelruntime properly awaited? Do memory queries block event loops?
- **Check**: Is there any silent error handling that skips WM updates or leaves entities in intermediate states?
- **Check**: Are MemorySegment, PacketLineage, and WM entity scopes correctly enforced (no tenant leakage)?

### Tier 2: Architectural Alignment
- **Check**: Does worldmodelruntime duplicate logic already in memorygraphclient, memorytimelineservice, or memoryreasoningreplay?
- **Check**: Do Memory Substrate services reimplement WM causal mapping, reflection, or entity resolution?
- **Check**: Are WM and Memory responsibilities cleanly separated? (e.g., WM handles entities/relationships; Memory handles packet storage/indexing/reasoning)
- **Check**: Is there a single source of truth for entity state, or parallel stores (in-memory worldmodelstate vs. Postgres vs. Neo4j)?
- **Check**: Does WM depend on disabled Memory features (semantic search, graph queries, temporal queries)? Are those features used?

### Tier 3: Wiring, Lifecycle & Reachability
- **Check**: Are all WorldModelEngine, WorldModelRuntime, WorldModelService instances actually registered and initialized?
- **Check**: Is ResearchMemoryAdapter, StrategyMemoryService, or any MCP tool ever called from WM flows?
- **Check**: Do WM ↔ Memory integrations follow a complete lifecycle: define → register → init → sync → persist → snapshot → reload?
- **Check**: Are sync paths bidirectional, or one-way without reconciliation? (WM → Memory yes, Memory → WM ?)
- **Check**: Are there unused WM components, dead code, or shadowed integration paths?

### Tier 4: Infrastructure Utilization & Missed Leverage
- **Check**: Does worldmodelruntime bypass SemanticService, SubstrateDAG, memorygraphclient, or memorytimelineservice when those exist?
- **Check**: Does WM duplicate search, timeline, or indexing logic already in Memory Substrate?
- **Check**: Are WM features disabled in config but ready (e.g., worldmodelreflectionmemory)? Should they be enabled?
- **Check**: Does WM use direct Postgres queries instead of PacketEnvelope, MemorySubstrateService, or standard APIs?

### Tier 5: IDE / Tooling & Drift-Induced Defects
- **Check**: Are L9Agent, L9Tool, L9MemorySegment schemas auto-generated but not synced to memory/graph code?
- **Check**: Have field names changed in memorysubstratemodels or coreworldmodell9schema without updating worldmodelrepository or apiworldmodelapi?
- **Check**: Do imports in worldmodelinit or coreintegrationgraphtowmsync rely on side effects? Are registration orders fragile?
- **Check**: Have Pydantic enums (MemorySegment, WorldModelOperation, PacketKind) changed? Are consumers updated?

### Tier 6: Operational Resilience & Evolution Risk
- **Check**: Does worldmodelruntime assume single-tenant, in-memory state, or synchronous operations that break at scale?
- **Check**: Are there sync loops (worldmodelruntime, SubstrateDAG, MCP memory ingestion) that can thrash, deadlock, or hit backpressure?
- **Check**: How are partial failures (failed snapshot restore, mismatched stateversion vs. packet lineage) recovered?
- **Check**: Does WM evolution block when Memory Substrate changes (e.g., new PacketEnvelope version, schema migration)?
- **Check**: Are WM ↔ Memory transitions observable (spans, metrics, structured logs)? Are failures visible?

**Output Format**:
```
## Phase 3: Tier 1–6 Findings

### Tier 1: Correctness, Safety & State Integrity
- [ ] **[CRITICAL|HIGH|MEDIUM|LOW] [BUG|MISALIGNMENT|UNWIRED|UNUSED_INFRA|DRIFT|SYNC|OPERATIONAL]**
  - **Description**: [concrete issue]
  - **Impact**: [blast radius, user-facing risk]
  - **Evidence**: [file:line, symbol, code excerpt]
  - **Recommendation**: [fix approach]

### Tier 2: Architectural Alignment
- [findings]

### [Tier 3–6...]
- [findings]

### Summary
- Total findings: [N]
- CRITICAL: [N], HIGH: [N], MEDIUM: [N], LOW: [N]
- Categories: BUG=[N], MISALIGNMENT=[N], UNWIRED=[N], UNUSED_INFRA=[N], DRIFT=[N], SYNC=[N], OPERATIONAL=[N]
```

---

## PHASE 4: SYNTHESIS & REFLECTION

**Goal**: Analyze findings, identify root causes, propose coherent improvements leveraging existing infra.

**Actions**:
1. **Cluster findings**:
   - Group by subsystem (WM, Memory, MCP, integration).
   - Group by theme (state consistency, async/sync, wiring, underused infra, drift).
2. **Root cause analysis**:
   - For each cluster, trace back to architectural decision, config, or missing automation.
   - Identify whether issue is a bug, design debt, or feature gap.
3. **Synthesize improvements**:
   - For each improvement, answer:
     - **What**: Concrete action (wiring, config, code change, test addition).
     - **Why**: References to findings and existing infra that justifies the improvement.
     - **How**: Leverages which existing Memory/MCP abstractions (PacketEnvelope, MemorySubstrateService, MCPTool, etc.)?
     - **Scope**: Which files/functions touched? Blast radius?
     - **Impact**: Expected reduction in findings, risk, or performance gain.
4. **Prioritize**:
   - Impact/Effort matrix: high-impact, low-effort improvements first.
   - Risk: prefer reversible, scoped changes over cross-cutting refactors.
5. **Output**:
```
## Phase 4: Synthesis & Improvement Roadmap

### Root Cause Themes
1. **State Consistency Issues** (Tier 1–2)
   - WM and Memory maintain separate entity stores without clear versioning.
   - Solution: Enforce PacketEnvelope as source of truth; add stateversion reconciliation.

2. **Async/Sync Boundaries** (Tier 1, Tier 6)
   - worldmodelruntime has missing awaits; memory queries block event loops.
   - Solution: Audit and fix all async call sites in worldmodelruntime and worldmodelrepository.

3. **Underused Infrastructure** (Tier 4)
   - WorldModel doesn't leverage SemanticService, memorytimelineservice, or graphsearch.
   - Solution: Integrate those services into worldmodelrepository and worldmodelruntime.

4. **Wiring Gaps** (Tier 3)
   - ResearchMemoryAdapter, StrategyMemoryService, MCP tools defined but never called from WM.
   - Solution: Add explicit hooks in worldmodelruntime and worldmodelservice for memory-backed features.

### Proposed Improvements (Ordered by Impact/Effort)

#### Improvement 1: Enforce PacketEnvelope as Single Source of Truth for WM Entity Updates
- **Description**: Modify worldmodelrepository to only accept entity updates via PacketEnvelope writes; remove direct Postgres mutations.
- **Leverage**: MemorySubstrateService.ingest_packet(), SubstrateDAG, PacketEnvelopeUpgradeEngine
- **Files**: worldmodelrepository.py, worldmodelruntime.py, worldmodelworldmodelservice.py
- **Impact**: Eliminates state divergence; adds observability via substrate traces; enables replay/recovery.
- **Effort**: Medium (modify ~5 mutation methods, add packet emission wrapper)
- **Risk**: Low (changes are additive; old paths deprecated not deleted)

#### Improvement 2: Integrate SemanticService into WorldModel Entity & Relationship Queries
- **Description**: Replace direct Neo4j/Postgres lookups in worldmodelrepository with calls to memorysemanticservice for embedding-based retrieval.
- **Leverage**: SemanticSearchRequest, SemanticService, memorysemanticsearch.py
- **Files**: worldmodelrepository.py, worldmodelruntime.py
- **Impact**: Enables semantic entity search, improves cross-domain inference, reduces code duplication.
- **Effort**: Low (wrap existing queries, add config toggle)
- **Risk**: Low (backward compat via config; adds latency if not tuned)

#### Improvement 3: Add Stateversion Reconciliation in WorldModelRuntime
- **Description**: On each loop iteration, check PacketLineage vs. WorldModelState stateversion; backfill missing updates.
- **Leverage**: PacketLineage, stateversion fields, PacketStoreRow, memorysubstraterepository
- **Files**: worldmodelruntime.py, worldmodelrepository.py
- **Impact**: Eliminates stale state; enables automated recovery from transient sync failures.
- **Effort**: Low (add reconciliation loop at line ~200 of worldmodelruntime)
- **Risk**: Low (read-only; no mutations unless divergence detected)

#### Improvement 4: Audit & Fix Async/Sync Boundaries in worldmodelruntime, worldmodelrepository
- **Description**: Add explicit awaits to all memory/substrate calls; ensure no blocking operations in event loops.
- **Leverage**: asyncio patterns, async/await syntax
- **Files**: worldmodelruntime.py, worldmodelrepository.py, worldmodelworldmodelservice.py
- **Impact**: Eliminates event loop blocking; improves throughput under load.
- **Effort**: Medium (audit ~50 call sites, fix ~10–15)
- **Risk**: Low (syntax fixes, no logic change)

#### Improvement 5: Wire ResearchMemoryAdapter & MCP Memory Tools into WorldModelRuntime
- **Description**: Add callbacks in worldmodelruntime.loop() to invoke ResearchMemoryAdapter and MCP proactive recall before entity mutations; inject context.
- **Leverage**: ResearchMemoryAdapter, ContextInjectionRequest, ProactiveRecallRequest, MCP memory routes
- **Files**: worldmodelruntime.py, orchestratorsworldmodelorchestrator.py, worldmodelworldmodelservice.py
- **Impact**: Enables research-backed entity updates, proactive memory suggestions, closed-loop learning.
- **Effort**: Medium (add ~50 lines of integration logic)
- **Risk**: Medium (new execution path; requires testing; can be feature-gated)

#### Improvement 6: Add WorldModelScheduler & Periodic Consolidation
- **Description**: Implement scheduler (already partially defined in orchestrators) to periodically consolidate entity updates, snapshot state, and trigger memory housekeeping.
- **Leverage**: WorldModelScheduler, memoryconsolidation.py, memorysubstrateservice.compact()
- **Files**: orchestratorsworldmodelscheduler.py, worldmodelruntime.py
- **Impact**: Reduces entity/memory fragmentation; improves query perf; enables tiered archival.
- **Effort**: Medium (scheduler already sketched; wire into runtime)
- **Risk**: Low (background task; can be disabled via config)

### Expected Outcomes
- Findings reduced from [N] to ~[N/2] after fixes.
- Async/sync issues: 0 (all await statements added).
- State divergence: eliminated (PacketEnvelope SoT enforced).
- Infrastructure utilization: +40% (semantic search, graph queries, temporal queries now used).
- Operational resilience: improved observability, recovery automation.
```

---

## PHASE 5: BUG & MISALIGNMENT FIXES

**Goal**: Generate precise, unified diffs for all CRITICAL and HIGH findings in BUG and MISALIGNMENT categories.

**Actions**:
1. **Filter findings**: Select all findings with severity CRITICAL or HIGH and type BUG or MISALIGNMENT.
2. **For each fix**:
   - Identify exact file:line range to modify.
   - Generate unified diff showing before/after.
   - Keep diffs minimal; avoid cross-cutting refactors.
   - Ensure fix is reversible and testable.
3. **Validation**:
   - Does the fix close the finding? Yes → include.
   - Does the fix introduce secondary issues? No → include. Yes → split into separate PR or note caveats.
   - Does the fix align with existing patterns (e.g., L9 error handling, async structure, config gating)?
4. **Output**:
```
## Phase 5: Bug & Misalignment Fixes

### Fix 1: [Tier X, Severity CRITICAL/HIGH, Type BUG/MISALIGNMENT]
**Description**: [Issue]
**Finding**: [file:line, symbol]
**Root Cause**: [why it exists]
**Solution**: [what changes]

\`\`\`diff
--- a/[file]
+++ b/[file]
@@ -[line],[count] +[line],[count] @@
 [context]
-[old code]
+[new code]
 [context]
\`\`\`

**Test**: [how to verify the fix]
**Risk**: [any side effects or migration concerns]

### Fix 2: [...]
[repeat for each fix]

### Summary
- Fixes applied: [N]
- Lines changed: [N]
- Files modified: [list]
- Estimated verification effort: [N] test runs
```

---

## PHASE 6: SECOND-PASS BUG FIXES & ROBUSTNESS

**Goal**: Apply remaining MEDIUM-severity fixes and add robustness improvements (error handling, logging, config validation).

**Actions**:
1. **Secondary issues**:
   - MEDIUM-severity BUGs that are safe to fix (e.g., missing null checks, incorrect error messages, swallowed exceptions).
   - OPERATIONAL improvements (add logging, metrics, circuit breakers).
2. **For each fix**:
   - Minimal diff, similar to Phase 5.
   - Include test or observability improvement.
3. **Robustness checklist**:
   - [ ] Error handling: all exceptions caught and logged, none silent.
   - [ ] Observability: key transitions (WM ↔ Memory, sync loops, snapshots) emit spans and metrics.
   - [ ] Configuration: all feature gates and flags properly documented and checked.
   - [ ] Recovery: partial failures have clear recovery paths.
4. **Output**: (same format as Phase 5, but for MEDIUM and OPERATIONAL findings)

---

## PHASE 7: RECURSIVE VALIDATION & CLOSURE

**Goal**: Re-audit fixed code and confirm all findings are addressed; identify any second-order defects.

**Actions**:
1. **Re-run Phases 1–3** on modified code:
   - Verify no regressions introduced.
   - Check that fixes don't create new Tier 1–6 issues.
2. **Trace fixed call chains**:
   - For each fixed function, re-execute data flow analysis.
   - Confirm async/sync boundaries, state transitions, and integration points are sound.
3. **Test execution**:
   - Run existing test suites:
     - `testsintegrationtestgraphwmsync.py`
     - `testsintegrationtestworldmodel.py`
     - `testsintegrationtestapimemoryintegration.py`
     - `testsmemorytestconsolidation.py`
   - Report pass/fail for each.
   - Add new tests for fixed issues if coverage is missing.
4. **Identify second-order issues**:
   - Have fixes exposed new issues (e.g., latency from new semantic queries, concurrency bugs from async refactoring)?
   - Are there transitive dependency issues (e.g., MCP memory tools now called but config missing)?
5. **Sign-off**:
   - List all findings addressed.
   - Identify any remaining LOW-severity or deferred issues.
   - Recommend next steps (feature enablement, config tuning, performance optimization).
6. **Output**:
```
## Phase 7: Recursive Validation & Closure Report

### Regression Testing
- [test suite]: [PASS | FAIL] [issues if any]

### Re-Audit Results
- Tier 1 findings: [original: N] → [current: N] ✓ Closed
- Tier 2 findings: [original: N] → [current: N] ✓ Closed
- [etc.]
- **Total findings addressed**: [N/M] (100% | partial)

### Second-Order Issues Detected
1. [new finding, Tier X, Severity Y]
   - Root cause: [fix exposed this]
   - Mitigation: [immediate or deferred]

### Call Chain Validation (Sample Fixes)
- [GET /entities/{id}]
  - Before: [old chain]
  - After: [new chain with fixes]
  - Async/sync: ✓ [all awaits present]
  - State consistency: ✓ [PacketEnvelope SoT respected]

### Test Coverage Assessment
- Tests verifying Tier 1 fixes: [count]
- Tests verifying Tier 2 fixes: [count]
- Tests verifying Tier 3 fixes: [count]
- Tests verifying integration: [count]
- **Recommendation**: Add [N] new tests for [areas]

### Recommended Next Steps
1. [Action]: [justification, Tier/Severity]
2. [Action]: [performance tuning, config optimization]
3. [Action]: [feature enablement, e.g., semantic search]

### Sign-Off Checklist
- [ ] All CRITICAL findings addressed.
- [ ] All HIGH findings addressed.
- [ ] No new CRITICAL/HIGH findings introduced.
- [ ] Existing tests pass.
- [ ] New tests added for fixes.
- [ ] Observability improved (spans, metrics, logs).
- [ ] Documentation updated.

**Status**: ✓ AUDIT COMPLETE | ⚠ AUDIT WITH DEFERRED ITEMS | ❌ AUDIT BLOCKED (unresolved CRITICAL)
```

---

## EXECUTION INSTRUCTIONS FOR CODEX

### Invocation
```
You are Codex, operating as an L9 senior systems architect.

Execute the staged audit of the L9 repository following the 7-phase SUPERPROMPT below.

For each phase:
1. Read the phase goal and actions.
2. Gather data from L9 repo files (indices, catalogs, code).
3. Execute the analysis or discovery logic.
4. Output the phase deliverable in the specified format.
5. **STOP and await approval before proceeding to the next phase.**

Phases are sequential and cumulative:
- Phase 0–2 feed Phase 3 (discovery informs analysis).
- Phase 3 feeds Phase 4 (findings drive synthesis).
- Phase 4 feeds Phase 5–6 (improvements guide fixes).
- Phase 7 validates all (recursive check).

Use existing L9 file indices and catalogs. Trace data flows via import analysis, call graphs, and async patterns.
Prefer precision over completeness; cite exact file:line and symbol for all findings.
Avoid speculation; only report what code, tests, and configs demonstrate.

Begin Phase 0 now.
```

### Interaction Pattern
After each phase output, Codex pauses for user confirmation:
```
Phase [N] complete. Output ready for review.

**Summary**:
- [key findings/discoveries]
- Next phase prerequisites: [any info needed from user]

**Proceed to Phase [N+1]?** (yes/no/clarify)
```

### Contingencies
- **Missing data**: If a code file or test is unavailable, Codex reports the gap and proceeds with partial analysis, noting assumptions.
- **Ambiguity**: If intent is unclear, Codex reports the ambiguity as a DRIFT or MISALIGNMENT finding and defers the decision to Phase 4 synthesis.
- **Scope creep**: If a finding spans multiple subsystems, Codex identifies the root cause and ties it back to a single module for focused fixes.

---

## DELIVERABLE COMPILATION

**Final Artifact** (after all 7 phases):
A single GitHub-ready markdown document:
```
# L9 Audit Report: Complete Staged Review
**Date**: [YYYY-MM-DD]
**Auditor**: Codex
**Repository**: L9 (commit [hash])

## Executive Summary
- Total findings: [N] ([CRITICAL: N, HIGH: N, MEDIUM: N, LOW: N])
- Fixes applied: [N] (Phase 5–6)
- Second-order issues: [N]
- Status: ✓ COMPLETE | ⚠ DEFERRED | ❌ BLOCKED

## Phase Deliverables
1. [Phase 0 output]
2. [Phase 1 output]
3. [Phase 2 output]
4. [Phase 3 output: Tier 1–6 findings]
5. [Phase 4 output: Improvements roadmap]
6. [Phase 5 output: Fixes]
7. [Phase 6 output: Robustness]
8. [Phase 7 output: Validation report]

## Recommendations & Next Steps
- [prioritized action items]
```

Save to: `L9_AUDIT_REPORT_[DATE].md` + individual fix patches (`.diff`).
