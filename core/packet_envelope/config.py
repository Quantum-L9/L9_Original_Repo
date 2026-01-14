"""
l9/upgrades/packet_envelope/config.py
Configuration for PacketEnvelope upgrade phases

Centralizes all configuration for phases 2-5:
  - Observability settings (Jaeger, Prometheus)
  - CloudEvents configuration
  - Batch ingestion limits
  - Governance policies
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List

# ============================================================================
# ENVIRONMENT-BASED CONFIGURATION
# ============================================================================


def _get_env(key: str, default: str = "") -> str:
    """Get environment variable with fallback"""
    return os.environ.get(key, default)


def _get_env_bool(key: str, default: bool = False) -> bool:
    """Get boolean environment variable"""
    return _get_env(key, str(default)).lower() in ("true", "1", "yes")


def _get_env_int(key: str, default: int = 0) -> int:
    """Get integer environment variable"""
    try:
        return int(_get_env(key, str(default)))
    except ValueError:
        return default


# ============================================================================
# OBSERVABILITY CONFIGURATION (Phase 2)
# ============================================================================


@dataclass
class JaegerConfig:
    """Jaeger tracing configuration"""

    host: str = field(default_factory=lambda: _get_env("JAEGER_AGENT_HOST", "localhost"))
    port: int = field(default_factory=lambda: _get_env_int("JAEGER_AGENT_PORT", 6831))
    service_name: str = field(
        default_factory=lambda: _get_env("JAEGER_SERVICE_NAME", "l9-packet-envelope")
    )
    sample_rate: float = 1.0
    max_tag_length: int = 2048


@dataclass
class PrometheusConfig:
    """Prometheus metrics configuration"""

    port: int = field(default_factory=lambda: _get_env_int("PROMETHEUS_PORT", 8000))
    namespace: str = "l9"
    subsystem: str = "packet_envelope"


@dataclass
class ObservabilityPhaseConfig:
    """Phase 2 observability configuration"""

    enabled: bool = field(default_factory=lambda: _get_env_bool("L9_OBSERVABILITY_ENABLED", True))
    jaeger: JaegerConfig = field(default_factory=JaegerConfig)
    prometheus: PrometheusConfig = field(default_factory=PrometheusConfig)
    trace_internal_calls: bool = True
    trace_cache_ops: bool = True
    trace_serialization: bool = False  # Too noisy


# ============================================================================
# CLOUDEVENTS CONFIGURATION (Phase 3)
# ============================================================================


@dataclass
class CloudEventsConfig:
    """Phase 3 CloudEvents configuration"""

    spec_version: str = "1.0"
    source_prefix: str = "l9"
    default_content_type: str = "application/json"
    max_event_size_bytes: int = 1_000_000  # 1MB
    schema_validation_enabled: bool = True


# ============================================================================
# BATCH INGESTION CONFIGURATION (Phase 4)
# ============================================================================


@dataclass
class BatchIngestionConfig:
    """Phase 4 batch ingestion configuration"""

    batch_size: int = field(default_factory=lambda: _get_env_int("L9_BATCH_SIZE", 1000))
    max_concurrent_batches: int = field(
        default_factory=lambda: _get_env_int("L9_MAX_CONCURRENT_BATCHES", 10)
    )
    db_pool_size: int = field(default_factory=lambda: _get_env_int("L9_DB_POOL_SIZE", 20))
    timeout_seconds: int = 30
    idempotency_cache_ttl_seconds: int = 3600


@dataclass
class EventStoreConfig:
    """Phase 4 event store configuration"""

    snapshot_interval: int = 100
    max_events_per_aggregate: int = 10000
    enable_compression: bool = True


@dataclass
class ScalabilityPhaseConfig:
    """Phase 4 scalability configuration"""

    batch_ingestion: BatchIngestionConfig = field(default_factory=BatchIngestionConfig)
    event_store: EventStoreConfig = field(default_factory=EventStoreConfig)
    cqrs_enabled: bool = True
    streaming_enabled: bool = True


# ============================================================================
# GOVERNANCE CONFIGURATION (Phase 5)
# ============================================================================


@dataclass
class RetentionConfig:
    """Data retention policies"""

    default_ttl_days: int = 90
    pii_ttl_days: int = 14
    audit_log_ttl_days: int = 2555  # 7 years
    enable_auto_cleanup: bool = True
    cleanup_batch_size: int = 1000


@dataclass
class GDPRConfig:
    """GDPR compliance configuration"""

    require_approval_for_delete: bool = True
    enable_cascading_delete: bool = True
    enable_anonymization: bool = True
    proof_signature_algorithm: str = "sha256"


@dataclass
class GovernancePhaseConfig:
    """Phase 5 governance configuration"""

    retention: RetentionConfig = field(default_factory=RetentionConfig)
    gdpr: GDPRConfig = field(default_factory=GDPRConfig)
    compliance_logging_enabled: bool = True


# ============================================================================
# MASTER CONFIGURATION
# ============================================================================


@dataclass
class PacketEnvelopeUpgradeConfig:
    """Master configuration for all upgrade phases"""

    # Phase enablement flags
    phase_2_enabled: bool = field(
        default_factory=lambda: _get_env_bool("L9_PHASE_2_ENABLED", True)
    )
    phase_3_enabled: bool = field(
        default_factory=lambda: _get_env_bool("L9_PHASE_3_ENABLED", True)
    )
    phase_4_enabled: bool = field(
        default_factory=lambda: _get_env_bool("L9_PHASE_4_ENABLED", True)
    )
    phase_5_enabled: bool = field(
        default_factory=lambda: _get_env_bool("L9_PHASE_5_ENABLED", True)
    )

    # Phase-specific configurations
    observability: ObservabilityPhaseConfig = field(
        default_factory=ObservabilityPhaseConfig
    )
    cloudevents: CloudEventsConfig = field(default_factory=CloudEventsConfig)
    scalability: ScalabilityPhaseConfig = field(default_factory=ScalabilityPhaseConfig)
    governance: GovernancePhaseConfig = field(default_factory=GovernancePhaseConfig)

    # Global settings
    backward_compatible: bool = True
    rollback_enabled: bool = True
    dry_run_mode: bool = field(
        default_factory=lambda: _get_env_bool("L9_UPGRADE_DRY_RUN", False)
    )


# ============================================================================
# SINGLETON CONFIG INSTANCE
# ============================================================================

_config_instance: PacketEnvelopeUpgradeConfig | None = None


def get_config() -> PacketEnvelopeUpgradeConfig:
    """Get singleton configuration instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = PacketEnvelopeUpgradeConfig()
    return _config_instance


def reload_config() -> PacketEnvelopeUpgradeConfig:
    """Reload configuration from environment"""
    global _config_instance
    _config_instance = PacketEnvelopeUpgradeConfig()
    return _config_instance

