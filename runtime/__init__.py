"""
L9 Runtime Package
==================

Runtime components for L9 execution environment.

Includes:
- Task queue (Redis-backed with in-memory fallback)
- Rate limiter (Redis-backed with in-memory fallback)
- Redis client (production-ready with graceful fallback)
- Kernel loader (THE choke point for kernel loading)
- WebSocket orchestrator (agent connection management)

Version: 2.2.0 (consolidated from runtime-local)
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "2.2.0 (consolidated from runtime-local)",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-21T00:00:34Z",
    "updated_at": "2026-01-31T22:21:51Z",
    "layer": "operations",
    "domain": "runtime_operations",
    "module_name": "__init__",
    "type": "utility",
    "status": "production",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Redis"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

__version__ = "2.2.0"

# Execution Gate (GODMODE Part 2)
# Kernel State (GODMODE Part 1.1 + 7.2)
# Redis Tools (GMP-122 - migrated from l_tools.py)
# Note: These are auto-registered via @register_tool decorator
# Import triggers registration with tool_executor_registry
import runtime.redis_tools
from runtime import execution_gate as execution_gate
from runtime import kernel_state as kernel_state

# Background Task Registry (Auto-Wiring)
from runtime.background_tasks import (
    BackgroundTaskRegistry,
    get_background_task_registry,
)

# DORA Block Runtime (L9_TRACE_TEMPLATE auto-update)
from runtime.dora import (
    DoraGraph,
    DoraMetrics,
    DoraTraceBlock,
    emit_executor_trace,
    get_empty_dora_block_python,
    l9_traced,
    update_dora_block_in_file,
)
from runtime.execution_gate import (
    DEFAULT_TOOL_AUTHORIZATION,
    FORBIDDEN_PATTERNS,
    escalate_to_igor,
    select_mode_based_on_confidence,
    should_escalate_on_confidence,
)
from runtime.execution_gate import guarded_execute as guarded_execute_v2

# Kernel Loader (consolidated from private_loader.py)
from runtime.kernel_loader import (  # Configuration; Agent loading; Dynamic discovery; Query functions; Validation; Enforcement
    DEFAULT_KERNEL_PATH,
    KERNEL_EXTENSIONS,
    KERNEL_ID_MAP,
    KERNEL_ORDER,
    KernelStack,
    get_enabled_rules,
    get_kernel_by_name,
    get_rules_by_type,
    guarded_execute,
    load_all_private_kernels,
    load_kernel_file,
    load_kernel_stack,
    load_kernels,
    load_layered_kernels,
    require_kernel_activation,
    validate_all_kernels,
    validate_kernel_structure,
    validate_packet_protocol_rules,
    verify_kernel_activation,
)
from runtime.kernel_state import KernelState, create_kernel_state

# Rate Limiter
from runtime.rate_limiter import RateLimiter

# Redis Client
from runtime.redis_client import RedisClient, close_redis_client, get_redis_client

# Task Queue
from runtime.task_queue import QueuedTask, TaskQueue

# Tool Package Registry (GMP-122)
from runtime.tool_packages import (
    TOOL_PACKAGES,
    discover_from_packages,
    get_tool_packages,
    register_tool_package,
)

# WebSocket Orchestrator
from runtime.websocket_orchestrator import WebSocketOrchestrator, ws_orchestrator

__all__ = [
    # Kernel Loader - Configuration
    "DEFAULT_KERNEL_PATH",
    "DEFAULT_TOOL_AUTHORIZATION",
    "FORBIDDEN_PATTERNS",
    "KERNEL_EXTENSIONS",
    "KERNEL_ID_MAP",
    "KERNEL_ORDER",
    # Tool Package Registry (GMP-122)
    "TOOL_PACKAGES",
    # Background Task Registry
    "BackgroundTaskRegistry",
    "DoraGraph",
    "DoraMetrics",
    "DoraTraceBlock",
    "KernelStack",
    "KernelState",
    "QueuedTask",
    # Rate Limiter
    "RateLimiter",
    # Redis Client
    "RedisClient",
    # Task Queue
    "TaskQueue",
    # WebSocket Orchestrator
    "WebSocketOrchestrator",
    "close_redis_client",
    "create_kernel_state",
    "discover_from_packages",
    "emit_executor_trace",
    "escalate_to_igor",
    # Execution Gate (GODMODE Part 2)
    "execution_gate",
    "get_background_task_registry",
    "get_empty_dora_block_python",
    "get_enabled_rules",
    # Kernel Loader - Query functions
    "get_kernel_by_name",
    "get_redis_client",
    "get_rules_by_type",
    "get_tool_packages",
    # Kernel Loader - Enforcement
    "guarded_execute",
    "guarded_execute_v2",
    # Kernel State (GODMODE Part 1.1 + 7.2)
    "kernel_state",
    # DORA Block Runtime
    "l9_traced",
    "load_all_private_kernels",
    # Kernel Loader - Dynamic discovery
    "load_kernel_file",
    "load_kernel_stack",
    # Kernel Loader - Agent loading
    "load_kernels",
    "load_layered_kernels",
    "register_tool_package",
    "require_kernel_activation",
    "select_mode_based_on_confidence",
    "should_escalate_on_confidence",
    "update_dora_block_in_file",
    "validate_all_kernels",
    # Kernel Loader - Validation
    "validate_kernel_structure",
    "validate_packet_protocol_rules",
    "verify_kernel_activation",
    "ws_orchestrator",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "RUN-OPER-014",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "runtime.background_tasks",
        "runtime.dora",
        "runtime.execution_gate",
        "runtime.kernel_loader",
        "runtime.kernel_state",
    ],
    "tags": [
        "auth",
        "cache",
        "metrics",
        "operations",
        "queue",
        "realtime",
        "runtime-operations",
        "tracing",
        "utility",
    ],
    "keywords": [
        "agent",
        "backed",
        "fallback",
        "kernel",
        "memory",
        "orchestrator",
        "queue",
        "redis",
    ],
    "business_value": "Utility module for   init  ",
    "last_modified": "2026-01-31T22:21:51Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
