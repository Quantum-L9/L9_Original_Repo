"""
L9 Research Factory State

Generated from: research_factory_schema.yaml
LangGraph-compatible state model for the 5-pass research pipeline.

The state flows through:
  pass_1_plan_queries → pass_2_build_superprompts → pass_3_execute_retrieval →
  pass_4_extract_results → pass_5_integrate_results
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Research Factory State",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "research_factory_state",
    "type": "enum",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["core.schemas.__init__", "core.schemas.research_factory_nodes", "core.schemas.tests.test_research_factory", "core.schemas.universal_schema"],
    },
}
# ============================================================================

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from core.schemas.research_factory_models import (
    IntegrationResult,
    ParsedObject,
    QueryPlan,
    ResearchJobSpec,
    ResearchMetrics,
    RetrievalBatch,
    Superprompt,
)


class PassStatus(str, Enum):
    """Status of each pass in the pipeline."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PassMetadata(BaseModel):
    """Metadata for a single pass execution."""

    status: PassStatus = Field(default=PassStatus.PENDING)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    error: Optional[str] = None

    model_config = {"extra": "allow"}


class ResearchState(BaseModel):
    """
    LangGraph state model for the Research Factory 5-pass pipeline.

    This state object is passed through each node and accumulated
    as the pipeline progresses.

    Usage:
        async def pass_1_plan_queries(state: ResearchState) -> ResearchState:
            ...
            return state.model_copy(update={"query_plan": new_plan, ...})
    """

    # === Identity ===
    state_id: UUID = Field(default_factory=uuid4, description="Unique state identifier")
    thread_id: UUID = Field(default_factory=uuid4, description="Thread/conversation ID")

    # === Input ===
    job_spec: Optional[ResearchJobSpec] = Field(
        None, description="Input job specification"
    )

    # === Pass 1 Output ===
    query_plan: Optional[QueryPlan] = Field(None, description="Generated query plan")

    # === Pass 2 Output ===
    superprompts: list[Superprompt] = Field(
        default_factory=list, description="Built superprompts"
    )

    # === Pass 3 Output ===
    retrieval_batches: list[RetrievalBatch] = Field(
        default_factory=list, description="Retrieval results"
    )

    # === Pass 4 Output ===
    parsed_objects: list[ParsedObject] = Field(
        default_factory=list, description="Extracted objects"
    )

    # === Pass 5 Output ===
    integration_result: Optional[IntegrationResult] = Field(
        None, description="Final integration result"
    )

    # === Execution Tracking ===
    current_pass: int = Field(
        default=0, ge=0, le=5, description="Current pass number (0=not started)"
    )
    pass_metadata: dict[str, PassMetadata] = Field(
        default_factory=lambda: {
            "pass_1": PassMetadata(),
            "pass_2": PassMetadata(),
            "pass_3": PassMetadata(),
            "pass_4": PassMetadata(),
            "pass_5": PassMetadata(),
        },
        description="Metadata for each pass",
    )

    # === Error Handling ===
    errors: list[str] = Field(default_factory=list, description="Accumulated errors")
    warnings: list[str] = Field(
        default_factory=list, description="Accumulated warnings"
    )

    # === Timestamps ===
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"extra": "allow"}  # Allow LangGraph to add fields

    def start_pass(self, pass_num: int) -> "ResearchState":
        """Mark a pass as started and update state."""
        pass_key = f"pass_{pass_num}"
        new_metadata = self.pass_metadata.copy()
        new_metadata[pass_key] = PassMetadata(
            status=PassStatus.RUNNING, started_at=datetime.utcnow()
        )
        return self.model_copy(
            update={
                "current_pass": pass_num,
                "pass_metadata": new_metadata,
                "updated_at": datetime.utcnow(),
            }
        )

    def complete_pass(
        self, pass_num: int, error: Optional[str] = None
    ) -> "ResearchState":
        """Mark a pass as completed or failed."""
        pass_key = f"pass_{pass_num}"
        current_meta = self.pass_metadata.get(pass_key, PassMetadata())

        completed_at = datetime.utcnow()
        duration_ms = None
        if current_meta.started_at:
            duration_ms = (
                completed_at - current_meta.started_at
            ).total_seconds() * 1000

        new_metadata = self.pass_metadata.copy()
        new_metadata[pass_key] = PassMetadata(
            status=PassStatus.FAILED if error else PassStatus.COMPLETED,
            started_at=current_meta.started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            error=error,
        )

        errors = self.errors.copy()
        if error:
            errors.append(f"Pass {pass_num}: {error}")

        return self.model_copy(
            update={
                "pass_metadata": new_metadata,
                "errors": errors,
                "updated_at": datetime.utcnow(),
            }
        )

    def add_error(self, error: str) -> "ResearchState":
        """Add an error to the state."""
        return self.model_copy(
            update={"errors": self.errors + [error], "updated_at": datetime.utcnow()}
        )

    def add_warning(self, warning: str) -> "ResearchState":
        """Add a warning to the state."""
        return self.model_copy(
            update={
                "warnings": self.warnings + [warning],
                "updated_at": datetime.utcnow(),
            }
        )

    @property
    def is_complete(self) -> bool:
        """Check if all passes are complete."""
        return all(
            meta.status == PassStatus.COMPLETED for meta in self.pass_metadata.values()
        )

    @property
    def has_errors(self) -> bool:
        """Check if any errors occurred."""
        return len(self.errors) > 0 or any(
            meta.status == PassStatus.FAILED for meta in self.pass_metadata.values()
        )

    def to_metrics(self) -> ResearchMetrics:
        """Generate metrics from current state."""
        valid = sum(
            1 for p in self.parsed_objects if p.validation_status.value == "valid"
        )
        invalid = sum(
            1 for p in self.parsed_objects if p.validation_status.value == "invalid"
        )

        avg_conf = 0.0
        if self.parsed_objects:
            avg_conf = sum(p.confidence for p in self.parsed_objects) / len(
                self.parsed_objects
            )

        pass_durations = {}
        total_latency = 0.0
        for key, meta in self.pass_metadata.items():
            if meta.duration_ms is not None:
                pass_durations[key] = meta.duration_ms
                total_latency += meta.duration_ms

        return ResearchMetrics(
            total_queries=len(self.query_plan.queries) if self.query_plan else 0,
            total_results=len(self.parsed_objects),
            valid_results=valid,
            invalid_results=invalid,
            avg_confidence=avg_conf,
            total_latency_ms=total_latency,
            pass_durations_ms=pass_durations,
        )

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-071",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.schemas.research_factory_models"],
    "tags": ["async", "batch-processing", "data-models", "enum", "foundation", "metrics", "pydantic", "validation"],
    "keywords": ["complete", "errors", "factory", "metadata", "metrics", "pass", "plan", "queries"],
    "business_value": "pass_1_plan_queries → pass_2_build_superprompts → pass_3_execute_retrieval → pass_4_extract_results → pass_5_integrate_results",
    "last_modified": "2026-01-07T13:35:57Z",
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
