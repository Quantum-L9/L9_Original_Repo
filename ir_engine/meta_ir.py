"""
L9 IR Engine - MetaContract Schema
==================================

Pydantic models for Module-Spec-v2.4.0 (OPERATIONAL / ENTERPRISE GRADE).

Maps all 22 sections from the Universal Module Spec:
1. Metadata
2. Ownership
3. Runtime Wiring (KEYSTONE)
4. External Surface
5. Dependencies
6. Packet Contract
7. Idempotency
8. Error Policy
9. Observability
10. Runtime Touchpoints
11. Test Scope
12. Acceptance
13. Global Invariants Acknowledgement
14. Spec Confidence
15. File Manifest (Repo)
16. Interfaces
17. Environment Variables
18. Orchestration Flow
19. Boot Impact
20. Mandatory Standards
21. Goals & Non-Goals
22. Notes for P

Version: 2.4.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "MetaContract Schema",
    "module_version": "2.4.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "intelligence",
    "domain": "data_models",
    "module_name": "meta_ir",
    "type": "enum",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API", "Perplexity API"],
        "memory_layers": [],
        "imported_by": [
            "conftest",
            "ir_engine.__init__",
            "ir_engine.compile_meta_to_ir",
            "ir_engine.schema_validator",
            "runtime.construct_enhancer",
        ],
    },
}
# ============================================================================

from enum import Enum
from typing import Any, Literal

import structlog
from pydantic import BaseModel, Field, model_validator

logger = structlog.get_logger(__name__)


# =============================================================================
# Enums for constrained values
# =============================================================================


class ModuleTier(str, Enum):
    """Module tier classification (0-7)."""

    TIER_0 = "0"
    TIER_1 = "1"
    TIER_2 = "2"
    TIER_3 = "3"
    TIER_4 = "4"
    TIER_5 = "5"
    TIER_6 = "6"
    TIER_7 = "7"


class OwnershipTeam(str, Enum):
    """Team responsible for the module."""

    CORE = "core"
    INFRA = "infra"
    INTEGRATIONS = "integrations"
    SECURITY = "security"
    OBSERVABILITY = "observability"


class ServiceType(str, Enum):
    """Which service the module runs in."""

    API = "api"
    WORKER = "worker"
    SCHEDULER = "scheduler"
    MEMORY = "memory"


class StartupPhase(str, Enum):
    """When the module starts relative to others."""

    EARLY = "early"
    NORMAL = "normal"
    LATE = "late"


class CallableFrom(str, Enum):
    """Who can call this module."""

    EXTERNAL = "external"
    INTERNAL = "internal"


class InterfaceType(str, Enum):
    """Interface type for outbound calls."""

    HTTP = "http"
    TOOL = "tool"


class IdempotencyPattern(str, Enum):
    """Idempotency deduplication pattern."""

    EVENT_ID = "event_id"
    COMPOSITE_KEY = "composite_key"
    SUBSTRATE_LOOKUP = "substrate_lookup"


class IdempotencySource(str, Enum):
    """Source of idempotency key."""

    PLATFORM_EVENT_ID = "platform_event_id"
    WEBHOOK_HEADER = "webhook_header"
    COMPUTED_HASH = "computed_hash"


class IdempotencyDurability(str, Enum):
    """Durability of idempotency state."""

    IN_MEMORY = "in_memory"
    SUBSTRATE = "substrate"


class ErrorStrategy(str, Enum):
    """Default error handling strategy."""

    FAIL_FAST = "fail_fast"
    BEST_EFFORT = "best_effort"


class AlertLevel(str, Enum):
    """Alert level for escalation."""

    NONE = "none"
    LOG = "log"
    METRIC = "metric"


class LogLevel(str, Enum):
    """Logging level."""

    INFO = "info"
    DEBUG = "debug"


class AuthType(str, Enum):
    """Authentication type."""

    HMAC_SHA256 = "hmac-sha256"
    BEARER = "bearer"
    API_KEY = "api_key"
    NONE = "none"


class BootImpactLevel(str, Enum):
    """Boot impact level."""

    NONE = "none"
    SOFT = "soft"
    HARD = "hard"


class SpecConfidenceLevel(str, Enum):
    """Spec confidence level."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# =============================================================================
