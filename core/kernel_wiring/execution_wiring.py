"""
07_execution_kernel → Execution Engine / State Machine

In your execution engine module (or where you plan to put it).
"""


_KERNELS = None


def _get_kernels():
    """Lazy load kernel stack."""
    global _KERNELS
    if _KERNELS is None:
        from runtime.kernel_loader import load_kernel_stack

        _KERNELS = load_kernel_stack()
    return _KERNELS


def get_execution_state_machine() -> dict:
    """
    Returns the current execution state machine dictionary from the kernel management system.

    Args: None

    Returns:
        A dictionary representing the execution state machine with states and transitions.
    """
    return _get_kernels().get_kernel("execution") or {}


def get_allowed_transitions(state: str) -> list:
    """
    Returns a list of allowed state transitions based on the current execution state from the state machine.

    Args:
        state: The current execution state for which to retrieve allowed transitions.

    Returns:
        A list of permissible next states according to the execution state machine.
    """
    sm = get_execution_state_machine()
    transitions = sm.get("transitions", {})
    return transitions.get(state, [])


# Runtime execution trace - updated automatically on every execution
