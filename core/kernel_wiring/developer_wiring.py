"""
09_developer_kernel → Engineering Governance

In dev-only or spec/validation modules.
"""


_KERNELS = None


def _get_kernels():
    """Lazy load kernel stack."""
    global _KERNELS
    if _KERNELS is None:
        from runtime.kernel_loader import load_kernel_stack

        _KERNELS = load_kernel_stack()
    return _KERNELS


def get_dev_policies() -> dict:
    """Returns a dictionary of developer-specific policies from the kernel configuration."""
    return _get_kernels().get_kernel("developer") or {}


# Runtime execution trace - updated automatically on every execution
