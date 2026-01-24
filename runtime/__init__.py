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
    # Task Queue
    "TaskQueue",
    "QueuedTask",
    # Rate Limiter
    "RateLimiter",
    # Redis Client
    "RedisClient",
    "get_redis_client",
    "close_redis_client",
    # Kernel Loader - Configuration
    "DEFAULT_KERNEL_PATH",
    "KERNEL_EXTENSIONS",
    "KERNEL_ORDER",
    "KERNEL_ID_MAP",
    # Kernel Loader - Agent loading
    "load_kernels",
    "load_kernel_stack",
    "KernelStack",
    # Kernel Loader - Dynamic discovery
    "load_kernel_file",
    "load_all_private_kernels",
    "load_layered_kernels",
    # Kernel Loader - Query functions
    "get_kernel_by_name",
    "get_enabled_rules",
    "get_rules_by_type",
    # Kernel Loader - Validation
    "validate_kernel_structure",
    "validate_all_kernels",
    "validate_packet_protocol_rules",
    # Kernel Loader - Enforcement
    "guarded_execute",
    "verify_kernel_activation",
    "require_kernel_activation",
    # WebSocket Orchestrator
    "WebSocketOrchestrator",
    "ws_orchestrator",
    # DORA Block Runtime
    "l9_traced",
    "DoraTraceBlock",
    "DoraMetrics",
    "DoraGraph",
    "update_dora_block_in_file",
    "emit_executor_trace",
    "get_empty_dora_block_python",
    # Kernel State (GODMODE Part 1.1 + 7.2)
    "kernel_state",
    "KernelState",
    "create_kernel_state",
    # Execution Gate (GODMODE Part 2)
    "execution_gate",
    "guarded_execute_v2",
    "should_escalate_on_confidence",
    "escalate_to_igor",
    "select_mode_based_on_confidence",
    "DEFAULT_TOOL_AUTHORIZATION",
    "FORBIDDEN_PATTERNS",
    # Background Task Registry
    "BackgroundTaskRegistry",
    "get_background_task_registry",
    # Tool Package Registry (GMP-122)
    "TOOL_PACKAGES",
    "get_tool_packages",
    "register_tool_package",
    "discover_from_packages",
]
