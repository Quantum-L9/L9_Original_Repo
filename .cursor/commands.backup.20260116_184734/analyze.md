---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "7.0.0"
component_id: "CMD-ANALYZE-001"
component_name: "Analyze - Rapid Exploration"
layer: "commands"
domain: "exploration"
type: "slash_command"
status: "active"
created: "2025-12-01T00:00:00Z"
updated: "2026-01-01T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "informational"
compliance_required: false
audit_trail: false
security_classification: "internal"

# === COMMAND METADATA ===
name: analyze
description: "L9-native rapid exploration — understand structure, map flows, identify hotspots fast"
memory_inject: true            # INJECT: Search VPS memory for preferences/lessons before execution
before_chain: extract-chat   # EXTRACT: Write learnings to VPS memory
auto_chain: ynp
---

# === L9 ANALYZE: Rapid Codebase Exploration ===
# Cursor Slash Command: /analyze
# Version: 7.0.0 (L9-native)
# Updated: 2026-01-01

---

## ⛓️ AUTO-CHAINS TO /ynp

This command **automatically runs /ynp at the end** to recommend whether to `/evaluate` deeper, `/gmp` to fix issues, or proceed to next module.

---

## WHAT IT DOES

Fast, exploratory analysis to understand code before acting:

1. **Orientation** — What is this module? What does it do?
2. **Structure Map** — Files, classes, functions, relationships
3. **Flow Tracing** — How does data/control flow through?
4. **Hotspot Detection** — Where are the critical paths?
5. **Quick Health** — Surface-level issues visible immediately
6. **Context for Action** — Enough to decide: dig deeper or act?

**Key principle:** Speed over thoroughness. Get oriented in <30 seconds, then decide next step.

---

## /analyze vs /evaluate

| Aspect | /analyze | /evaluate |
|--------|----------|-----------|
| **Goal** | Understand | Audit |
| **Question** | "What is this?" | "Is this production-ready?" |
| **Speed** | Fast (30s) | Thorough (2-5min) |
| **Depth** | Surface | Deep |
| **Output** | Structure map + hotspots | Compliance report + TODOs |
| **Use When** | New to code, exploring | Before commit, before deploy |

**Chain:** `/analyze` → understand → `/evaluate` → audit → `/gmp` → fix

---

## EXECUTION PROTOCOL

### Step 0: MEMORY INJECTION (/mem READ phase)

**MANDATORY** — Load context from L9 memory via MCP server before analysis:

```bash
# 1. User preferences and patterns (via MCP search_memory tool)
python3 .cursor-commands/cursor-memory/cursor_memory_client.py search "Igor preferences patterns"

# 2. Recent lessons and errors (via MCP search_memory tool)
python3 .cursor-commands/cursor-memory/cursor_memory_client.py search "lessons errors recent"

# 3. Analysis patterns (via MCP search_memory tool)
python3 .cursor-commands/cursor-memory/cursor_memory_client.py search "analysis patterns lessons"

# 4. Target-specific context (via MCP search_memory tool)
python3 .cursor-commands/cursor-memory/cursor_memory_client.py search "[TARGET_KEYWORDS] structure history"
```

**Note:** All searches use MCP server (PRIMARY). Client falls back to HTTP only if MCP unreachable.

**Output format:**

```
## 🧠 MEMORY CONTEXT LOADED

### Preferences Found
- [preference 1]
- [preference 2]

### Relevant Lessons
- [lesson 1]
- [lesson 2]

### Analysis Patterns
- [pattern 1]

### Target-Specific Matches
- [match 1]

---
📍 Memory context loaded. Proceeding with analysis.
```

### Step 1: QUICK STATE CHECK

```
1. Glance at workflow_state.md (don't full sync)
2. Note current PHASE and priority tier
3. Check if target is in active scope
4. Proceed with analysis
```

### Step 2: TARGET IDENTIFICATION

Classify what we're analyzing:

```
TARGET TYPES:
├── MODULE: Python package with __init__.py
├── SERVICE: Class with methods, likely has dependencies
├── AGENT: Agent class (inherits BaseAgent or similar)
├── ROUTER: FastAPI router with endpoints
├── TOOL: Tool definition in tool registry
├── KERNEL: YAML kernel file
├── MIGRATION: SQL file
├── CONFIG: Settings, docker-compose, env
├── TEST: Test file or directory
└── UNKNOWN: Needs deeper inspection
```

