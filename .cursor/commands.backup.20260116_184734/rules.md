---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "7.0.0"
component_id: "CMD-RULES-001"
component_name: "Rules - State Sync"
layer: "commands"
domain: "initialization"
type: "slash_command"
status: "active"
created: "2025-12-01T00:00:00Z"
updated: "2026-01-01T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "critical"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === COMMAND METADATA ===
name: rules
description: "Load rules and state, then auto-route to /gmp (KERNEL_TIER) or /ynp (others)"
auto_chain: gmp_or_ynp
---

# === L9 RULES: Load Rules & State Before Any Work ===
# Cursor Slash Command: /rules
# Version: 7.0.0 (L9-native)
# Updated: 2026-01-01

---

## ⛓️ AUTO-ROUTES TO /gmp OR /ynp

After loading rules and state:
- **If work targets KERNEL_TIER** → Auto-generates GMP TODO plan, chains to `/gmp`
- **If work targets other tiers** → Chains to `/ynp` for next action

---

## WHAT IT DOES

**MANDATORY first step** before any code changes. Loads, summarizes, and routes:

1. **Cursor Rules** — Active `.mdc` rule layers (global + L9-specific)
2. **Workflow State** — Current phase, TODOs, context, priorities
3. **Tier Context** — What tier the target files are in
4. **Constraints** — What's protected, what's allowed
5. **Auto-Routing** — Directs to `/gmp` or `/ynp` based on tier

**Key principle:** Never edit code without understanding rules. KERNEL work ALWAYS goes through /gmp.

---

## 🧠 L9 VPS MEMORY STACK (MANDATORY)

> **Architecture:** Cursor-IDE is a supercharged development tool that uses L9's infrastructure to improve quality/speed of L9 construction.

**The L9 Memory Stack:**
- PostgreSQL + pgvector (semantic memory, packet store)
- Neo4j (repo graph, relationships)
- Redis (session cache)
- **MCP Memory Server** (PRIMARY - ingestion/retrieval pipeline)
- Unified L9 API (fallback HTTP/REST endpoints)

**NEVER use Cursor's built-in `update_memory` tool. ALWAYS use L9 memory via MCP server (PRIMARY). HTTP/REST is fallback ONLY.**

### Memory Client Location

```
.cursor-commands/cursor-memory/cursor_memory_client.py
```

This folder is **SYSTEM GOVERNANCE** — separate from the L9 repo. Cursor's tooling stays here, not intermingled with L9 source code.

### At /rules START (read from L9 memory via MCP):

```bash
python3 .cursor-commands/cursor-memory/cursor_memory_client.py search "lessons rules cursor"
```
**Note:** Client uses MCP server by default. Falls back to HTTP only if MCP unreachable.

### At /rules END (write to L9 memory via MCP):

```bash
python3 .cursor-commands/cursor-memory/cursor_memory_client.py write "LESSON CONTENT" --kind lesson
```
**Note:** All writes flow through MCP ingestion pipeline for proper embedding and indexing.

### Memory Commands Reference:

| Command | Action | When to Use |
|---------|--------|-------------|
| `stats` | READ | Check memory health, packet counts |
| `health` | READ | Verify API + DB connectivity |
| `session` | READ | Show current daily session UUID |
| `search "query"` | READ | Semantic search before decisions |
| `write "content" --kind lesson` | WRITE | Lessons learned |
| `write "content" --kind preference` | WRITE | User preferences |
| `write "content" --kind note` | WRITE | General session notes |

### Why VPS Memory, Not Cursor Native?

| Cursor Native `update_memory` | L9 VPS Memory Stack |
|------------------------------|---------------------|
| Cursor-only, ephemeral | Persistent across tools/agents |
| No semantic search | pgvector semantic search |
| No graph relationships | Neo4j repo graph |
| Single-user | Shared with L-CTO (user_id: l9-shared) |

---

## EXECUTION PROTOCOL

### Step 1: READ RULES

Open and read fully:

