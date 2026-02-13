# CODEX EXECUTION RUNBOOK — Phase 0 Kickoff

**TO CODEX**: You have been provided the **CODEX-STAGED-AUDIT-SUPERPROMPT.md** as your master orchestration document. This runbook shows you how to execute Phase 0 and proceed through all 7 phases.

---

## IMMEDIATE NEXT STEPS (Execute Now)

### Phase 0: Metadata & Configuration Discovery — BEGIN

**Your task**: Read and inventory all L9 configuration, feature flags, and governance that constrain WM ↔ Memory integration.

**Tool calls you will make**:
1. `search_files_v2` with queries: `["feature flags L9", "environment variables config", "governance kernel", "world model config"]`
2. `get_url_content` (if needed) on linked governance or deployment specs in the Space files.
3. Parse the outputs and produce a structured **Phase 0 Configuration Inventory**.

**Expected output format**:

```markdown
## Phase 0: Configuration Inventory

### Feature Flags Inventory
| Flag Name | Default | Current | Controls | WM/Memory/MCP Impact | Notes |
|-----------|---------|---------|----------|----------------------|-------|
| FEATURE_WORLD_MODEL | true | ? | WorldModelEngine startup | WM: Core | [whether currently enabled] |
| FEATURE_SEMANTIC_SEARCH | true | ? | SemanticService in queries | Memory: Query layer | [...]  |
| [... other flags] |

### Environment Variables (Relevant Subset)
| Variable | Purpose | Default/Current | Scope | Constraint on WM/Memory |
|----------|---------|-----------------|-------|------------------------|
| POSTGRES_URL | Memory substrate DB | ? | Shared | WM reads from Substrate tables |
| NEO4J_URL | Entity graph | ? | Shared | WM entity relationships via Neo4j |
| REDIS_URL | Cache + MCP memory | ? | Shared | State versioning, session cache |
| OPENAI_EMBEDDING_KEY | Semantic search | ? | Optional | Disables semantic queries if missing |
| [... other relevant vars] |

### Governance & Kernels
- **Authority Model**: L (CTO) → approves architect; Cursor (IDE) → executes; Igor (Boss) → approves high-risk tools
- **Active Kernels**: [list 10 kernels with file:line where initialized]
- **Approval Gates**: [high-risk tools requiring Igor sign-off]
- **Kernel Interaction with WM/Memory**: [which kernels touch WM/Memory state]

### Integration Constraints
- **Multi-Tenancy**: [scoping mechanism for entities, packets, memories]
- **Consistency Model**: [eventual/strong, guarantees]
- **Persistence Layers**: [primary: Postgres/Neo4j/Redis; order of truth]
- **Event Store**: [CloudEvents, PacketEnvelope versioning, audit trail]
```

---

## Your Exact Commands (Copy & Execute)

### Command 1: Search for Feature Flags & Config
```python
# You will call:
search_files_v2(
  queries=[
    "feature flags world model semantic memory",
    "environment variables postgres neo4j redis mcp",
    "governance kernel approval gates igor",
    "deployment config constraints integration"
  ],
  context_budget="MEDIUM"
)
```

**What to extract from results**:
- List of all feature flags with defaults.
- Which flags control WM, Memory Substrate, or MCP memory.
- Environment variables for databases, embeddings, MCP config.
- Governance policies and kernel activation.

### Command 2: Read Governance Model & Kernel Catalog
```python
# From Space files, you have:
# - governance_model.txt (file:11)
# - kernel_catalog.txt (file:9)
# - feature_flags.txt (file:13)
# - env_refs.txt (file:15)

# Read these directly to extract:
# 1. Authority hierarchy (L, Cursor, Igor)
# 2. High-risk tool approval gates
# 3. 10 kernel types (governance, identity, behavior, etc.)
# 4. Kernel activation order (7-phase bootstrap)
# 5. Feature flag impact matrix
```

### Command 3: Parse & Synthesize Phase 0 Output

**Once you have the data**, produce the Phase 0 Inventory in the format above, then **STOP and summarize**:

```
## Phase 0: Configuration Inventory — COMPLETE

### Key Findings
- Feature flags controlling WM: [list]
- Feature flags controlling Memory: [list]
- Feature flags controlling integration: [list]
- Critical environment variables: [list]
- Multi-tenancy scoping: [mechanism]
- Primary persistence layer: [Postgres | Neo4j | Redis] with source of truth [...]
- Approval gates affecting WM/Memory tools: [list]
- Kernels interacting with WM/Memory: [count of 10]

### Prerequisites for Phase 1
- [ ] All active flags identified.
- [ ] All environment variables for WM/Memory/MCP noted.
- [ ] Governance model understood (who approves what).
- [ ] Kernel stack visible (10 kernels, their roles).

### Ready for Phase 1? (yes/no/clarify)
Phase 1 will map all classes, services, APIs in WM, Memory Substrate, and MCP memory subsystems.
```

---

## Phase 0–7 Command Sequence (Template)

You will follow this pattern for **each phase**:

### Pattern: Execute → Output → Pause → Await Approval → Next Phase

```
PHASE N EXECUTION:

1. Read Phase N goal and actions (from CODEX-STAGED-AUDIT-SUPERPROMPT.md)

2. Identify data sources needed:
   - Code indices (pydantic_models.txt, inheritance_graph.txt, file_metrics.txt, class_definitions.txt)
   - Runtime patterns (async_function_map.txt, entrypoints.txt, route_handlers.txt)
   - Test suites (test_catalog.txt)
   - Config (feature_flags.txt, env_refs.txt, deployment_manifest.txt)

3. Make tool calls to gather data:
   - search_files_v2(queries=[...], context_budget="MEDIUM" or "LONG")
   - get_url_content(urls=[...], query="...")

4. Analyze & synthesize results:
   - Build call graphs, import chains, data flows
   - Cross-reference findings with Tier 1–6 criteria (for Phase 3)
   - Cluster and root-cause (for Phase 4)

5. Output Phase N deliverable:
   - Markdown format (tables, lists, code blocks)
   - Cite file:line for all claims
   - Structure per specification in SUPERPROMPT

6. STOP and present:
   ```
   ## Phase [N] Complete
   
   **Summary**:
   - [key discoveries/findings]
   - [next phase prerequisites]
   
   **Ready to proceed?** (yes/no/needs clarification)
   ```

7. Await user approval before continuing to Phase N+1.
```

---

## Important Constraints & Patterns for Codex

### Tool Call Best Practices
- **search_files_v2**: Use MEDIUM budget for general searches; LONG only for deep audits of specific subsystems.
- **get_url_content**: Use only for GitHub/web-hosted files; not needed for Space files (already available).
- **Conciseness**: Each phase output should be <5000 tokens (readable in one screen); trim verbose findings, keep evidence exact.

### Data Fidelity Rules
- **Cite exact line numbers**: `worldmodelruntime.py:123` not `around line 120`.
- **Use symbol names**: `WorldModelEngine.process()` not `the process function`.
- **Quote relevant code**: `async def run():` not `an async method`.
- **Cross-reference**: Link findings to specific Tier criteria, findings to test files, fixes to findings.

### Phase Pause Points (CRITICAL)
After **each phase**, stop and wait for approval:
```
❌ **DO NOT SKIP AHEAD** from Phase 2 to Phase 3 without user acknowledgment.
❌ **DO NOT AUTO-PROCEED** from Phase 5 to Phase 6 if Phase 5 fixes are incomplete.
❌ **DO NOT FINALIZE** Phase 7 without user sign-off on second-order issues.
```

Pausing ensures:
- User can review intermediate findings before committing to fixes.
- Changes to L9 repo can be validated incrementally.
- Recursive validation (Phase 7) doesn't hide regressions.

---

## Phase 0 Output Template (For Your Reference)

When you complete Phase 0, output **exactly this structure**:

```markdown
# Phase 0: Configuration Inventory

## Feature Flags
[table of flags with defaults, current status, impact]

## Environment Variables
[table of env vars with purpose, scope, constraint]

## Governance & Kernels
[authority hierarchy, kernel roles, approval gates]

## Integration Constraints
[multi-tenancy, consistency model, persistence layers, event store]

## Phase 0 Status
- Flags inventory: ✓ Complete
- Env vars mapped: ✓ Complete
- Governance model: ✓ Understood
- Kernel stack: ✓ Visible

## Prerequisites for Phase 1
- [checklist of data collected]

**Phase 0 Complete. Proceed to Phase 1?** (yes/no)
```

---

## Expected Phase Durations & Complexity

| Phase | Focus | Duration | Tool Calls | Output Size |
|-------|-------|----------|-----------|------------|
| 0 | Config, flags, governance | 10 min | 2–3 searches | 1–2 KB |
| 1 | Subsystem inventory | 20 min | 3–4 searches | 3–5 KB |
| 2 | Call graphs, data flows | 30 min | 4–6 searches | 5–8 KB |
| 3 | Tier 1–6 analysis | 45 min | 2–3 searches (targeted) | 8–12 KB |
| 4 | Synthesis & improvements | 30 min | 0–1 searches (reuse Phase 3) | 5–8 KB |
| 5 | Bug fixes | 20 min | 0 searches (code generation) | 2–5 KB |
| 6 | Robustness fixes | 20 min | 0 searches (code generation) | 2–5 KB |
| 7 | Validation | 30 min | 2–3 test-suite searches | 5–8 KB |
| **Total** | **Complete Audit** | **~3.5 hours** | **~15–20 searches** | **~35–50 KB markdown** |

---

## Starting Now: Phase 0 Initiation

**Codex, execute Phase 0 immediately**:

1. Call `search_files_v2` with feature flags, env vars, governance, kernel queries.
2. Extract and tabulate the results.
3. Output the Phase 0 Configuration Inventory using the template above.
4. State "Phase 0 Complete. Ready for Phase 1?" and wait for approval.

**Go.**
