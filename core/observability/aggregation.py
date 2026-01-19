"""
Span aggregation and metrics computation.

Computes SRE metrics, KPIs, and detects regressions from spans.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Aggregation",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "aggregation",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["tests.core.observability.test_observability_integration"],
    },
}
# ============================================================================

import structlog
from typing import List, Dict, Optional, Any
from datetime import datetime
from statistics import mean

from .models import Span, AgentKPI, SpanStatus

logger = structlog.get_logger(__name__)


class MetricsAggregator:
    """Aggregates spans into SRE metrics and KPIs."""

    @staticmethod
    def compute_sre_metrics(spans: List[Span]) -> Dict[str, Any]:
        """Compute SRE-level metrics from spans."""
        if not spans:
            return {
                "span_count": 0,
                "error_count": 0,
                "error_rate": 0.0,
                "p50_latency_ms": 0,
                "p95_latency_ms": 0,
                "p99_latency_ms": 0,
                "avg_latency_ms": 0,
                "max_latency_ms": 0,
                "timestamp": datetime.utcnow().isoformat(),
            }

        # Latency analysis
        durations = [s.duration_ms for s in spans if s.duration_ms]
        durations.sort()

        p50_idx = max(0, len(durations) // 2)
        p95_idx = max(0, int(len(durations) * 0.95) - 1)
        p99_idx = max(0, int(len(durations) * 0.99) - 1)

        # Error analysis
        errors = [s for s in spans if s.status == SpanStatus.ERROR]
        error_by_type = {}
        for err in errors:
            key = err.name
            error_by_type[key] = error_by_type.get(key, 0) + 1

        return {
            "span_count": len(spans),
            "error_count": len(errors),
            "error_rate": len(errors) / len(spans) if spans else 0.0,
            "p50_latency_ms": durations[p50_idx] if p50_idx < len(durations) else 0,
            "p95_latency_ms": durations[p95_idx] if p95_idx < len(durations) else 0,
            "p99_latency_ms": durations[p99_idx] if p99_idx < len(durations) else 0,
            "avg_latency_ms": mean(durations) if durations else 0,
            "max_latency_ms": max(durations) if durations else 0,
            "errors_by_type": error_by_type,
            "timestamp": datetime.utcnow().isoformat(),
        }

    @staticmethod
    def compute_agent_kpis(
        spans: List[Span],
        agent_name: str,
        period: str = "1h",
    ) -> Dict[str, float]:
        """Compute agent-specific KPIs."""
        if not spans:
            return {}

        # Filter to agent's spans
        agent_spans = [s for s in spans if agent_name in s.name]
        if not agent_spans:
            return {}

        # Success rate
        successes = [s for s in agent_spans if s.status == SpanStatus.OK]
        success_rate = len(successes) / len(agent_spans) if agent_spans else 0.0

        # Tool efficiency (tool spans per task)
        task_spans = [s for s in agent_spans if "task" in s.name]
        tool_spans = [s for s in agent_spans if s.name.startswith("tool.")]
        tool_efficiency = (
            len(task_spans) / max(1, len(tool_spans)) if tool_spans else 0.0
        )

        # Cost (estimated from LLM spans)
        llm_spans = [s for s in agent_spans if hasattr(s, "cost_usd")]
        total_cost = sum(s.cost_usd for s in llm_spans if hasattr(s, "cost_usd"))

        return {
            "agent_name": agent_name,
            "success_rate": success_rate,
            "tool_efficiency": tool_efficiency,
            "total_cost_usd": total_cost,
            "avg_latency_ms": mean(
                [s.duration_ms for s in agent_spans if s.duration_ms]
            ),
            "period": period,
        }

    @staticmethod
    def detect_regressions(
        current_metrics: Dict[str, Any],
        baseline_metrics: Dict[str, Any],
        threshold_percent: float = 20.0,
    ) -> List[Dict[str, Any]]:
        """Detect metric regressions vs baseline.

        Returns list of regressions (metric name, baseline, current, change_percent).
        """
        regressions = []

        for metric_name in current_metrics:
            if metric_name not in baseline_metrics:
                continue

            current_val = current_metrics.get(metric_name, 0)
            baseline_val = baseline_metrics.get(metric_name, 1)

            if baseline_val == 0:
                continue

            change_percent = abs((current_val - baseline_val) / baseline_val) * 100

            # Determine if it's a regression (higher latency/error is bad, higher success is good)
            is_regression = False
            if "error" in metric_name.lower() or "latency" in metric_name.lower():
                is_regression = (
                    current_val > baseline_val and change_percent > threshold_percent
                )
            elif "success" in metric_name.lower():
                is_regression = (
                    current_val < baseline_val and change_percent > threshold_percent
                )

            if is_regression:
                regressions.append(
                    {
                        "metric_name": metric_name,
                        "baseline": baseline_val,
                        "current": current_val,
                        "change_percent": change_percent,
                    }
                )
                logger.warning(
                    f"Regression detected: {metric_name} "
                    f"({baseline_val} → {current_val}, +{change_percent:.1f}%)"
                )

        return regressions

    @staticmethod
    def compute_cost_breakdown(spans: List[Span]) -> Dict[str, float]:
        """Compute cost breakdown by service."""
        costs = {}

        for span in spans:
            service = span.name.split(".")[0]
            if hasattr(span, "cost_usd"):
                costs[service] = costs.get(service, 0) + span.cost_usd

        return costs


class KPITracker:
    """Tracks KPI history for trending and alerting."""

    def __init__(self, window_size: int = 100):
        """Initialize KPI tracker.

        Args:
            window_size: Number of data points to keep in memory.
        """
        self.window_size = window_size
        self.history: Dict[str, List[Dict[str, Any]]] = {}

    def record_kpi(self, kpi: AgentKPI) -> None:
        """Record a KPI measurement."""
        key = f"{kpi.agent_name}.{kpi.metric_name}"
        if key not in self.history:
            self.history[key] = []

        self.history[key].append(
            {
                "value": kpi.value,
                "timestamp": kpi.timestamp,
            }
        )

        # Keep only recent window
        if len(self.history[key]) > self.window_size:
            self.history[key] = self.history[key][-self.window_size :]

    def get_trend(self, kpi_name: str) -> Optional[str]:
        """Get trend (up, down, stable) for a KPI."""
        if kpi_name not in self.history or len(self.history[kpi_name]) < 2:
            return None

        recent = self.history[kpi_name][-5:]
        avg_recent = mean([p["value"] for p in recent])
        avg_previous = mean([p["value"] for p in recent[:-1]])

        change_percent = (
            abs((avg_recent - avg_previous) / avg_previous) * 100 if avg_previous else 0
        )

        if change_percent < 5:
            return "stable"
        elif avg_recent > avg_previous:
            return "up"
        else:
            return "down"

    def get_alerts(self, thresholds: Dict[str, float]) -> List[Dict[str, Any]]:
        """Get alerts for KPIs exceeding thresholds."""
        alerts = []

        for kpi_name, threshold in thresholds.items():
            if kpi_name not in self.history:
                continue

            recent = self.history[kpi_name][-1]
            if recent["value"] > threshold:
                alerts.append(
                    {
                        "kpi_name": kpi_name,
                        "value": recent["value"],
                        "threshold": threshold,
                        "timestamp": recent["timestamp"],
                    }
                )

        return alerts


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-058",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["core", "foundation", "logging", "metrics", "utility"],
    "keywords": [
        "agent",
        "aggregation",
        "aggregator",
        "alerts",
        "breakdown",
        "compute",
        "cost",
        "detect",
    ],
    "business_value": "Provides aggregation components including MetricsAggregator, KPITracker",
    "last_modified": "2026-01-14T15:03:00Z",
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