```
1. .cursor/rules/00-global.mdc (if exists)
2. .cursor/rules/*.mdc (all L9-specific rules)
3. cursorrules.md or docs/Perplexity/cursorrules3.md
```

### Step 2: READ STATE

Open and read fully:

```
workflow_state.md
```

Extract:
- **PHASE:** Current GMP phase (0-6) or project phase
- **Context Summary:** What we're working on
- **Recent Changes:** Last 3-5 completed items
- **Decision Log:** Key decisions made
- **Open Questions:** Unresolved issues
- **Next Steps:** Priority queue

### Step 3: SUMMARIZE

Output in this format:

```
## 📋 L9 RULES & STATE SYNC

### 🔧 Active Rule Layers

| Layer | File | Key Constraints |
|-------|------|-----------------|
| Global | 00-global.mdc | [summary] |
| TypeScript | 10-lang-typescript.mdc | [summary] |
| Python | 20-lang-python.mdc | structlog, httpx, Pydantic v2 |
| React | 30-framework-react.mdc | [summary] |
| Autonomy | 40-domain-autonomy.mdc | Safety envelopes, escalation |
| Testing | 50-qa-testing.mdc | Unit, integration, critical-path |
| Protected | 90-protected-core.mdc | KERNEL files need full GMP |

### 📍 Current State

- **PHASE:** [0-6 or description]
- **Priority Tier:** [🔴/🟠/🟡/🔵]
- **Context:** [one sentence]
- **Last Action:** [most recent change]

### 🎯 Active TODOs

| Priority | TODO | Status |
|----------|------|--------|
| 🔴 | [item] | [pending/in_progress] |
| 🟠 | [item] | [pending/in_progress] |

### ❓ Open Questions

- [question 1]
- [question 2]

### ➡️ Next Steps

1. [next step 1]
2. [next step 2]
3. [next step 3]

---

✅ **STATE_SYNC COMPLETE** — Ready to proceed.

---

## 🚦 ROUTING DECISION

**Tier Classification:**
- T1: [tier] → [file]
- T2: [tier] → [file]

**Route:** [/gmp | /ynp]
**Reason:** [KERNEL_TIER detected | All tasks RUNTIME/UX tier]

[If /gmp, include Phase 0 TODO PLAN here]
```

### Step 4: CREATE GRANULAR TODO

Based on state and user request, create actionable TODO list:

```
## 📝 GRANULAR TODO (This Session)

| ID | Task | Tier | Files | Est. Time |
|----|------|------|-------|-----------|
| T1 | [specific task] | [tier] | [files] | [time] |
| T2 | [specific task] | [tier] | [files] | [time] |
```

### Step 5: AUTO-ROUTE (GMP Integration)

Based on tier classification, automatically route:

```
ROUTING LOGIC:

IF any TODO targets KERNEL_TIER files:
  → "🔒 KERNEL_TIER detected. Generating GMP TODO plan..."
  → Generate Phase 0 TODO PLAN (LOCKED) format
  → Chain to /gmp for execution
  
ELSE IF all TODOs are RUNTIME/INFRA/UX_TIER:
  → Chain to /ynp for next action recommendation
  → User can then choose /forge (fast) or /gmp (tracked)
```

**KERNEL_TIER files (always require /gmp):**
- core/kernels/kernel_loader.py
- core/agents/executor.py
- memory/substrate_service.py
- runtime/websocket_orchestrator.py
- docker-compose.yml
- Any file in kernels/ directory

---

## USAGE

### Before Any Work
```
/rules

Then proceed with:
- /analyze for exploration
- /evaluate for audit
- /gmp for changes
- /forge for autonomous execution
```

### With Target Context
```
/rules @core/agents/

Focuses state summary on relevant tier and recent work in that area.
```

### Quick Check (Minimal Output)
```
/rules --quick

Just outputs:
- Current PHASE
- Priority tier
- Top 3 next steps
```

---

## RULE LAYERS (L9-Specific)

