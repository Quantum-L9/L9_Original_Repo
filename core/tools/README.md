---
dora:
  version: "1.0"
  type: subsystem_readme
  generated: "2026-02-17 00:14:44 UTC"
  generator: scripts/generate_subsystem_readmes.py
  config: config/subsystems/readme_config.yaml
  time_verified: "system clock (verification skipped)"
  auto_generated: true
---

# Tool Registry & Dispatch

> **Tier:** CORE | **Path:** `core/tools` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                         Tool Registry & Dispatch                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │    core_tools   │ ───► │  Outbound   │                  │
│  │ Dependencies│      │   Module    │      │ Dependencies│                  │
│  └─────────────┘      └─────────────┘      └─────────────┘                  │
│                              │                                              │
│                              ▼                                              │
│                    ┌─────────────────┐                                      │
│                    │  Memory/Audit   │                                      │
│                    │   Substrate     │                                      │
│                    └─────────────────┘                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Overview

Tool definitions, capability enforcement, and safe tool invocation

**Purpose:** Manages tool definitions, capability enforcement, approval gates, and safe tool invocation.

**What depends on it:** `core/agents/executor.py`

---

## Responsibilities and Boundaries

### What This Module Owns

- Tool manifest registry and discovery
- Capability enforcement per agent
- Approval gates for high-risk tools
- Tool input sanitization and validation
- Audit logging of all tool executions

### What This Module Does NOT Do

- Actual tool implementation (tools are self-contained)
- Agent execution logic (owned by core/agents)
- Memory operations (owned by memory/)

### Inbound Dependencies

| Module | Purpose |
|--------|---------|
| `core/agents/executor.py` | Uses this module |

### Outbound Dependencies

| Module | Purpose |
|--------|---------|
| `runtime/l_tools.py` | Required dependency |
| `core/governance/approval_manager.py` | Required dependency |

---

## Directory Layout

```
core/tools/
├── __init__.py
├── agent_self_modify.py
├── base_registry.py
├── discovery_tracing.py
├── dynamic_discovery.py
├── introspection_tools.py
├── memory_tools.py
├── prompt_caching.py
├── reflection_tools.py
├── registry_adapter.py
├── registry_cache.py
├── research_tools.py
├── sanitizer.py
├── semantic_discovery.py
├── semantic_tool_search.py
└── ... (4 more files)
```

| File | Purpose |
|------|---------|
| `registry_adapter.py` | RegistryAdapter for tool discovery and dispatch (PROTECTED) |
| `tool_graph.py` | Tool definitions and L_TOOLS_DEFINITIONS registry (PROTECTED) |
| `sanitizer.py` | Input sanitization and validation for tool arguments |
| `memory_tools.py` | Memory-related tools (search, write, retrieve) |
| `research_tools.py` | Research and web search tools |
| `reflection_tools.py` | Self-reflection and metacognition tools |
| `tool_embeddings.py` | Semantic tool discovery via embeddings |

### Naming Conventions

- **Tool definitions:** UPPER_SNAKE_CASE in L_TOOLS_DEFINITIONS
- **Tool wrappers:** `<name>_tool` function
- **Tool classes:** `<Name>Tool` (if class-based)

---

## Key Components

### `tool_embeddings.py` — ToolEmbeddingResult

```python
class ToolEmbeddingResult:
    """Result from tool embedding search."""

    # Key methods:

```

**Lines:** 73-81 in `tool_embeddings.py`

### `prompt_caching.py` — CacheMetrics

```python
class CacheMetrics:
    """Metrics for prompt caching."""

    # Key methods:

    def hit_rate(self, ...) -> float: ...

```

**Public Methods:** `hit_rate`

**Lines:** 48-62 in `prompt_caching.py`

### `prompt_caching.py` — PromptCachingStrategy

```python
class PromptCachingStrategy:
    """Two-tier prompt caching strategy for tool-heavy agents."""

    # Key methods:

    def __init__(self, ...): ...

    def build_cached_system_prompt(self, ...) -> str: ...

    def build_dynamic_tool_context(self, ...) -> str: ...

    def build_full_prompt(self, ...) -> tuple[str, str]: ...

    def estimate_token_savings(self, ...) -> dict[str, int]: ...

```

**Public Methods:** `__init__`, `build_cached_system_prompt`, `build_dynamic_tool_context`, `build_full_prompt`, `estimate_token_savings`

**Lines:** 65-246 in `prompt_caching.py`

### `prompt_caching.py` — CachingMetricsCollector

