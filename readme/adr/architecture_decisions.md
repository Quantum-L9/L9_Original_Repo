# Architecture Decisions

## Cursor File Organization (2026-01-11)

**Decision:** All Cursor-related files consolidated into `agents/cursor/`.

**Rationale:** Clear separation from core L9, matches `agents/codegenagent/` pattern.

**Files Moved:**

- `core/governance/cursor_memory_kernel.py` → `agents/cursor/cursor_memory_kernel.py`
- `tools/cursor_client.py` → `agents/cursor/cursor_client.py`
- `scripts/cursor_check_mistakes.py` → `agents/cursor/scripts/cursor_check_mistakes.py`
- `memory/extractor/cursor_action_extractor.py` → `agents/cursor/extractors/cursor_action_extractor.py`
- `readme/CURSOR-L9-INTEGRATION.md` → `agents/cursor/docs/CURSOR-L9-INTEGRATION.md`
- `prompts/cursor-extraction-*.md` → `agents/cursor/prompts/`

**Import Paths:**

```python
from agents.cursor import CursorMemoryKernel, create_cursor_memory_kernel, CursorClient
from agents.cursor.cursor_memory_kernel import SessionState, Lesson, TodoItem
```

---

## Type System Strategy: TypedDict vs Pydantic (2026-01-11)

**Decision:** TypedDict for LangGraph state, Pydantic BaseModel for everything else.

**Rationale:**

- LangGraph `StateGraph` requires dict-based state for merging
- TypedDict provides type hints without runtime overhead
- Pydantic provides runtime validation for external data

**Usage:**

- **TypedDict:** LangGraph state schemas (`SubstrateGraphState`, `ResearchGraphState`, etc.)
- **Pydantic:** API models, database models, external validation

**Conversion Pattern:**

```python
# Entry: Pydantic → TypedDict
state: SubstrateGraphState = {"envelope": envelope.model_dump(mode="json"), "errors": []}

# Exit: TypedDict → Pydantic (if needed)
result = PacketEnvelope.model_validate(state["envelope"])
```

**References:** `l9/langgraph/README.md`, `l9/langgraph/TYPEDDICT_VS_PYDANTIC.md`
