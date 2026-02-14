# Package Wiring Audit: api

**Date:** 2026-02-14 05:36 UTC

## Level B: File Wiring — `api`

Files checked: 19
- WIRED: 0
- PARTIAL: 7
- ORPHAN: 9
- ENTRYPOINT: 1
- TEST_ONLY: 2

| File | Ext Consumers | Test Consumers | Test File | Re-exported | Status |
|------|-------------:|---------------:|-----------|-------------|--------|
| `api/agent_routes.py` | 0 | 0 | - | - | ORPHAN |
| `api/auth.py` | 3 | 1 | Y | - | PARTIAL |
| `api/db.py` | 0 | 0 | - | - | ORPHAN |
| `api/dependencies.py` | 1 | 0 | - | - | PARTIAL |
| `api/e2e_slack_audit.py` | 0 | 0 | Y | - | ENTRY |
| `api/llm.py` | 1 | 0 | - | - | PARTIAL |
| `api/openapi_config.py` | 0 | 0 | - | - | ORPHAN |
| `api/os_routes.py` | 0 | 0 | - | - | ORPHAN |
| `api/server.py` | 2 | 5 | Y | - | PARTIAL |
| `api/server_memory.py` | 0 | 1 | - | - | TEST |
| `api/slack_adapter.py` | 1 | 5 | Y | - | PARTIAL |
| `api/slack_client.py` | 5 | 3 | - | - | PARTIAL |
| `api/startup_guard.py` | 0 | 1 | - | - | TEST |
| `api/vps_executor.py` | 1 | 0 | - | - | PARTIAL |
| `api/webhook_mac_agent.py` | 0 | 0 | - | - | ORPHAN |
| `api/webhook_twilio.py` | 0 | 0 | - | - | ORPHAN |
| `api/webhook_waba.py` | 0 | 0 | - | - | ORPHAN |
| `api/whatsapp.py` | 0 | 0 | - | - | ORPHAN |
| `api/world_model_api.py` | 0 | 0 | - | - | ORPHAN |

## Level C: API Instantiation — `api`

API Status: **SHOULD_HAVE_API**
Symbols checked: 135
- USED: 45
- TEST_ONLY: 11
- UNUSED: 79

