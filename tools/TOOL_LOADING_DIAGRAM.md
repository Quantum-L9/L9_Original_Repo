# L9 Tool Loading Architecture

## Tool Loading Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           L9 TOOL SYSTEM                                    │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    1. TOOL DEFINITION LAYER                           │  │
│  │                                                                       │  │
│  │  ┌─────────────────────┐    ┌──────────────────────────────────────┐  │  │
│  │  │ core/tools/         │    │ services/research/tools/             │  │  │
│  │  │ tool_graph.py       │    │ tool_registry.py                     │  │  │
│  │  │                     │    │                                      │  │  │
│  │  │ • ToolDefinition    │    │ • ToolMetadata                       │  │  │
│  │  │ • L9_TOOLS          │    │ • ToolRegistry (singleton)           │  │  │
│  │  │ • L_INTERNAL_TOOLS  │    │ • Default tools:                     │  │  │
│  │  │ • ToolGraph (Neo4j) │    │   - perplexity_search                │  │  │
│  │  └─────────────────────┘    │   - http_request                     │  │  │
│  │                             │   - mock_search                      │  │  │
│  │                             │   - calculate                        │  │  │
│  │                             └──────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    2. CAPABILITY & ACCESS CONTROL                     │  │
│  │                                                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │ core/schemas/capabilities.py                                    │  │  │
│  │  │                                                                 │  │  │
│  │  │ • ToolName (Enum) ──────────────────┐                           │  │  │
│  │  │   SHELL, BROWSER, PYTHON,           │                           │  │  │
│  │  │   MEMORY_WRITE, MEMORY_READ,        │ Defines ALL valid tools   │  │  │
│  │  │   GMP_RUN, GIT_COMMIT,              │ and gating options        │  │  │
│  │  │   MAC_AGENT_EXEC_TASK,              │                           │  │  │
│  │  │   LONG_PLAN_EXECUTE, etc.           │                           │  │  │
│  │  │                                     │                           │  │  │
│  │  │ • Capability ───────────────────────┤                           │  │  │
│  │  │   - tool: ToolName                  │ Per-tool permission       │  │  │
│  │  │   - allowed: bool                   │ with rate limits          │  │  │
│  │  │   - rate_limit: int                 │ and scope                 │  │  │
│  │  │   - scope: str                      │                           │  │  │
│  │  │                                     │                           │  │  │
│  │  │ • DEFAULT_L_CAPABILITIES ───────────┘                           │  │  │
│  │  │   L's complete capability set                                   │  │  │
│  │  │   (high-risk tools: scope="requires_igor_approval")             │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    3. EXECUTOR IMPLEMENTATION                         │  │
│  │                                                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │ runtime/l_tools.py                                              │  │  │
│  │  │                                                                 │  │  │
│  │  │ TOOL_EXECUTORS = {                                              │  │  │
│  │  │   "memory_search":      memory_search,                          │  │  │
│  │  │   "memory_write":       memory_write,                           │  │  │
│  │  │   "gmp_run":            gmp_run,          # High-risk           │  │  │
│  │  │   "git_commit":         git_commit,       # High-risk           │  │  │
│  │  │   "mac_agent_exec_task":mac_agent_exec_task, # High-risk        │  │  │
│  │  │   "mcp_call_tool":      mcp_call_tool,                          │  │  │
│  │  │   "world_model_query":  world_model_query,                      │  │  │
│  │  │   "kernel_read":        kernel_read,                            │  │  │
│  │  │   "long_plan.execute":  long_plan_execute_tool,                 │  │  │
│  │  │   "long_plan.simulate": long_plan_simulate_tool,                │  │  │
│  │  │   "symbolic_compute":   (lazy loaded),                          │  │  │
│  │  │   "symbolic_codegen":   (lazy loaded),                          │  │  │
│  │  │   "simulation":         simulation_execute,                     │  │  │
│  │  │ }                                                               │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    4. REGISTRY ADAPTER                                │  │
│  │                                                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │ core/tools/registry_adapter.py                                  │  │  │
│  │  │                                                                 │  │  │
│  │  │ ExecutorToolRegistry                                            │  │  │
│  │  │   • Wraps ToolRegistry from services/research/tools             │  │  │
│  │  │   • Enforces DEFAULT_L_CAPABILITIES for L agent                 │  │  │
│  │  │   • Integrates with GovernanceEngineService                     │  │  │
│  │  │   • Provides get_approved_tools() for agent context             │  │  │
│  │  │   • Provides dispatch_tool_call() for execution                 │  │  │
│  │  │                                                                 │  │  │
│  │  │ register_l_tools() ─────────────────────────────────────────┐   │  │  │
│  │  │   Called at server startup                                  │   │  │  │
│  │  │   1. Creates ToolDefinition for each L-CTO tool             │   │  │  │
│  │  │   2. Registers in Neo4j via ToolGraph                       │   │  │  │
│  │  │   3. Registers executors in base ToolRegistry               │   │  │  │
│  │  └─────────────────────────────────────────────────────────────┘   │  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    5. ORCHESTRATOR LAYER                              │  │
│  │                                                                       │  │
│  │  ┌──────────────────────────┐    ┌────────────────────────────────┐  │  │
│  │  │ orchestrators/           │    │ api/tools/router.py            │  │  │
│  │  │ action_tool/             │    │                                │  │  │
│  │  │ orchestrator.py          │    │ POST /tools/execute            │  │  │
│  │  │                          │    │   → ActionToolOrchestrator     │  │  │
│  │  │ • ActionToolOrchestrator │    │   → Validates & executes       │  │  │
│  │  │ • Validates tool calls   │    │   → Returns result             │  │  │
│  │  │ • Safety assessment      │    └────────────────────────────────┘  │  │
│  │  │ • Retry with backoff     │                                        │  │
│  │  │ • Packet logging         │                                        │  │
│  │  └──────────────────────────┘                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    6. AGENT EXECUTOR                                  │  │
│  │                                                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │ core/agents/executor.py                                         │  │  │
│  │  │                                                                 │  │  │
│  │  │ AgentExecutorService.dispatch_tool_call()                       │  │  │
│  │  │   1. Get executor from get_tool_executor(tool_name)             │  │  │
│  │  │   2. Check capability via DEFAULT_L_CAPABILITIES                │  │  │
│  │  │   3. Check approval for high-risk (scope=requires_igor_approval)│  │  │
│  │  │   4. Execute tool with arguments                                │  │  │
│  │  │   5. Log result to memory substrate                             │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Startup Registration Sequence