```python
class CachingMetricsCollector:
    """Initializes the CachingMetricsCollector for tracking cache performance metrics in prompt caching strategy."""

    # Key methods:

    def __init__(self, ...): ...

    def record_cache_hit(self, ...) -> None: ...

    def record_cache_miss(self, ...) -> None: ...

    def record_latency(self, ...) -> None: ...

    def get_metrics(self, ...) -> dict[str, Any]: ...

```

**Public Methods:** `__init__`, `record_cache_hit`, `record_cache_miss`, `record_latency`, `get_metrics`

**Lines:** 249-292 in `prompt_caching.py`

### `sanitizer.py` — ToolInputSanitizationError

```python
class ToolInputSanitizationError:
    """Raised when tool input cannot be sanitized/validated."""

    # Key methods:

    def __init__(self, ...) -> None: ...

```

**Public Methods:** `__init__`

**Lines:** 61-73 in `sanitizer.py`


---

## Data Models and Contracts

The following data models define the contracts for this subsystem:

- **`ToolSchema`** — JSON Schema for tool parameters (OpenAI function calling compatible).

### Exported Symbols (`__all__`)

`CacheConfig`, `CacheEntry`, `CacheMetrics`, `CacheStrategy`, `CachedToolRegistry`, `CachingMetricsCollector`, `DiscoveryMethod`, `DiscoveryPhase`, `DiscoveryResult`, `DiscoveryTrace`

*...and 62 more*

### Module Constants

| Constant | Value | Line |
|----------|-------|------|
| `EMBEDDING_MODEL` | `os.getenv('TOOL_EMBEDDING_MODEL', 'text-...` | 68 |
| `EMBEDDING_DIMENSION` | `1536` | 69 |
| `AGENT_SELF_MODIFY_TOOL_DEFINITIONS` | `[{'tool_id': 'agent_add_directive', 'nam...` | 382 |
| `INJECTION_PATTERNS` | `['\\bDROP\\b', '\\bDELETE\\b', '\\bTRUNC...` | 47 |
| `MEMORY_TOOL_DEFINITIONS` | `[{'tool_id': 'memory_search', 'name': 'm...` | 291 |
| `DEFAULT_TENANT_ID` | `os.getenv('L9_TENANT_ID', 'l-cto')` | 69 |
| `OPENAI_TOOL_NAME_PATTERN` | `re.compile('^[a-zA-Z0-9_-]+$')` | 73 |
| `L9_TOOLS` | `[ToolDefinition(name='web_search', descr...` | 662 |

*...and 3 more constants*

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

class CoreToolsRequest(BaseModel):
    """Request model for core_tools operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class CoreToolsResponse(BaseModel):
    """Response model for core_tools operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Tool names must exist in L_TOOLS_DEFINITIONS registry**
- **Destructive tools require explicit approval gates**
- **All tool executions logged to PacketEnvelope audit trail**
- **Tool dispatch respects AgentCapabilities enum**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Core_Tools components are discovered and registered.
2. **Configuration:** Settings loaded from environment and config files.
3. **Dependencies:** Required services (Redis, PostgreSQL, etc.) are connected.
4. **Initialization:** Internal state is initialized; ready for requests.

### Main Execution

1. **Request received:** Validate input against schema.
2. **Processing:** Execute core logic with appropriate error handling.
3. **State updates:** Persist any state changes atomically.
4. **Response:** Return structured response with timing metadata.

### Shutdown

1. **Graceful stop:** Stop accepting new requests.
2. **Drain:** Complete in-flight operations (with timeout).
3. **Cleanup:** Release resources, close connections.
4. **Log:** Emit shutdown complete event.

### Background Tasks

No background tasks. Operations are request-driven.

---

## Configuration

### Feature Flags

