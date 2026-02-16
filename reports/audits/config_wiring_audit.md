# Package Wiring Audit: config

**Date:** 2026-02-14 05:36 UTC

## Level B: File Wiring — `config`

Files checked: 10
- WIRED: 3
- PARTIAL: 5
- ORPHAN: 0
- ENTRYPOINT: 0
- TEST_ONLY: 2

| File | Ext Consumers | Test Consumers | Test File | Re-exported | Status |
|------|-------------:|---------------:|-----------|-------------|--------|
| `config/ai_eval_settings.py` | 1 | 0 | - | Y | OK |
| `config/cursor_langgraph_config.py` | 1 | 0 | - | - | PARTIAL |
| `config/di_async_config.py` | 1 | 1 | Y | - | PARTIAL |
| `config/di_config.py` | 0 | 1 | - | - | TEST |
| `config/di_runtime_config.py` | 0 | 1 | - | - | TEST |
| `config/memory_substrate_settings.py` | 0 | 1 | - | Y | PARTIAL |
| `config/research_settings.py` | 2 | 0 | - | Y | OK |
| `config/rls_config.py` | 13 | 1 | - | - | PARTIAL |
| `config/settings.py` | 15 | 3 | - | Y | OK |
| `config/tool_schemas.py` | 2 | 0 | - | - | PARTIAL |

## Level C: API Instantiation — `config`

API Status: **HAS_API**
Symbols checked: 13
- USED: 6
- TEST_ONLY: 2
- UNUSED: 5

| Symbol | Ext | Test | Status |
|--------|----:|-----:|--------|
| `AIEvalSettings` | 0 | 0 | UNUSED |
| `IntegrationSettings` | 0 | 1 | TEST_ONLY |
| `MemorySubstrateSettings` | 0 | 1 | TEST_ONLY |
| `ResearchSettings` | 0 | 0 | UNUSED |
| `reset_ai_eval_settings` | 0 | 0 | UNUSED |
| `reset_integration_settings` | 0 | 0 | UNUSED |
| `reset_research_settings` | 0 | 0 | UNUSED |

**API-pattern symbols NOT in `__all__`:**
- `CursorLangGraphConfig`
- `RLSConfig`
- `create_kernel_loader`
- `create_memory_substrate_service`
- `create_neo4j_client`
- `create_observability_service`
- `create_pgvector_client`
- `create_redis_client`
- `create_tool_registry`
- `create_world_model_service`
- `get_async_di_container`
- `get_cache_client`
- `get_cursor_langgraph_config`
- `get_environment`
- `get_graph_client`
- `get_memory_service`
- `get_rls_config`
- `get_rls_uuids`
- `get_runtime_config_loader`
- `get_slack_files_dir`
- `get_tool_schema`
- `get_vector_store`
- `get_world_model_service_di`
