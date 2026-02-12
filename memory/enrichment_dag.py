"""
memory.enrichment_dag — DEPRECATED compatibility shim.

.. deprecated:: 2.0.0
    This module has been superseded by SubstrateDAG (memory/substrate_dag.py)
    as part of the Memory Pipeline Unification (2026-02-12).

    The original implementation is preserved at memory/archive/enrichment_dag.py.
    All new code should use SubstrateDAG directly.

    This shim re-exports all symbols from the archived module to avoid
    breaking existing imports during the transition period.

    Removal target: next major release after all callers migrate.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "memory.enrichment_dag is deprecated. "
    "Use memory.substrate_dag (SubstrateDAG) instead. "
    "See Memory Pipeline Unification SuperPack for migration guide.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from the archived module
from memory.archive.enrichment_dag import (  # noqa: F401
    EnrichmentConfig,
    EnrichmentDAG,
    EnrichmentResult,
    EnrichmentStatus,
    EnrichmentTier,
)

# Also re-export telemetry function used by tests that patch this module
from telemetry.memory_metrics import record_memory_enrichment  # noqa: F401

__all__ = [
    "EnrichmentConfig",
    "EnrichmentDAG",
    "EnrichmentResult",
    "EnrichmentStatus",
    "EnrichmentTier",
    "record_memory_enrichment",
]
