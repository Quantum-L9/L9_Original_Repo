# Dead Code Triage: `config`

**Date:** 2026-02-14 05:42 UTC

## Symbol Classification

**USED** (6): `get_ai_eval_settings`, `get_integration_settings`, `get_research_settings`, `get_settings`, `reset_settings`, `settings`
**TEST_ONLY** (2): `IntegrationSettings`, `MemorySubstrateSettings`
**ZERO_REF** (5): `AIEvalSettings`, `ResearchSettings`, `reset_ai_eval_settings`, `reset_integration_settings`, `reset_research_settings`

## File Classification

**WIRED** (10):
- `config/ai_eval_settings.py`
- `config/cursor_langgraph_config.py`
- `config/di_async_config.py`
- `config/di_config.py`
- `config/di_runtime_config.py`
- `config/memory_substrate_settings.py`
- `config/research_settings.py`
- `config/rls_config.py`
- `config/settings.py`
- `config/tool_schemas.py`

## Recommended Actions

### Review 5 zero-reference symbols
These have no references anywhere (not even internal). Either wire them or remove from `__all__`.
