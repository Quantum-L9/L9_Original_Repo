"""
L9 Research Factory Models

Generated from: research_factory_schema.yaml
Module: research_factory v1.0.0
Schema version: 1.3.0

Implements a 5-pass structured research pipeline:
1. Pass 1 — plan_queries: derive research plan from job specification
2. Pass 2 — build_superprompts: construct optimized prompts
3. Pass 3 — execute_retrieval: call research backend(s)
4. Pass 4 — extract_results: transform raw JSON into validated objects
5. Pass 5 — integrate_results: persist output to hypergraph and world model
"""


from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

# =============================================================================
# Enums
# =============================================================================


class ValidationStatus(str, Enum):
    """Validation status for parsed objects."""

    VALID = "valid"
    INVALID = "invalid"
    PARTIAL = "partial"
    PENDING = "pending"


# =============================================================================
# Input Models
# =============================================================================


class ResearchJobSpec(BaseModel):
    """
    Input specification for a research job.

    Example:
        {
            "domain": "example_domain",
            "polymer": "HDPE",
            "regions": ["US"],
            "max_results": 50
        }
    """

    job_id: UUID = Field(default_factory=uuid4, description="Unique job identifier")
    domain: str = Field(..., min_length=1, description="Research domain context")
    polymer: str = Field(..., min_length=1, description="Target polymer type")
    regions: list[str] = Field(
        ..., min_length=1, description="Geographic regions to search"
    )
    max_results: int = Field(
        default=50, ge=1, le=1000, description="Maximum results to retrieve"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = {"frozen": True}

    @field_validator("regions")
    @classmethod
    def validate_regions(cls, v: list[str]) -> list[str]:
        """
        Validates and normalizes the list of region codes for research job specifications by ensuring at least one region is provided and converting all region codes to uppercase.

        Args:
            v: List of region codes to validate and normalize.

        Returns:
            List of uppercase region codes.

        Raises:
            ValueError: If no regions are provided.
        """
        if not v:
            raise ValueError("At least one region must be specified")
        return [r.upper() for r in v]  # Normalize to uppercase


# =============================================================================
# Pass 1: Query Planning
# =============================================================================


class Query(BaseModel):
    """Individual query within a query plan."""

    query_id: UUID = Field(default_factory=uuid4)
    query_text: str = Field(..., min_length=1, description="The search query")
    priority: int = Field(
        default=1, ge=1, le=10, description="Query priority (1=highest)"
    )
    filters: dict[str, Any] = Field(
        default_factory=dict, description="Optional filters"
    )

    model_config = {"frozen": True}


class QueryPlan(BaseModel):
    """
    Output of Pass 1: plan_queries

    Contains structured queries derived from the job specification.
    """

    plan_id: UUID = Field(default_factory=uuid4)
    job_id: UUID = Field(..., description="Reference to originating job")
    queries: list[Query] = Field(
        ..., min_length=1, description="Ordered list of queries"
    )
    strategy: str = Field(
        ..., description="Search strategy (e.g., 'breadth_first', 'depth_first')"
    )
    constraints: dict[str, Any] = Field(
        default_factory=dict, description="Plan constraints"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = {"frozen": True}


# =============================================================================
# Pass 2: Superprompt Building
# =============================================================================


class Superprompt(BaseModel):
    """
    Output of Pass 2: build_superprompts

    Optimized prompt constructed for retrieval.
    """

    prompt_id: UUID = Field(default_factory=uuid4)
    query_id: UUID = Field(..., description="Reference to source query")
    template: str = Field(..., min_length=1, description="Prompt template")
    variables: dict[str, Any] = Field(..., description="Template variables")
    context: str | None = Field(None, description="Additional context")
    rendered: str = Field(..., description="Final rendered prompt")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = {"frozen": True}


# =============================================================================
# Pass 3: Retrieval Execution
# =============================================================================


class RetrievalBatch(BaseModel):
    """
    Output of Pass 3: execute_retrieval

    Contains raw responses from research backends.
    """

    batch_id: UUID = Field(default_factory=uuid4)
    prompt_id: UUID = Field(..., description="Reference to source superprompt")
    sources: list[str] = Field(..., description="Data sources queried")
    raw_responses: list[dict[str, Any]] = Field(..., description="Raw JSON responses")
    response_count: int = Field(..., ge=0, description="Number of results retrieved")
    latency_ms: float = Field(
        ..., ge=0, description="Retrieval latency in milliseconds"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = {"frozen": True}


# =============================================================================
# Pass 4: Result Extraction
# =============================================================================


class ParsedObject(BaseModel):
    """
    Output of Pass 4: extract_results

    Validated, structured object extracted from raw response.
    """

    object_id: UUID = Field(default_factory=uuid4)
    batch_id: UUID = Field(..., description="Reference to source batch")
    extracted_data: dict[str, Any] = Field(..., description="Extracted structured data")
    validation_status: ValidationStatus = Field(..., description="Validation result")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Extraction confidence score"
    )
    errors: list[str] = Field(
        default_factory=list, description="Validation errors if any"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = {"frozen": True}


# =============================================================================
# Pass 5: Integration Result
# =============================================================================


class ResearchMetrics(BaseModel):
    """Metrics collected during research execution."""

    total_queries: int = Field(..., ge=0)
    total_results: int = Field(..., ge=0)
    valid_results: int = Field(..., ge=0)
    invalid_results: int = Field(..., ge=0)
    avg_confidence: float = Field(..., ge=0.0, le=1.0)
    total_latency_ms: float = Field(..., ge=0)
    pass_durations_ms: dict[str, float] = Field(default_factory=dict)

    model_config = {"frozen": True}


class IntegrationResult(BaseModel):
    """
    Final output of the 5-pass Research Factory pipeline.

    Contains complete research job output including:
    - Original job specification
    - Query plan
    - Superprompts
    - Retrieval batches count
    - Parsed objects
    - Integration summary
    - Execution metrics
    """

    result_id: UUID = Field(default_factory=uuid4)
    job_spec: ResearchJobSpec = Field(..., description="Original job specification")
    query_plan: QueryPlan = Field(..., description="Generated query plan")
    superprompts: list[Superprompt] = Field(..., description="Built superprompts")
    retrieval_batches: int = Field(..., ge=0, description="Number of retrieval batches")
    parsed_objects: list[ParsedObject] = Field(
        ..., description="Extracted and validated objects"
    )
    integration_summary: dict[str, Any] = Field(
        ..., description="Summary of integration actions"
    )
    metrics: ResearchMetrics = Field(..., description="Execution metrics")
    status: str = Field(default="completed", description="Final status")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = {"frozen": True}

    @property
    def success_rate(self) -> float:
        """Calculate success rate of parsed objects."""
        total = len(self.parsed_objects)
        if total == 0:
            return 0.0
        valid = sum(
            1
            for p in self.parsed_objects
            if p.validation_status == ValidationStatus.VALID
        )
        return valid / total


# Runtime execution trace - updated automatically on every execution
