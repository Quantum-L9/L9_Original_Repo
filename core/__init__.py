"""
L9 Core Module
==============

Core infrastructure for L9 orchestration system.

Submodules:
- abstractions: Protocol definitions for DI (kernel, memory, agent, observability)
- di: Dependency injection container and utilities
- schemas: Pydantic models for packets, research, security
- retrievers: Memory substrate retrievers
- kernels: Kernel integrity and loading
- boundary: PRIVATE_BOUNDARY enforcement
- gmp: GMP v2.0 meta-learning system (L2→L5 autonomy)

Version: 2.3.0
"""

# Note: Submodules are imported on-demand to avoid circular imports
# Use explicit imports:
#   from core.schemas import PacketEnvelope
#   from core.kernels import check_kernel_integrity
#   from core.boundary import enforce_boundary

__version__ = "2.2.0"

# GMP v2.0 meta-learning system (lazy import to avoid circular deps)
# Usage: from core.gmp import GMPMetaLearningEngine, AutonomyController