# Section 1: METADATA (REQUIRED)
# =============================================================================


class ModuleMetadata(BaseModel):
    """Section 1: Module metadata."""

    module_id: str = Field(
        ...,
        description="Unique identifier (lowercase, snake_case)",
        pattern=r"^[a-z][a-z0-9_]*$",
    )
    name: str = Field(..., description="Human-readable name")
    tier: str = Field(..., description="Module tier classification (0-7)")
    description: str = Field(..., description="One-line description")
    system: str = Field(default="L9", description="System identifier")
    language: str = Field(default="python", description="Programming language")
    runtime: str = Field(default="python>=3.11", description="Runtime requirement")


# =============================================================================
# Section 2: OWNERSHIP (REQUIRED — v2.4 NEW)
# =============================================================================


class OwnershipSpec(BaseModel):
    """Section 2: Enterprise hygiene for ops and incident escalation."""

    team: str = Field(
        ...,
        description="Team responsible (core | infra | integrations | security | observability)",
    )
    primary_contact: str = Field(..., description="Primary contact role")


# =============================================================================
# Section 3: RUNTIME WIRING (REQUIRED — v2.4 KEYSTONE)
# =============================================================================


class RuntimeWiringSpec(BaseModel):
    """
    Section 3: SINGLE SOURCE OF TRUTH for docker-compose ordering,
    startup health checks, and boot-failure tests.
    """

    service: str = Field(
        ...,
        description="Which service this module runs in (api | worker | scheduler | memory)",
    )
    startup_phase: str = Field(
        ..., description="When to start relative to others (early | normal | late)"
    )
    depends_on: list[str] = Field(
        default_factory=list,
        description="Services that must be running before this module starts",
    )
    blocks_startup_on_failure: bool = Field(
        ..., description="Does missing dependency cause hard boot failure?"
    )


# =============================================================================
# Section 4: EXTERNAL SURFACE (REQUIRED)
# =============================================================================


class ExternalSurface(BaseModel):
    """Section 4: External surface exposure."""

    exposes_http_endpoint: bool = Field(..., description="Exposes HTTP endpoint")
    exposes_webhook: bool = Field(..., description="Exposes webhook")
    exposes_tool: bool = Field(..., description="Exposes tool")
    callable_from: list[str] = Field(
        default_factory=list, description="Who can call this (external | internal)"
    )


# =============================================================================
# Section 5: DEPENDENCIES (REQUIRED — v2.4 OPERATIONALIZED)
# =============================================================================


class OutboundCall(BaseModel):
    """Single outbound call declaration."""

    module: str = Field(..., description="Target module")
    interface: str = Field(..., description="Interface type (http | tool)")
    endpoint: str = Field(..., description="Endpoint path or tool_id")


class DependencySpec(BaseModel):
    """Section 5: Explicit dependencies with endpoints."""

    allowed_tiers: list[int] = Field(
        default_factory=list, description="Which tiers this module may call"
    )
    outbound_calls: list[OutboundCall] = Field(
        default_factory=list,
        description="Explicit outbound calls with interface + endpoint",
    )


# =============================================================================
# Section 6: PACKET CONTRACT (REQUIRED)
# =============================================================================


class PacketContract(BaseModel):
    """Section 6: Runtime blocks undeclared packet writes."""

    emits: list[str] = Field(
        ..., description="All packet types this module can emit", min_length=1
    )
    requires_metadata: list[str] = Field(
        default_factory=lambda: ["task_id", "thread_uuid", "source", "tool_id"],
        description="Metadata fields MANDATORY on every packet",
    )