### Step 3: TIER CLASSIFICATION

```
TIER DETECTION:
├── KERNEL_TIER if:
│   ├── Path contains: kernel, executor, orchestrator
│   ├── Imports from: core/kernels, core/agents/executor
│   └── Referenced by: safety, governance, memory substrate
├── RUNTIME_TIER if:
│   ├── Path contains: task_queue, tools, registry, agents
│   └── Imports from: runtime/, orchestration/
├── INFRA_TIER if:
│   ├── Path contains: docker, deploy, k8s, helm
│   └── File is: .yml, .yaml, .sh, Dockerfile
└── UX_TIER otherwise
```

### Step 4: STRUCTURE MAP

Generate quick overview:

```
MODULE STRUCTURE:
├── Files: [count] ([lines] total)
├── Classes: [list with one-liner purpose]
├── Functions: [key public functions]
├── Imports: [notable dependencies]
├── Exports: [what's in __init__.py or __all__]
└── Tests: [exists? coverage hint?]
```

### Step 5: FLOW TRACING

Map how data/control flows:

```
ENTRY POINTS:
├── HTTP: /api/v1/... endpoints
├── WebSocket: ws://... handlers
├── CLI: Command-line entry
├── Internal: Called by other modules
└── Scheduled: Cron/background tasks

DATA FLOW:
Input → [Validation] → [Processing] → [Storage] → Output
         ↓               ↓              ↓
      Packets         Memory        Database

CONTROL FLOW:
Trigger → Router → Service → [Tool/LLM] → Result → Response
                      ↓
                 Governance Check
```

### Step 6: HOTSPOT DETECTION

Identify critical areas:

```
HOTSPOTS (requires attention):
├── 🔴 CRITICAL: Affects safety, data integrity, auth
├── 🟠 COMPLEX: High cyclomatic complexity, many branches
├── 🟡 COUPLED: Many dependencies, hard to change alone
├── 🔵 ENTRY: Main entry points, high traffic
└── ⚪ ORPHAN: Not called, possibly dead code
```

### Step 7: QUICK HEALTH SCAN

Surface-level issues (not deep audit):

```
QUICK HEALTH:
├── ✅ Looks OK: [patterns present]
├── ⚠️ Flags: [obvious issues visible]
├── ❓ Unclear: [needs deeper look]
└── 🔗 Related: [connected modules to check]
```

---

## OUTPUT FORMAT

```
## 🔍 L9 ANALYZE: [Target Name]

### 📍 ORIENTATION
- **Type:** [MODULE/SERVICE/AGENT/ROUTER/TOOL/etc.]
- **Tier:** [KERNEL/RUNTIME/INFRA/UX]
- **Purpose:** [One sentence: what does this do?]
- **Location:** [path]

### 🗺️ STRUCTURE MAP

```
[target]/
├── __init__.py (exports: ...)
├── models.py (3 classes: X, Y, Z)
├── service.py (main: FooService)
├── routes.py (endpoints: /foo, /bar)
└── tests/
    └── test_service.py (12 tests)
```

**Key Classes:**
| Class | Purpose | Lines |
|-------|---------|-------|
| FooService | Main service, handles X | 245 |
| FooModel | Pydantic model for Y | 45 |

**Key Functions:**
| Function | Purpose | Calls |
|----------|---------|-------|
| process_task() | Entry point for tasks | ToolRegistry, Memory |
| validate_input() | Input validation | Pydantic |

### 🔀 FLOW TRACE

```
Entry: POST /api/v1/foo
  ↓
routes.py:create_foo()
  ↓
service.py:FooService.create()
  ├── validate_input()
  ├── governance.check_permission()
  ├── tool_registry.dispatch()
  └── memory.ingest_packet()
  ↓
