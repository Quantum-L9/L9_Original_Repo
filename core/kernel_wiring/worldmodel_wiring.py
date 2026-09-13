"""
06_worldmodel_kernel → World Model / Entity Graph

In world_model/repository.py or world_model/*.
"""


_KERNELS = None


def _get_kernels():
    """Lazy load kernel stack."""
    global _KERNELS
    if _KERNELS is None:
        from runtime.kernel_loader import load_kernel_stack

        _KERNELS = load_kernel_stack()
    return _KERNELS


def get_worldmodel_schema() -> dict:
    """Returns the schema dictionary for the world model from the kernel repository, or an empty dict if not available."""
    return _get_kernels().get_kernel("worldmodel") or {}


# Runtime execution trace - updated automatically on every execution