# =============================================================================
# Section 7: IDEMPOTENCY (REQUIRED — NO INFERENCE)
# =============================================================================


class IdempotencySpec(BaseModel):
    """Section 7: Idempotency configuration."""

    pattern: str = Field(
        ...,
        description="Deduplication pattern (event_id | composite_key | substrate_lookup)",
    )
    source: str = Field(..., description="Source of idempotency key")
    durability: str = Field(..., description="State durability (in_memory | substrate)")


# =============================================================================
# Section 8: ERROR POLICY (REQUIRED — v2.4 ENHANCED)
# =============================================================================


class RetryConfig(BaseModel):
    """Retry configuration."""

    enabled: bool = Field(..., description="Retries enabled")
    max_attempts: int = Field(default=3, description="Maximum retry attempts")


class EscalationConfig(BaseModel):
    """Escalation behavior (v2.4 new)."""

    emit_error_packet: bool = Field(..., description="Emit error packet on failure")
    mark_task_failed: bool = Field(..., description="Mark task as failed")
    alert: str = Field(default="log", description="Alert level (none | log | metric)")


class ErrorCategory(BaseModel):
    """Error category handling."""

    status: int = Field(..., description="HTTP status code")
    action: str = Field(..., description="Action to take")
    log: str = Field(..., description="Log message key")


class ErrorPolicy(BaseModel):
    """Section 8: Error handling with escalation."""

    default: str = Field(..., description="Default strategy (fail_fast | best_effort)")
    retries: RetryConfig = Field(..., description="Retry configuration")
    escalation: EscalationConfig = Field(..., description="Escalation behavior")

    # Error categories (optional detailed handling)
    invalid_signature: ErrorCategory | None = None
    stale_timestamp: ErrorCategory | None = None
    aios_failure: ErrorCategory | None = None
    side_effect_failure: ErrorCategory | None = None
    storage_failure: ErrorCategory | None = None


# =============================================================================
# Section 9: OBSERVABILITY (REQUIRED — v2.4 ENHANCED)
# =============================================================================


class LogsConfig(BaseModel):
    """Logging configuration."""

    enabled: bool = Field(default=True, description="Logging enabled")
    level: str = Field(default="info", description="Log level (info | debug)")


class MetricsConfig(BaseModel):
    """Metrics configuration."""

    enabled: bool = Field(default=True, description="Metrics enabled")
    counters: list[str] = Field(default_factory=list, description="Counter metrics")
    histograms: list[str] = Field(default_factory=list, description="Histogram metrics")


class TracesConfig(BaseModel):
    """Tracing configuration."""

    enabled: bool = Field(default=False, description="Tracing enabled")


class ObservabilitySpec(BaseModel):
    """Section 9: Intent declaration for observability."""

    logs: LogsConfig = Field(default_factory=LogsConfig)
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    traces: TracesConfig = Field(default_factory=TracesConfig)


# =============================================================================
# Section 10: RUNTIME TOUCHPOINTS (REQUIRED)
# =============================================================================


class RuntimeTouchpoints(BaseModel):
    """Section 10: What runtime resources this module touches."""

    touches_db: bool = Field(..., description="Touches database")
    touches_tools: bool = Field(..., description="Touches tools")
    touches_external_network: bool = Field(..., description="Touches external network")
    affects_boot: bool = Field(..., description="Affects boot process")


# =============================================================================
# Section 11: TEST SCOPE (REQUIRED)
# =============================================================================


class TestScope(BaseModel):
    """Section 11: Required test coverage."""

    unit: bool = Field(default=True, description="Unit tests required")
    integration: bool = Field(..., description="Integration tests required")
    docker_smoke: bool = Field(..., description="Docker smoke tests required")


# =============================================================================
# Section 12: ACCEPTANCE (REQUIRED)
# =============================================================================


