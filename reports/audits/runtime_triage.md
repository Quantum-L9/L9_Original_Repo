# Dead Code Triage: `runtime`

**Date:** 2026-02-14 05:43 UTC

## Symbol Classification

**USED** (37): `BackgroundTaskRegistry`, `DEFAULT_KERNEL_PATH`, `DoraTraceBlock`, `FORBIDDEN_PATTERNS`, `KERNEL_EXTENSIONS`, `KERNEL_ID_MAP`, `KERNEL_ORDER`, `KernelStack`, `KernelState`, `QueuedTask`, `RateLimiter`, `RedisClient`, `TaskQueue`, `WebSocketOrchestrator`, `close_redis_client`, `emit_executor_trace`, `escalate_to_igor`, `execution_gate`, `get_cursor_wmc`, `get_enabled_rules`
  ... and 17 more
**INTERNAL_ONLY** (2): `TOOL_PACKAGES`, `create_kernel_state`
**TEST_ONLY** (7): `DEFAULT_TOOL_AUTHORIZATION`, `discover_from_packages`, `get_tool_packages`, `register_tool_package`, `select_mode_based_on_confidence`, `should_escalate_on_confidence`, `validate_packet_protocol_rules`
**ZERO_REF** (6): `DoraGraph`, `DoraMetrics`, `get_background_task_registry`, `get_empty_dora_block_python`, `get_wmc`, `guarded_execute_v2`

## File Classification

**WIRED** (24):
- `runtime/auth_rate_limiter.py`
- `runtime/background_tasks.py`
- `runtime/dora.py`
- `runtime/execution_gate.py`
- `runtime/gmp_tool.py`
- `runtime/gmp_worker.py`
- `runtime/introspection.py`
- `runtime/kernel_config_loader.py`
- `runtime/kernel_loader.py`
- `runtime/kernel_state.py`
- `runtime/l_tools.py`
- `runtime/local_api.py`
- `runtime/mcp_server_registry.py`
- `runtime/mcp_tool.py`
- `runtime/mcp_tools.py`
- `runtime/memory_helpers.py`
- `runtime/rate_limiter.py`
- `runtime/redis_client.py`
- `runtime/redis_tools.py`
- `runtime/task_queue.py`
- `runtime/tool_packages.py`
- `runtime/tool_registry.py`
- `runtime/tool_search_meta.py`
- `runtime/websocket_orchestrator.py`
**INTERNAL_ONLY** (1):
- `runtime/mcp_client.py`
**WIP** (8):
- `runtime/construct_enhancer.py`
- `runtime/git_tool.py`
- `runtime/gmp_approval.py`
- `runtime/long_plan_tool.py`
- `runtime/response_renderer.py`
- `runtime/response_tagger.py`
- `runtime/superprompt_emitter.py`
- `runtime/tool_call_wrapper.py`

## Recommended Actions

### Remove 2 internal-only symbols from `__all__`
These are used within the package but not externally. Remove from `__all__` to reduce API surface noise.

### Review 6 zero-reference symbols
These have no references anywhere (not even internal). Either wire them or remove from `__all__`.

### Wire 8 WIP files
Recently created but not yet integrated.
