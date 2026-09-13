"""
08_safety_kernel → Safety Scanners / Guardrails

In your safety layer (modules/safety/ or preflight hooks).
"""


_KERNELS = None


def _get_kernels():
    """Lazy load kernel stack."""
    global _KERNELS
    if _KERNELS is None:
        from runtime.kernel_loader import load_kernel_stack

        _KERNELS = load_kernel_stack()
    return _KERNELS


def get_safety_policies() -> dict:
    """
    Retrieves the safety policies defined in the safety kernel for validation and enforcement.


    Returns:
        A dictionary containing safety-related policies and rules from the safety kernel.
    """
    return _get_kernels().get_kernel("safety") or {}


def is_destructive_action(action: str) -> bool:
    """
    Checks if the given action is classified as destructive within the safety kernel.

    Args:
        action: The action string to evaluate against destructive rules.

    Returns:
        True if the action is considered destructive according to safety rules, False otherwise.
    """
    destructive = (
        _get_kernels().get_rule("safety", "destructive.actions", default=[]) or []
    )
    return action in destructive


# Runtime execution trace - updated automatically on every execution