| Symbol | Ext | Test | Status |
|--------|----:|-----:|--------|
| `ExecuteTaskRequest` | 0 | 0 | UNUSED |
| `ExecuteTaskResponse` | 0 | 0 | UNUSED |
| `agent_health` | 0 | 0 | UNUSED |
| `SegmentPreviewRequest` | 0 | 0 | UNUSED |
| `SegmentPreviewResponse` | 0 | 0 | UNUSED |
| `segment_preview` | 0 | 0 | UNUSED |
| `verify_api_key_with_rate_limit` | 0 | 0 | UNUSED |
| `insert_embedding` | 0 | 0 | UNUSED |
| `get_agent_executor` | 0 | 0 | UNUSED |
| `get_governance_engine` | 0 | 0 | UNUSED |
| `get_memory_orchestrator` | 0 | 0 | UNUSED |
| `get_timeline_service` | 0 | 0 | UNUSED |
| `get_memory_state_manager` | 0 | 0 | UNUSED |
| `get_consolidation_service` | 0 | 0 | UNUSED |
| `get_aios_runtime` | 0 | 0 | UNUSED |
| `get_virtual_context_manager` | 0 | 0 | UNUSED |
| `audit_slack_configuration` | 0 | 1 | TEST_ONLY |
| `audit_slack_security` | 0 | 1 | TEST_ONLY |
| `audit_slack_routing` | 0 | 1 | TEST_ONLY |
| `audit_slack_memory_integration` | 0 | 1 | TEST_ONLY |
| `audit_slack_telemetry` | 0 | 1 | TEST_ONLY |
| `audit_slack_rate_limiting` | 0 | 1 | TEST_ONLY |
| `audit_slack_e2e_flow` | 0 | 1 | TEST_ONLY |
| `chat_with_l9` | 0 | 0 | UNUSED |
| `get_openapi_config` | 0 | 0 | UNUSED |
| `get_security_schemes` | 0 | 0 | UNUSED |
| `os_health` | 0 | 0 | UNUSED |
| `os_status` | 0 | 0 | UNUSED |
| `os_readiness` | 0 | 0 | UNUSED |
| `custom_openapi` | 0 | 0 | UNUSED |
| `global_exception_handler` | 0 | 0 | UNUSED |
| `KernelReloadRequest` | 0 | 1 | TEST_ONLY |
| `KernelReloadResponse` | 0 | 1 | TEST_ONLY |
| `list_kernels_endpoint` | 0 | 0 | UNUSED |
| `tools_health_endpoint` | 0 | 0 | UNUSED |
| `reload_kernels_endpoint` | 0 | 0 | UNUSED |
| `neo4j_health` | 0 | 0 | UNUSED |
| `services_health` | 0 | 0 | UNUSED |
| `checkpoint_health` | 0 | 0 | UNUSED |
| `ChatRequest` | 0 | 0 | UNUSED |
| `ChatResponse` | 0 | 0 | UNUSED |
| `LChatRequest` | 0 | 0 | UNUSED |
| `LChatResponse` | 0 | 0 | UNUSED |
| `lchat` | 0 | 0 | UNUSED |
| `agent_ws_endpoint` | 0 | 0 | UNUSED |
| `l_ws` | 0 | 0 | UNUSED |
| `ChatRequest` | 0 | 0 | UNUSED |
| `ChatResponse` | 0 | 0 | UNUSED |
| `shutdown_http_client` | 0 | 0 | UNUSED |
| `SlackSignatureVerificationError` | 0 | 0 | UNUSED |
| `SlackRequestValidator` | 0 | 5 | TEST_ONLY |
| `format_task_message` | 0 | 0 | UNUSED |
| `format_list_message` | 0 | 0 | UNUSED |
| `build_approval_blocks` | 0 | 0 | UNUSED |
| `ensure_bootstrap` | 0 | 1 | TEST_ONLY |
| `ShellTask` | 0 | 0 | UNUSED |
| `MemoryHealthTask` | 0 | 0 | UNUSED |
| `CompositeTask` | 0 | 0 | UNUSED |
| `check_auth` | 0 | 0 | UNUSED |
| `is_allowed_command` | 0 | 0 | UNUSED |
| `run_shell` | 0 | 0 | UNUSED |
| `memory_health` | 0 | 0 | UNUSED |
| `agent_health` | 0 | 0 | UNUSED |
| `agent_exec` | 0 | 0 | UNUSED |
| `TaskResultRequest` | 0 | 0 | UNUSED |
| `get_next_mac_task` | 0 | 0 | UNUSED |
| `submit_task_result` | 0 | 0 | UNUSED |
| `list_mac_tasks` | 0 | 0 | UNUSED |
| `verify_twilio_signature` | 0 | 0 | UNUSED |
| `twilio_webhook` | 0 | 0 | UNUSED |
| `verify_webhook_signature` | 0 | 0 | UNUSED |
| `download_media` | 0 | 0 | UNUSED |
| `send_waba_message` | 0 | 0 | UNUSED |
| `verify_waba_webhook` | 0 | 0 | UNUSED |
| `waba_webhook` | 0 | 0 | UNUSED |
| `load_twilio_client` | 0 | 0 | UNUSED |
| `send_whatsapp_message` | 0 | 0 | UNUSED |
| `EntityResponse` | 0 | 0 | UNUSED |
| `EntityListResponse` | 0 | 0 | UNUSED |
| `StateVersionResponse` | 0 | 0 | UNUSED |
| `SnapshotRequest` | 0 | 0 | UNUSED |
| `SnapshotResponse` | 0 | 0 | UNUSED |
| `RestoreRequest` | 0 | 0 | UNUSED |
| `RestoreResponse` | 0 | 0 | UNUSED |
| `InsightInput` | 0 | 0 | UNUSED |
| `InsightsRequest` | 0 | 0 | UNUSED |
| `InsightsResponse` | 0 | 0 | UNUSED |
| `UpdatesListResponse` | 0 | 0 | UNUSED |
| `world_model_health` | 0 | 0 | UNUSED |
| `submit_insights` | 0 | 0 | UNUSED |

**Recommended `__all__` entries (used externally):**
- `AuditResult`
- `CallerIdentity`
- `SegmentResult`
- `SlackAPIClient`
- `SlackClientError`
- `SlackRequestNormalizer`
- `UpdateRecord`
- `agent_status`
- `chat`
- `create_snapshot`
- `echo`
- `execute_task`
- `get_client`
- `get_entity`
- `get_evaluator`
- `get_housekeeping_engine`
- `get_neo4j_client`
- `get_observability_service`
- `get_redis_client`
- `get_state_version`
- `get_substrate_service`
- `get_system_prompt`
- `get_tool_registry`
- `get_world_model_service`
- `health`
- `health`
- `init_db`
- `lifespan`
- `list_entities`
- `list_snapshots`
- `list_updates`
- `main`
- `on_shutdown`
- `on_startup`
- `post_result_async`
- `restore_from_snapshot`
- `root`
- `root`
- `run_full_audit`
- `send_mac_task`
- `shutdown`
- `startup`
- `startup_health`
- `submit_task`
- `verify_api_key`