```
api/server.py startup
        │
        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SERVER STARTUP (@lifespan)                           │
│                                                                             │
│  1. get_tool_registry() ─────────────────────────────────────────────────┐  │
│     │                                                                    │  │
│     └─► services/research/tools/tool_registry.py                         │  │
│           _initialize_default_tools()                                    │  │
│             • perplexity_search                                          │  │
│             • http_request                                               │  │
│             • mock_search                                                │  │
│             • calculate                                                  │  │
│                                                                          │  │
│  2. await register_l_tools() ────────────────────────────────────────────┤  │
│     │                                                                    │  │
│     └─► core/tools/registry_adapter.py                                   │  │
│           For each ToolDefinition:                                       │  │
│             1. ToolGraph.register_tool(tool_def) → Neo4j                 │  │
│             2. base_registry.register(metadata, executor)                │  │
│           Logs: "✓✓ L-CTO tools registered: N total, M high-risk"       │  │
│                                                                          │  │
│  3. ActionToolOrchestrator(tool_registry, governance_engine) ────────────┤  │
│     │                                                                    │  │
│     └─► orchestrators/action_tool/orchestrator.py                        │  │
│           Stored in app.state.action_tool_orchestrator                   │  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Tool Authorization Flow

```
Tool Call Request
        │
        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. AgentExecutorService receives tool_call from LLM                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. Check if tool_name exists in TOOL_EXECUTORS                              │
│    └─► If not found: return error "Tool not found"                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. Check capability in DEFAULT_L_CAPABILITIES                               │
│    └─► If not allowed: return error "Tool denied by capabilities"           │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. Check scope for high-risk tools                                          │
│    scope == "requires_igor_approval"?                                       │
│    ├─► YES: Check if approval exists in GovernanceApprovals                 │
│    │        └─► If no approval: emit BLOCKED packet, return error           │
│    └─► NO:  Proceed to execution                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│ 5. Execute tool via TOOL_EXECUTORS[tool_name](**arguments)                  │
├─────────────────────────────────────────────────────────────────────────────┤
│ 6. Log result to memory substrate via PacketEnvelope                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ 7. Return ToolCallResult to agent                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

## File Reference

| File                                        | Purpose                     | Key Exports                                                   |
| ------------------------------------------- | --------------------------- | ------------------------------------------------------------- |
| `core/tools/tool_graph.py`                  | Neo4j tool dependency graph | `ToolDefinition`, `ToolGraph`, `L9_TOOLS`, `L_INTERNAL_TOOLS` |
| `core/tools/registry_adapter.py`            | Executor registry wrapper   | `ExecutorToolRegistry`, `register_l_tools()`                  |
| `core/schemas/capabilities.py`              | Capability sandboxing       | `ToolName`, `Capability`, `DEFAULT_L_CAPABILITIES`            |
| `runtime/l_tools.py`                        | Tool implementations        | `TOOL_EXECUTORS`, individual tool functions                   |
| `services/research/tools/tool_registry.py`  | Base in-memory registry     | `ToolRegistry`, `ToolMetadata`, `get_tool_registry()`         |
| `api/tools/router.py`                       | HTTP API for tools          | `POST /tools/execute`                                         |
| `orchestrators/action_tool/orchestrator.py` | Tool orchestration          | `ActionToolOrchestrator`                                      |

## CI Validation

Tool wiring consistency is enforced by `ci/check_tool_wiring.py`:

1. **Check 1**: TOOL_EXECUTORS vs ToolName enum
2. **Check 2**: TOOL_EXECUTORS vs DEFAULT_L_CAPABILITIES
3. **Check 3**: High-risk tools have `scope="requires_igor_approval"`
4. **Check 4**: ToolDefinitions match TOOL_EXECUTORS
5. **Check 5**: l_tools.py ↔ register_l_tools() consistency

---

_Generated by L9 /analyze+evaluate tool audit_
