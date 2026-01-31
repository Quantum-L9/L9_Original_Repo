"""
L9 Core Tools - Discovery Tracing & Observability
==================================================

GMP-TD-WIRE: Comprehensive observability for tool discovery.
Adapted from: Tool Discovery research (harvested 8_observability.py)
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Discovery Tracing & Observability",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T11:17:21Z",
    "updated_at": "2026-01-25T11:16:07Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "discovery_tracing",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["core.tools.__init__", "core.tools.dynamic_discovery"],
    },
}
# ============================================================================

import json
import logging
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class DiscoveryPhase(Enum):
    """
    Represents the stages of the discovery process within the observability framework for tool discovery.

    Args:
        phase (DiscoveryPhase): The current stage in the discovery workflow, such as discovery, selection, loading, or execution.


    Raises:
        ValueError: If an invalid phase is provided.
    """

    DISCOVERY = "discovery"
    SELECTION = "selection"
    LOADING = "loading"
    EXECUTION = "execution"


@dataclass
class DiscoveryTrace:
    """Complete trace of discovery process"""

    task_id: str
    phase: DiscoveryPhase
    query: str
    num_results: int
    num_selected: int
    """
    Records a discovery trace within the DiscoveryTracer for observability of tool discovery operations.

    Args:
        trace: An instance of DiscoveryTrace representing the discovery event to be logged.
    """
    tokens_used: int
    latency_ms: float
    success: bool
    error: str | None = None


class DiscoveryTracer:
    """Trace and log discovery operations"""

    def __init__(self):
        """
        Records a discovery trace within the DiscoveryTracer for observability of tool discovery processes.

        Args:
            trace: An instance of DiscoveryTrace representing the discovery event to log.
        """
        self.logger = logging.getLogger("l9.discovery")
        self.traces: list[DiscoveryTrace] = []

    def trace_discovery(self, trace: DiscoveryTrace):
        """Record discovery trace"""
        self.traces.append(trace)

        # Log with appropriate level
        level = logging.INFO if trace.success else logging.WARNING
        self.logger.log(level, json.dumps(asdict(trace)))

    def get_discovery_stats(self) -> dict[str, Any]:
        """Compute statistics from traces"""
        if not self.traces:
            return {}

        successful = [t for t in self.traces if t.success]
        failed = [t for t in self.traces if not t.success]

        return {
            "total_discoveries": len(self.traces),
            "success_rate": len(successful) / len(self.traces) * 100,
            "avg_latency_ms": sum(t.latency_ms for t in self.traces) / len(self.traces),
            "avg_tokens_used": sum(t.tokens_used for t in self.traces)
            / len(self.traces),
            "avg_results_per_query": sum(t.num_results for t in self.traces)
            / len(self.traces),
            "failures": len(failed),
        }


__all__ = [
    "DiscoveryPhase",
    "DiscoveryTrace",
    "DiscoveryTracer",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-030",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["data-models", "dataclass", "foundation", "serialization", "tracing"],
    "keywords": [
        "discovery",
        "observability",
        "phase",
        "stats",
        "tool",
        "trace",
        "tracer",
        "tracing",
    ],
    "business_value": "Provides discovery tracing components including DiscoveryPhase, DiscoveryTrace, DiscoveryTracer",
    "last_modified": "2026-01-25T11:16:07Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
