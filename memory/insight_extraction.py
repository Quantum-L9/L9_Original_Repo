"""
memory.insight_extraction — DEPRECATED compatibility shim.

.. deprecated:: 2.0.0
    Superseded by ``extract_insights_node`` in ``memory/substrate_dag.py``
    and ``EntityExtractionService`` in ``memory/entity_extraction.py``
    as part of the Memory Pipeline Unification (2026-02-12).

    The original implementation is preserved at memory/archive/insight_extraction.py.
    All new code should use the SubstrateDAG extract_insights_node directly.

    Removal target: next major release after all callers migrate.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "memory.insight_extraction is deprecated. "
    "Use extract_insights_node (memory.substrate_dag) and "
    "EntityExtractionService (memory.entity_extraction) instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from the archived module
from memory.archive.insight_extraction import (  # noqa: F401
    InsightExtractionPipeline,
    get_insight_pipeline,
    init_insight_pipeline,
)

__all__ = [
    "InsightExtractionPipeline",
    "get_insight_pipeline",
    "init_insight_pipeline",
]
