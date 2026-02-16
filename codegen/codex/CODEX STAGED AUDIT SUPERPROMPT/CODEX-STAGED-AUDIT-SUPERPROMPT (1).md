# ═══════════════════════════════════════════════════════════════════════════════
# CODEX STAGED AUDIT SUPERPROMPT — Master Orchestration Document
# ═══════════════════════════════════════════════════════════════════════════════
# 
# PURPOSE: 
# Define a 7-phase audit methodology for Codex to systematically examine L9 repo.
# Stages: 3 Discovery Phases → 1 Analysis → 1 Synthesis → 2 Fix Phases → 1 Recursion.
#
# INVARIANTS:
# ✓ Each phase builds on prior phase outputs.
# ✓ Pause points after each phase (NO auto-proceed).
# ✓ All findings tied to exact file:line references.
# ✓ All recommendations grounded in frontier AI standards (ISO 42001, NIST AI RMF).
#
# ═══════════════════════════════════════════════════════════════════════════════

---

## EXECUTIVE SUMMARY FOR USERS

This superprompt guides **Codex** through a **7-phase audit** of the L9 repository:

| Phase | Name | Goal | Time | Output |
|-------|------|------|------|--------|
| **0** | Metadata Discovery | Inventory config, flags, governance | 10 min | Configuration Inventory |
| **1** | Layer 1 Mapping | Extract WM, Memory, MCP classes | 20 min | Subsystem Inventory |
| **2** | Layer 2–3 Mapping | Map call graphs, data flows | 30 min | Call Graph Report |
| **3** | Adversarial Analysis | Classify findings into Tiers 1–6 | 45 min | Tier 1–6 Findings Report |
| **4** | Synthesis | Root-cause clustering, improvements | 30 min | Improvement Roadmap |
| **5** | Bug & MISALIGNMENT Fixes | Generate diffs for CRITICAL/HIGH issues | 20 min | Unified Diffs + Reasoning |
| **6** | Robustness & Ops Fixes | Logging, error handling, second-pass | 20 min | Robustness Diffs + Tests |
| **7** | Recursive Validation | Re-audit, verify fixes, catch regressions | 30 min | Validation Report + Second-Order Findings |

**Total time**: ~3.5 hours for a complete, production-grade audit.

---

# PHASE 0: METADATA & CONFIGURATION DISCOVERY

## Goal
Inventory all L9 configuration, feature flags, governance, and kernel infrastructure that constrain World Model ↔ Memory Substrate ↔ MCP Memory integration.

## Actions for Codex

### Action 0.1: Feature Flags Inventory
```
Search L9 files for:
- Feature flag definitions (defaults, current values, purpose)
- Flags that control World Model engine, Memory Substrate, or MCP memory behavior
- Kernel activation flags (bootstrap sequence)

Queries to execute:
  search_files_v2(
    queries=[
      "feature flags world model wm semantic memory",
      "enable disable flag environment",
      "kernel activation bootstrap phase"
    ],
    context_budget="MEDIUM"
  )

Extract & Tabulate:
| Flag Name | Default | Current | Purpose | Affects | Notes |
|-----------|---------|---------|---------|---------|-------|
| FEATURE_WORLD_MODEL | true | ? | WM engine startup | WM core | [control state] |
| FEATURE_SEMANTIC_SEARCH | true | ? | Semantic query layer | Memory queries | [control state] |
| ... | ... | ... | ... | ... | ... |
```

### Action 0.2: Environment Variables Mapping
```
Search for:
- Database URLs (Postgres, Neo4j, Redis)
- API keys (OpenAI embeddings, MCP services)
- Constraint variables (multi-tenancy scope, consistency guarantees)
- Audit/logging config (event store, tracing)

Queries:
  search_files_v2(
    queries=[
      "environment variables postgres neo4j redis url",
      "openai embedding api key mcp",
      "tenant scope consistency guarantee eventual strong",
      "audit event store logging tracing"
    ],
    context_budget="MEDIUM"
  )

Extract & Tabulate:
| Variable | Purpose | Default/Current | Scope | Constraint on WM/Memory |
|----------|---------|-----------------|-------|------------------------|
| POSTGRES_URL | Memory substrate primary DB | ? | Shared | WM entity persistence |
| NEO4J_URL | Entity relationships graph | ? | Shared | WM knows entity deps |
| REDIS_URL | Cache + session state | ? | Shared | WM invalidation on updates |
| OPENAI_EMBEDDING_KEY | Semantic search | ? | Optional | Disable if missing |
| ... | ... | ... | ... | ... |
```

### Action 0.3: Governance Model & Authority
```
Search for:
- Authority hierarchy (L=CTO, Cursor=IDE, Igor=Boss)
- Approval gates for high-risk tools / kernel modifications
- Audit and compliance controls

Queries:
  search_files_v2(
    queries=[
      "authority hierarchy l cto cursor igor boss",
      "approval gates high risk tools governance",
      "kernel modification audit compliance"
    ],
    context_budget="MEDIUM"
  )

Extract:
- Authority roles and responsibilities
- Tools requiring L approval vs. Cursor approval vs. Igor approval
- Kernel interaction constraints
```

### Action 0.4: Kernel Stack Inventory
```
Search for:
- 10 kernel types defined in L9 (governance, identity, behavior, memory, reasoning, etc.)
- Each kernel's file:line, purpose, and role in bootstrap
- Kernels interacting with World Model or Memory Substrate

Queries:
  search_files_v2(
    queries=[
      "kernel types governance identity behavior memory reasoning",
      "kernel initialization bootstrap phase order",
      "kernel interaction world model memory substrate"
    ],
    context_budget="MEDIUM"
  )

Extract & List:
1. Governance Kernel (file:line)
2. Identity Kernel (file:line)
3. Behavior Kernel (file:line)
4. Memory Kernel (file:line)
5. Reasoning Kernel (file:line)
6. [... 5 more kernels]

Cross-reference with WM and Memory Substrate to identify integration points.
```

## Phase 0 Output Template

```markdown
# Phase 0: Configuration Inventory

## 0.1 Feature Flags
| Flag Name | Default | Current | Purpose | Affects WM/Memory | Notes |
|-----------|---------|---------|---------|-------------------|-------|
| FEATURE_WORLD_MODEL | true | [?] | WM engine startup | WM: Core | ... |
| FEATURE_SEMANTIC_SEARCH | true | [?] | Semantic query layer | Memory: Queries | ... |
| [... all flags] |

## 0.2 Environment Variables
| Variable | Purpose | Default/Current | Scope | WM/Memory Constraint |
|----------|---------|-----------------|-------|----------------------|
| POSTGRES_URL | Primary DB | [?] | Shared | WM persistence |
| NEO4J_URL | Entity graph | [?] | Shared | WM entity deps |
| REDIS_URL | Cache | [?] | Shared | Session state |
| [... all vars] |

## 0.3 Governance & Authority
- **Authority Model**: [L → CTO; Cursor → IDE; Igor → Risk approval]
- **Approval Gates**: [list tools requiring Igor sign-off]
- **Audit Controls**: [compliance, logging, compliance framework]

## 0.4 Kernel Stack
1. [Kernel Name] → [file:line] — [purpose + WM/Memory role]
2. [Kernel Name] → [file:line] — [purpose + WM/Memory role]
... (10 kernels total)

## Phase 0 Status
- Feature flags inventory: ✓ Complete
- Environment variables mapped: ✓ Complete
- Governance model understood: ✓ Complete
- Kernel stack visible: ✓ Complete

## Prerequisites for Phase 1
- [ ] All 10 kernels identified
- [ ] All feature flags controlling WM/Memory found
- [ ] All env vars mapped to subsystems
- [ ] Authority hierarchy clear

**Phase 0 Complete. Ready for Phase 1?**
```

## Pause Point: **STOP HERE**
Do **NOT** proceed to Phase 1 until user approves Phase 0 output.

---

# PHASE 1: LAYER 1 SUBSYSTEM MAPPING

## Goal
Extract and inventory all class definitions, APIs, and responsibilities in:
- **World Model** subsystem (WorldModelEngine, WorldModelRuntime, WorldModelRepository, WorldModelService)
- **Memory Substrate** subsystem (MemorySubstrateService, SubstrateDAG, SemanticService, MemoryPacketSource)
- **MCP Memory** subsystem (MCPTool classes, MCP routes, MCP memory models)

## Actions for Codex

### Action 1.1: World Model Classes
```
Search for WM class definitions:

Queries:
  search_files_v2(
    queries=[
      "world model engine class definition api",
      "world model runtime class async methods",
      "world model repository data access entity",
      "world model service public interface"
    ],
    context_budget="MEDIUM"
  )

For each class, extract:
- File path and line number
- Class name and inheritance
- Constructor signature and dependencies
- Public methods (name, signature, purpose)
- Direct integration with Memory Substrate (if any)
- State management (attributes, invariants)

Example output row:
| Class | File:Line | Inherits | Public Methods | WM→Memory Links | Notes |
|-------|-----------|----------|---|---|---|
| WorldModelEngine | worldmodelengine.py:42 | ABC | bootstrap(), process(), ingest() | ingest_packet() → MemorySubstrateService | Core WM runner |
| WorldModelRuntime | worldmodelruntime.py:15 | Runnable | run(), loop(), shutdown() | memory_search() | Async event loop |
| ... |
```

### Action 1.2: Memory Substrate Classes
```
Search for Memory Substrate class definitions:

Queries:
  search_files_v2(
    queries=[
      "memory substrate service class definition api",
      "memory substrate dag graph data structure",
      "semantic service embedding search",
      "memory packet source ingest"
    ],
    context_budget="MEDIUM"
  )

For each class, extract:
- File:line, class name, inheritance
- Constructor and dependencies
- Public methods (name, signature, purpose)
- Direct integration with WM
- Persistence layer (Postgres, Neo4j, Redis)

Example output row:
| Class | File:Line | Public Methods | Memory→WM Links | Persistence |
|-------|-----------|---|---|---|
| MemorySubstrateService | memorysubstrate.py:33 | ingest_packet(), search(), get_entity() | reads WM state via PacketEnvelope | Postgres + Neo4j |
| ... |
```

### Action 1.3: MCP Memory Classes
```
Search for MCP memory tool and route definitions:

Queries:
  search_files_v2(
    queries=[
      "mcp tool class save memory research memory",
      "mcp memory route handler endpoint",
      "mcp memory model entity memory",
      "mcp adapter world model memory"
    ],
    context_budget="MEDIUM"
  )

For each class/route, extract:
- File:line, name, type (Tool | Route | Model)
- Signature and parameters
- Side effects (reads from WM? writes to Memory?)
- Integration with WM/Memory subsystems

Example:
| Name | Type | File:Line | Signature | WM Read | Memory Write | Notes |
|------|------|-----------|-----------|---------|--------------|-------|
| SaveMemoryTool | Tool | mcpmemory.py:120 | save(entity: Entity, memory: Memory) | Yes | Yes | Persists to Substrate |
| SearchMemoryRoute | Route | mcproutes.py:85 | GET /memory/search?q=... | No | No | Calls SemanticService |
| ... |
```

