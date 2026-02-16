"""
Observability module configuration and settings.

Loads configuration from environment variables (OBS_*) using Pydantic.
See docs/OBSERVABILITY.md for full documentation.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Config",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-12T16:30:23Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "config",
    "type": "schema",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "core.observability.circuit_breaker",
            "tests.core.observability.test_observability_integration",
        ],
    },
}
# ============================================================================


import os

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ObservabilitySettings(BaseSettings):
    """Central configuration for observability subsystem."""

    model_config = SettingsConfigDict(
        env_prefix="OBS_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra env vars not in this model
    )

    enabled: bool = Field(
        default=True,
        description="Enable/disable observability system",
    )
    sampling_rate: float = Field(
        default=0.10,
        description="Fraction of requests to sample (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )
    error_sampling_rate: float = Field(
        default=1.0,
        description="Fraction of errors to sample (0.0-1.0), typically 1.0 for full coverage",
        ge=0.0,
        le=1.0,
    )
    exporters: list[str] = Field(
        default_factory=lambda: ["console"],
        description="List of exporters: console, file, substrate, jaeger, datadog, honeycomb",
    )
    jaeger_enabled: bool = Field(
        default=False,
        description="Export to Jaeger for distributed tracing",
    )
    jaeger_endpoint: str | None = Field(
        default=None,
        description="Jaeger OTLP endpoint (default: http://jaeger:4318/v1/traces)",
    )
    batch_size: int = Field(
        default=100,
        description="Number of spans to batch before export",
        gt=0,
    )
    batch_timeout_sec: int = Field(
        default=10,
        description="Seconds to wait before flushing batch (whichever comes first)",
        gt=0,
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR",
    )
    file_export_path: str = Field(
        default_factory=lambda: os.getenv("L9_SPANS_PATH", "/tmp/l9_spans.jsonl"),  # noqa: S108 — intentional temp path for span export
        description="Path for file exporter output",
    )
    substrate_enabled: bool = Field(
        default=True,
        description="Export to L9 Memory Substrate (if available)",
    )
    datadog_enabled: bool = Field(
        default=False,
        description="Export to Datadog APM",
    )
    datadog_api_key: str | None = Field(
        default=None,
        description="Datadog API key (required if datadog_enabled=True)",
    )
    context_strategy_default: str = Field(
        default="recency_biased_window",
        description="Default context window strategy",
    )
    context_max_tokens: int = Field(
        default=8000,
        description="Maximum tokens in assembled context",
        gt=0,
    )
    enable_circuit_breaker: bool = Field(
        default=True,
        description="Enable circuit breaker for failure recovery",
    )
    enable_backoff_retry: bool = Field(
        default=True,
        description="Enable exponential backoff retry",
    )
    circuit_breaker_threshold: int = Field(
        default=5,
        description="Number of failures before circuit opens",
        gt=0,
    )
    circuit_breaker_window_sec: int = Field(
        default=60,
        description="Time window for failure counting",
        gt=0,
    )
    circuit_breaker_reset_timeout_sec: int = Field(
        default=30,
        description="Seconds to wait in OPEN state before testing recovery (HALF_OPEN)",
        gt=0,
    )

    @model_validator(mode="after")
    def auto_enable_substrate_exporter(self) -> "ObservabilitySettings":
        """
        Automatically add 'substrate' to exporters if substrate_enabled=True
        and it's not already in the list.
        """
        if self.substrate_enabled and "substrate" not in self.exporters:
            # Create a new list to avoid mutating the default
            self.exporters = [*list(self.exporters), "substrate"]
        return self


def load_config() -> ObservabilitySettings:
    """Load observability configuration from environment."""
    return ObservabilitySettings()


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-059",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "batch-processing",
        "core",
        "debugging",
        "foundation",
        "schema",
        "testing",
        "tracing",
        "validation",
    ],
    "keywords": [
        "auto",
        "configuration",
        "enable",
        "exporter",
        "load",
        "module",
        "observability",
        "substrate",
    ],
    "business_value": "Implements ObservabilitySettings for config functionality",
    "last_modified": "2026-01-12T16:30:23Z",
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
