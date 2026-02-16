# L9 Core Subsystems: Complete README Templates

---

## 1. Agents Subsystem README

### File: `l9/core/agents/README.md`

```markdown
# Agents Subsystem

## Subsystem Overview

The **Agents subsystem** is the execution runtime for autonomous agents in L9 OS. It defines agent kernels (compute execution units), provides a registry of available agents, manages agent lifecycle (initialization, execution, shutdown), and enforces delegation boundaries. 

Agents are the "main characters" of the system—they receive goals, plan multi-step workflows, invoke tools, read memory, and produce output. Every agent is tied to a kernel entry point that ensures type safety, memory isolation, and observability.

**What depends on it:** API handlers, task queue workers, long-plan graph executor, memory subsystem (agents query and update memory), tool registry (agents invoke tools).

## Responsibilities and Boundaries

### What This Module Owns

- **Agent execution model:** Starting, running, and cleanly shutting down agents.
- **Kernel registry:** Mapping agent types (e.g., "researcher", "executor") to kernel classes.
- **Agent lifecycle:** Initialization (reading config), execution (main loop), cleanup (logging final state).
- **Delegation and authority:** Agents can delegate to sub-agents; authority is tracked and audited.
- **Context propagation:** Correlation IDs, user identity, execution context flow through agent execution.
- **Agent manifests:** YAML definitions of agent config, capabilities, and tool access.

### What This Module Does NOT Do

- **Tool execution** — That is owned by the tool registry.
- **Memory persistence** — That is owned by the memory subsystem.
- **Network communication** — That is the WebSocket orchestrator's job.
- **Scheduling and queueing** — That is the task queue's job.
- **Authentication** — That is handled at the API gateway.

### Inbound Dependencies

- **Task Queue** — Agents are enqueued and executed by workers.
- **Memory Subsystem** — Agents read/write memory during execution.
- **Tool Registry** — Agents invoke tools via the tool registry.
- **Kernel Loader** — Agents are dispatched via the kernel loader entry point.

### Outbound Dependencies

- **Observability** — Agents emit structured logs and metrics.
- **Memory Substrate** — Agents read and write to Redis/PostgreSQL.
- **Tool Registry** — Agents invoke tools by name and receive results.

## Directory Layout

```
l9/core/agents/
├── README.md                    # This file
├── __init__.py                  # Package exports
├── kernel.py                    # Kernel class and entry point (PROTECTED)
├── executor.py                  # Agent execution loop and lifecycle
├── registry.py                  # Agent type registry and discovery
├── manifest.py                  # Agent manifest schema (YAML parsing)
├── context.py                   # Execution context (correlation ID, user, etc.)
├── builtin/                     # Built-in agents (researcher, executor, planner)
│   ├── researcher.py            # Researcher agent kernel
│   ├── executor.py              # Task executor agent kernel
│   └── planner.py               # Long-plan orchestrator agent
├── config/                      # Agent configuration files
│   ├── researcher.yaml          # Researcher agent manifest
│   ├── executor.yaml            # Executor agent manifest
│   └── planner.yaml             # Planner agent manifest
└── tests/                       # Unit and integration tests
    ├── test_kernel.py           # Kernel entry point tests
    ├── test_executor.py         # Agent lifecycle tests
    └── test_registry.py         # Agent discovery tests