## Phase 1 Output Template

```markdown
# Phase 1: Layer 1 Subsystem Mapping

## 1.1 World Model Classes

| Class | File:Line | Inherits | Public Methods | WM→Memory | Notes |
|-------|-----------|----------|---|---|---|
| WorldModelEngine | wme.py:42 | ABC | bootstrap(), process(), ingest() | MemorySubstrateService.ingest_packet() | Core |
| WorldModelRuntime | wmr.py:15 | Runnable | run(), loop() | memory_search() calls | Async loop |
| WorldModelRepository | wmrep.py:78 | Repository | fetch_entity(), store_entity(), delete_entity() | read/write via Substrate | Persistence |
| WorldModelService | wmsvc.py:102 | Service | apply_mutation(), query_reasoning() | coordinates via PacketEnvelope | API boundary |
| [... more WM classes] |

## 1.2 Memory Substrate Classes

| Class | File:Line | Public Methods | Memory→WM | Persistence |
|-------|-----------|---|---|---|
| MemorySubstrateService | mss.py:33 | ingest_packet(), search(), get_entity() | reads WM state | Postgres + Neo4j |
| SubstrateDAG | sdag.py:55 | add_edge(), compute_path(), invalidate() | WM entity deps | Neo4j |
| SemanticService | ss.py:89 | embed(), search_similar() | called by WM queries | Redis cache |
| MemoryPacketSource | mps.py:44 | ingest(), subscribe() | event source for WM updates | Event log |
| [... more Memory classes] |

## 1.3 MCP Memory Classes & Routes

| Name | Type | File:Line | WM Read | Memory Write | Notes |
|------|------|-----------|---------|--------------|-------|
| SaveMemoryTool | Tool | mcp.py:120 | Yes | Yes | Persists entity |
| SearchMemoryRoute | Route | mcpr.py:85 | No | No | Semantic search |
| ResearchMemoryAdapter | Adapter | mcpa.py:67 | Yes (for context) | Yes (stores findings) | Research workflow |
| [... more MCP classes] |

## 1.4 Integration Points (Identified)

### Direct Links (WM → Memory)
- WorldModelRuntime.run() → calls memory_search()
- WorldModelService.apply_mutation() → MemorySubstrateService.ingest_packet()

### Direct Links (Memory → WM)
- MemoryPacketSource.subscribe() → notifies WM of updates
- SemanticService.embed() ← called by WM.query_reasoning()

### MCP Bridges
- SaveMemoryTool ← called from research workflows → writes to Substrate
- SearchMemoryRoute ← called from user queries → reads Memory via SemanticService

## Phase 1 Status
- WM classes identified: [N] classes
- Memory Substrate classes identified: [N] classes
- MCP classes identified: [N] classes
- Integration points mapped: [N] direct links

**Phase 1 Complete. Ready for Phase 2?**
```

## Pause Point: **STOP HERE**

---

# PHASE 2: LAYER 2–3 DATA FLOW MAPPING

## Goal
Map call chains, async/sync boundaries, and data flow between:
- WM → Memory reads/writes
- Memory → WM state notifications
- MCP tools ↔ WM/Memory interactions

## Actions for Codex

### Action 2.1: Call Chains (Synchronous)
```
Search for direct method call sequences:

Queries:
  search_files_v2(
    queries=[
      "worldmodelservice apply_mutation memory substrate ingest",
      "worldmodelruntime query memory_search semanticservice",
      "worldmodelrepository fetch_entity substrate get_entity"
    ],
    context_budget="LONG"
  )

For each call chain, trace:
1. Caller (WM method)
2. Callee (Memory method)
3. Parameters passed (signature)
4. Return value used
5. Invariants/assumptions

Example:
```
Call Chain: WM Mutation Propagation
├─ WorldModelService.apply_mutation(mutation: Mutation)
│  └─ WorldModelRepository.store_entity(entity: Entity)
│     └─ MemorySubstrateService.ingest_packet(packet: PacketEnvelope)
│        ├─ validate_packet()
│        ├─ SubstrateDAG.add_edge(...) [Neo4j]
│        ├─ Postgres.insert(entity_state)
│        └─ Redis.invalidate(cache_keys)
└─ [END] Mutation persisted to all layers
```

### Action 2.2: Async Boundaries
```
Search for async/await patterns:

Queries:
  search_files_v2(
    queries=[
      "async def world model runtime loop await memory",
      "async def memory substrate ingest await postgres",
      "worldmodelruntime awaited missing await pattern"
    ],
    context_budget="LONG"
  )

For each async method, identify:
1. Is it actually async (returns coroutine)?
2. Are all awaits present in call chain?
3. Any blocking I/O without await?
4. Race conditions or ordering issues?

Example table:
| Method | File:Line | Async? | Missing Awaits? | Blocking I/O? | Issue |
|--------|-----------|--------|---|---|---|
| WorldModelRuntime.run() | wmr.py:42 | Yes | No | No | ✓ Clean |
| WorldModelRuntime.loop() | wmr.py:88 | Yes | ??? | ??? | [needs checking] |
| MemorySubstrateService.ingest_packet() | mss.py:150 | No | N/A | Postgres.insert() | [potential block] |
```

### Action 2.3: Data Flow Diagram
```
Construct high-level flows:

WM Query Flow:
┌─────────────────────────────────────────────────────┐
│ User Query (MCP SearchMemoryRoute)                  │
└────────────────┬────────────────────────────────────┘
                 ↓
         ┌─────────────────┐
         │ SemanticService │
         │  .search(...)   │
         └────────┬────────┘
                  ↓
         ┌────────────────────┐
         │ Redis Cache Lookup │  ← Fast path
         └────────┬───────────┘
                  ↓
         ┌──────────────────────┐
         │ Neo4j Graph Query    │  ← Fallback
         │ (entity relationships) │
         └────────┬──────────────┘
                  ↓
         ┌──────────────────────┐
         │ Postgres Fetch       │  ← Entity data
         │ (full entity state)  │
         └────────┬──────────────┘
                  ↓
         ┌──────────────────────┐
         │ Return to WorldModel │
         └──────────────────────┘

Risks:
- Triple hit (cache miss → Neo4j → Postgres) blocks WM event loop
- No timeout on any layer
- Cache invalidation not coordinated with WM mutations
```

## Phase 2 Output Template

```markdown
# Phase 2: Layer 2–3 Data Flow Mapping

## 2.1 Synchronous Call Chains

### Chain 1: WM Mutation → Memory Persistence
Caller: WorldModelService.apply_mutation()
│
├─→ WorldModelRepository.store_entity()
│   │
│   └─→ MemorySubstrateService.ingest_packet()
│       ├─→ SubstrateDAG.add_edge()  [async, returns Promise]
│       ├─→ Postgres.insert()         [blocking, no await]
│       └─→ Redis.invalidate()        [async, missing await]
│
└─ [ISSUE] Missing awaits on Neo4j + Redis calls → Inconsistent state

### Chain 2: WM Query → Memory Search
Caller: WorldModelService.query_reasoning()
│
├─→ MemorySubstrateService.search()
│   │
│   ├─→ SemanticService.embed()     [calls OpenAI, 500ms–2s latency]
│   ├─→ Redis.get_similar()         [fallback, 10ms]
│   └─→ Neo4j.query_entities()      [if cache miss, 100ms–1s]
│
└─ [ISSUE] No timeout; blocks WM event loop if Neo4j slow

## 2.2 Async Boundaries Analysis

| Method | File:Line | Returns Coroutine? | All Awaited? | Blocking I/O? | Issue |
|--------|-----------|---|---|---|---|
| WorldModelRuntime.run() | wmr.py:42 | Yes | Yes | No | ✓ Clean |
| WorldModelRuntime.loop() | wmr.py:88 | Yes | No, line 105 missing await | No | ❌ Missing await on memory_search |
| MemorySubstrateService.ingest_packet() | mss.py:150 | No (not async!) | N/A | Yes, Postgres.insert | ❌ Blocking, should be async |
| [... more methods] |

## 2.3 Data Flow Diagram

### WM Query Flow (Current)
```
MCP SearchMemoryRoute
  ↓
SemanticService.search()
  ↓ (no await)
Redis cache_hit → RETURN [10ms, fast path]
  ↓ (cache miss)
Neo4j.query_entities() [100ms–1s, blocks event loop]
  ↓
Postgres.fetch_entity_data() [100ms–500ms]
  ↓ (slow path completes after 1–2 seconds)
RETURN to WorldModel

⚠️  Risk: WM blocked for 1–2 seconds on single query if cache misses
```

### WM Mutation Flow (Current)
```
apply_mutation(mutation)
  ↓
WorldModelRepository.store_entity()
  ↓
MemorySubstrateService.ingest_packet()
  ├─→ SubstrateDAG.add_edge() [async, awaited ✓]
  ├─→ Postgres.insert() [NOT async, blocks ✓ problematic]
  └─→ Redis.invalidate() [async, NOT awaited ✗ potential race]

⚠️  Risk: Postgres insert may block; Redis invalidate may not complete before next query
```

## 2.4 Critical Observations

1. **Async/Sync Mismatch**: MemorySubstrateService.ingest_packet() is NOT async, but calls async methods.
2. **Missing Awaits**: WorldModelRuntime.loop() line 105 missing await on memory_search().
3. **No Timeouts**: SemanticService.search() can hang for 2+ seconds; no timeout protection.
4. **Cache Invalidation Ordering**: Redis invalidate not awaited; next query may hit stale cache.
5. **Blocking I/O**: Postgres.insert() in ingest_packet() blocks event loop.

## Phase 2 Status
- Call chains traced: [N] flows
- Async/sync boundaries analyzed: [N] methods
- Data flow diagrams produced: [N] flows
- Critical issues identified: [N] (async mismatches, missing awaits, no timeouts)

**Phase 2 Complete. Ready for Phase 3?**
```

## Pause Point: **STOP HERE**

---

# PHASE 3: ADVERSARIAL ANALYSIS (Tier 1–6 Findings)

## Goal
Classify all identified issues into **6 tiers of severity + category**:
- **Tier 1: CRITICAL** (Safety/correctness violation, data loss risk, security breach)
- **Tier 2: HIGH** (Feature misalignment, state inconsistency, missing integration)
- **Tier 3: MEDIUM** (Performance issue, incomplete error handling, observability gap)
- **Tier 4: LOW** (Code smell, tech debt, minor inefficiency)
- **Tier 5: OPERATIONAL** (Deployment, scaling, observability concern)
- **Tier 6: FUTURE** (Speculative/architectural evolution)

Within each tier, categorize:
- **BUG**: Code does not match intent.
- **MISALIGNMENT**: Code intent diverges from design/frontier standard.
- **UNWIRED**: Feature exists but not integrated.
- **INCOMPLETE**: Feature only partially implemented.

## Actions for Codex

### Action 3.1: Scan for Critical Issues
```
Queries:
  search_files_v2(
    queries=[
      "race condition deadlock state inconsistency world model memory",
      "data loss persistence bug packet envelope mismatch",
      "security vulnerability auth check world model memory"
    ],
    context_budget="LONG"
  )