Return: FooResponse
```

### 🎯 HOTSPOTS

| Location | Type | Why |
|----------|------|-----|
| service.py:87 | 🔴 CRITICAL | Governance check, approval gate |
| service.py:145 | 🟠 COMPLEX | 6 branches, needs refactor |
| routes.py:23 | 🔵 ENTRY | Main API endpoint |

### 🩺 QUICK HEALTH

| Check | Status | Note |
|-------|--------|------|
| Has tests | ✅ | 12 tests found |
| Type hints | ⚠️ | 3 functions missing |
| Error handling | ✅ | Try/except present |
| Packet logging | ⚠️ | Not in all paths |
| structlog | ✅ | Uses structlog |

### 🔗 CONNECTIONS

**Depends on:**
- `core/tools/registry.py` — Tool dispatch
- `memory/substrate_service.py` — Packet storage
- `core/governance/engine.py` — Permission checks

**Depended on by:**
- `api/routes/tasks.py` — Imports FooService
- `orchestration/task_router.py` — Routes to this

### ➡️ NEXT STEPS

| If you want to... | Run... |
|-------------------|--------|
| Deep audit for production | `/evaluate @[target]` |
| Understand a specific flow | `/analyze @[specific_file]` |
| Fix the flagged issues | `/gmp` with TODO plan |
| Just proceed to next task | `/ynp` |

---

### 📊 ANALYSIS METADATA
- Analyzed: [timestamp]
- Files scanned: [count]
- Time: [Xms]
- Tier: [tier]
- Complexity: [low/medium/high]
```

---

## USAGE MODES

### Quick Module Scan (default)
```
/analyze @core/agents/
```
Scans entire module, generates structure map.

### Single File Deep Look
```
/analyze @core/agents/executor.py
```
Focuses on one file with more detail.

### Flow-Focused
```
/analyze @api/routes/tasks.py --flow
```
Emphasizes control/data flow tracing.

### Hotspot Hunt
```
/analyze @core/ --hotspots
```
Just find critical areas, skip structure details.

### Comparison
```
/analyze @core/agents/executor.py @orchestration/task_router.py
```
Analyze multiple targets, show relationships.

---

## FLAGS & OPTIONS

| Flag | Description | Default |
|------|-------------|---------|
| `--flow` | Emphasize flow tracing | false |
| `--hotspots` | Focus on critical areas only | false |
| `--deps` | Show full dependency graph | false |
| `--quick` | Ultra-fast, just structure | false |
| `--json` | Output as JSON | false |

---

## L9-SPECIFIC ANALYSIS

### For KERNEL_TIER targets:
- Check for approval gate usage
- Verify packet logging at decision points
- Map to kernel YAML if applicable
- Note safety-critical paths

### For RUNTIME_TIER targets:
- Map tool registrations
- Check async patterns
- Verify timeout configs
- Note rate limiting

### For INFRA_TIER targets:
- Parse env var usage
- Check port mappings
- Verify volume mounts
- Note deployment dependencies

### For Agents:
```
AGENT ANALYSIS:
├── Capabilities: [from AgentCapabilities]
├── Tools available: [from tool registry]
├── Kernels loaded: [from kernel stack]
├── Memory access: [substrate permissions]
└── Governance: [approval requirements]
```

### For Routers:
```
ROUTER ANALYSIS:
├── Endpoints: [list with methods]
├── Auth required: [which endpoints]
├── Request models: [Pydantic schemas]
├── Response models: [Pydantic schemas]
└── Dependencies: [injected services]
```

---

## INTEGRATION

### Before Analyze:
- Quick glance at workflow_state.md (not full sync)
- Know current phase context

### After Analyze:
- `/evaluate` for deep audit
- `/gmp` to fix issues found
- `/ynp` for next action

### Typical Exploration Flow:
```
/analyze @new_module/          # What is this?
  ↓
Understand structure
  ↓
/analyze @new_module/service.py --flow  # How does it work?
  ↓
Understand flows
  ↓
/evaluate @new_module/         # Is it production-ready?
  ↓
Get actionable TODOs
  ↓
/gmp [fix issues]
```

---

## EXAMPLES

### Example 1: New to a Module
```
/analyze @core/agents/

Output:
## 🔍 L9 ANALYZE: core/agents/

### 📍 ORIENTATION
- Type: MODULE
- Tier: KERNEL_TIER
- Purpose: Agent execution runtime — instantiates agents, runs reasoning loops, dispatches tools
- Location: core/agents/

### 🗺️ STRUCTURE MAP
core/agents/
├── __init__.py (exports: AgentExecutorService, AgentInstance)
├── executor.py (main: AgentExecutorService)
├── instance.py (AgentInstance, per-task agent)
├── registry.py (AgentRegistry, agent configs)
├── runtime.py (AIOSRuntime, reasoning loop)
├── capabilities.py (AgentCapabilities enum)
└── tests/
    └── test_executor.py (8 tests)

### 🎯 HOTSPOTS
| Location | Type | Why |
|----------|------|-----|
| executor.py:156 | 🔴 CRITICAL | Tool dispatch with governance |
| runtime.py:89 | 🟠 COMPLEX | Reasoning loop, many branches |
```

