# Tools Subsystem

## Overview

The **Tools Subsystem** is the Tool registry, discovery, and dispatch for L9 Secure AI OS. It manages tool definitions, capability enforcement, semantic discovery, and safe tool invocation.

**What depends on it:** `core/agents/executor.py`, `core/agents/agent_instance.py`

## Tool Access Methods

### Dynamic Tool Discovery (PREFERRED - GMP-78)

**Status: ACTIVE (v2.0.0+)**

Dynamic discovery uses semantic search to find relevant tools per-task, reducing context overhead by 40-70%.

```python
from core.tools import discover_tools_for_task, is_dynamic_discovery_enabled

# Check if enabled (default: true)
if is_dynamic_discovery_enabled():
    # Discover tools semantically relevant to task
    tools = await discover_tools_for_task(
        "search memory for user preferences",
        top_k=5,
        min_similarity=0.3,
        max_tokens=2000,
    )
    # Returns OpenAI function calling format
```

**Configuration:**
```bash
L9_DYNAMIC_TOOL_DISCOVERY=true      # Feature flag (default: true)
L9_TOOL_DISCOVERY_TOP_K=5           # Max tools per task
L9_TOOL_DISCOVERY_MIN_SIMILARITY=0.3 # Cosine similarity threshold
L9_TOOL_DISCOVERY_MAX_TOKENS=2000   # Token budget for tools
```

**How It Works:**
1. At startup, `sync_all_tool_embeddings()` embeds all tools to pgvector
2. At task execution, `AgentInstance.prepare_dynamic_tools()` is called
3. Semantic search finds relevant tools for the task payload
4. Tools are formatted in OpenAI function calling format
5. Token budget is enforced to prevent context bloat

### Static Tool Binding (DEPRECATED)

**Status: DEPRECATED (emits DeprecationWarning)**

Static binding loads all configured tools into context regardless of task. This is legacy behavior.

```python
# DEPRECATED - will emit DeprecationWarning
from core.tools import L9_TOOLS  # Static list - AVOID

# This happens automatically if dynamic discovery is disabled or fails
tools = agent_instance.get_tool_definitions()  # Falls back to static
```

**To disable deprecation warnings (temporary):**
```bash
L9_DYNAMIC_TOOL_DISCOVERY=false  # Revert to static binding
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    STARTUP (api/server.py)                           │
├─────────────────────────────────────────────────────────────────────┤
│  sync_all_tool_embeddings()                                          │
│    → Reads L_INTERNAL_TOOLS + L9_TOOLS                              │
│    → Generates OpenAI embeddings                                    │
│    → Stores in pgvector tool_embeddings table                       │
└────────────────────────────┬────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│              EXECUTION (executor.py)                                 │
├─────────────────────────────────────────────────────────────────────┤
│  await instance.prepare_dynamic_tools()                             │
│    → discover_tools_for_task(task_payload)                          │
│    → find_relevant_tools() via pgvector                             │
│    → Cache in instance._discovered_tools                            │
└────────────────────────────┬────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│              CONTEXT ASSEMBLY                                        │
├─────────────────────────────────────────────────────────────────────┤
│  instance.get_tool_definitions()                                     │
│    → Returns cached discovered tools (preferred)                    │
│    → OR static binding with DeprecationWarning (fallback)           │
└─────────────────────────────────────────────────────────────────────┘
```

## Directory Layout

```
core/tools/
├── __init__.py              # Exports (v2.0.0 - dynamic discovery)
├── dynamic_discovery.py     # GMP-78 Phase 2 - semantic discovery
├── tool_embeddings.py       # GMP-78 Phase 1 - pgvector storage
├── base_registry.py         # In-memory tool registry
├── registry_adapter.py      # PROTECTED - executor adapter
├── tool_graph.py            # PROTECTED - Neo4j dependency graph
├── sanitizer.py             # Input sanitization
├── tool_audit.py            # Audit logging
├── memory_tools.py          # Memory tool implementations
├── research_tools.py        # Research tool implementations
└── reflection_tools.py      # Reflection tool implementations
```

## Key Components

### `dynamic_discovery.py` — Dynamic Tool Discovery (GMP-78 Phase 2)