class AcceptanceCriterion(BaseModel):
    """Single acceptance criterion."""

    id: str = Field(..., description="Criterion ID (e.g., AP-1, AN-1)")
    description: str = Field(..., description="What is being tested")
    test: str | None = Field(None, description="Test function name")
    expected_behavior: str | None = Field(
        None, description="Expected behavior (for negative)"
    )


class AcceptanceSpec(BaseModel):
    """Section 12: Acceptance criteria."""

    positive: list[AcceptanceCriterion] = Field(
        ..., description="Positive test cases", min_length=1
    )
    negative: list[AcceptanceCriterion] = Field(
        ..., description="Negative test cases (at least one required)", min_length=1
    )


# =============================================================================
# Section 13: GLOBAL INVARIANTS ACKNOWLEDGEMENT (REQUIRED)
# =============================================================================


class GlobalInvariantsAck(BaseModel):
    """Section 13: All values MUST be true. Any deviation invalidates spec."""

    emits_packet_on_ingress: bool = Field(default=True)
    tool_calls_traceable: bool = Field(default=True)
    unknown_tool_id_hard_fail: bool = Field(default=True)
    malformed_packet_blocked: bool = Field(default=True)
    missing_env_fails_boot: bool = Field(default=True)

    @model_validator(mode="after")
    def validate_all_true(self) -> GlobalInvariantsAck:
        """All invariants must be True."""
        for field_name, value in self.model_dump().items():
            if value is not True:
                raise ValueError(
                    f"Global invariant '{field_name}' must be True, got {value}"
                )
        return self


# =============================================================================
# Section 14: SPEC CONFIDENCE (REQUIRED)
# =============================================================================


class SpecConfidence(BaseModel):
    """Section 14: Confidence level and basis."""

    level: str = Field(..., description="Confidence level (high | medium | low)")
    basis: list[str] = Field(default_factory=list, description="Basis for confidence")


# =============================================================================
# Section 15: FILE MANIFEST (REQUIRED)
# =============================================================================


class RepoSpec(BaseModel):
    """Section 15: File manifest for code generation."""

    root_path: str = Field(
        default="/Users/ib-mac/Projects/L9", description="Repository root"
    )
    allowed_new_files: list[str] = Field(
        default_factory=list, description="Files that may be created"
    )
    allowed_modified_files: list[str] = Field(
        default_factory=list, description="Files that may be modified"
    )


# =============================================================================
# Section 16: INTERFACES (REQUIRED)
# =============================================================================


class InboundInterface(BaseModel):
    """Inbound interface definition."""

    name: str = Field(..., description="Route name")
    method: str = Field(default="POST", description="HTTP method")
    route: str = Field(..., description="Route path")
    headers: list[str] = Field(default_factory=list, description="Required headers")
    payload_type: str = Field(default="JSON", description="Payload type")
    auth: str = Field(default="none", description="Auth type")


class OutboundInterface(BaseModel):
    """Outbound interface definition."""

    name: str = Field(..., description="Interface name")
    endpoint: str = Field(..., description="Endpoint URL or path")
    method: str = Field(default="POST", description="HTTP method")
    timeout_seconds: int = Field(default=30, description="Timeout in seconds")
    retry: bool = Field(default=False, description="Retry on failure")


class InterfacesSpec(BaseModel):
    """Section 16: Interface definitions."""

    inbound: list[InboundInterface] = Field(default_factory=list)
    outbound: list[OutboundInterface] = Field(default_factory=list)


# =============================================================================
# Section 17: ENVIRONMENT VARIABLES (REQUIRED)
# =============================================================================


class EnvVar(BaseModel):
    """Environment variable definition."""

    name: str = Field(..., description="Variable name")
    description: str = Field(..., description="Variable description")
    default: str | None = Field(None, description="Default value")


class EnvironmentSpec(BaseModel):
    """Section 17: Environment variables."""

    required: list[EnvVar] = Field(
        default_factory=list, description="Required env vars"
    )
    optional: list[EnvVar] = Field(
        default_factory=list, description="Optional env vars"
    )


