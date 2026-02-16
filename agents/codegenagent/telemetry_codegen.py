"""
CodeGenAgent Telemetry
======================

Emits telemetry from each CodeGenAgent run:
- File count
- Line count
- Time-to-generate
- Failure conditions

Supports Prometheus metrics and OpenTelemetry export.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Telemetry Codegen",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-15T23:26:53Z",
    "updated_at": "2026-01-15T23:26:53Z",
    "layer": "intelligence",
    "domain": "data_models",
    "module_name": "telemetry_codegen",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================


class MetricType(str, Enum):
    """Types of metrics."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


class FailureType(str, Enum):
    """Types of generation failures."""

    VALIDATION_ERROR = "validation_error"
    COMPILATION_ERROR = "compilation_error"
    EMISSION_ERROR = "emission_error"
    TIMEOUT = "timeout"
    GOVERNANCE_BLOCKED = "governance_blocked"
    UNKNOWN = "unknown"


# Histogram buckets for latency (in ms)
LATENCY_BUCKETS = [10, 50, 100, 250, 500, 1000, 2500, 5000, 10000]


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class MetricValue:
    """A single metric value."""

    name: str
    value: float
    metric_type: MetricType
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_prometheus(self) -> str:
        """Format as Prometheus metric line."""
        label_str = ""
        if self.labels:
            pairs = [f'{k}="{v}"' for k, v in self.labels.items()]
            label_str = "{" + ",".join(pairs) + "}"

        return f"{self.name}{label_str} {self.value}"

    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary representation of the MetricValue, including name, value, type, labels, and ISO-formatted timestamp, suitable for telemetry reporting."""
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.value,
            "labels": self.labels,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class GenerationMetrics:
    """Metrics from a single generation run."""

    module_name: str

    # Counts
    files_generated: int = 0
    lines_generated: int = 0

    # Timing
    start_time: float | None = None
    end_time: float | None = None
    latency_ms: float = 0.0

    # Status
    success: bool = True
    failure_type: FailureType | None = None
    error_message: str | None = None

    # Additional context
    meta_source: str = ""
    output_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary representation of the generation metrics, including module name, files and lines generated, latency in milliseconds, and success status."""
        return {
            "module_name": self.module_name,
            "files_generated": self.files_generated,
            "lines_generated": self.lines_generated,
            "latency_ms": self.latency_ms,
            "success": self.success,
            "failure_type": self.failure_type.value if self.failure_type else None,
            "error_message": self.error_message,
            "meta_source": self.meta_source,
            "output_path": self.output_path,
        }


