"""
Span exporters for sending telemetry to various backends.

Includes console, file, substrate, and extensible composite exporter.
"""

import structlog
from typing import List, Any
from abc import ABC, abstractmethod

logger = structlog.get_logger(__name__)

from .models import Span

logger = structlog.get_logger(__name__)


class SpanExporter(ABC):
    """Abstract base class for span exporters."""

    @abstractmethod
    def export(self, spans: List[Span]) -> None:
        """Synchronously export spans."""
        pass


class AsyncSpanExporter(ABC):
    """Base class for async span exporters."""

    @abstractmethod
    async def export_async(self, spans: List[Span]) -> None:
        """Asynchronously export spans."""
        pass

    async def flush(self) -> None:
        """Flush any pending spans."""
        pass


class ConsoleExporter(SpanExporter):
    """Export spans to console (stdout)."""

    def export(self, spans: List[Span]) -> None:
        """Print spans to console."""
        for span in spans:
            status_icon = "✓" if span.status.value == "OK" else "✗"
            duration = f"{span.duration_ms:.2f}ms" if span.duration_ms else "pending"
            logger.info(
                f"  {status_icon} {span.name:30s} {duration:10s} "
                f"(trace: {span.trace_id[:8]}...)"
            )


class JSONFileExporter(SpanExporter):
    """Export spans to JSON Lines file."""

    def __init__(self, file_path: str = "/tmp/l9_spans.jsonl"):
        """Initialize file exporter."""
        self.file_path = file_path

    def export(self, spans: List[Span]) -> None:
        """Write spans as JSONL."""
        try:
            with open(self.file_path, "a") as f:
                for span in spans:
                    json_str = span.model_dump_json()
                    f.write(json_str + "\n")
                    f.flush()
        except Exception as exc:
            logger.error(f"Failed to write spans to file: {exc}")


class SubstrateExporter(AsyncSpanExporter):
    """Export spans to L9 Memory Substrate."""

    def __init__(self, substrate_service: Any):
        """Initialize substrate exporter."""
        self.substrate = substrate_service
        self._batch: List[Span] = []
        self._batch_size = 100

    async def export_async(self, spans: List[Span]) -> None:
        """Export spans to substrate (batched)."""
        self._batch.extend(spans)
        if len(self._batch) >= self._batch_size:
            await self.flush()

    async def flush(self) -> None:
        """Flush accumulated spans to substrate."""
        if not self._batch:
            return

        try:
            # Store telemetry in substrate with appropriate key
            for span in self._batch:
                key = f"traces/{span.trace_id}/{span.span_id}"
                await self.substrate.write(
                    key=key,
                    value=span.model_dump(),
                    metadata={
                        "span_name": span.name,
                        "duration_ms": span.duration_ms,
                        "status": span.status.value,
                    },
                )
            logger.debug(f"Flushed {len(self._batch)} spans to substrate")
            self._batch.clear()
        except Exception as exc:
            logger.error(f"Failed to export to substrate: {exc}")


class CompositeExporter:
    """Export to multiple backends simultaneously."""

    def __init__(self, exporters: List[SpanExporter]):
        """Initialize composite exporter."""
        self.exporters = exporters

    def export(self, spans: List[Span]) -> None:
        """Export spans to all backends."""
        for exporter in self.exporters:
            if isinstance(exporter, AsyncSpanExporter):
                continue  # Skip async exporters in sync context
            try:
                exporter.export(spans)
            except Exception as exc:
                logger.error(f"Export failed in {type(exporter).__name__}: {exc}")

    async def export_async(self, spans: List[Span]) -> None:
        """Export spans to all backends (async)."""
        for exporter in self.exporters:
            try:
                if isinstance(exporter, AsyncSpanExporter):
                    await exporter.export_async(spans)
                else:
                    exporter.export(spans)
            except Exception as exc:
                logger.error(f"Export failed in {type(exporter).__name__}: {exc}")

    async def flush(self) -> None:
        """Flush all async exporters."""
        for exporter in self.exporters:
            if isinstance(exporter, AsyncSpanExporter):
                try:
                    await exporter.flush()
                except Exception as exc:
                    logger.error(f"Flush failed in {type(exporter).__name__}: {exc}")