```

### Naming Conventions

- **Kernel classes:** `<AgentName>Kernel` (e.g., `ResearcherKernel`, `ExecutorKernel`)
- **Executor classes:** `<AgentName>Executor` (e.g., `ResearcherExecutor`)
- **Config files:** `<agent-name>.yaml` (kebab-case, matches kernel name)
- **Private methods:** `_method_name()` (indicates internal helper)
- **Public APIs:** Defined in `kernel.py` and `__init__.py`

### Domain-Driven Design

We follow a **kernel-based execution model**:

- **Kernel:** Entry point for agent execution (single responsibility: dispatch).
- **Executor:** Implements the agent's main loop (plan → tool invocation → memory update).
- **Context:** Carries execution metadata (correlation ID, user, deadline, token budget).

This separates **entry point logic** (kernel, must be deterministic) from **execution logic** (executor, can be complex).

## Key Components

### `kernel.py`

```python
class Kernel:
    """Base class for agent kernels. Defines the entry point interface."""
    
    async def execute(
        self,
        agent_id: str,
        goal: str,
        memory_context: dict,
        tools_available: list[str],
        context: ExecutionContext,
    ) -> AgentResult:
        """
        Execute the agent with a goal.
        
        Args:
            agent_id: Unique identifier for this agent instance
            goal: The task or goal the agent should work toward
            memory_context: Recent memory entries (short-term context)
            tools_available: Names of tools the agent can invoke
            context: Execution context (correlation ID, deadline, etc.)
        
        Returns:
            AgentResult with output, memory updates, and execution trace
        
        Note:
            This is the PROTECTED entry point. Changes here require human review.
        """
        raise NotImplementedError
```

**Status:** Public API. All agents must inherit from this class.

### `executor.py`

```python
class AgentExecutor:
    """
    Main execution loop for agents.
    Coordinates planning, tool invocation, and memory updates.
    """
    
    async def run(
        self,
        kernel: Kernel,
        goal: str,
        max_steps: int = 20,
    ) -> ExecutionTrace:
        """Execute agent with up to max_steps planning/action cycles."""
        ...
```

**Status:** Public API. Subclass or use directly for custom agents.

### `registry.py`

```python
class AgentRegistry:
    """Discover and instantiate agents by name."""
    
    def get_agent(self, agent_name: str) -> Kernel:
        """Get a kernel instance by agent name (e.g., 'researcher')."""
        ...
    
    def list_agents(self) -> list[dict]:
        """List all available agents with metadata."""
        ...
```

**Status:** Public API. Used by the task queue and API handlers.

### `manifest.py`

```python
class AgentManifest:
    """Parsed agent configuration from YAML."""
    
    name: str  # Unique agent identifier
    description: str  # Human-readable purpose
    tools: list[str]  # Tools this agent can invoke
    memory_layers: list[str]  # Which memory layers it can access
    timeout_seconds: int  # Max execution time
    token_budget: int  # Max LLM tokens
```

**Status:** Public data model. Agents are discovered by manifest.

## Data Models and Contracts

### AgentManifest (YAML Schema)

```yaml
name: "researcher"  # Unique agent identifier
description: "Autonomous research agent using web search and memory"
version: "1.0.0"  # Schema version
agents_supported: "1.0"  # L9 agents API version

capabilities:
  - "semantic_search"  # Agent can search memory
  - "tool_invocation"  # Agent can call tools
  - "delegation"  # Agent can delegate to other agents

tools:
  - "search_web"  # Tool names this agent can invoke
  - "fetch_url"
  - "read_memory"
  - "write_memory"

constraints:
  timeout_seconds: 600  # Max 10 minutes per execution
  max_tool_calls: 50  # Max 50 tool invocations per run
  token_budget: 100000  # Max tokens from LLM
  memory_read_limit_entries: 1000  # Max memory entries to read

default_config:
  model: "gpt-4-turbo"  # Default LLM model
  temperature: 0.7  # Sampling temperature
  max_planning_steps: 20  # Max steps before completing
```

**Invariants:**
- Agent names are lowercase, alphanumeric, underscore-separated (`[a-z0-9_]+`).
- Tool names must exist in the tool registry.
- Timeouts must be positive integers (seconds).
- Token budgets must be > 1000.

### ExecutionContext (Data Model)

```python
@dataclass
class ExecutionContext:
    """Metadata for agent execution."""
    
    correlation_id: str  # Unique ID linking logs and memory
    user_id: str  # Who triggered this execution
    deadline: datetime  # When execution must complete
    token_budget_remaining: int  # Tokens left to spend
    parent_agent_id: Optional[str]  # If delegated, parent agent
    execution_trace: list[ExecutionEvent]  # Log of all steps