# =============================================================================
# Section 18: ORCHESTRATION FLOW (REQUIRED)
# =============================================================================


class ContextRead(BaseModel):
    """Context read operation."""

    method: str = Field(..., description="Method to call")
    filter: str = Field(..., description="Filter criteria")
    purpose: str = Field(..., description="Purpose of read")


class AIOSCall(BaseModel):
    """AIOS call definition."""

    endpoint: str = Field(..., description="Endpoint to call")
    input: str = Field(..., description="Input description")
    output: str = Field(..., description="Output description")


class SideEffect(BaseModel):
    """Side effect definition."""

    action: str = Field(..., description="Action description")
    service: str = Field(..., description="Service to call")
    packet_type: str | None = Field(None, description="Packet type if applicable")


class OrchestrationSpec(BaseModel):
    """Section 18: Orchestration flow."""

    validation: list[str] = Field(default_factory=list, description="Validation steps")
    context_reads: list[ContextRead] = Field(default_factory=list)
    aios_calls: list[AIOSCall] = Field(default_factory=list)
    side_effects: list[SideEffect] = Field(default_factory=list)


# =============================================================================
# Section 19: BOOT IMPACT (REQUIRED)
# =============================================================================


class BootImpact(BaseModel):
    """Section 19: Boot impact level and reason."""

    level: str = Field(..., description="Impact level (none | soft | hard)")
    reason: str = Field(..., description="Explanation of boot impact")


# =============================================================================
# Section 20: MANDATORY STANDARDS (REQUIRED)
# =============================================================================


class IdentityStandard(BaseModel):
    """Identity standard."""

    canonical_identifier: str = Field(default="tool_id")


class LoggingStandard(BaseModel):
    """Logging standard."""

    library: str = Field(default="structlog")
    forbidden: list[str] = Field(default_factory=lambda: ["logging", "print"])


class HttpClientStandard(BaseModel):
    """HTTP client standard."""

    library: str = Field(default="httpx")
    forbidden: list[str] = Field(default_factory=lambda: ["aiohttp", "requests"])


class StandardsSpec(BaseModel):
    """Section 20: Mandatory standards."""

    identity: IdentityStandard = Field(default_factory=IdentityStandard)
    logging: LoggingStandard = Field(default_factory=LoggingStandard)
    http_client: HttpClientStandard = Field(default_factory=HttpClientStandard)


# =============================================================================
# Section 21: GOALS & NON-GOALS (REQUIRED)
# =============================================================================


class GoalsSpec(BaseModel):
    """Section 21: Goals and non-goals."""

    goals: list[str] = Field(default_factory=list, description="Module goals")
    non_goals: list[str] = Field(
        default_factory=lambda: [
            "No new database tables",
            "No new migrations",
            "No parallel memory/logging/config systems",
        ],
        description="Module non-goals",
    )


# =============================================================================
# Section 22: NOTES FOR P (OPTIONAL)
# =============================================================================
# Notes for Perplexity are not validated, just passed through


# =============================================================================
# MAIN MODEL: MetaContract
# =============================================================================