For each potential critical issue:
- File:line where it occurs
- Exact code snippet (5–10 lines)
- Impact (data loss? state divergence? security?)
- Evidence (test failure? design doc contradiction? frontier standard breach?)

Example Critical Finding:
**Tier 1 — BUG: Missing Await Causes State Divergence**
File: worldmodelruntime.py:105
Code:
```python
async def loop(self):
    while True:
        # BUG: Missing await — memory_search returns coroutine, not result
        result = memory_search(query)  # line 105
        self.state.last_result = result  # result is <coroutine>, not actual data
```
Impact: WM state contains coroutine object instead of search results; all downstream reasoning is broken.
Frontier Standard Breach: NIST AI RMF "Measure" function requires state consistency verification; this violates it.
Test Evidence: testsunittestworld_model.py:234 — test_query_result fails; result is <coroutine object>.
```

### Action 3.2: Scan for High Misalignment Issues
```
Queries:
  search_files_v2(
    queries=[
      "world model duplicates memory substrate responsibilities",
      "integration missing world model memory semantic search",
      "packet envelope not used source of truth world model state",
      "async sync boundary mismatch ingest query"
    ],
    context_budget="LONG"
  )

For each misalignment:
- Files involved
- How WM and Memory diverge from design
- Which frontier standard (ISO 42001, NIST AI RMF, EU Annex 22) is violated
- Path to alignment

Example High Finding:
**Tier 2 — MISALIGNMENT: WM Duplicates Memory Substrate Responsibilities**
Files: worldmodelrepository.py:78–95, memorysubstrate.py:120–140
Issue: Both WM.fetch_entity() and Memory.get_entity() query Postgres for entity data.
Design Intent: Single Source of Truth (SoT) pattern — Memory Substrate owns entity persistence; WM reads through Memory API.
Current Reality: WM bypasses Memory API, queries Postgres directly.
Frontier Standard: ISO 42001 "Information Management" → Data ownership should be centralized.
Recommendation: WM.fetch_entity() should call Memory.get_entity(); remove direct Postgres access from WM.
```

### Action 3.3: Scan for Unwired / Incomplete Features
```
Queries:
  search_files_v2(
    queries=[
      "semantic service not integrated world model query",
      "research memory adapter not called world model reasoning",
      "mcp memory tools partially implemented world model",
      "graph search not wired entity relationships"
    ],
    context_budget="LONG"
  )

For each feature gap:
- Which component exists but is not used
- Where it should be integrated
- Why integration is missing (tech debt? oversight? complexity?)

Example Unwired Finding:
**Tier 2 — UNWIRED: SemanticService Not Integrated into WM Queries**
File: worldmodelservice.py:102–150 (query_reasoning method)
Issue: SemanticService exists (semanticservice.py:89) but is never called from WM queries.
Current behavior: WM queries only use entity ID lookup (exact match, no semantic understanding).
Missing: Semantic similarity search, embedding-based ranking, approximate entity matching.
Impact: WM cannot find relevant entities if entity names change or are misspelled.
Frontier Standard: NIST AI RMF "Map" function → ML data pipeline should use best available data; semantic search is better than keyword match.
Recommendation: Integrate SemanticService into query_reasoning; add semantic ranking after ID lookup.
```

### Action 3.4: Build Findings Matrix

Create a comprehensive table:

```
| Tier | Category | Finding Summary | File:Line | Affected Subsystem | Frontier Standard | Fix Complexity | Impact Score |
|------|----------|---|---|---|---|---|---|
| T1 | BUG | Missing await in loop() causes state divergence | wmr.py:105 | WM Runtime | NIST Measure | Low | 9/10 |
| T2 | MISALIGNMENT | WM duplicates Memory entity storage | wmrep.py:78 | WM↔Memory | ISO 42001 Info | Medium | 8/10 |
| T2 | UNWIRED | SemanticService not called from WM | wmsvc.py:102 | WM↔Memory | NIST Map | Medium | 7/10 |
| T3 | INCOMPLETE | No timeout on semantic search | ss.py:89 | SemanticService | NIST Measure | Low | 6/10 |
| T3 | BUG | Cache invalidation race in ingest | mss.py:180 | Memory | NIST Measure | Medium | 6/10 |
| T4 | SMELL | Long method in apply_mutation | wmsvc.py:120–160 | WM Service | Code clarity | Low | 3/10 |
| [... continue with all findings] |
```

## Phase 3 Output Template

```markdown
# Phase 3: Adversarial Analysis (Tier 1–6 Findings)

## Summary Statistics
- Total Findings: [N]
- Tier 1 (CRITICAL): [N]
- Tier 2 (HIGH): [N]
- Tier 3 (MEDIUM): [N]
- Tier 4 (LOW): [N]
- Tier 5 (OPERATIONAL): [N]
- Tier 6 (FUTURE): [N]

## Findings by Tier

### Tier 1: CRITICAL

#### Finding T1.1: Missing Await in WorldModelRuntime.loop()
**Category**: BUG
**File:Line**: worldmodelruntime.py:105
**Code**:
```python
async def loop(self):
    while True:
        result = memory_search(query)  # BUG: missing await
        self.state.last_result = result  # result is <coroutine>, not data
```
**Impact**: State divergence. WM stores coroutine object instead of search result. All downstream reasoning broken.
**Frontier Standard**: NIST AI RMF "Measure" — state consistency verification.
**Test Evidence**: testsunittestworld_model.py:234 (test_query_result fails).
**Fix**: Add `await` → `result = await memory_search(query)`
**Effort**: Low (1-line change)

#### [... more T1 findings ...] 

### Tier 2: HIGH

#### Finding T2.1: WM Duplicates Memory Substrate Responsibilities
**Category**: MISALIGNMENT
**Files**: worldmodelrepository.py:78–95, memorysubstrate.py:120–140
**Issue**: Both WM and Memory query Postgres directly for entity data.
**Design Intent**: Single Source of Truth (Memory owns entity persistence).
**Current Reality**: WM bypasses Memory, queries Postgres directly.
**Frontier Standard**: ISO 42001 "Information Management" — data ownership centralized.
**Impact**: State divergence possible; updates to entity may not propagate correctly; cache invalidation not coordinated.
**Recommendation**: WM.fetch_entity() → Memory.get_entity(); remove direct Postgres access from WM.
**Effort**: Medium (refactor WM queries to use Memory API; ~50 lines of code changes; backward-compat testing)

#### Finding T2.2: SemanticService Not Integrated into WM Queries
**Category**: UNWIRED
**File**: worldmodelservice.py:102–150
**Issue**: SemanticService exists but is never called from WM.query_reasoning().
**Current**: WM queries only use entity ID lookup (exact match).
**Missing**: Semantic similarity, embedding-based ranking, approximate matching.
**Impact**: WM cannot find relevant entities if names change or are misspelled.
**Frontier Standard**: NIST AI RMF "Map" — data pipeline should use best available data.
**Recommendation**: Integrate SemanticService into query_reasoning; add semantic ranking.
**Effort**: Medium (wire SemanticService into query flow; ~40 lines; config toggle for backward-compat)

#### [... more T2 findings ...] 

### Tier 3: MEDIUM

#### Finding T3.1: No Timeout on SemanticService.search()
**Category**: INCOMPLETE
**File**: semanticservice.py:89
**Issue**: OpenAI embedding call can hang indefinitely (no timeout).
**Impact**: WM event loop blocked for 2+ seconds per query if OpenAI is slow.
**Frontier Standard**: NIST AI RMF "Measure" — latency SLO monitoring.
**Recommendation**: Add timeout (e.g., 500ms) with fallback to keyword search.
**Effort**: Low (~10 lines; config-driven timeout value)

#### [... more T3 findings ...] 

### Tier 4: LOW

#### Finding T4.1: Long Method in WorldModelService.apply_mutation()
**Category**: SMELL
**File**: worldmodelservice.py:120–160
**Issue**: apply_mutation() is 40 lines; mixing mutation validation, persistence, state update, logging.
**Recommendation**: Extract sub-methods (validate_mutation, persist_mutation, update_state).
**Effort**: Low (refactor, no behavior change)

#### [... more T4 findings ...] 

### Tier 5: OPERATIONAL

#### Finding T5.1: Missing Logging in MemorySubstrateService.ingest_packet()
**Category**: INCOMPLETE
**File**: memorysubstrate.py:150
**Issue**: No structured logging of packet ingestion; difficult to debug state divergence in production.
**Recommendation**: Add log statements at key points (received packet, validated, persisted, invalidated cache).
**Effort**: Low (~15 lines of logging code)

#### [... more T5 findings ...] 

### Tier 6: FUTURE

#### Finding T6.1: WorldModel Scheduler (Architectural Evolution)
**Category**: SPECULATIVE
**Issue**: Current single-threaded event loop may be limiting; consider background job scheduler for expensive operations.
**Recommendation**: Design task scheduler (e.g., Celery-like) for semantic search, research workflows.
**Effort**: High (new subsystem; design first)
**Timeline**: Post-fix phase; revisit after stabilizing current architecture.

## Findings Matrix (Compact View)

| Tier | Category | Summary | File:Line | Subsystem | Frontier Standard | Complexity | Impact |
|------|----------|---------|-----------|-----------|---|---|---|
| T1 | BUG | Missing await in loop() | wmr.py:105 | WM Runtime | NIST Measure | Low | 9/10 |
| T2 | MISALIGNMENT | WM duplicates Memory queries | wmrep.py:78 | WM↔Memory | ISO 42001 | Medium | 8/10 |
| T2 | UNWIRED | SemanticService not integrated | wmsvc.py:102 | WM↔Memory | NIST Map | Medium | 7/10 |
| T3 | INCOMPLETE | No timeout on semantic search | ss.py:89 | SemanticService | NIST Measure | Low | 6/10 |
| T3 | BUG | Cache race in ingest | mss.py:180 | Memory | NIST Measure | Medium | 6/10 |
| T4 | SMELL | Long method apply_mutation | wmsvc.py:120 | WM Service | Code clarity | Low | 3/10 |
| T5 | INCOMPLETE | Missing logging in ingest | mss.py:150 | Memory | Observability | Low | 4/10 |
| T6 | SPECULATIVE | Scheduler for expensive tasks | N/A | N/A | Architecture | High | 0/10 (future) |

## Phase 3 Status
- Findings identified: [N] total
- Tier 1–6 breakdown: [breakdown]
- Frontier standards mapped: [list of standards violated]
- Evidence collected: [N] test failures, code reviews, design doc mismatches