```yaml
# Core_Tools feature flags
L9_ENABLE_CORE_TOOLS_TRACING: true  # Enable detailed tracing
L9_ENABLE_CORE_TOOLS_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_CORE_TOOLS_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
core_tools:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
CORE_TOOLS_LOG_LEVEL=INFO
CORE_TOOLS_TIMEOUT=30
CORE_TOOLS_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `async def embed_tool_description(description) -> list[float] | None`

Generate embedding vector for a tool description.

- **File:** `tool_embeddings.py:137`
- **Async:** Yes
- **Returns:** `list[float] | None`

#### `async def store_tool_embedding(tool_name, description, category, negative_constraints, metadata, repository) -> bool`

Store a tool's embedding in the database.

- **File:** `tool_embeddings.py:162`
- **Async:** Yes
- **Returns:** `bool`

#### `async def find_relevant_tools(query, top_k, exclude_categories, min_similarity, repository) -> list[ToolEmbeddingResult]`

Find tools relevant to a query using semantic search.

- **File:** `tool_embeddings.py:221`
- **Async:** Yes
- **Returns:** `list[ToolEmbeddingResult]`

#### `async def find_tools_keyword(query, top_k, min_rank, repository) -> list[ToolEmbeddingResult]`

Find tools using BM25 keyword search (PostgreSQL full-text).

- **File:** `tool_embeddings.py:298`
- **Async:** Yes
- **Returns:** `list[ToolEmbeddingResult]`

#### `async def find_tools_hybrid(query, top_k, semantic_weight, keyword_weight, min_similarity, repository) -> list[ToolEmbeddingResult]`

Hybrid tool discovery combining semantic + keyword (BM25) search.

- **File:** `tool_embeddings.py:367`
- **Async:** Yes
- **Returns:** `list[ToolEmbeddingResult]`


### Usage Example

```python
from core.tools import RegistryAdapter, AgentCapabilities

adapter = RegistryAdapter()

# Get available tools for agent
tools = adapter.get_tools_for_capabilities(
    AgentCapabilities.RESEARCH | AgentCapabilities.MEMORY_READ
)

# Invoke a tool
result = await adapter.invoke_tool(
    tool_name="search_web",
    arguments={"query": "AI breakthroughs 2025"},
    agent_id="researcher-001",
    correlation_id="corr-xyz789",
)

print(result.success)  # True
print(result.output)   # Search results
```


---

## Observability

### Logging

Core Tools operations emit structured JSON logs:

```json
{
  "timestamp": "2026-02-17T00:14:44Z",
  "level": "INFO",
  "module": "core.tools",
  "message": "Operation completed",
  "correlation_id": "corr-xyz789",
  "agent_id": "agent-001",
  "duration_ms": 125
}
```

**Log Levels:**
- `DEBUG` — Detailed execution steps (off in production)
- `INFO` — Lifecycle events, successful operations
- `WARNING` — Timeouts, resource warnings, recoverable errors
- `ERROR` — Failures, exceptions, unrecoverable errors

### Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `core_tools_operation_duration_ms` | Histogram | Operation latency distribution |
| `core_tools_operation_total` | Counter | Total operations processed |
| `core_tools_error_total` | Counter | Total errors encountered |
| `core_tools_active_connections` | Gauge | Current active connections |

### Tracing

Core Tools emits OpenTelemetry spans:

- `core_tools.execute` — Root span for operation
  - `core_tools.validate` — Input validation
  - `core_tools.process` — Core processing
  - `core_tools.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/core_tools/`:
- `test_core_tools.py` — Core unit tests
- `test_core_tools_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test core_tools with real dependencies
- Test cross-subsystem interactions
- Test failure scenarios and recovery

### Known Edge Cases

1. **Tool not found** — Requested tool name not in registry → raise ToolNotFoundError
1. **Capability denied** — Agent lacks capability for tool → log warning, return capability error
1. **Approval required** — High-risk tool needs Igor approval → block until approved or timeout
1. **Input validation failure** — Tool arguments fail schema validation → return validation error

---

## AI Usage Rules

### ✅ Allowed Scopes (AI can modify freely)

- `sanitizer.py` — Application logic, safe to modify
- `memory_tools.py` — Application logic, safe to modify
- `research_tools.py` — Application logic, safe to modify
- `reflection_tools.py` — Application logic, safe to modify
- `tool_embeddings.py` — Application logic, safe to modify
- `tests/**` — Application logic, safe to modify
- `docs/**` — Application logic, safe to modify

### ⚠️ Restricted Scopes (requires human review)

- `registry_adapter.py` — Requires human review before merge
- `tool_graph.py` — Requires human review before merge

### ❌ Forbidden Scopes (NEVER modify without explicit approval)

- `registry_adapter.py` — PROTECTED: Changes break system invariants
- `tool_graph.py` — PROTECTED: Changes break system invariants
- `__init__.py` — PROTECTED: Changes break system invariants

### Required Pre-Reading

1. [`README-L9_ARCHITECTURE.md`](README-L9_ARCHITECTURE.md)
2. [`docs/CURSOR-RUNBOOK.md`](docs/CURSOR-RUNBOOK.md)
3. [`core/tools/README.md`](core/tools/README.md)

### Change Policy

All changes proposed by AI tools must:
1. Be scoped PRs with clear commit messages
2. Include tests (unit + integration where applicable)
3. Update documentation if APIs change
4. Respect feature flags for gradual rollout
5. Get human approval for restricted scopes
