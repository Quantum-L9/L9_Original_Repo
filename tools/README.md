# L9 Tools

## Overview

**L9 Tools** is the protocol and client layer for external tool communications. This folder contains utilities for Cursor IDE integration and Mac agent reverse-tunnel protocols.

> **Note:** This is NOT the main tool registry. The L9 tool system spans multiple directories:
> - `core/tools/` — **PRIMARY**: Tool graph, registry, dynamic discovery, embeddings
> - `runtime/l_tools.py` — Tool executor implementations  
> - `services/research/tools/` — Base tool registry and wrappers
> - `api/tools/` — HTTP API routes for tool execution

---

## 🚨 DEPRECATION NOTICES

### Static Tool Binding (DEPRECATED)

**Effective: 2026-01-25 (GMP-78 Phase 2)**

Static tool binding (loading all tools into context) is **DEPRECATED**. Dynamic tool discovery is now the default.

| Old Pattern | New Pattern |
|-------------|-------------|
| `from core.tools import L9_TOOLS` | `from core.tools import discover_tools_for_task` |
| `agent_instance.get_bound_tools()` | `await agent_instance.prepare_dynamic_tools()` |
| Static tool lists in config | Semantic search at runtime |

**Migration:**
```python
# DEPRECATED
tools = L9_TOOLS  # Static list

# PREFERRED
tools = await discover_tools_for_task("task description")
```

**To temporarily disable:**
```bash
L9_DYNAMIC_TOOL_DISCOVERY=false
```

### Tool Access Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│ PREFERRED: Dynamic Discovery (GMP-78)                            │
├─────────────────────────────────────────────────────────────────┤
│ from core.tools import discover_tools_for_task                  │
│ tools = await discover_tools_for_task("search memory")          │
│                                                                  │
│ Benefits:                                                        │
│ - 40-70% token reduction                                        │
│ - Task-relevant tools only                                      │
│ - Scales to 100+ tools                                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓ fallback
┌─────────────────────────────────────────────────────────────────┐
│ DEPRECATED: Static Binding                                       │
├─────────────────────────────────────────────────────────────────┤
│ from core.tools import L9_TOOLS                                 │
│ tools = agent_instance.get_tool_definitions()  # if no dynamic  │
│                                                                  │
│ Problems:                                                        │
│ - Context bloat (5000-15000 tokens)                             │
│ - Poor tool selection at scale                                  │
│ - Emits DeprecationWarning                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Directory Contents

| File | Purpose | Status |
|------|---------|--------|
| `mac_protocol.py` | JSON schema for Mac agent tunnel | ✅ Active |
| `export_repo_indexes.py` | Repo indexing utility | 🟡 Legacy |
| `TOOL_LOADING_DIAGRAM.md` | Architecture diagram | ⚠️ Needs update for GMP-78 |

---

## Architecture

See [`TOOL_LOADING_DIAGRAM.md`](./TOOL_LOADING_DIAGRAM.md) for tool loading flow.

### Tool Discovery Flow (GMP-78)

```
Task Request Flow (v2.0.0):
  AgentExecutorService
    → prepare_dynamic_tools()           # NEW: Semantic discovery
    → discover_tools_for_task()         # NEW: pgvector search
    → get_tool_definitions()            # Returns discovered OR static
    → TOOL_EXECUTORS (runtime/l_tools.py)
    → Capability check
    → Approval check (if high-risk)
    → Execute & log packet
```

---

## Mac Protocol

The Mac agent uses a JSON-only protocol for reverse tunnel communications:

### MacMessage (Request)

```python
from tools.mac_protocol import MacMessage

msg = MacMessage(
    token="auth_token",
    cmd="ls",
    args=["-la"],
    cwd="/opt/l9",
    timeout=30
)
```

### MacResponse

```python
from tools.mac_protocol import create_mac_response

response = create_mac_response(
    success=True,
    output="file1.txt\nfile2.txt\n",
    error="",
    exit_code=0
)
```

---

## L's Authorized Tools

L (the L9 CTO agent) has access to these tools via `DEFAULT_L_CAPABILITIES`:

| Tool | Category | Risk Level | Approval Required |
|------|----------|------------|-------------------|
| `memory_search` | Memory | Low | No |
| `memory_write` | Memory | Medium | No |
| `memory_read` | Memory | Low | No |
| `world_model_query` | Knowledge | Low | No |
| `kernel_read` | Knowledge | Low | No |
| `mcp_call_tool` | Integration | Medium | No |
| `long_plan.execute` | Orchestration | Medium | No |
| `long_plan.simulate` | Orchestration | Low | No |
| `symbolic_compute` | Computation | Low | No |
| `symbolic_codegen` | Computation | Low | No |
| `gmp_run` | Governance | **High** | ✅ Yes |
| `git_commit` | VCS | **High** | ✅ Yes |
| `mac_agent_exec_task` | Execution | **High** | ✅ Yes |

**Note:** With dynamic discovery, only tools relevant to the current task are loaded.

---

## Related Files

| Location | Purpose |
|----------|---------|
| `core/tools/dynamic_discovery.py` | **NEW** Semantic tool discovery |
| `core/tools/tool_embeddings.py` | **NEW** pgvector tool storage |
| `core/tools/tool_graph.py` | Tool definitions (L9_TOOLS, L_INTERNAL_TOOLS) |
| `core/tools/registry_adapter.py` | ExecutorToolRegistry, register_l_tools() |
| `core/schemas/capabilities.py` | ToolName enum, Capability, AgentCapabilities |
| `runtime/l_tools.py` | TOOL_EXECUTORS dict, tool implementations |
| `services/research/tools/tool_registry.py` | Base ToolRegistry singleton |
| `api/tools/router.py` | POST /tools/execute endpoint |
| `ci/check_tool_wiring.py` | CI gate for tool consistency |

---

## Adding New Tools

### 1. Define the tool (still required)

```python
# core/tools/tool_graph.py
L_INTERNAL_TOOLS.append(
    ToolDefinition(
        name="my_new_tool",
        description="Does something useful - will be embedded for discovery",
        category="custom",
        scope="internal",
        risk_level="low",
        agent_id="L",
    )
)
```

### 2. Implement the executor

```python
# runtime/l_tools.py
async def my_new_tool(arg1: str, **kwargs) -> dict:
    """Implementation here."""
    return {"result": arg1}

TOOL_EXECUTORS["my_new_tool"] = my_new_tool
```

### 3. Tool will be auto-embedded at startup

The tool will be automatically:
- Embedded via `sync_all_tool_embeddings()` at server startup
- Discoverable via semantic search
- Available in `/health/services` tool count

### 4. Run CI check

```bash
python ci/check_tool_wiring.py
```

---

## CI Enforcement

Tool wiring is validated by `ci/check_tool_wiring.py`:

```bash
python ci/check_tool_wiring.py
```

Checks:
1. All TOOL_EXECUTORS have ToolName enum entries
2. All TOOL_EXECUTORS have L capability entries
3. High-risk tools have `scope="requires_igor_approval"`
4. ToolDefinitions match TOOL_EXECUTORS
5. l_tools.py ↔ register_l_tools() consistency

---

## Security Model

- **Capability sandboxing**: Each agent declares capabilities on handshake
- **Immutable capabilities**: Once set, cannot be modified during session
- **Rate limiting**: Time-based sliding window per tool
- **Approval gates**: High-risk tools require Igor approval before execution
- **Audit logging**: All tool calls logged to memory substrate
- **Token budget**: Dynamic discovery enforces max tokens for tool context

---

*Last updated: 2026-01-25 (GMP-78 Phase 2)*
