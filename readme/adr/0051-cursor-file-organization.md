# ADR 0051: Cursor File Organization

## Status

Accepted

## Pattern

Consolidate all Cursor-related files into `agents/cursor/` directory following the agent-specific organization pattern.

## Files

- `agents/cursor/__init__.py`
- `agents/cursor/cursor_memory_kernel.py`
- `agents/cursor/cursor_memory_client.py`
- `agents/cursor/scripts/`
- `agents/cursor/extractors/`
- `agents/cursor/docs/`
- `agents/cursor/prompts/`

## Import Block

```python
from agents.cursor import CursorMemoryKernel, create_cursor_memory_kernel
from agents.cursor.cursor_memory_client import CursorMemoryClient
from agents.cursor.cursor_memory_kernel import SessionState, Lesson, TodoItem
```

## Directory Structure

```
agents/cursor/
├── __init__.py
├── cursor_memory_kernel.py      # Core kernel for Cursor memory
├── cursor_memory_client.py      # MCP/HTTP client for memory operations
├── scripts/
│   └── cursor_check_mistakes.py
├── extractors/
│   └── cursor_action_extractor.py
├── docs/
│   └── CURSOR-L9-INTEGRATION.md
└── prompts/
    └── cursor-extraction-*.md
```

## Rationale

1. **Consistency** — Matches existing `agents/codegenagent/` pattern
2. **Discoverability** — All Cursor code in one place
3. **Separation of Concerns** — Clear boundary between core L9 and Cursor integration
4. **Maintainability** — Easier to update/remove Cursor integration
5. **Scalability** — Pattern can be applied to other agent integrations

## Anti-Pattern Example

```python
# ❌ WRONG — Scattered across multiple directories
from core.governance import cursor_memory_kernel
from tools import cursor_client
from memory.extractor import cursor_action_extractor

# ✅ CORRECT — All from agents/cursor/
from agents.cursor import cursor_memory_kernel
from agents.cursor import cursor_memory_client
from agents.cursor.extractors import cursor_action_extractor
```

## Rules

1. All agent-specific code goes in `agents/<agent-name>/`
2. Follow the directory structure pattern (scripts/, extractors/, docs/, prompts/)
3. Export public APIs from `__init__.py`
4. Keep agent-specific tests in `tests/agents/<agent-name>/`

## AI Guidance

**DO:**

- Place new Cursor-related files in `agents/cursor/`
- Follow the established directory structure
- Update imports when moving files

**DO NOT:**

- Scatter Cursor code across `core/`, `tools/`, `scripts/`
- Create new top-level directories for agent integrations
- Mix Cursor code with core L9 functionality