**Phase 3 Complete. Ready for Phase 4 (Synthesis)?**
```

## Pause Point: **STOP HERE**

---

# PHASE 4: SYNTHESIS & REFLECTION

## Goal
Root-cause cluster findings; synthesize 5–8 improvements leveraging existing L9 infrastructure; order by impact/effort.

## Actions for Codex

### Action 4.1: Root-Cause Analysis & Clustering

Group findings by underlying cause:

```
Root Cause 1: STATE CONSISTENCY FAILURE
├─ Missing PacketEnvelope enforcement in WM
├─ No single source of truth (WM reads Postgres directly)
├─ Cache invalidation race in ingest
├─ Missing state-version reconciliation on startup
└─ Findings: T1.1 (missing await), T2.1 (WM duplicates Memory)

Root Cause 2: INTEGRATION GAPS
├─ SemanticService exists but unused
├─ ResearchMemoryAdapter partially implemented
├─ MCP memory tools not wired to WM reasoning
├─ Graph search not leveraged
└─ Findings: T2.2 (SemanticService unwired), T2.3 (ResearchMemoryAdapter incomplete)

Root Cause 3: ASYNC/SYNC BOUNDARIES
├─ MemorySubstrateService.ingest_packet() is not async
├─ Missing awaits on async calls
├─ No timeout on OpenAI embedding calls
├─ Blocking I/O in event loop
└─ Findings: T1.1, T3.1, T3.2

Root Cause 4: OBSERVABILITY & OPERATIONS
├─ Missing structured logging in Substrate
├─ No tracing of WM state mutations
├─ No SLO monitoring on latency
└─ Findings: T5.1, T5.2, T5.3
```

### Action 4.2: Synthesize Improvements

For each root cause, propose 1–2 improvements:

```
Improvement 1: Enforce PacketEnvelope as Single Source of Truth (SoT)
────────────────────────────────────────────────────────────
Root Cause: State Consistency Failure
Addresses Findings: T1.1, T2.1 (eliminates both state divergence issues)
Impact: State is deterministic and reproducible; enables replay/recovery.
Frontier Standard: NIST AI RMF "Measure" — state consistency verification.

Design:
- All WM state mutations must go through PacketEnvelope.
- WM.fetch_entity() reads from Memory.get_entity() (via PacketEnvelope).
- MemorySubstrateService.ingest_packet() is the single write path.
- WM maintains cache of latest PacketEnvelope version; reconciles on startup.

Files to Modify:
1. worldmodelrepository.py — Remove direct Postgres access; always read via Memory
2. worldmodelruntime.py — Add state-version reconciliation in bootstrap
3. memorysubstrateservice.py — Ensure all writes go through ingest_packet

Leverage Existing Infrastructure:
- PacketEnvelope (already used in MCP) → generalize as WM state envelope
- MemorySubstrateService.ingest_packet() → already exists, just enforce its use
- SubstrateDAG.state_version field → already tracks state versions

Effort: Medium (~50 lines, 3 files, 1–2 day implementation)
Risk: Medium (refactor affects WM core, needs integration tests)
Testing: Re-run testsunittestworld_model.py; add state-replay tests
```

### Action 4.3: Order by Impact × Effort

Create prioritization matrix:

```
**Improvement Priority Matrix** (Impact vs. Effort)

High Impact
     │
     │  ┌─────────────────────────────────────────────┐
     │  │   Improvement 1: PacketEnvelope SoT       │  (High Impact, Medium Effort)
     │  │   → Fix T1.1, T2.1 (state divergence)      │
     │  └─────────────────────────────────────────────┘
     │
     │  ┌─────────────────┐
     │  │ Improvement 4:  │ (Medium Impact, Low Effort)
     │  │ Semantic Search │
     │  │ Integration     │
     │  └─────────────────┘
     │          ┌──────────────────────────┐
     │          │ Improvement 2: Async/Sync Fix │ (Medium Impact, Low Effort)
     │          └──────────────────────────┘
     │
Low  └────────────────────────────────────────────────────────
  Impact      Low Effort              High Effort
              
Top 3 to implement immediately:
1. Improvement 1: PacketEnvelope SoT (high impact, medium effort) → enable others
2. Improvement 2: Async/Sync boundaries fix (medium impact, low effort) → quick win
3. Improvement 4: SemanticService integration (medium impact, low effort) → unlock feature
```

## Phase 4 Output Template

```markdown
# Phase 4: Synthesis & Improvement Roadmap

## 4.1 Root-Cause Clustering

### Cluster 1: STATE CONSISTENCY FAILURE
**Underlying Cause**: WM and Memory maintain separate state; no PacketEnvelope enforcement.
**Findings Addressed**: T1.1 (missing await → stale state), T2.1 (WM duplicates Memory queries)
**Frontier Standard**: NIST AI RMF "Measure" — state consistency verification.
**Impact if Fixed**: Eliminates state divergence issues; enables state replay/recovery.

### Cluster 2: INTEGRATION GAPS
**Underlying Cause**: Advanced features (SemanticService, ResearchMemoryAdapter) exist but are unused.
**Findings Addressed**: T2.2 (SemanticService unwired), T2.3 (ResearchMemoryAdapter incomplete)
**Frontier Standard**: NIST AI RMF "Map" — data pipeline should use best available tools.
**Impact if Fixed**: WM gains semantic search, research workflows, better entity matching.

### Cluster 3: ASYNC/SYNC BOUNDARIES
**Underlying Cause**: Mixing async and blocking I/O; missing awaits; no timeouts.
**Findings Addressed**: T1.1 (missing await), T3.1 (no timeout on semantic search), T3.2 (blocking I/O in event loop)
**Frontier Standard**: NIST AI RMF "Measure" — latency SLO and consistency.
**Impact if Fixed**: Event loop unblocked; predictable latency; improved resilience.

### Cluster 4: OBSERVABILITY & OPERATIONS
**Underlying Cause**: Insufficient logging and tracing in Substrate; no SLO monitoring.
**Findings Addressed**: T5.1 (missing logging), T5.2 (no tracing), T5.3 (no SLO monitoring)
**Frontier Standard**: ISO 42001 "Monitoring & Measurement" — operational visibility.
**Impact if Fixed**: Production debugging, SLO tracking, alerting.

## 4.2 Proposed Improvements (Prioritized)

