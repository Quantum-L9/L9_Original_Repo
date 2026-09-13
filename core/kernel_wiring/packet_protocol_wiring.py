"""
10_packet_protocol_kernel → WS Router / Task Routing / EventStream

In orchestration/ws_task_router.py, runtime/websocket_orchestrator.py, or EventStream layer.
"""


_KERNELS = None


def _get_kernels():
    """Lazy load kernel stack."""
    global _KERNELS
    if _KERNELS is None:
        from runtime.kernel_loader import load_kernel_stack

        _KERNELS = load_kernel_stack()
    return _KERNELS


def get_packet_protocol() -> dict:
    """Returns the packet protocol configuration from the kernel registry used in WebSocket task routing and event streaming."""
    return _get_kernels().get_kernel("packet_protocol") or {}


def get_allowed_event_types() -> list:
    """Returns a list of allowed event types based on packet protocol rules from kernel configurations."""
    return (
        _get_kernels().get_rule("packet_protocol", "events.allowed_types", default=[])
        or []
    )


def get_default_channel() -> str:
    """Returns the default communication channel for packet protocol routing in the WebSocket task router."""
    return _get_kernels().get_rule(
        "packet_protocol", "routing.default_channel", default="agent"
    )


# Runtime execution trace - updated automatically on every execution
