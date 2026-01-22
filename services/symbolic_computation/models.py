"""
Pydantic models for symbolic computation module.

Provides strict input/output validation for all symbolic operations.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Models",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-17T23:51:17Z",
    "layer": "operations",
    "domain": "data_models",
    "module_name": "models",
    "type": "enum",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator


class BackendType(str, Enum):
    """Supported computational backends."""

    NUMPY = "numpy"
    MATH = "math"
    MPMATH = "mpmath"
    SYMPY = "sympy"
    CYTHON = "cython"
    F2PY = "f2py"


class CodeLanguage(str, Enum):
    """Supported code generation languages."""

    C = "C"
    FORTRAN = "Fortran"
    PYTHON = "Python"
    CYTHON = "Cython"


class ComputationRequest(BaseModel):
    """Request model for symbolic computation."""

    expression: str = Field(
        ..., description="SymPy expression as string", example="x**2 + sin(x)"
    )
    variables: List[str] = Field(
        ..., description="List of variable names in the expression", example=["x"]
    )
    backend: BackendType = Field(
        default=BackendType.NUMPY, description="Numerical backend to use"
    )
    values: Dict[str, Union[float, List[float]]] = Field(
        ..., description="Variable values for evaluation", example={"x": 1.0}
    )
    use_cache: bool = Field(
        default=True, description="Enable memoization for performance"
    )

    @validator("expression")
    def validate_expression(cls, v: str) -> str:
        """Validate expression is not empty."""
        if not v.strip():
            raise ValueError("Expression cannot be empty")
        return v.strip()

    @validator("variables")
    def validate_variables(cls, v: List[str]) -> List[str]:
        """Validate variables list."""
        if not v:
            raise ValueError("At least one variable must be specified")
        return v


class ComputationResult(BaseModel):
    """Result model for symbolic computation."""

    success: bool = Field(..., description="Whether computation succeeded")
    result: Optional[Union[float, List[float]]] = Field(
        None, description="Numerical result of computation"
    )
    expression_str: str = Field(
        ..., description="String representation of evaluated expression"
    )
    backend_used: BackendType = Field(..., description="Backend that was used")
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")
    error_message: Optional[str] = Field(
        None, description="Error message if computation failed"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class CodeGenRequest(BaseModel):
    """Request model for code generation."""

    expression: str = Field(..., description="SymPy expression to generate code for")
    variables: List[str] = Field(..., description="Input variables")
    language: CodeLanguage = Field(
        default=CodeLanguage.C, description="Target programming language"
    )
    function_name: str = Field(
        default="generated_func", description="Name of generated function"
    )
    optimize: bool = Field(default=True, description="Apply code optimizations")
    compile: bool = Field(
        default=False, description="Compile generated code (autowrap)"
    )


class CodeGenResult(BaseModel):
    """Result model for code generation."""

    success: bool = Field(..., description="Whether code generation succeeded")
    source_code: Optional[str] = Field(None, description="Generated source code")
    language: CodeLanguage = Field(..., description="Target language")
    compiled: bool = Field(default=False, description="Whether code was compiled")
    compilation_output: Optional[str] = Field(
        None, description="Compilation output/logs"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if generation failed"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SER-OPER-015",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "caching",
        "data-models",
        "enum",
        "messaging",
        "operations",
        "pydantic",
        "validation",
    ],
    "keywords": [
        "backend",
        "computation",
        "expression",
        "gen",
        "language",
        "models",
        "module",
        "symbolic",
    ],
    "business_value": "Provides strict input/output validation for all symbolic operations.",
    "last_modified": "2026-01-17T23:51:17Z",
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
