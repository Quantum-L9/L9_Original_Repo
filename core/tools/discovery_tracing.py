"""
L9 Core Tools - Discovery Tracing & Observability
==================================================

GMP-TD-WIRE: Comprehensive observability for tool discovery.
Adapted from: Tool Discovery research (harvested 8_observability.py)
"""

import json
import logging
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class DiscoveryPhase(Enum):
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
    tokens_used: int
    latency_ms: float
    success: bool
    error: str | None = None


class DiscoveryTracer:
    """Trace and log discovery operations"""

    def __init__(self):
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