```python
async def discover_tools_for_task(
    task_payload: str,
    top_k: int = 5,
    min_similarity: float = 0.3,
    max_tokens: int = 2000,
) -> list[dict[str, Any]]:
    """Semantic search → OpenAI tool format."""

def is_dynamic_discovery_enabled() -> bool:
    """Check feature flag."""

async def get_discovery_stats() -> dict[str, Any]:
    """Health metrics for monitoring."""
```

### `tool_embeddings.py` — Tool Embedding Storage (GMP-78 Phase 1)

```python
async def sync_all_tool_embeddings() -> int:
    """Sync all tools to pgvector (called at startup)."""

async def find_relevant_tools(
    query: str,
    top_k: int = 5,
    min_similarity: float = 0.3,
) -> list[ToolEmbeddingResult]:
    """Semantic search for tools."""
```

### `tool_graph.py` — Tool Dependency Graph

```python
class ToolDefinition:
    """Definition of a tool for graph registration."""
    name: str
    description: str
    category: str
    risk_level: str  # "low" | "medium" | "high"
    requires_igor_approval: bool
    negative_constraints: list[str]  # When NOT to use

L9_TOOLS: list[ToolDefinition]  # DEPRECATED - use dynamic discovery
L_INTERNAL_TOOLS: list[ToolDefinition]  # Internal tools for L agent
```

### `sanitizer.py` — Input Sanitization

```python
class ToolInputSanitizer:
    """Centralized input sanitization for tool arguments."""
    def sanitize(self, value: Any) -> Any: ...
```

## Health Monitoring

```bash
GET /health/services
```

```json
{
  "dynamic_tool_discovery": {
    "synced": true,
    "tool_count": 45,
    "enabled": true,
    "top_k": 5
  }
}
```

## Invariants

- **Dynamic discovery is default**: Set `L9_DYNAMIC_TOOL_DISCOVERY=false` to revert
- **Tool names must match OpenAI pattern**: `^[a-zA-Z0-9_-]+$`
- **Destructive tools require approval gates**
- **All tool executions logged to PacketEnvelope audit trail**
- **Tool dispatch respects AgentCapabilities enum**
- **Token budget enforced**: Tools stop loading at `max_tokens` limit

## Configuration

### Feature Flags

```yaml
L9_DYNAMIC_TOOL_DISCOVERY: true  # Enable semantic discovery (default)
L9_ENABLE_TOOLS_TRACING: true    # Enable detailed tracing
```

### Environment Variables

```bash
# Dynamic Discovery (GMP-78)
L9_DYNAMIC_TOOL_DISCOVERY=true
L9_TOOL_DISCOVERY_TOP_K=5
L9_TOOL_DISCOVERY_MIN_SIMILARITY=0.3
L9_TOOL_DISCOVERY_MAX_TOKENS=2000

# General
TOOLS_LOG_LEVEL=INFO
```

## Observability

### Logging

```json
{
  "event": "Dynamic tool discovery complete",
  "task_preview": "search memory for...",
  "tools_discovered": 3,
  "top_k": 5
}
```

### Metrics

- `tools_discovery_duration_ms` — Discovery latency (histogram)
- `tools_discovered_count` — Tools per task (histogram)
- `tools_static_fallback_total` — Static binding fallbacks (counter)

## Testing

### Unit Tests

Located in `tests/unit/`:
- `test_dynamic_tool_discovery.py` — Dynamic discovery tests
- `tests/core/tools/test_tool_graph_unified.py` — Tool graph tests

## AI Usage Rules

### ✅ Allowed Scopes (AI can modify freely)

- `dynamic_discovery.py` — Discovery logic
- `sanitizer.py` — Input validation
- `memory_tools.py` — Memory tool implementations
- `research_tools.py` — Research tool implementations
- `reflection_tools.py` — Reflection tool implementations

### ⚠️ Restricted Scopes (requires human review)

- `tool_embeddings.py` — Embedding sync logic
- Schema changes
- Feature flag logic

### ❌ Forbidden Scopes (never modify without approval)

- `registry_adapter.py` — PROTECTED (executor wiring)
- `tool_graph.py` — PROTECTED (L9_TOOLS definitions)
- `__init__.py` — PROTECTED (exports)

## Related

- ADR-0064: Dynamic Tool Discovery
- `config/settings.py` — Feature flag definitions
- `api/server.py` — Startup sync
- `core/agents/executor.py` — Execution wiring

---

*L9 Secure AI OS — Tools Subsystem*
*Version: 2.0.0 (GMP-78 Dynamic Tool Discovery)*
*Updated: 2026-01-25*