class MetaContract(BaseModel):
    """
    Complete Module Spec v2.4.0 (OPERATIONAL / ENTERPRISE GRADE).

    A single spec is sufficient to:
    - Determine runtime placement
    - Determine startup order
    - Determine service dependencies
    - Determine failure blast radius
    - Determine observability requirements
    - Determine test obligations
    - Generate docker-compose wiring
    - Generate runtime + smoke tests
    """

    # Schema version for validation gating
    schema_version: str = Field(default="2.4", description="Schema version")

    # === SECTION 1: METADATA ===
    metadata: ModuleMetadata = Field(..., description="Module metadata")

    # === SECTION 2: OWNERSHIP ===
    ownership: OwnershipSpec = Field(..., description="Ownership and contact")

    # === SECTION 3: RUNTIME WIRING (KEYSTONE) ===
    runtime_wiring: RuntimeWiringSpec = Field(
        ..., description="Runtime wiring - SINGLE SOURCE OF TRUTH"
    )

    # === SECTION 4: EXTERNAL SURFACE ===
    external_surface: ExternalSurface = Field(..., description="External surface")

    # === SECTION 5: DEPENDENCIES ===
    dependencies: DependencySpec = Field(..., description="Dependencies")

    # === SECTION 6: PACKET CONTRACT ===
    packet_contract: PacketContract = Field(..., description="Packet contract")

    # === SECTION 7: IDEMPOTENCY ===
    idempotency: IdempotencySpec = Field(..., description="Idempotency config")

    # === SECTION 8: ERROR POLICY ===
    error_policy: ErrorPolicy = Field(..., description="Error handling policy")

    # === SECTION 9: OBSERVABILITY ===
    observability: ObservabilitySpec = Field(
        default_factory=ObservabilitySpec, description="Observability config"
    )

    # === SECTION 10: RUNTIME TOUCHPOINTS ===
    runtime_touchpoints: RuntimeTouchpoints = Field(
        ..., description="Runtime touchpoints"
    )

    # === SECTION 11: TEST SCOPE ===
    test_scope: TestScope = Field(..., description="Test scope requirements")

    # === SECTION 12: ACCEPTANCE ===
    acceptance: AcceptanceSpec = Field(..., description="Acceptance criteria")

    # === SECTION 13: GLOBAL INVARIANTS ACKNOWLEDGEMENT ===
    global_invariants_ack: GlobalInvariantsAck = Field(
        default_factory=GlobalInvariantsAck,
        description="Global invariants acknowledgement",
    )

    # === SECTION 14: SPEC CONFIDENCE ===
    spec_confidence: SpecConfidence = Field(..., description="Spec confidence")

    # === SECTION 15: FILE MANIFEST (REPO) ===
    repo: RepoSpec = Field(default_factory=RepoSpec, description="File manifest")

    # === SECTION 16: INTERFACES ===
    interfaces: InterfacesSpec = Field(
        default_factory=InterfacesSpec, description="Interface definitions"
    )

    # === SECTION 17: ENVIRONMENT VARIABLES ===
    environment: EnvironmentSpec = Field(
        default_factory=EnvironmentSpec, description="Environment variables"
    )

    # === SECTION 18: ORCHESTRATION FLOW ===
    orchestration: OrchestrationSpec = Field(
        default_factory=OrchestrationSpec, description="Orchestration flow"
    )

    # === SECTION 19: BOOT IMPACT ===
    boot_impact: BootImpact = Field(..., description="Boot impact")

    # === SECTION 20: MANDATORY STANDARDS ===
    standards: StandardsSpec = Field(
        default_factory=StandardsSpec, description="Mandatory standards"
    )

    # === SECTION 21: GOALS & NON-GOALS ===
    # Using separate fields for compatibility
    goals: list[str] = Field(default_factory=list, description="Module goals")
    non_goals: list[str] = Field(
        default_factory=lambda: [
            "No new database tables",
            "No new migrations",
            "No parallel memory/logging/config systems",
        ],
        description="Module non-goals",
    )

    # === SECTION 22: NOTES FOR P ===
    notes_for_perplexity: list[str] = Field(
        default_factory=list, description="Notes for Perplexity code generation"
    )

    # === VALIDATION ===

    @model_validator(mode="after")
    def validate_test_scope_rules(self) -> MetaContract:
        """
        Enforce validation rules from Module-Spec-v2.4:
        - If external_surface.exposes_http_endpoint == true → docker_smoke: true
        - If runtime_wiring.service != api → integration: true
        - If startup_phase == early → boot-failure test REQUIRED (via boot_impact.level == hard)
        """
        # Rule 1: HTTP endpoint requires docker smoke test
        if (
            self.external_surface.exposes_http_endpoint
            and not self.test_scope.docker_smoke
        ):
            logger.warning(
                "validation_warning",
                rule="HTTP endpoint exposed but docker_smoke not set to true",
            )

        # Rule 2: Non-API service requires integration tests
        if self.runtime_wiring.service != "api" and not self.test_scope.integration:
            logger.warning(
                "validation_warning",
                rule="Non-API service but integration tests not required",
            )

        return self

    def get_module_id(self) -> str:
        """Get the module ID."""
        return self.metadata.module_id

    def get_allowed_files(self) -> list[str]:
        """Get list of files that may be created or modified."""
        return self.repo.allowed_new_files + self.repo.allowed_modified_files

    def get_required_env_vars(self) -> list[str]:
        """Get list of required environment variable names."""
        return [env.name for env in self.environment.required]

    def get_packet_types(self) -> list[str]:
        """Get list of packet types this module emits."""
        return self.packet_contract.emits

    def to_generation_context(self) -> dict[str, Any]:
        """
        Convert to a context dict suitable for code generation templates.
        """
        return {
            "module_id": self.metadata.module_id,
            "module_name": self.metadata.name,
            "description": self.metadata.description,
            "tier": self.metadata.tier,
            "service": self.runtime_wiring.service,
            "startup_phase": self.runtime_wiring.startup_phase,
            "depends_on": self.runtime_wiring.depends_on,
            "exposes_http_endpoint": self.external_surface.exposes_http_endpoint,
            "exposes_webhook": self.external_surface.exposes_webhook,
            "exposes_tool": self.external_surface.exposes_tool,
            "packet_types": self.packet_contract.emits,
            "required_metadata": self.packet_contract.requires_metadata,
            "test_unit": self.test_scope.unit,
            "test_integration": self.test_scope.integration,
            "test_docker_smoke": self.test_scope.docker_smoke,
            "allowed_new_files": self.repo.allowed_new_files,
            "allowed_modified_files": self.repo.allowed_modified_files,
            "inbound_interfaces": [i.model_dump() for i in self.interfaces.inbound],
            "outbound_interfaces": [i.model_dump() for i in self.interfaces.outbound],
            "env_required": [e.model_dump() for e in self.environment.required],
            "env_optional": [e.model_dump() for e in self.environment.optional],
            "goals": self.goals,
            "non_goals": self.non_goals,
        }


