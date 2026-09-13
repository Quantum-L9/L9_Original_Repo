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

import structlog


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
        self.logger = structlog.get_logger("l9.discovery")
        self.traces: list[DiscoveryTrace] = []

    def trace_discovery(self, trace: DiscoveryTrace):
        """Record discovery trace"""
        self.traces.append(trace)

        # Log with appropriate level
        level = logging.INFO if trace.success else logging.WARNING
        # Use a custom serializer for Enum
        trace_dict = asdict(trace)
        trace_dict["phase"] = trace.phase.value
        self.logger.log(level, json.dumps(trace_dict))

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

# Runtime execution trace - updated automatically on every execution
