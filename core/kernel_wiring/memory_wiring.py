"""
05_memory_kernel → Memory Adapter / Substrate Client

In memory/memory_client.py or similar.
"""


_KERNELS = None


def _get_kernels():
    """Lazy load kernel stack."""
    global _KERNELS
    if _KERNELS is None:
        from runtime.kernel_loader import load_kernel_stack

        _KERNELS = load_kernel_stack()
    return _KERNELS


def get_memory_layers_config() -> dict:
    """Returns the configuration dictionary for memory layers from kernel rules, used in memory adapter setup."""
    return _get_kernels().get_rule("memory", "layers", default={}) or {}


def should_checkpoint_now(event_type: str) -> bool:
    """
    Checks if the given event type should trigger a memory checkpoint based on configured rules.

    Args:
        event_type: The type of event to evaluate against checkpointing triggers.

    Returns:
        True if the event type matches a checkpointing trigger; otherwise, False.
    """
    rules = (
        _get_kernels().get_rule("memory", "checkpointing.triggers", default=[]) or []
    )
    return event_type in rules


# Runtime execution trace - updated automatically on every execution
