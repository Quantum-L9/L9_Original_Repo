# Package Wiring Audit: runtime

**Date:** 2026-02-14 05:36 UTC

## Level B: File Wiring — `runtime`

Files checked: 33
- WIRED: 9
- PARTIAL: 12
- ORPHAN: 9
- ENTRYPOINT: 0
- TEST_ONLY: 3

| File | Ext Consumers | Test Consumers | Test File | Re-exported | Status |
|------|-------------:|---------------:|-----------|-------------|--------|
| `runtime/auth_rate_limiter.py` | 1 | 0 | - | - | PARTIAL |
| `runtime/background_tasks.py` | 1 | 0 | - | Y | OK |
| `runtime/construct_enhancer.py` | 0 | 0 | - | - | ORPHAN |
| `runtime/dora.py` | 3 | 1 | Y | Y | OK |
| `runtime/execution_gate.py` | 2 | 1 | Y | Y | OK |
| `runtime/git_tool.py` | 0 | 0 | - | - | ORPHAN |
| `runtime/gmp_approval.py` | 0 | 0 | - | - | ORPHAN |
| `runtime/gmp_tool.py` | 1 | 0 | - | - | PARTIAL |
| `runtime/gmp_worker.py` | 1 | 0 | - | - | PARTIAL |
| `runtime/introspection.py` | 1 | 0 | - | - | PARTIAL |
| `runtime/kernel_config_loader.py` | 0 | 1 | - | - | TEST |
| `runtime/kernel_loader.py` | 16 | 5 | - | Y | OK |
| `runtime/kernel_state.py` | 2 | 2 | Y | Y | OK |
| `runtime/l_tools.py` | 2 | 3 | - | - | PARTIAL |
| `runtime/local_api.py` | 1 | 0 | - | - | PARTIAL |
| `runtime/long_plan_tool.py` | 0 | 0 | - | - | ORPHAN |
| `runtime/mcp_client.py` | 0 | 0 | - | - | ORPHAN |
| `runtime/mcp_server_registry.py` | 1 | 1 | Y | - | PARTIAL |
| `runtime/mcp_tool.py` | 1 | 2 | - | - | PARTIAL |
| `runtime/mcp_tools.py` | 0 | 2 | - | - | TEST |
| `runtime/memory_helpers.py` | 2 | 0 | - | - | PARTIAL |
| `runtime/rate_limiter.py` | 2 | 0 | - | Y | OK |
| `runtime/redis_client.py` | 16 | 2 | - | Y | OK |
| `runtime/redis_tools.py` | 0 | 2 | - | Y | PARTIAL |
| `runtime/response_renderer.py` | 0 | 0 | - | - | ORPHAN |
| `runtime/response_tagger.py` | 0 | 0 | - | - | ORPHAN |
| `runtime/superprompt_emitter.py` | 0 | 0 | - | - | ORPHAN |
| `runtime/task_queue.py` | 2 | 1 | Y | Y | OK |
| `runtime/tool_call_wrapper.py` | 0 | 0 | - | - | ORPHAN |
| `runtime/tool_packages.py` | 0 | 4 | - | Y | PARTIAL |
| `runtime/tool_registry.py` | 8 | 4 | Y | - | PARTIAL |
| `runtime/tool_search_meta.py` | 0 | 2 | - | - | TEST |
| `runtime/websocket_orchestrator.py` | 2 | 2 | Y | Y | OK |

## Level C: API Instantiation — `runtime`

API Status: **HAS_API**
Symbols checked: 52
- USED: 37
- TEST_ONLY: 9
- UNUSED: 6

| Symbol | Ext | Test | Status |
|--------|----:|-----:|--------|
| `DEFAULT_TOOL_AUTHORIZATION` | 0 | 1 | TEST_ONLY |
| `DoraGraph` | 0 | 0 | UNUSED |
| `DoraMetrics` | 0 | 0 | UNUSED |
| `TOOL_PACKAGES` | 0 | 4 | TEST_ONLY |
| `create_kernel_state` | 0 | 1 | TEST_ONLY |
| `discover_from_packages` | 0 | 1 | TEST_ONLY |
| `get_background_task_registry` | 0 | 0 | UNUSED |
| `get_empty_dora_block_python` | 0 | 0 | UNUSED |
| `get_tool_packages` | 0 | 2 | TEST_ONLY |
| `get_wmc` | 0 | 0 | UNUSED |
| `guarded_execute_v2` | 0 | 0 | UNUSED |
| `register_tool_package` | 0 | 2 | TEST_ONLY |
| `select_mode_based_on_confidence` | 0 | 1 | TEST_ONLY |
| `should_escalate_on_confidence` | 0 | 1 | TEST_ONLY |
| `validate_packet_protocol_rules` | 0 | 1 | TEST_ONLY |

**API-pattern symbols NOT in `__all__`:**
- `AuthRateLimitConfig`
- `MCPServerConfig`
- `get_all_mcp_servers`
- `get_auth_rate_limiter`
- `get_calibration_score`
- `get_config_path`
- `get_environment`
- `get_gmp_task`
- `get_kernel_cached`
- `get_kernel_order`
- `get_mcp_client`
- `get_mcp_server_snapshot`
- `get_mcp_servers_by_category`
- `get_mcp_tool_metadata`
- `get_minimum_kernel_count`
- `get_pending_task`
- `get_required_kernels`
- `get_rule_cached`
- `get_tool_executors`
- `get_tool_snapshot`
- `get_tools_by_category`
- `get_tools_by_server`
- `get_tools_by_tags`