```

**Invariants:**
- `correlation_id` is a UUIDv4.
- `deadline` is UTC ISO-8601 timestamp.
- `token_budget_remaining` is always >= 0.

### AgentResult (Return Type)

```python
@dataclass
class AgentResult:
    """Result of agent execution."""
    
    agent_id: str
    goal: str
    status: Literal["success", "timeout", "error", "incomplete"]
    output: str  # What the agent produced
    memory_updates: list[MemoryEntry]  # Data the agent learned
    tool_invocations: list[ToolInvocation]  # All tools the agent called
    token_usage: int  # Total tokens used
    execution_time_ms: float  # Total wall-clock time
    error: Optional[str]  # If status == "error", error message
```

## Execution and Lifecycle

### Agent Startup

1. **Discovery:** Agent name is resolved via `AgentRegistry.get_agent()`.
2. **Manifest loading:** YAML config is parsed and validated.
3. **Kernel instantiation:** A kernel instance is created (lightweight).
4. **Context creation:** `ExecutionContext` is initialized with correlation ID, user, deadline.

### Agent Execution (Main Loop)

1. **Planning:** Kernel calls LLM to plan next action or produce final output.
2. **Tool invocation:** If the plan calls a tool, it is dispatched to the tool registry.
3. **Memory updates:** Agent reads recent memory and writes new findings.
4. **Iteration:** Repeat until goal is achieved or timeout/max-steps reached.

### Agent Shutdown

1. **Finalization:** Kernel writes any remaining state to memory.
2. **Logging:** Execution trace is logged (structured JSON).
3. **Cleanup:** Context is released, resources freed.
4. **Result:** `AgentResult` is returned to the caller.

### Background Tasks

None. Agents are synchronous (blocking) from the task queue worker's perspective. Async execution is handled at the queue level.

## Configuration

### Feature Flags

```yaml
L9_ENABLE_AGENT_TRACING: true  # Enable detailed execution tracing
L9_ENABLE_AGENT_CHECKPOINTING: false  # Save intermediate states
L9_ENABLE_AGENT_DELEGATION: true  # Allow agents to delegate
L9_ENABLE_SEMANTIC_MEMORY_FOR_AGENTS: true  # Semantic search for agents
```

### Tuning Parameters

```yaml
agent:
  default_timeout_seconds: 600
  default_token_budget: 100000
  max_concurrent_agents: 100
  executor_pool_size: 20
  memory_context_window: 1000  # entries to load per execution
```

### Environment Variables

```bash
AGENT_REGISTRY_PATH=/app/l9/core/agents/config/  # Where manifests live
AGENT_LOG_LEVEL=info  # Logging verbosity
AGENT_TRACING_ENABLED=true  # Send traces to Datadog
```

## API Surface (Public)

### Kernel Entry Point

```python
async def Kernel.execute(
    agent_id: str,
    goal: str,
    memory_context: dict,
    tools_available: list[str],
    context: ExecutionContext,
) -> AgentResult
```

**Usage:**
```python
from l9.core.agents import AgentRegistry

registry = AgentRegistry()
researcher = registry.get_agent("researcher")

result = await researcher.execute(
    agent_id="researcher-001",
    goal="Find the top 3 AI breakthroughs in 2025",
    memory_context={"recent_findings": [...]},
    tools_available=["search_web", "fetch_url"],
    context=ExecutionContext(
        correlation_id=str(uuid4()),
        user_id="user-123",
        deadline=datetime.utcnow() + timedelta(minutes=10),
        token_budget_remaining=100000,
    ),
)