### Improvement 1: Enforce PacketEnvelope as Single Source of Truth
**Priority**: 🔴 CRITICAL (Addresses root cause #1)
**Root Cause**: State Consistency Failure
**Addresses**: T1.1, T2.1
**Impact**: Eliminates state divergence; enables replay/recovery.
**Frontier Standard**: NIST AI RMF "Measure"

**Design**:
- All WM state mutations go through PacketEnvelope.
- WM.fetch_entity() → Memory.get_entity() (always uses Memory API).
- Remove direct Postgres access from WM.
- WM caches latest PacketEnvelope; reconciles on bootstrap.

**Files Modified**:
1. worldmodelrepository.py — Remove direct Postgres queries
2. worldmodelruntime.py — Add reconciliation in bootstrap()
3. memorysubstrateservice.py — Ensure ingest_packet is single write path

**Leverage**:
- PacketEnvelope (already used in MCP)
- MemorySubstrateService.ingest_packet() (already exists)
- SubstrateDAG.state_version (already tracks versions)

**Effort**: Medium (~50 lines, ~1.5 days)
**Risk**: Medium (affects WM core, needs integration tests)
**Tests**: Re-run unit tests; add state-replay tests
**Second-Order Benefits**: Enables Improvements 2, 3, and enables audit/replay systems.

### Improvement 2: Fix Async/Sync Boundaries & Missing Awaits
**Priority**: 🟠 HIGH (Addresses root cause #3)
**Root Cause**: Async/Sync Boundaries
**Addresses**: T1.1, T3.1, T3.2
**Impact**: Event loop unblocked; predictable latency.
**Frontier Standard**: NIST AI RMF "Measure"

**Changes**:
1. Add missing `await` in worldmodelruntime.py:105
2. Make MemorySubstrateService.ingest_packet() async
3. Add timeout to SemanticService.embed() (500ms default)
4. Await all async calls in cache invalidation

**Effort**: Low (~40 lines, ~0.5 days)
**Risk**: Low (localized changes, good test coverage)
**Tests**: Existing tests should pass; add timeout tests

### Improvement 3: Integrate SemanticService into WM Queries
**Priority**: 🟡 HIGH (Addresses root cause #2)
**Root Cause**: Integration Gaps
**Addresses**: T2.2
**Impact**: WM gains semantic search; better entity matching.
**Frontier Standard**: NIST AI RMF "Map"

**Design**:
- WM.query_reasoning() calls SemanticService.search() after ID lookup.
- Add semantic ranking (re-rank results by embedding similarity).
- Add config toggle for backward-compat.
- Use cached embeddings from Redis if available.

**Effort**: Low (~40 lines, ~0.5 days)
**Risk**: Low (new call path, additive)
**Tests**: Add tests for semantic ranking; verify backward-compat

### Improvement 4: Add State-Version Reconciliation on Startup
**Priority**: 🟡 MEDIUM (Prevents state divergence after restarts)
**Root Cause**: State Consistency Failure
**Addresses**: T1.1 (enables recovery from missing awaits)
**Impact**: Auto-recovery after WM crashes; consistent startup state.

**Design**:
- WM.bootstrap() checks latest PacketEnvelope state version.
- If WM local state is stale, reconciles from Memory.
- Logs reconciliation for audit.

**Effort**: Low (~20 lines, ~0.5 days)
**Risk**: Low (defensive mechanism, no impact if not needed)
**Tests**: Add tests for startup reconciliation

### Improvement 5: Wire ResearchMemoryAdapter into WM Reasoning
**Priority**: 🔵 MEDIUM (Completes integration gap)
**Root Cause**: Integration Gaps
**Addresses**: T2.3
**Impact**: Research workflows integrate with WM; enables knowledge discovery.

**Design**:
- WM.apply_research_task(task) calls ResearchMemoryAdapter.execute(task).
- Results stored in Memory via ingest_packet.
- WM can query research findings via Memory.search().

**Effort**: Medium (~60 lines, ~1.5 days)
**Risk**: Medium (new integration, needs testing with MCP)
**Tests**: Add integration tests with MCP research tools

### Improvement 6: Add Structured Logging & Tracing to MemorySubstrateService
**Priority**: 🟢 MEDIUM (Operational quality)
**Root Cause**: Observability & Operations
**Addresses**: T5.1, T5.2
**Impact**: Production debugging, SLO tracking.

**Design**:
- Structured logs at key points (ingest, search, invalidate).
- Trace WM mutations through Substrate.
- Log latency metrics (OpenAI embedding time, Postgres query time, Neo4j search time).

**Effort**: Low (~30 lines, ~0.5 days)
**Risk**: Low (additive, no behavior change)
**Tests**: Verify logs appear in output; add SLO thresholds

### Improvement 7: Implement WorldModelScheduler for Expensive Operations
**Priority**: 🔵 FUTURE (Post-stabilization)
**Root Cause**: Async/Sync Boundaries (architectural)
**Addresses**: Prevents T3.1 regression as query load grows
**Impact**: WM can offload semantic search, research workflows to background jobs.

**Design**:
- Background job queue (e.g., Celery or similar).
- WM.schedule_task(task) for expensive operations.
- Callback mechanism to update WM state on completion.

**Effort**: High (~200 lines, ~3 days, new subsystem)
**Risk**: High (new architecture, needs redesign)
**Timeline**: Post-Phase 5; prioritize after Improvements 1–6 are stable.

## 4.3 Impact × Effort Prioritization

| Improvement | Impact | Effort | Priority | Addresses | Quick Win? |
|------------|--------|--------|----------|-----------|-----------|
| 1: PacketEnvelope SoT | High | Medium | 🔴 CRITICAL | T1.1, T2.1 | No (enables others) |
| 2: Async/Sync Fix | High | Low | 🟠 HIGH | T1.1, T3.1, T3.2 | **Yes** |
| 3: SemanticService | Medium | Low | 🟡 HIGH | T2.2 | **Yes** |
| 4: State Reconciliation | Medium | Low | 🟡 MEDIUM | T1.1 recovery | **Yes** |
| 5: ResearchMemoryAdapter | Medium | Medium | 🔵 MEDIUM | T2.3 | No |
| 6: Structured Logging | Medium | Low | 🟡 MEDIUM | T5.1, T5.2 | **Yes** |
| 7: Scheduler | Medium | High | 🔵 FUTURE | Architectural | No |

## 4.4 Implementation Roadmap

### Phase 5 (Bug Fixes): ~2 hours
1. **Improvement 2**: Async/Sync Fix (quick win, unblocks event loop)
2. **Improvement 4**: State Reconciliation (defensive, enables Improvement 1)
3. **Improvement 1**: PacketEnvelope SoT (foundational, enables others)

### Phase 6 (Robustness Fixes): ~2 hours
4. **Improvement 3**: SemanticService Integration (feature unlock, quick win)
5. **Improvement 6**: Structured Logging (observability, enables SLO tracking)

### Phase 7 (Recursive Validation): ~1.5 hours
- Re-audit Improvements 1–6
- Verify T1–5 findings addressed
- Identify second-order issues
- Note Improvement 7 as future work

## 4.5 Summary

- **Root-cause clusters identified**: 4 clusters
- **Improvements proposed**: 7 improvements
- **Immediate wins**: Improvements 2, 3, 4, 6 (quick, high-value)
- **Foundational change**: Improvement 1 (medium effort, enables others)
- **Future architecture**: Improvement 7 (post-stabilization)

**Expected impact**: 50% reduction in findings (from ~45 to ~22) after Improvements 1–6.

**Phase 4 Complete. Ready for Phase 5 (Bug Fixes)?**
```

## Pause Point: **STOP HERE**

---

# PHASE 5: BUG & MISALIGNMENT FIXES

## Goal
Generate unified diffs for Improvements 2, 4, and 1 (CRITICAL/HIGH tier fixes). Ensure diffs are minimal, testable, and can be applied independently or in sequence.

## Actions for Codex

### Action 5.1: Improvement 2 (Async/Sync Fixes)

Generate diff:

```diff
--- a/worldmodelruntime.py
+++ b/worldmodelruntime.py
@@ -103,8 +103,8 @@
  async def loop(self):
      while True:
          query = self.state.last_query
-        result = memory_search(query)  # BUG: missing await
+        result = await memory_search(query)  # FIX: add await
          self.state.last_result = result  # now result is data, not coroutine
```

### Action 5.2: Improvement 4 (State Reconciliation)

Generate diff:

```diff
--- a/worldmodelruntime.py
+++ b/worldmodelruntime.py
@@ -45,6 +45,20 @@
  async def bootstrap(self):
      """Initialize WM with memory state."""
      self.kernel.activate()
+     # FIX: Add state-version reconciliation
+     latest_version = await self.memory.get_latest_state_version()
+     if latest_version > self.state.version:
+         logger.info(
+             f"Reconciling WM state: local={self.state.version}, latest={latest_version}"
+         )
+         latest_state = await self.memory.get_state_at_version(latest_version)
+         self.state = latest_state
+         logger.info(
+             f"WM state reconciled to version {latest_version}"
+         )
+     else:
+         logger.debug(f"WM state is current (version {self.state.version})")
```

### Action 5.3: Improvement 1 (PacketEnvelope SoT)

Generate multi-file diff:

```diff
--- a/worldmodelrepository.py
+++ b/worldmodelrepository.py
@@ -78,10 +78,8 @@
  def fetch_entity(self, entity_id: str) -> Entity:
      """Fetch entity by ID."""
-     # BUG: Direct Postgres access, bypasses Memory API
-     result = self.postgres.query(f"SELECT * FROM entities WHERE id = {entity_id}")
-     return Entity.from_db(result)
+     # FIX: Always read through Memory API
+     packet = self.memory.get_entity(entity_id)
+     return packet.entity

--- a/memorysubstrateservice.py
+++ b/memorysubstrateservice.py
@@ -148,7 +148,7 @@
  def ingest_packet(self, packet: PacketEnvelope) -> None:
      """Ingest packet into substrate."""
      # BUG: Not async, but calls async methods
-     # Mutations: 1. Validate packet 2. Store in Postgres 3. Update Neo4j 4. Invalidate Redis
+    # FIX: Make async, await all operations
+    async def ingest_packet_async(self, packet: PacketEnvelope) -> None:
```

## Phase 5 Output Template

```markdown
# Phase 5: Bug & MISALIGNMENT Fixes

## 5.1 Fix: Missing Await in WorldModelRuntime.loop()

**Finding**: T1.1 (BUG)
**File**: worldmodelruntime.py
**Severity**: CRITICAL
**Change**: Add missing `await` on memory_search() call

\`\`\`diff
--- a/worldmodelruntime.py
+++ b/worldmodelruntime.py
@@ -103,8 +103,8 @@
  async def loop(self):
      while True:
          query = self.state.last_query
-        result = memory_search(query)  # BUG: missing await
+        result = await memory_search(query)  # FIX: await added
          self.state.last_result = result
\`\`\`

**Rationale**: Without await, memory_search() returns a coroutine object, not the actual result. WM state is corrupted.
**Test Impact**: testsunittestworld_model.py:234 now passes.
**Backward Compat**: Yes (same result, just fixed timing).

---

## 5.2 Fix: Async/Sync Mismatch in MemorySubstrateService.ingest_packet()

**Finding**: T3.2 (BUG)
**File**: memorysubstrateservice.py
**Severity**: HIGH
**Change**: Convert ingest_packet() to async; await all async operations

\`\`\`diff
--- a/memorysubstrateservice.py
+++ b/memorysubstrateservice.py
@@ -148,8 +148,9 @@
  def ingest_packet(self, packet: PacketEnvelope) -> None:
      """Ingest packet into substrate."""
-     # Blocking I/O in event loop
-     dag_result = self.dag.add_edge(packet.source, packet.target)  # async but not awaited
+    async def ingest_packet_async(self, packet: PacketEnvelope) -> None:
+        """Ingest packet into substrate (async)."""
+        dag_result = await self.dag.add_edge(packet.source, packet.target)
      postgres_result = self.postgres.insert(packet.entity_state)
-     redis_invalidate = self.redis.invalidate(cache_keys)  # async but not awaited
+        await self.redis.invalidate(cache_keys)
\`\`\`

**Rationale**: Mixing sync and async causes race conditions and blocks event loop.
**Test Impact**: Integration tests for cache invalidation now pass.
**Backward Compat**: Rename old method to `ingest_packet_sync()`; wire async method as default.

---

## 5.3 Fix: WM Duplicates Memory Substrate Responsibilities

**Finding**: T2.1 (MISALIGNMENT)
**Files**: worldmodelrepository.py, memorysubstrateservice.py
**Severity**: HIGH
**Change**: Remove direct Postgres access from WM; always read through Memory API

\`\`\`diff
--- a/worldmodelrepository.py
+++ b/worldmodelrepository.py
@@ -78,10 +78,10 @@
  def fetch_entity(self, entity_id: str) -> Entity:
      """Fetch entity by ID."""
-     # BUG: Direct Postgres access bypasses Memory API
-     result = self.postgres.query(f"SELECT * FROM entities WHERE id = {entity_id}")
-     return Entity.from_db(result)
+     # FIX: Always read through Memory API (ensures consistency)
+     packet = self.memory.get_entity(entity_id)
+     return packet.entity
\`\`\`

\`\`\`diff
--- a/worldmodelrepository.py
+++ b/worldmodelrepository.py
@@ -95,8 +95,11 @@
  def store_entity(self, entity: Entity) -> None:
      """Store entity."""
-     # Direct Postgres write (bypasses Memory SoT)
-     self.postgres.insert(entity.to_db_row())
+     # FIX: Write through Memory API (enforces SoT pattern)
+     packet = PacketEnvelope(
+         entity=entity,
+         version=self.state.current_version + 1
+     )
+     self.memory.ingest_packet_async(packet)
\`\`\`

**Rationale**: WM and Memory must use single source of truth. All entity I/O goes through Memory API.
**Test Impact**: All worldmodelrepository tests must be updated to mock Memory API (not Postgres).
**Backward Compat**: Internal change; API unchanged.

---

## 5.4 Fix: Missing State-Version Reconciliation

**Finding**: T1.1 (Recovery mechanism)
**File**: worldmodelruntime.py
**Severity**: HIGH
**Change**: Add reconciliation in bootstrap()

\`\`\`diff
--- a/worldmodelruntime.py
+++ b/worldmodelruntime.py
@@ -45,6 +45,20 @@
  async def bootstrap(self):
      """Initialize WM with memory state."""
      self.kernel.activate()
+     # FIX: Reconcile WM state with Memory Substrate
+     latest_version = await self.memory.get_latest_state_version()
+     if latest_version > self.state.version:
+         logger.info(
+             f"Reconciling WM state: local={self.state.version}, latest={latest_version}"
+         )
+         latest_state = await self.memory.get_state_at_version(latest_version)
+         self.state = latest_state
+         logger.info(
+             f"WM state reconciled to version {latest_version}"
+         )
+     else:
+         logger.debug(f"WM state is current (version {self.state.version})")
\`\`\`

**Rationale**: If WM crashes and restarts, it should recover latest state from Memory automatically.
**Test Impact**: Add test_bootstrap_reconciliation tests.
**Backward Compat**: No change to public API; internal state management only.

---

## 5.5 Summary

| Fix | File:Line | Severity | Lines Changed | Tests Affected | Complexity |
|-----|-----------|----------|---|---|---|
| Missing await | wmr.py:105 | CRITICAL | 1 | test_query_result | Low |
| Async/Sync mismatch | mss.py:148 | HIGH | ~10 | integration_tests | Medium |
| WM duplicates Memory | wmrep.py:78–95 | HIGH | ~15 | repo_tests | Medium |
| State reconciliation | wmr.py:45–60 | HIGH | ~15 | bootstrap_tests | Low |
| **Total** | 4 files | | ~41 lines | ~8 tests | Medium |

## 5.6 Application Order

```
1. Apply Fix 5.1 (Missing await) → unblock event loop
2. Apply Fix 5.4 (State reconciliation) → enable recovery
3. Apply Fix 5.2 (Async/Sync) → fix ingest_packet
4. Apply Fix 5.3 (WM SoT) → enforce single source of truth

(Can apply 5.1–5.4 in any order; 5.3 depends on 5.2 being stable)
```

**Phase 5 Complete. Fixes applied. Ready for Phase 6 (Robustness)?**
```

## Pause Point: **STOP HERE**

---

# PHASE 6: ROBUSTNESS & SECOND-PASS FIXES

## Goal
Generate diffs for Improvements 3 and 6 (integrations, observability). Add logging, error handling, timeouts, and backward-compatibility toggles.

## Actions for Codex

### Action 6.1: Improvement 3 (SemanticService Integration)

```diff
--- a/worldmodelservice.py
+++ b/worldmodelservice.py
@@ -102,13 +102,35 @@
  def query_reasoning(self, query: str) -> List[Entity]:
      """Query world model reasoning."""
      # First pass: ID-based lookup
      id_results = self.repository.fetch_entities_by_id(query)
      
+     # Second pass: Semantic search (if enabled and faster)
+     if self.config.semantic_search_enabled and len(id_results) < 10:
+         try:
+             logger.debug(f"Performing semantic search for: {query}")
+             semantic_results = await self.semantic_service.search(
+                 query,
+                 timeout=self.config.semantic_search_timeout_ms / 1000
+             )
+             # Merge and re-rank by similarity
+             combined = self._merge_and_rank_results(id_results, semantic_results)
+             logger.info(
+                 f"Query '{query}': {len(id_results)} ID hits, "
+                 f"{len(semantic_results)} semantic hits → {len(combined)} merged"
+             )
+             return combined
+         except asyncio.TimeoutError:
+             logger.warning(
+                 f"Semantic search timed out for query '{query}'; "
+                 f"falling back to ID-based results"
+             )
+             return id_results
+         except Exception as e:
+             logger.error(f"Semantic search error: {e}; using ID-based results")
+             return id_results
      
      return id_results
```

### Action 6.2: Improvement 6 (Structured Logging & Observability)

```diff
--- a/memorysubstrateservice.py
+++ b/memorysubstrateservice.py
@@ -148,6 +148,10 @@
  async def ingest_packet_async(self, packet: PacketEnvelope) -> None:
      """Ingest packet into substrate."""
+     start_time = time.time()
+     logger.info(
+         f"Ingesting packet: id={packet.id}, version={packet.version}, "
+         f"entity_type={packet.entity.type}"
+     )
      
      try:
          # Validate
          self._validate_packet(packet)
@@ -156,17 +160,45 @@
          # Neo4j update
          dag_result = await self.dag.add_edge(packet.source, packet.target)
          logger.debug(f"DAG updated: {dag_result}")
          
+         # Postgres insert with timing
+         pg_start = time.time()
          postgres_result = await self.postgres.insert_async(packet.entity_state)
+         pg_duration = time.time() - pg_start
          logger.debug(f"Postgres insert: {postgres_result}, duration={pg_duration:.3f}s")
+         
+         if pg_duration > self.config.postgres_slow_query_threshold:
+             logger.warning(
+                 f"Slow Postgres insert: {pg_duration:.3f}s > "
+                 f"{self.config.postgres_slow_query_threshold}s; "
+                 f"entity_id={packet.entity.id}"
+             )
          
          # Redis invalidate
          redis_start = time.time()
          await self.redis.invalidate(self._compute_cache_keys(packet))
          redis_duration = time.time() - redis_start
          logger.debug(f"Redis invalidate: duration={redis_duration:.3f}s")
+     
      
+         total_duration = time.time() - start_time
+         logger.info(
+             f"Packet ingested successfully: id={packet.id}, "
+             f"total_duration={total_duration:.3f}s, "
+             f"pg={pg_duration:.3f}s, redis={redis_duration:.3f}s"
+         )
+         
+         # Emit metrics (Prometheus, DataDog, etc.)
+         self.metrics.observe(
+             "memory.ingest_packet.duration_seconds",
+             total_duration,
+             tags={"entity_type": packet.entity.type}
+         )
+     
      except PacketValidationError as e:
-         logger.error(f"Packet validation failed: {e}")
+         logger.error(
+             f"Packet validation failed: {e}; packet_id={packet.id}; "
+             f"attempting recovery..."
+         )
          raise
      except Exception as e:
-         logger.error(f"Ingest failed: {e}")
+         logger.error(
+             f"Ingest failed: {e}; packet_id={packet.id}; "
+             f"duration={time.time() - start_time:.3f}s",
+             exc_info=True
+         )
          raise
```

## Phase 6 Output Template

```markdown
# Phase 6: Robustness & Second-Pass Fixes

## 6.1 Integration: SemanticService into WM Query Path

**Finding**: T2.2 (UNWIRED)
**File**: worldmodelservice.py
**Change**: Add semantic search as second pass with fallback

\`\`\`diff
[diff shown above]
\`\`\`

**Design**:
- If ID-based lookup returns fewer than 10 results, run semantic search in parallel.
- Re-rank combined results by embedding similarity.
- Timeout on semantic search (default 500ms); fall back to ID results.
- Config toggle for backward-compat.

**Robustness**:
- Timeout prevents event loop blocking.
- Error handling for semantic service failures.
- Logging tracks performance of both strategies.
- Metrics emitted for SLO tracking.

**Test Impact**:
- Add test_query_with_semantic_search
- Add test_semantic_search_timeout_fallback
- Add test_semantic_search_disabled_backward_compat

**Backward Compat**: 
- Config `semantic_search_enabled=false` disables new behavior.
- Default: enabled (with timeout fallback).

---

## 6.2 Observability: Structured Logging in MemorySubstrateService

**Finding**: T5.1, T5.2 (Missing logging & tracing)
**File**: memorysubstrateservice.py
**Change**: Add structured logging and latency metrics at key points

\`\`\`diff
[diff shown above]
\`\`\`

**Logging Strategy**:
- INFO: Packet received, total duration (operational visibility)
- DEBUG: Sub-operation durations (Postgres, Redis, Neo4j)
- WARNING: Slow queries (exceeds threshold)
- ERROR: Validation/ingest failures with stack trace

**Metrics**:
- memory.ingest_packet.duration_seconds (histogram)
  - Breakdown by entity_type
  - Percentiles: p50, p95, p99
  - Useful for SLO tracking and capacity planning

**Thresholds** (configurable):
- postgres_slow_query_threshold (default: 100ms)
- redis_slow_invalidate_threshold (default: 50ms)
- semantic_search_timeout_ms (default: 500ms)

**Test Impact**:
- Add test_slow_postgres_query_warning
- Add test_metrics_emitted_on_ingest
- Add test_error_logging_includes_stacktrace

**Backward Compat**: 
- Additive (no behavior change).
- Logging can be configured to INFO level to reduce noise in prod.

---

## 6.3 Additional Robustness: Error Recovery in Cache Invalidation

**Finding**: T3.2 (Cache race condition)
**File**: memorysubstrateservice.py
**Change**: Add retry logic and circuit breaker for Redis invalidation

\`\`\`diff
--- a/memorysubstrateservice.py
+++ b/memorysubstrateservice.py
@@ -185,8 +185,25 @@
  async def _invalidate_cache(self, keys: List[str]) -> None:
      """Invalidate Redis cache with retry logic."""
-     await self.redis.invalidate(keys)
+     max_retries = 3
+     retry_delay = 0.1  # seconds
+     
+     for attempt in range(max_retries):
+         try:
+             await self.redis.invalidate(keys)
+             logger.debug(f"Cache invalidated: {len(keys)} keys")
+             return
+         except redis.ConnectionError as e:
+             if attempt < max_retries - 1:
+                 logger.warning(
+                     f"Redis invalidation attempt {attempt + 1} failed; "
+                     f"retrying in {retry_delay}s: {e}"
+                 )
+                 await asyncio.sleep(retry_delay)
+                 retry_delay *= 2  # Exponential backoff
+             else:
+                 logger.error(f"Cache invalidation failed after {max_retries} attempts")
+                 raise
\`\`\`

**Rationale**: Cache misses are better than application failures. Retry with backoff ensures eventual consistency.

---

## 6.4 Additional Robustness: Timeout Protection on Semantic Search

**Finding**: T3.1 (No timeout)
**File**: semanticservice.py
**Change**: Add timeout with graceful fallback

\`\`\`diff
--- a/semanticservice.py
+++ b/semanticservice.py
@@ -89,12 +89,25 @@
  async def search(self, query: str, timeout: float = 0.5) -> List[Entity]:
      """Search entities by semantic similarity."""
      try:
+         start_time = time.time()
          embedding = await asyncio.wait_for(
              self._embed_query(query),
              timeout=timeout
          )
+         embed_duration = time.time() - start_time
+         logger.debug(f"Query embedding: {embed_duration:.3f}s")
+         
          results = await self._search_similar(embedding)
          return results
      except asyncio.TimeoutError:
-         logger.error(f"Embedding timeout for query: {query}")
+         logger.warning(
+             f"Semantic embedding timed out after {timeout}s; "
+             f"query: '{query[:50]}...'"
+         )
          return []  # Return empty list; caller will fall back to ID-based search
+     except Exception as e:
+         logger.error(
+             f"Semantic search error: {e}; falling back to ID-based search",
+             exc_info=True
+         )
+         return []
\`\`\`

**Rationale**: Never let external service (OpenAI) block WM event loop.

---

## 6.5 Configuration & Feature Flags

Add to `config.py`:

```python
class MemoryConfig:
    # Semantic search
    semantic_search_enabled: bool = True
    semantic_search_timeout_ms: int = 500  # milliseconds
    
    # Observability
    postgres_slow_query_threshold: float = 0.1  # seconds
    redis_slow_invalidate_threshold: float = 0.05
    
    # Resilience
    cache_invalidation_max_retries: int = 3
    cache_invalidation_initial_retry_delay: float = 0.1
```

Add to `feature_flags.txt`:

```yaml
FEATURE_SEMANTIC_SEARCH_IN_WM:
  enabled: true
  description: "Enable semantic search integration in WM query path"
  rollout_percentage: 100
  rollback_url: "/api/admin/features/semantic-search/rollback"
```

---

## 6.6 Testing Strategy for Phase 6

### Unit Tests
```python
# tests/unit/test_semantic_integration.py
def test_query_with_semantic_search_enabled():
    # Semantic search runs if ID results < 10
    assert ...

def test_query_without_semantic_search_disabled():
    # If config.semantic_search_enabled=False, skip semantic
    assert ...

def test_semantic_search_timeout_fallback():
    # If semantic search times out, fall back to ID results
    assert ...

# tests/unit/test_memory_logging.py
def test_slow_query_warning_logged():
    # If Postgres insert > threshold, warning logged
    assert "Slow Postgres insert" in caplog.text

def test_metrics_emitted_on_ingest():
    # Metrics emitted for duration, breakdown by entity_type
    assert metrics_mock.observe.called

# tests/unit/test_cache_invalidation_retry.py
def test_cache_invalidation_retries_on_redis_error():
    # Redis error triggers retry with backoff
    assert ...

def test_cache_invalidation_circuit_breaker():
    # After max retries, raise exception (to be handled upstream)
    assert ...
```

### Integration Tests
```python
# tests/integration/test_wm_memory_integration.py
def test_semantic_search_improves_query_results():
    # End-to-end: query returns more relevant results with semantic search
    assert len(results_with_semantic) > len(results_without_semantic)

def test_slow_postgres_query_triggers_warning_metric():
    # Slow ingest triggers warning log and slow-query metric
    assert ...
```

---

## 6.7 Summary of Phase 6 Changes

| Improvement | File | Type | Lines Added | Test Cases | Config Flags |
|-------------|------|------|---|---|---|
| Semantic integration | wmsvc.py | Feature + Robustness | ~35 | 4 | semantic_search_enabled, timeout |
| Logging + metrics | mss.py | Observability | ~40 | 5 | slow_query_threshold, metrics_endpoint |
| Cache invalidation retry | mss.py | Resilience | ~20 | 3 | max_retries, retry_delay |
| Semantic search timeout | ss.py | Robustness | ~15 | 2 | timeout_ms |
| **Total** | 3 files | | ~110 lines | ~14 tests | ~8 config options |

## 6.8 Quality Checklist

- [ ] All error paths have logging
- [ ] All async operations have timeouts
- [ ] All metrics are labeled and queryable
- [ ] Config toggles allow graceful feature rollout
- [ ] Tests cover both success and failure paths
- [ ] Backward-compat maintained (disable new features if needed)
- [ ] No blocking I/O in event loop
- [ ] Structured logging (JSON-compatible)

**Phase 6 Complete. Robustness enhancements applied. Ready for Phase 7 (Recursive Validation)?**
```

## Pause Point: **STOP HERE**

---

# PHASE 7: RECURSIVE VALIDATION & SECOND-ORDER FINDINGS

## Goal
Re-audit the L9 repo after Phases 5–6 fixes to verify all T1–T3 findings are addressed, identify regressions, and surface second-order issues.

## Actions for Codex

### Action 7.1: Re-scan for T1–T3 Fixes

Repeat Phases 1–3 on **modified code only** (files touched in Phases 5–6):
- worldmodelruntime.py (missing await fix)
- memorysubstrateservice.py (async/sync, logging, cache retry)
- worldmodelrepository.py (WM SoT enforcement)
- worldmodelservice.py (semantic integration)
- semanticservice.py (timeout protection)

Check:
1. **All T1 findings resolved**: Use git diff to verify fixes applied correctly.
2. **All T2 findings resolved**: Check integration points are wired.
3. **No new T1/T2 introduced**: Run static analysis on modified code.

### Action 7.2: Run Test Suite

Execute:
```bash
pytest tests/ -v --cov=l9 --cov-report=html
```

Verify:
- All existing tests pass (no regressions).
- New tests (from Phase 6) pass.
- Coverage increased or maintained.

### Action 7.3: Second-Order Findings

Scan for issues that emerged from fixes:

```
Second-Order Finding 1: New config options not documented
├─ Files: config.py, feature_flags.txt
├─ Issue: Added ~8 new config options; no README documentation
└─ Recommendation: Add config reference guide

Second-Order Finding 2: Metrics not aggregated
├─ Files: memorysubstrateservice.py
├─ Issue: Metrics emitted but no aggregation/dashboard setup
└─ Recommendation: Provision Prometheus/Grafana dashboard

Second-Order Finding 3: Semantic search latency unchecked
├─ Files: worldmodelservice.py
├─ Issue: Timeout added but no SLO defined or monitored
└─ Recommendation: Define SLO (p95 < 500ms) and alert threshold

Second-Order Finding 4: Feature flag rollout strategy
├─ Files: feature_flags.txt
├─ Issue: semantic_search_enabled=true at 100%; no gradual rollout
└─ Recommendation: Start at 10%, gradually increase to 100% over 1 week
```

### Action 7.4: Identify Regressions

Compare Phase 3 findings with current state:

```
Tier 1 Findings (Phase 3 → Phase 7):
┌─────────────────────────────────────┬──────┬──────────┐
│ Finding                             │ Ph3  │ Ph7      │
├─────────────────────────────────────┼──────┼──────────┤
│ T1.1: Missing await in loop()       │ ❌   │ ✅ FIXED │
│ (No new T1 introduced)              │      │ ✅       │
└─────────────────────────────────────┴──────┴──────────┘

Tier 2 Findings (Phase 3 → Phase 7):
┌─────────────────────────────────────┬──────┬──────────┐
│ Finding                             │ Ph3  │ Ph7      │
├─────────────────────────────────────┼──────┼──────────┤
│ T2.1: WM duplicates Memory          │ ❌   │ ✅ FIXED │
│ T2.2: SemanticService unwired       │ ❌   │ ✅ FIXED │
│ T2.3: ResearchMemoryAdapter         │ ⚠️   │ ⚠️ DEFERRED to Ph6+1 |
│ (No new T2 introduced)              │      │ ✅       │
└─────────────────────────────────────┴──────┴──────────┘

Tier 3 Findings (Phase 3 → Phase 7):
┌─────────────────────────────────────┬──────┬──────────┐
│ Finding                             │ Ph3  │ Ph7      │
├─────────────────────────────────────┼──────┼──────────┤
│ T3.1: No timeout on semantic search │ ❌   │ ✅ FIXED │
│ T3.2: Cache race in ingest          │ ❌   │ ✅ FIXED │
│ (No new T3 introduced)              │      │ ✅       │
└─────────────────────────────────────┴──────┴──────────┘

Overall Reduction: 45 findings → 22 findings (51% reduction)
```

## Phase 7 Output Template

```markdown
# Phase 7: Recursive Validation & Second-Order Findings

## 7.1 Tier 1–3 Re-audit Results

### Tier 1 (CRITICAL): Phase 3 → Phase 7

| Finding | Phase 3 Status | Phase 7 Status | Evidence |
|---------|---|---|---|
| T1.1: Missing await in loop() | ❌ PRESENT | ✅ FIXED | Git diff shows await added; test passes |
| **(No new T1 introduced)** | — | ✅ VERIFIED | Static analysis, code review, tests pass |

**Summary**: T1 findings resolved. No regressions. ✅

### Tier 2 (HIGH): Phase 3 → Phase 7

| Finding | Phase 3 Status | Phase 7 Status | Evidence |
|---------|---|---|---|
| T2.1: WM duplicates Memory | ❌ PRESENT | ✅ FIXED | WM now reads via Memory API; diff verified |
| T2.2: SemanticService unwired | ❌ PRESENT | ✅ FIXED | SemanticService integrated; tests pass |
| T2.3: ResearchMemoryAdapter | ⚠️ INCOMPLETE | ⚠️ DEFERRED | Not addressed in Ph5–6; scheduled for Ph6+1 |
| **(No new T2 introduced)** | — | ✅ VERIFIED | Code review, integration tests pass |

**Summary**: 2/3 HIGH findings resolved; 1 deferred. No regressions. ✅

### Tier 3 (MEDIUM): Phase 3 → Phase 7

| Finding | Phase 3 Status | Phase 7 Status | Evidence |
|---------|---|---|---|
| T3.1: No timeout on semantic search | ❌ PRESENT | ✅ FIXED | Timeout added; test_timeout_fallback passes |
| T3.2: Cache race in ingest | ❌ PRESENT | ✅ FIXED | Retry logic + Redis invalidation fixed; tests pass |
| T3.3–T3.N: Other MEDIUM findings | [various] | [status] | [evidence] |
| **(No new T3 introduced)** | — | ✅ VERIFIED | Static analysis, unit tests, integration tests pass |

**Summary**: T3 findings resolved. No regressions. ✅

### Overall Tier Reduction

```
Phase 3 Findings:       Phase 7 Findings:
├─ T1: 8                ├─ T1: 0 ✅
├─ T2: 15               ├─ T2: 1 (deferred) ⚠️
├─ T3: 22               ├─ T3: 0 ✅
├─ T4: 10               ├─ T4: 10 (no fixes attempted)
├─ T5: 8                ├─ T5: 3 (observability added, but not all gaps filled)
└─ T6: 2                └─ T6: 2 (future, no change expected)

TOTAL: 45 → 16 findings (64% reduction)
```

---

## 7.2 Test Suite Results

### Unit Tests
```
tests/unit/
├── test_worldmodelruntime.py
│   ├── test_loop_with_await ✅ PASS (was FAIL)
│   ├── test_bootstrap_reconciliation ✅ PASS (new)
│   └── [6 other tests] ✅ ALL PASS
├── test_memorysubstrateservice.py
│   ├── test_ingest_packet_async ✅ PASS (was FAIL)
│   ├── test_cache_invalidation_retry ✅ PASS (new)
│   ├── test_slow_query_warning ✅ PASS (new)
│   ├── test_metrics_emitted ✅ PASS (new)
│   └── [8 other tests] ✅ ALL PASS
├── test_worldmodelservice.py
│   ├── test_query_with_semantic_search ✅ PASS (new)
│   ├── test_semantic_search_timeout ✅ PASS (new)
│   ├── test_semantic_search_disabled ✅ PASS (new)
│   └── [10 other tests] ✅ ALL PASS
├── test_semanticservice.py
│   ├── test_search_with_timeout ✅ PASS (new)
│   └── [5 other tests] ✅ ALL PASS
└── [Other unit tests] ✅ ALL PASS (no changes)

Unit Test Results:
───────────────────────────────────────
Total:    156 tests
Passed:   156 ✅
Failed:   0
Skipped:  0
Coverage: 87% (↑ from 82%)
───────────────────────────────────────
```

### Integration Tests
```
tests/integration/
├── test_wm_memory_integration.py
│   ├── test_entity_persist_and_retrieve ✅ PASS
│   ├── test_state_divergence_recovery ✅ PASS (new)
│   ├── test_semantic_search_improves_results ✅ PASS (new)
│   └── [8 other tests] ✅ ALL PASS
├── test_mcp_memory_integration.py
│   ├── test_save_memory_tool ✅ PASS
│   └── [6 other tests] ✅ ALL PASS
└── test_api_endpoints.py
   ├── test_query_endpoint ✅ PASS
   └── [12 other tests] ✅ ALL PASS

Integration Test Results:
───────────────────────────────────────
Total:    45 tests
Passed:   45 ✅
Failed:   0
Skipped:  0
Duration: 18.2s (↓ from 22.1s; async fixes improved performance)
───────────────────────────────────────
```

### Coverage Report
```
File                         Coverage  Change
─────────────────────────────────────────────
worldmodelruntime.py         95%       ↑ 10%
memorysubstrateservice.py    92%       ↑ 8%
worldmodelservice.py         89%       ↑ 6%
semanticservice.py           88%       ↑ 5%
worldmodelrepository.py      91%       ↑ 9%
─────────────────────────────────────────────
OVERALL                      87%       ↑ 5%
```

---

## 7.3 Second-Order Findings

### S1: Configuration Documentation Gap

**Finding**: New config options not documented for operators.
**Files**: config.py, feature_flags.txt
**Severity**: T5 (OPERATIONAL)
**Details**:
- Added 8 new config options (semantic_search_enabled, timeouts, thresholds)
- No config reference guide for operators
- Feature flags documented in code but not in runbooks

**Recommendation**:
1. Create CONFIG_REFERENCE.md with all options, defaults, and impact
2. Add feature flag description to deployment runbook
3. Link from main README

**Effort**: Low (~1 hour)

### S2: Metrics Not Aggregated

**Finding**: Metrics emitted but no dashboard/aggregation.
**Files**: memorysubstrateservice.py
**Severity**: T5 (OPERATIONAL)
**Details**:
- Metrics emitted via self.metrics.observe()
- No Prometheus scrape config
- No Grafana dashboard provisioned

**Recommendation**:
1. Provision Prometheus scrape endpoint for L9 service
2. Create Grafana dashboard for ingest latency (by entity_type, quantiles)
3. Document SLO thresholds in dashboard

**Effort**: Medium (~2–3 hours; requires infra setup)

### S3: Semantic Search SLO Undefined

**Finding**: Timeout added but no SLO target or alerting.
**Files**: worldmodelservice.py
**Severity**: T5 (OPERATIONAL)
**Details**:
- Timeout set to 500ms (default, configurable)
- No SLO published (p95 target)
- No alert if p95 > 500ms

**Recommendation**:
1. Define SLO: p95(semantic_search_latency) < 500ms
2. Configure alert: if p95 > 600ms for 5min, page on-call
3. Document in SLA documentation

**Effort**: Low (~1–2 hours; requires monitoring setup)

### S4: Feature Flag Rollout Strategy Not Defined

**Finding**: semantic_search_enabled rolled out at 100% immediately.
**Files**: feature_flags.txt
**Severity**: T5 (OPERATIONAL)
**Details**:
- No gradual rollout strategy
- No canary or shadow mode
- Risk: If semantic search causes issues, affects all users

**Recommendation**:
1. Start at 10% rollout (feature_flags.rollout_percentage)
2. Monitor error rates, latency, user feedback for 1 day
3. Gradually increase to 25%, 50%, 100% over 1 week
4. Keep manual rollback available

**Timeline**: 1 week (hands-off monitoring)

### S5: ResearchMemoryAdapter Integration Deferred

**Finding**: T2.3 not addressed in Ph5–6.
**Files**: N/A (incomplete component)
**Severity**: T2 (HIGH, but deferred)
**Details**:
- ResearchMemoryAdapter exists but is not called from WM
- Improvement 5 (from Phase 4) not implemented
- Should be next priority after Ph7 stabilization

**Recommendation**:
1. Schedule Improvement 5 for next sprint
2. Re-run audit after implementing Improvement 5
3. Track as "Ph6+1" in roadmap

**Timeline**: Next sprint (post-stabilization)

---

## 7.4 Regression Analysis

### Test Coverage Regression Check

```
Phase 3 Test Gaps:
├─ No timeout tests for semantic search → ✅ ADDED (test_semantic_search_timeout)
├─ No async/await tests → ✅ ADDED (test_loop_with_await)
├─ No integration tests for state divergence → ✅ ADDED (test_state_divergence_recovery)
└─ No metrics tests → ✅ ADDED (test_metrics_emitted)

Phase 5–6 Introduced New Code Paths:
├─ Retry logic in cache invalidation → ✅ TESTED (test_cache_invalidation_retry)
├─ Semantic search fallback → ✅ TESTED (test_semantic_search_timeout_fallback)
├─ Structured logging → ✅ TESTED (test_slow_query_warning_logged)
└─ Feature flag toggle → ✅ TESTED (test_semantic_search_disabled)

No Regressions Detected: ✅ ALL TESTS PASS
```

### Performance Regression Check

```
Metric                           Phase 3      Phase 7      Change
────────────────────────────────────────────────────────────────
Test execution time:             45s          42.2s        ↓ 6% (async fixes)
Memory usage (startup):          256MB        258MB        ↑ 1% (logging overhead)
Ingest latency (p95):            120ms        115ms        ↓ 4% (optimizations)
Query latency (p95):             85ms → 140ms¹ 140ms       = (semantic search opt-in)

¹ Phase 3: ID-only queries → Phase 7: ID + semantic fallback option
  Backward-compat: Can disable semantic search → revert to Phase 3 latency
```

**No critical performance regressions. ✅**

---

## 7.5 Audit Summary

### Fixes Applied
- ✅ 4 diffs applied successfully (Phases 5–6)
- ✅ 156 unit tests passing (↑ from Phase 3)
- ✅ 45 integration tests passing (↑ from Phase 3)
- ✅ Code coverage 87% (↑ from 82%)

### Findings Reduced
- Phase 3: 45 findings (8 T1, 15 T2, 22 T3, ...)
- Phase 7: 16 findings (0 T1, 1 T2 deferred, 0 T3, ...)
- **Reduction: 64% (29 findings resolved)**

### Second-Order Findings Identified
- S1: Config documentation gap (T5, low effort)
- S2: Metrics aggregation gap (T5, medium effort)
- S3: SLO not defined (T5, low effort)
- S4: Feature rollout not planned (T5, process task)
- S5: ResearchMemoryAdapter deferred (T2, next sprint)

### Quality Assessment

| Dimension | Phase 3 State | Phase 7 State | Verdict |
|-----------|---|---|---|
| Correctness | ❌ Multiple T1 bugs | ✅ All T1 fixed | Improved |
| Integration | ⚠️ Gaps (unwired features) | ✅ SemanticService wired | Improved |
| Robustness | ⚠️ No timeouts, limited logging | ✅ Timeouts, structured logging | Improved |
| Performance | ✅ Baseline | ✅ Improved 4–6% | Stable |
| Test Coverage | ⚠️ 82% | ✅ 87% | Improved |
| Operability | ⚠️ Missing observability | ✅ Structured logging, metrics | Improved |
| **Overall** | **⚠️ Needs fixes** | **✅ Production-ready** | **APPROVED** |

---

## 7.6 Recommendations for Next Steps

### Immediate (Do Now)
1. ✅ Apply Phases 5–6 diffs to production
2. ✅ Deploy with semantic_search feature flag at 10%
3. ✅ Monitor error rates, latency, user feedback for 24h
4. 📋 Address S1 (config documentation) before Phase 6+1

### Short-term (1–2 weeks)
5. 📋 Gradually roll out semantic search to 100% (per S4 strategy)
6. 📋 Set up Prometheus/Grafana dashboard (S2)
7. 📋 Define and publish SLO for semantic search (S3)
8. 📋 Plan Improvement 5 (ResearchMemoryAdapter, S5) for next sprint

### Medium-term (1 month)
9. 🎯 Implement Improvement 5 (ResearchMemoryAdapter integration)
10. 🎯 Re-run audit post-Improvement-5 (check for regressions)
11. 🎯 Consider Improvement 7 (WorldModelScheduler) if query load increases

### Future (Post-stabilization)
12. 🔄 Run audit quarterly to catch drift
13. 🔄 Use audit findings to guide feature prioritization

---

## 7.7 Conclusion

**L9 Audit Complete: PASSED** ✅

All critical (T1) and high (T2) findings resolved. System is production-ready with second-order operational improvements identified. Recommended feature flag rollout and monitoring strategy in place. Next audit in Q2 (post-stabilization).

**Phase 7 Complete. Audit Cycle Closed. Ready for Production Deployment?**

---

## Appendix: Audit Trail & Evidence

### Files Modified (Phases 5–6)
```
worldmodelruntime.py          (48 lines added/modified)
memorysubstrateservice.py     (65 lines added/modified)
worldmodelrepository.py       (15 lines modified)
worldmodelservice.py          (30 lines added)
semanticservice.py            (20 lines added)
config.py                     (8 new config options)
feature_flags.txt             (1 new flag)
tests/unit/                   (14 new test functions)
tests/integration/            (3 new test functions)
```

### Git Log (for audit trail)
```
commit <hash5> | Phase 5: Fix T1.1 missing await in WorldModelRuntime.loop()
commit <hash5> | Phase 5: Fix T3.2 async/sync mismatch in MemorySubstrateService
commit <hash5> | Phase 5: Fix T2.1 WM duplicates Memory queries
commit <hash5> | Phase 5: Add state-version reconciliation for T1.1 recovery
commit <hash6> | Phase 6: Integrate SemanticService into WM queries (T2.2)
commit <hash6> | Phase 6: Add structured logging and metrics to MemorySubstrateService
commit <hash6> | Phase 6: Add timeout and retry resilience for cache invalidation
commit <hash6> | Phase 7: Re-audit and validate all fixes
```

### Quality Gate Sign-Off

```
Auditor: Codex (L9 Systems Architect)
Date: [YYYY-MM-DD]
Status: ✅ APPROVED FOR PRODUCTION

Checklist:
- [x] All T1 findings resolved
- [x] All T2 findings resolved (except deferred T2.3)
- [x] All T3 findings resolved
- [x] 100% of unit tests passing
- [x] 100% of integration tests passing
- [x] Code coverage >= 85%
- [x] No performance regressions
- [x] Feature flags configured for safe rollout
- [x] Second-order findings documented
- [x] Rollback plan in place

Signature: [Codex]
Authorization: [Igor, if required for production deployment]
```

**END OF PHASE 7**
```

## Pause Point: **AUDIT COMPLETE** ✅

---

## HOW TO USE THIS SUPERPROMPT

**For users executing the audit:**

1. **Save all 3 documents**:
   - CODEX-STAGED-AUDIT-SUPERPROMPT.md (master spec)
   - CODEX-PHASE-0-KICKOFF.md (execution runbook)
   - CODEX-AUDIT-INTEGRATION-GUIDE.md (workflow guide)

2. **Invoke Codex with Phase 0**:
   ```
   You are Codex, operating as an L9 senior systems architect.
   
   Execute PHASE 0 of the CODEX Staged Audit using the specification
   in CODEX-STAGED-AUDIT-SUPERPROMPT.md and the execution pattern
   in CODEX-PHASE-0-KICKOFF.md.
   
   Follow the Phase 0 template. Output the Configuration Inventory.
   STOP and wait for approval before proceeding to Phase 1.
   
   Begin Phase 0 now.
   ```

3. **For each subsequent phase**, send:
   ```
   Phase [N-1] approved. Proceed to Phase [N]: [Goal].
   
   Follow CODEX-STAGED-AUDIT-SUPERPROMPT.md for the Phase [N] specification.
   Output the Phase [N] deliverable as specified.
   STOP and wait for approval before Phase [N+1].
   
   Begin Phase [N] now.
   ```

4. **Review, approve, iterate**. Each phase pause point allows you to review findings before committing to the next phase.

---

**This superprompt is complete and ready to use. Invoke Phase 0 whenever you're ready to audit L9.**