@dataclass
class TelemetryReport:
    """Aggregated telemetry report."""

    period_start: datetime
    period_end: datetime

    # Aggregates
    total_generations: int = 0
    successful_generations: int = 0
    failed_generations: int = 0

    total_files: int = 0
    total_lines: int = 0

    avg_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    min_latency_ms: float = 0.0

    # By module
    by_module: dict[str, int] = field(default_factory=dict)

    # By failure type
    by_failure_type: dict[str, int] = field(default_factory=dict)
    """Returns a dictionary representation of the telemetry report with ISO-formatted timestamps and generation metrics."""

    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary with telemetry data including period timestamps, total and successful generation counts, suitable for Prometheus and OpenTelemetry integration."""
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_generations": self.total_generations,
            "successful_generations": self.successful_generations,
            "failed_generations": self.failed_generations,
            "total_files": self.total_files,
            "total_lines": self.total_lines,
            "avg_latency_ms": self.avg_latency_ms,
            "max_latency_ms": self.max_latency_ms,
            "min_latency_ms": self.min_latency_ms,
            "by_module": self.by_module,
            "by_failure_type": self.by_failure_type,
        }


# =============================================================================
# CODEGEN TELEMETRY
# =============================================================================


class CodeGenTelemetry:
    """
    Telemetry collector for CodeGenAgent.

    Tracks generation metrics and exports to Prometheus/OpenTelemetry.
    """

    def __init__(
        self,
        namespace: str = "codegen",
        enable_prometheus: bool = True,
        enable_logging: bool = True,
    ):
        """
        Initialize telemetry collector.

        Args:
            namespace: Metric namespace prefix
            enable_prometheus: Enable Prometheus metrics
            enable_logging: Enable structured logging
        """
        self.namespace = namespace
        self.enable_prometheus = enable_prometheus
        self.enable_logging = enable_logging

        # In-memory metric storage
        self._metrics: list[MetricValue] = []
        self._generation_history: list[GenerationMetrics] = []

        # Counters
        self._total_generations = 0
        self._total_files = 0
        self._total_lines = 0
        self._total_failures = 0

        # Latency tracking
        self._latencies: list[float] = []

        # Current generation context
        self._current_start: float | None = None
        self._current_module: str | None = None

        logger.info(
            "telemetry_initialized",
            namespace=namespace,
            prometheus=enable_prometheus,
        )

    def record_generation(
        self,
        meta: dict[str, Any],
        files: dict[str, str],
        success: bool = True,
        error: str | None = None,
    ) -> GenerationMetrics:
        """
        Record metrics from a generation run.

        Args:
            meta: Meta specification used
            files: Generated files (path -> content)
            success: Whether generation succeeded
            error: Error message if failed

        Returns:
            GenerationMetrics for this run
        """
        module_name = meta.get("name") or meta.get("filename", "unknown")

        # Calculate metrics
        files_count = len(files)
        lines_count = sum(content.count("\n") + 1 for content in files.values())

        # Calculate latency if we were tracking
        latency_ms = 0.0
        if self._current_start:
            latency_ms = (time.time() - self._current_start) * 1000
            self._latencies.append(latency_ms)

        # Determine failure type
        failure_type = None
        if not success and error:
            failure_type = self._classify_failure(error)

        # Create metrics record
        metrics = GenerationMetrics(
            module_name=module_name,
            files_generated=files_count,
            lines_generated=lines_count,
            start_time=self._current_start,
            end_time=time.time(),
            latency_ms=latency_ms,
            success=success,
            failure_type=failure_type,
            error_message=error,
            meta_source=meta.get("_source_file", ""),
        )

        # Update counters
        self._total_generations += 1
        self._total_files += files_count
        self._total_lines += lines_count
        if not success:
            self._total_failures += 1

        # Store history
        self._generation_history.append(metrics)

        # Emit metrics
        self._emit_generation_metrics(metrics)

        # Reset context
        self._current_start = None
        self._current_module = None

        if self.enable_logging:
            logger.info(
                "generation_recorded",
                module=module_name,
                files=files_count,
                lines=lines_count,
                latency_ms=latency_ms,
                success=success,
            )

        return metrics

    def emit_metrics(self) -> list[MetricValue]:
        """
        Emit current metrics snapshot.

        Returns:
            List of MetricValues
        """
        metrics = []

        # Counter: total generations
        metrics.append(
            MetricValue(
                name=f"{self.namespace}_generations_total",
                value=self._total_generations,
                metric_type=MetricType.COUNTER,
            )
        )

        # Counter: total files
        metrics.append(
            MetricValue(
                name=f"{self.namespace}_files_total",
                value=self._total_files,
                metric_type=MetricType.COUNTER,
            )
        )

        # Counter: total lines
        metrics.append(
            MetricValue(
                name=f"{self.namespace}_lines_total",
                value=self._total_lines,
                metric_type=MetricType.COUNTER,
            )
        )

        # Counter: failures
        metrics.append(
            MetricValue(
                name=f"{self.namespace}_failures_total",
                value=self._total_failures,
                metric_type=MetricType.COUNTER,
            )
        )

        # Gauge: avg latency
        if self._latencies:
            avg_latency = sum(self._latencies) / len(self._latencies)
            metrics.append(
                MetricValue(
                    name=f"{self.namespace}_latency_avg_ms",
                    value=avg_latency,
                    metric_type=MetricType.GAUGE,
                )
            )

        self._metrics = metrics
        return metrics

    def track_latency(self, start: float, end: float) -> float:
        """
        Track latency from start/end times.

        Args:
            start: Start timestamp (time.time())
            end: End timestamp (time.time())

        Returns:
            Latency in milliseconds
        """
        latency_ms = (end - start) * 1000
        self._latencies.append(latency_ms)

        if self.enable_logging:
            logger.debug("latency_tracked", latency_ms=latency_ms)

        return latency_ms

    def record_failure(
        self,
        error_type: FailureType,
        details: str,
        module_name: str | None = None,
    ) -> None:
        """
        Record a generation failure.

        Args:
            error_type: Type of failure
            details: Error details
            module_name: Optional module name
        """
        self._total_failures += 1

        # Add metric with failure label
        self._metrics.append(
            MetricValue(
                name=f"{self.namespace}_failure",
                value=1,
                metric_type=MetricType.COUNTER,
                labels={
                    "type": error_type.value,
                    "module": module_name or "unknown",
                },
            )
        )

        if self.enable_logging:
            logger.error(
                "generation_failure_recorded",
                error_type=error_type.value,
                details=details,
                module=module_name,
            )

    def start_generation(self, module_name: str) -> None:
        """
        Mark start of a generation run.

        Args:
            module_name: Name of module being generated
        """
        self._current_start = time.time()
        self._current_module = module_name

        if self.enable_logging:
            logger.debug("generation_started", module=module_name)

    def get_prometheus_output(self) -> str:
        """
        Get metrics in Prometheus format.

        Returns:
            Prometheus exposition format string
        """
        metrics = self.emit_metrics()
        lines = []
        for m in metrics:
            lines.extend(
                [
                    f"# HELP {m.name} CodeGen metric",
                    f"# TYPE {m.name} {m.metric_type.value}",
                    m.to_prometheus(),
                ]
            )
        return "\n".join(lines)

    def get_report(
        self,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> TelemetryReport:
        """
        Generate aggregated telemetry report.

        Args:
            period_start: Start of reporting period
            period_end: End of reporting period

        Returns:
            TelemetryReport with aggregates
        """
        now = datetime.now(UTC)
        start = period_start or datetime.min.replace(tzinfo=UTC).replace(tzinfo=UTC)
        end = period_end or now

        # Filter history by period
        history = [
            m
            for m in self._generation_history
            if m.start_time and start.timestamp() <= m.start_time <= end.timestamp()
        ]

        # Aggregate
        report = TelemetryReport(
            period_start=start,
            period_end=end,
            total_generations=len(history),
            successful_generations=sum(1 for m in history if m.success),
            failed_generations=sum(1 for m in history if not m.success),
            total_files=sum(m.files_generated for m in history),
            total_lines=sum(m.lines_generated for m in history),
        )

        # Latency stats
        latencies = [m.latency_ms for m in history if m.latency_ms > 0]
        if latencies:
            report.avg_latency_ms = sum(latencies) / len(latencies)
            report.max_latency_ms = max(latencies)
            report.min_latency_ms = min(latencies)

        # By module
        for m in history:
            report.by_module[m.module_name] = report.by_module.get(m.module_name, 0) + 1

        # By failure type
        for m in history:
            if m.failure_type:
                ft = m.failure_type.value
                report.by_failure_type[ft] = report.by_failure_type.get(ft, 0) + 1

        return report

    def _emit_generation_metrics(self, metrics: GenerationMetrics) -> None:
        """Emit metrics for a single generation."""
        labels = {"module": metrics.module_name}

        # Files generated
        self._metrics.append(
            MetricValue(
                name=f"{self.namespace}_files_generated",
                value=metrics.files_generated,
                metric_type=MetricType.GAUGE,
                labels=labels,
            )
        )

        # Lines generated
        self._metrics.append(
            MetricValue(
                name=f"{self.namespace}_lines_generated",
                value=metrics.lines_generated,
                metric_type=MetricType.GAUGE,
                labels=labels,
            )
        )

        # Latency
        if metrics.latency_ms > 0:
            self._metrics.append(
                MetricValue(
                    name=f"{self.namespace}_latency_ms",
                    value=metrics.latency_ms,
                    metric_type=MetricType.HISTOGRAM,
                    labels=labels,
                )
            )

    def _classify_failure(self, error: str) -> FailureType:
        """Classify failure type from error message."""
        error_lower = error.lower()

        if "validation" in error_lower or "invalid" in error_lower:
            return FailureType.VALIDATION_ERROR
        if "compile" in error_lower or "syntax" in error_lower:
            return FailureType.COMPILATION_ERROR
        if "emit" in error_lower or "write" in error_lower:
            return FailureType.EMISSION_ERROR
        if "timeout" in error_lower:
            return FailureType.TIMEOUT
        if "governance" in error_lower or "blocked" in error_lower:
            return FailureType.GOVERNANCE_BLOCKED

        return FailureType.UNKNOWN

    def reset(self) -> None:
        """Reset all telemetry data."""
        self._metrics.clear()
        self._generation_history.clear()
        self._latencies.clear()
        self._total_generations = 0
        self._total_files = 0
        self._total_lines = 0
        self._total_failures = 0

        logger.info("telemetry_reset")


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


# Global telemetry instance
_telemetry: CodeGenTelemetry | None = None


def get_telemetry() -> CodeGenTelemetry:
    """Get or create global telemetry instance."""
    global _telemetry
    if _telemetry is None:
        _telemetry = CodeGenTelemetry()
    return _telemetry


def record_generation(
    meta: dict[str, Any],
    files: dict[str, str],
    success: bool = True,
) -> GenerationMetrics:
    """Record a generation using global telemetry."""
    return get_telemetry().record_generation(meta, files, success)


def emit_metrics() -> list[MetricValue]:
    """Emit metrics from global telemetry."""
    return get_telemetry().emit_metrics()


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "AGE-INTE-008",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "data-models",
        "dataclass",
        "debugging",
        "intelligence",
        "logging",
        "messaging",
        "metrics",
    ],
    "keywords": [
        "codegen",
        "codegenagent",
        "count",
        "emit",
        "failure",
        "gen",
        "generation",
        "latency",
    ],
    "business_value": "Provides telemetry codegen components including MetricType, FailureType, MetricValue",
    "last_modified": "2026-01-15T23:26:53Z",
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