print(result.output)  # Agent's findings
print(result.tool_invocations)  # Tools it called
print(result.memory_updates)  # What it learned
```

### Registry

```python
registry = AgentRegistry()

# Get a kernel
kernel = registry.get_agent("researcher")

# List all agents
agents = registry.list_agents()
# Returns: [{"name": "researcher", "description": "...", "tools": [...]}, ...]
```

## Observability

### Logging

Agents emit **structured JSON logs** with:

```json
{
  "timestamp": "2025-12-25T08:42:00Z",
  "level": "INFO",
  "module": "agents.executor",
  "message": "Agent step completed",
  "agent_id": "researcher-001",
  "goal": "Find AI breakthroughs",
  "correlation_id": "corr-abc123",
  "step_number": 3,
  "action_type": "tool_invocation",
  "tool_name": "search_web",
  "duration_ms": 1250,
  "status": "success"
}
```

**Log levels:**
- `DEBUG` — Detailed execution steps (off in production).
- `INFO` — Agent lifecycle events, tool calls, memory updates.
- `WARNING` — Timeouts, token budget warnings, delegation failures.
- `ERROR` — Agent crashes, tool failures, memory access denied.

### Metrics

- `agent_execution_duration_ms` — Agent task latency (histogram)
- `agent_goal_success_rate` — % of agents reaching their goal (gauge)
- `agent_tool_invocations_total` — Total tools called by agents (counter)
- `agent_memory_operations_total` — Total memory reads/writes (counter)
- `agent_delegation_depth` — Max delegation chain length (gauge)

### Tracing

Agents emit OpenTelemetry spans:
- `agent.execute` — Root span for entire execution
  - `agent.plan` — Span for planning step
  - `agent.tool_invoke` — Span for each tool call
  - `agent.memory.read` — Span for memory query
  - `agent.memory.write` — Span for memory update

## Testing

### Unit Tests

Located in `l9/core/agents/tests/test_*.py`.

**Examples:**
- `test_kernel.py` — Tests for `Kernel.execute()` entry point with mocked memory/tools.
- `test_executor.py` — Tests for agent lifecycle: startup, multi-step execution, shutdown.
- `test_registry.py` — Tests for agent discovery and instantiation.
- `test_manifest.py` — Tests for YAML parsing and schema validation.

### Integration Tests

Located in `tests/integration/test_agents_*.py`.

**Examples:**
- `test_agents_with_memory.py` — Agents executing with real memory substrate.
- `test_agents_with_tools.py` — Agents invoking real sandboxed tools.
- `test_agents_delegation.py` — One agent delegating to another.

### Known Edge Cases

1. **Token exhaustion:** Agent hits token budget mid-execution → returns partial result.
2. **Tool not available:** Agent tries to invoke a tool not in its manifest → logged, agent continues.
3. **Memory timeout:** Agent tries to read memory but query times out → agent continues with cached data.
4. **Deadline exceeded:** Execution time exceeds context deadline → agent is interrupted and result returned.

## AI Usage Rules for This Subsystem

### What AI Can Safely Modify

✅ **Application logic:**
- Executor loop logic (planning, iteration, retry).
- New built-in agents (e.g., `NewAgentKernel` subclass).
- Tests (unit tests, fixtures, test data).
- Documentation and examples.

### What Requires Human Review

⚠️ **Restricted scopes:**
- Changes to `Kernel.execute()` signature (breaking change to agent contract).
- Agent manifest schema changes (impacts all existing agents).
- Feature flag logic (`L9_ENABLE_*`).
- Timeout or token budget defaults.

### What Is Forbidden

❌ **Never modify:**
- `l9/core/agents/kernel.py` (entry point, protected).
- Agent names or removal of built-in agents.
- Authentication/authorization for agent execution.
- Memory substrate binding (how agents read/write memory).

### Required Pre-Reading

Before proposing changes to this subsystem, AI must read:

1. **`docs/architecture.md`** — System design and agent role.
2. **`docs/ai-collaboration.md`** — AI usage rules.
3. **`l9/core/agents/kernel.py`** (first 50 lines) — Entry point interface.
4. **This file** — Subsystem overview and contracts.

---

## 2. Memory Subsystem README

### File: `l9/core/memory/README.md`

[TEMPLATE: Similar structure to agents subsystem, but focused on:]

- **Responsibilities:** Multi-layer storage (short-term in Redis, long-term in PostgreSQL), semantic indexing, retrieval.
- **Key components:** `semantic_search.py`, `audit_log.py`, `knowledge_graph.py`, `retention_policy.py`.
- **Data models:** `MemoryEntry`, `MemoryQuery`, `RetrievalResult`.
- **APIs:** `memory.search()`, `memory.write()`, `memory.delete()`, `memory.audit_log()`.
- **Configuration:** Retention policies, semantic embedding model, index refresh interval.
- **Observability:** Memory latency, cache hit rate, semantic search accuracy.

---

## 3. Tool Registry Subsystem README

### File: `l9/core/tools/README.md`

[TEMPLATE: Similar structure, but focused on:]

- **Responsibilities:** Tool manifest registry, sandboxing, resource limits, execution.
- **Key components:** `registry.py`, `sandbox.py`, `manifest.py`, `executor.py`.
- **Data models:** `ToolManifest`, `ToolInvocation`, `ToolResult`.
- **APIs:** `registry.invoke()`, `registry.get_tool()`, `registry.validate_input()`.
- **Configuration:** Resource limits (CPU, memory, disk), timeout, rate limits per tool.
- **Observability:** Tool invocation count, execution latency, sandboxing violations.

---

## 4. API & Gateway Subsystem README

### File: `l9/api/README.md`

[TEMPLATE: Similar structure, but focused on:]

- **Responsibilities:** HTTP and WebSocket API surface, authentication, request validation.
- **Key components:** `server.py` (FastAPI app), `routes/`, `websocket_handler.py`, `auth.py`.
- **Data models:** Request/response schemas (Pydantic models).
- **APIs:** HTTP endpoints (`/agents/<id>/execute`, `/memory/search`, etc.), WebSocket events.
- **Configuration:** CORS origins, rate limits, auth secrets.
- **Observability:** Request latency, error rates, authentication failures.

---

## 5. README.meta.yaml Template for Each Subsystem

Each README should have a corresponding `.meta.yaml` file for codegen/validation:

```yaml
location: "/l9/core/agents/README.md"
type: "subsystem_readme"
metadata:
  subsystem: "agents"
  module_path: "l9/core/agents/"
  owner: "Igor"
  last_updated: "2025-12-25"
purpose: |
  Documents the agent kernel, registry, and execution model.

sections:
  overview: { required: true }
  responsibilities: { required: true }
  components: { required: true }
  data_models: { required: true }
  lifecycle: { required: true }
  api_surface: { required: true }
  observability: { required: true }
  testing: { required: false }
  ai_rules: { required: true }

invariants:
  - "Agent IDs are UUIDv4"
  - "Agent execution uses kernel entry point"
  - "All state is in memory substrate"

ai_collaboration:
  allowed_scopes:
    - "Application logic: executors, tests, docs"
  restricted_scopes:
    - "Kernel entry points, manifest schema"
  forbidden_scopes:
    - "kernel.py, auth, memory substrate"
  required_pre_reading:
    - "docs/architecture.md"
    - "docs/ai-collaboration.md"
    - "l9/core/agents/kernel.py (50 lines)"
  change_policy: |
    AI changes must be scoped PRs with tests and docs.
```

---

This template suite is ready to integrate into your repo. Each subsystem README follows the same structure, making it easy for:
- **Humans** to understand scope, APIs, and invariants.
- **AI tools** to know exactly what they can modify and what requires review.
- **Codegen** to validate that generated code respects subsystem contracts.
```
