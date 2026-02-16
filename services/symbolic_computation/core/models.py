"""
SymPy Symbolic Computation Models
=================================

Pydantic models for request/response types and data structures.

Version: 6.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Models",
    "module_version": "6.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-07T13:35:58Z",
    "layer": "operations",
    "domain": "data_models",
    "module_name": "models",
    "type": "enum",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "Redis"],
        "memory_layers": [],
        "imported_by": [
            "services.symbolic_computation.api.routes",
            "services.symbolic_computation.core.__init__",
            "services.symbolic_computation.core.code_generator",
            "services.symbolic_computation.core.expression_evaluator",
            "services.symbolic_computation.core.metrics",
            "services.symbolic_computation.core.validator",
        ],
    },
}
# ============================================================================

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class BackendType(str, Enum):
    """Numerical evaluation backend types."""

    NUMPY = "numpy"
    MATH = "math"
    MPMATH = "mpmath"


class CodeLanguage(str, Enum):
    """Supported code generation languages."""

    C = "C"
    FORTRAN = "Fortran"
    CYTHON = "Cython"
    PYTHON = "Python"


class ComputationRequest(BaseModel):
    """Request model for expression evaluation."""

    expression: str = Field(..., description="SymPy expression as string")
    variables: dict[str, float] = Field(
        default_factory=dict, description="Variable name to value mapping"
    )
    backend: BackendType = Field(
        default=BackendType.NUMPY, description="Numerical backend to use"
    )
    options: dict[str, Any] = Field(
        default_factory=dict, description="Additional evaluation options"
    )


class ComputationResult(BaseModel):
    """Result model for expression evaluation."""

    result: Any = Field(..., description="Computed result value")
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")
    cache_hit: bool = Field(default=False, description="Whether result was from cache")
    backend_used: str = Field(..., description="Backend that was used")
    expression_hash: str = Field(..., description="Hash of the expression")
    error: str | None = Field(default=None, description="Error message if failed")

    class Config:
        """
        Class Config defines custom JSON encoding for datetime objects within the SymPy symbolic computation models.

        Args:
            json_encoders: Dictionary mapping data types to encoder functions, here used to serialize datetime as ISO format.
        """

        json_encoders = {datetime: lambda v: v.isoformat()}


class CodeGenRequest(BaseModel):
    """Request model for code generation."""

    expression: str = Field(..., description="SymPy expression as string")
    variables: list[str] = Field(..., description="List of variable names")
    language: CodeLanguage = Field(
        default=CodeLanguage.C, description="Target language for code generation"
    )
    function_name: str = Field(
        default="evaluate", description="Name of the generated function"
    )


class CodeGenResult(BaseModel):
    """Result model for code generation."""

    source_code: str = Field(..., description="Generated source code")
    language: str = Field(..., description="Target language")
    function_name: str = Field(..., description="Name of generated function")
    success: bool = Field(..., description="Whether generation succeeded")
    execution_time_ms: float = Field(..., description="Generation time in milliseconds")
    error_message: str | None = Field(
        default=None, description="Error message if failed"
    )


class ValidationResult(BaseModel):
    """Result model for expression validation."""

    is_valid: bool = Field(..., description="Whether expression is valid")
    expression_length: int = Field(..., description="Length of expression")
    dangerous_functions_found: list[str] = Field(
        default_factory=list, description="List of dangerous functions found"
    )
    errors: list[str] = Field(
        default_factory=list, description="List of validation errors"
    )
    warnings: list[str] = Field(
        default_factory=list, description="List of validation warnings"
    )


class HealthStatus(BaseModel):
    """Health status model for the service."""

    status: str = Field(..., description="Overall status (healthy/degraded/unhealthy)")
    backends_available: list[str] = Field(..., description="Available backends")
    cache_available: bool = Field(..., description="Whether cache is available")
    memory_backends: dict[str, bool] = Field(
        default_factory=dict,
        description="Status of memory backends (redis, postgres, neo4j)",
    )
    version: str = Field(default="6.0.0", description="Service version")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Health check timestamp"
    )


class MetricsSummary(BaseModel):
    """Summary of performance metrics."""

    total_evaluations: int = Field(default=0)
    total_code_generations: int = Field(default=0)
    avg_evaluation_time_ms: float = Field(default=0.0)
    avg_codegen_time_ms: float = Field(default=0.0)
    cache_hit_rate: float = Field(default=0.0)
    backend_usage: dict[str, int] = Field(default_factory=dict)
    language_usage: dict[str, int] = Field(default_factory=dict)
    time_range_hours: int = Field(default=24)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SER-OPER-024",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "caching",
        "data-models",
        "enum",
        "messaging",
        "metrics",
        "operations",
        "pydantic",
        "security",
        "validation",
    ],
    "keywords": [
        "backend",
        "computation",
        "gen",
        "health",
        "language",
        "metrics",
        "models",
        "status",
    ],
    "business_value": "Provides models components including BackendType, CodeLanguage, ComputationRequest",
    "last_modified": "2026-01-07T13:35:58Z",
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