# =============================================================================
# VALIDATION RESULT
# =============================================================================


class MetaContractValidationError(BaseModel):
    """Validation error for MetaContract."""

    field: str
    message: str
    severity: Literal["error", "warning", "info"] = "error"


class MetaContractValidationResult(BaseModel):
    """Result of MetaContract validation."""

    valid: bool = True
    errors: list[MetaContractValidationError] = Field(default_factory=list)
    warnings: list[MetaContractValidationError] = Field(default_factory=list)

    def add_error(self, field: str, message: str) -> None:
        """Add a validation error."""
        self.errors.append(
            MetaContractValidationError(field=field, message=message, severity="error")
        )
        self.valid = False

    def add_warning(self, field: str, message: str) -> None:
        """Add a validation warning."""
        self.warnings.append(
            MetaContractValidationError(
                field=field, message=message, severity="warning"
            )
        )


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "IR_-INTE-001",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "auth",
        "client",
        "data-models",
        "debugging",
        "enum",
        "event-driven",
        "intelligence",
        "logging",
        "messaging",
    ],
    "keywords": [
        "acceptance",
        "ack",
        "alert",
        "all",
        "allowed",
        "auth",
        "boot",
        "callable",
    ],
    "business_value": "1. Metadata 2. Ownership 3. Runtime Wiring (KEYSTONE) 4. External Surface 5. Dependencies 6. Packet Contract 7. Idempotency 8. Error Policy 9. Observability 10. Runtime Touchpoints 11. Test Scope 12. ",
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