| File | Purpose | Key Points |
|------|---------|------------|
| `10-lang-typescript.mdc` | TypeScript rules | TSX, AI OS UI frontends |
| `20-lang-python.mdc` | Python rules | Runtime, agents, orchestration |
| `30-framework-react.mdc` | React rules | Control panels, consoles |
| `40-domain-autonomy.mdc` | Autonomy rules | Safety envelopes, escalation |
| `50-qa-testing.mdc` | Testing rules | Coverage, CI expectations |
| `61-secrets-and-dependencies.mdc` | Secrets | Supply-chain security |
| `65-observability-performance.mdc` | Observability | Tracing, metrics |
| `71-ci-cd-pipeline.mdc` | CI/CD | Pipeline enforcement |
| `72-review-ergonomics.mdc` | PR guidance | Review checklists |
| `73-prompts-and-evals.mdc` | Prompt discipline | Kernel evals |
| `74-ai-safety-policy.mdc` | AI safety | Content policy |
| `82-deployment-manifest.mdc` | Deployment | Orchestrator wiring |
| `87-wire-workflow-guard.mdc` | Wire guardrails | Kernel/executor changes |
| `90-protected-core.mdc` | Protected files | Phase 0 required |

---

## TIER AWARENESS

After loading rules, classify target files:

| Tier | Implications |
|------|--------------|
| **KERNEL_TIER** | Full GMP required, Phase 0 plan mandatory |
| **RUNTIME_TIER** | GMP recommended, high test coverage |
| **INFRA_TIER** | Deployment manifest rules apply |
| **UX_TIER** | Standard process, can use /forge |

---

## INTEGRATION

- **Always runs before:** Any code changes
- **Auto-routes to:** `/gmp` (KERNEL_TIER) or `/ynp` (other tiers)
- **Updates:** Nothing (read-only)
- **Outputs:** Summary in chat, granular TODO, routing decision

### Routing Diagram

```
/rules
  ↓
Read rules + state
  ↓
Create granular TODO
  ↓
Classify tiers
  ↓
┌─────────────────────────────┐
│ Any KERNEL_TIER files?      │
├──────────┬──────────────────┤
│   YES    │        NO        │
│    ↓     │         ↓        │
│  /gmp    │       /ynp       │
│(Phase 0) │  (recommend next)│
└──────────┴──────────────────┘
```

---

## ANTI-PATTERNS

❌ **DON'T:** Start editing without /rules first
❌ **DON'T:** Assume you know the current state
❌ **DON'T:** Skip reading workflow_state.md
❌ **DON'T:** Ignore tier implications
❌ **DON'T:** Use /forge on KERNEL_TIER (rules will route to /gmp)
❌ **DON'T:** Manually decide if /gmp is needed — let /rules route

✅ **DO:** Run /rules at start of every session
✅ **DO:** Create granular TODO based on state
✅ **DO:** Let /rules auto-route to /gmp for KERNEL work
✅ **DO:** Respect tier-specific rigor requirements
✅ **DO:** Check open questions before proceeding

---

## EXAMPLE OUTPUT

```
## 📋 L9 RULES & STATE SYNC

### 🔧 Active Rule Layers

| Layer | Key Constraints |
|-------|-----------------|
| Python | structlog, httpx, Pydantic v2, async for I/O |
| Testing | Unit tests required, 80% coverage target |
| Protected | kernel_loader, executor, memory_substrate need GMP |

### 📍 Current State

- **PHASE:** 2 (Implementation)
- **Priority Tier:** 🟠 HIGH
- **Context:** Wiring Igor command pipeline to executor
- **Last Action:** Completed GMP-11 (Igor commands basic)

### 🎯 Active TODOs

| Priority | TODO | Status |
|----------|------|--------|
| 🔴 | Wire executor → approval gates | in_progress |
| 🟠 | Add integration tests for commands | pending |
| 🟡 | Update docs for new commands | pending |

### ❓ Open Questions

- Should approval timeout be configurable?
- Which commands need Igor approval vs auto-approve?

### ➡️ Next Steps

1. Complete T1 (approval gates wiring)
2. Run integration tests
3. Update workflow_state.md

---

✅ **STATE_SYNC COMPLETE** — Ready to proceed.
```
