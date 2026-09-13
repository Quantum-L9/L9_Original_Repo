"""
04_behavioral_kernel → Prohibitions / Output Defaults

Anywhere you enforce behavior (e.g. controlling verbosity, humor, filters).
"""


_KERNELS = None


def _get_kernels():
    """Lazy load kernel stack."""
    global _KERNELS
    if _KERNELS is None:
        from runtime.kernel_loader import load_kernel_stack

        _KERNELS = load_kernel_stack()
    return _KERNELS


def get_output_verbosity() -> str:
    """Returns the current output verbosity setting from behavioral rules, defaulting to "minimal" if not specified."""
    return _get_kernels().get_rule(
        "behavioral",
        "output.verbosity",
        default="minimal",
    )


def is_topic_blocked(topic: str) -> bool:
    """
    Checks if a given topic is listed as prohibited in behavioral kernel rules.

    Args:
        topic: The topic string to verify against prohibited topics list.

    Returns:
        True if the topic is blocked based on behavioral rules, otherwise False.
    """
    blocked = (
        _get_kernels().get_rule("behavioral", "prohibited_topics", default=[]) or []
    )
    return topic in blocked


# Runtime execution trace - updated automatically on every execution
