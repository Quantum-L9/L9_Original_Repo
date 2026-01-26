# ADR 0017: Tool Definition Schema

## Status

Accepted

## Pattern

All tools defined via `ToolDefinition` dataclass with OpenAI-compatible naming (no dots, spaces).

## Files

- `core/tools/tool_graph.py` - ToolDefinition dataclass
- `runtime/l_tools.py` - L9 tool definitions
- `core/tools/registry_adapter.py` - Tool registry

## Import Block

```python
from core.tools.tool_graph import ToolDefinition, ToolParameter
from core.tools.registry_adapter import ToolRegistry
```

## Minimal Implementation

```python
from dataclasses import dataclass, field
from typing import Callable, Any
import re

# OpenAI function calling name pattern
TOOL_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")

@dataclass
class ToolParameter:
    """Single parameter for a tool."""
    name: str
    type: str  # "string", "integer", "boolean", "object", "array"
    description: str
    required: bool = True
    default: Any = None

@dataclass
class ToolDefinition:
    """Definition of an executable tool."""
    tool_id: str                    # Must match TOOL_NAME_PATTERN
    name: str                       # Human-readable name
    description: str                # What the tool does
    parameters: list[ToolParameter] = field(default_factory=list)
    handler: Callable | None = None # Async function to execute

    # Risk classification
    is_destructive: bool = False    # Modifies state
    requires_igor_approval: bool = False  # High-risk
    risk_level: str = "low"         # low|medium|high|critical

    def __post_init__(self):
        if not TOOL_NAME_PATTERN.match(self.tool_id):
            raise ValueError(
                f"Tool ID '{self.tool_id}' invalid. "
                f"Must match {TOOL_NAME_PATTERN.pattern}"
            )
```

## Usage Example

```python
# Define a tool
memory_search = ToolDefinition(
    tool_id="memory_search",         # ✅ Valid: alphanumeric + underscore
    name="Memory Search",
    description="Search semantic memory for relevant context",
    parameters=[
        ToolParameter(
            name="query",
            type="string",
            description="Search query",
            required=True,
        ),
        ToolParameter(
            name="limit",
            type="integer",
            description="Max results",
            required=False,
            default=10,
        ),
    ],
    handler=search_memory_handler,
    is_destructive=False,
    requires_igor_approval=False,
    risk_level="low",
)

# Register tool
registry = ToolRegistry()
registry.register(memory_search)

# Execute tool
result = await registry.execute("memory_search", query="user preferences")
```

## Anti-Pattern Example

```python
# ❌ WRONG — Dots in tool name (OpenAI rejects this)
ToolDefinition(
    tool_id="memory.search",  # INVALID: contains dot
    ...
)

# ❌ WRONG — Spaces in tool name
ToolDefinition(
    tool_id="memory search",  # INVALID: contains space
    ...
)

# ❌ WRONG — Special characters
ToolDefinition(
    tool_id="memory:search",  # INVALID: contains colon
    ...
)

# ✅ CORRECT — Underscore separator
ToolDefinition(
    tool_id="memory_search",  # VALID
    ...
)

# ✅ CORRECT — Hyphen separator
ToolDefinition(
    tool_id="memory-search",  # VALID
    ...
)
```

## Naming Convention

```
Valid:   memory_search, git_commit, file_read, perplexity-search
Invalid: memory.search, git:commit, file read, @tool
Pattern: ^[a-zA-Z0-9_-]+$
```

## Rules

1. Tool name MUST match `^[a-zA-Z0-9_-]+$` (no dots, spaces, special chars)
2. Use underscores `_` or hyphens `-` as separators
3. Set `is_destructive=True` for state-changing tools
4. Set `requires_igor_approval=True` for high-risk tools
5. Provide clear `description` for LLM function calling

## AI Guidance

**DO:**

- Use underscores in tool names (`memory_search`)
- Set appropriate `risk_level` and flags
- Include all parameters with descriptions
- Validate tool_id in `__post_init__`

**DO NOT:**

- Use dots in tool names (`memory.search` is INVALID)
- Use spaces or special characters
- Skip `is_destructive` flag for write operations
- Register tools without handlers