### Example 2: Trace a Flow
```
/analyze @api/routes/commands.py --flow

Output:
### 🔀 FLOW TRACE

POST /api/v1/commands/execute
  ↓
routes/commands.py:execute_command()
  ├── Parse CommandRequest
  ├── intent_extractor.extract_intent()
  │     └── LLM call or rule-based fallback
  ├── Check high_risk → require confirmation
  ├── command_dispatcher.dispatch()
  │     ├── propose_gmp → GMPService
  │     ├── approve → GovernanceEngine
  │     ├── status → StateService
  │     └── help → static response
  └── audit_logger.log_command()
  ↓
Return: CommandResponse
```

### Example 3: Find Hotspots
```
/analyze @core/ --hotspots

Output:
### 🎯 HOTSPOTS ACROSS core/

| File | Line | Type | Why |
|------|------|------|-----|
| agents/executor.py | 156 | 🔴 CRITICAL | Approval gate |
| kernels/kernel_loader.py | 45 | 🔴 CRITICAL | Identity loading |
| governance/engine.py | 89 | 🔴 CRITICAL | Permission eval |
| tools/registry.py | 123 | 🟠 COMPLEX | Tool dispatch logic |
| agents/runtime.py | 89 | 🟠 COMPLEX | Reasoning loop |
```

---

## MEMORY WRITE (/mem WRITE phase)

**MANDATORY** — After analysis completes, write insights to L9 memory via MCP server:

```bash
# 1. Analysis summary (always) - via MCP save_memory tool
python3 .cursor-commands/cursor-memory/cursor_memory_client.py write \
  "ANALYZE: [target]. TYPE: [type]. TIER: [tier]. HOTSPOTS: [count]." \
  --kind note

# 2. Lessons learned (if any patterns discovered) - via MCP save_memory tool
python3 .cursor-commands/cursor-memory/cursor_memory_client.py write \
  "LESSON: [pattern discovered]. CONTEXT: [when this applies]." \
  --kind lesson

# 3. Insights (if structural insights found) - via MCP save_memory tool
python3 .cursor-commands/cursor-memory/cursor_memory_client.py write \
  "INSIGHT: [structural insight]. APPLIES_TO: [context]." \
  --kind insight
```

**Note:** All writes use MCP server (PRIMARY) and flow through ingestion pipeline. Client falls back to HTTP only if MCP unreachable.

**Output format:**

```
## 📝 MEMORY UPDATED

| Type | Content | Status |
|------|---------|--------|
| note | Analysis summary | ✅ written |
| lesson | [if applicable] | ✅ written |
| insight | [if applicable] | ✅ written |

Session: [daily_session_id]
Timestamp: [ISO timestamp]
```

---

## INTEGRATION

- **Auto-chains to:** `/ynp` (always)
- **Chains from:** Initial exploration, `/mem` (memory-first execution)
- **Chains to:** `/evaluate` (for deep audit), `/gmp` (to fix issues found)
- **Memory integration:** Uses `/mem` READ phase before analysis, WRITE phase after completion

---

## ANTI-PATTERNS

❌ **DON'T:** Use /analyze for production readiness (use /evaluate)
❌ **DON'T:** Spend too long in analysis — it's for orientation
❌ **DON'T:** Skip to /gmp without understanding the code first
❌ **DON'T:** Analyze the entire repo at once (too slow)
❌ **DON'T:** Skip memory injection — prior context prevents mistakes

✅ **DO:** Start with /analyze when new to code
✅ **DO:** Use --flow to understand data paths
✅ **DO:** Use --hotspots to find critical areas fast
✅ **DO:** Chain to /evaluate for deep audit
✅ **DO:** Keep analysis focused (one module at a time)
✅ **DO:** Load memory context before analyzing (faster than mistakes)

---

## CHAINING

```
New code exploration:
/analyze → /evaluate → /gmp → /ynp

Quick orientation before fix:
/analyze --quick → /gmp (if simple) or /evaluate (if complex)

Hotspot hunting:
/analyze --hotspots → /evaluate @[hotspot] → /gmp
```
