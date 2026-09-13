"""
Symbolic CodeGen Specification Models
=====================================

Defines the input specification for symbolic code generation and verification.

Version: 1.0.0
"""

from __future__ import annotations


from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class CodegenIntent(str, Enum):
    """Intent for code generation."""

    VERIFY = "verify"
    OPTIMIZE = "optimize"
    REFACTOR = "refactor"
    GENERATE = "generate"


@dataclass
class CodegenSpec:
    """
    Specification for symbolic code generation.

    Attributes:
        intent: What kind of code operation to perform
        target_behavior: The desired behavior (e.g., mathematical expression)
        input_code: Optional existing code to transform
        invariants: Properties that must be preserved
        constraints: Hard constraints on the generated code
        variables: Variable names and their types
    """

    intent: CodegenIntent
    target_behavior: str
    input_code: str | None = None
    invariants: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    variables: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate and normalize the spec."""
        if isinstance(self.intent, str):
            self.intent = CodegenIntent(self.intent)

        if not self.target_behavior:
            raise ValueError("target_behavior is required")

        logger.debug(
            "codegen_spec_created",
            intent=self.intent.value,
            has_input_code=self.input_code is not None,
            num_invariants=len(self.invariants),
            num_constraints=len(self.constraints),
            num_variables=len(self.variables),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "intent": self.intent.value,
            "target_behavior": self.target_behavior,
            "input_code": self.input_code,
            "invariants": self.invariants,
            "constraints": self.constraints,
            "variables": self.variables,
        }


@dataclass
class SymbolicCandidate:
    """A candidate code solution."""

    code: str
    expression: Any | None = None  # SymPy expression
    complexity_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationResult:
    """Result of verifying a candidate."""

    candidate: SymbolicCandidate
    is_equivalent: bool = False
    all_invariants_pass: bool = False
    invariant_results: dict[str, bool] = field(default_factory=dict)
    error: str | None = None


@dataclass
class SymbolicCodegenPipelineResult:
    """Result of the full symbolic codegen pipeline."""

    success: bool
    candidates: list[SymbolicCandidate] = field(default_factory=list)
    verifications: list[VerificationResult] = field(default_factory=list)
    selected_code: str | None = None
    selection_result: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


# Runtime execution trace - updated automatically on every execution
