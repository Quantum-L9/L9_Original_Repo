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

__dora_meta__ = {
    "component_name": "Insight Extraction",
    "module_version": "1.0.0",
    "created_by": "Auto-fix ADR-0014",
    "created_at": "2026-02-13T23:37:34.982811+00:00",
    "updated_at": "2026-02-13T23:37:34.982811+00:00",
    "layer": "core",
    "domain": "memory",
    "module_name": "memory.insight_extraction",
    "type": "module",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}

import warnings

warnings.warn(
    "memory.insight_extraction is deprecated. "
    "Use extract_insights_node (memory.substrate_dag) and "
    "EntityExtractionService (memory.entity_extraction) instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from the archived module
from memory.archive.insight_extraction import (
    InsightExtractionPipeline,
    get_insight_pipeline,
    init_insight_pipeline,
)

__all__ = [
    "InsightExtractionPipeline",
    "get_insight_pipeline",
    "init_insight_pipeline",
]
