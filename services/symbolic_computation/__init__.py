"""
Symbolic Computation Module for AIOS

Production-ready SymPy utilities integration for semi-autonomous agents.
Provides symbolic-to-numeric conversion, code generation, and high-performance
mathematical computation capabilities.

Author: AIOS
Version: 1.0.0
"""

from .computation import CodeGenerator, ExpressionEvaluator, SymbolicComputation
from .exceptions import CodeGenerationError, EvaluationError, SymbolicComputationError
from .models import (
    BackendType,
    CodeGenRequest,
    CodeGenResult,
    CodeLanguage,
    ComputationRequest,
    ComputationResult,
)

__version__ = "1.0.0"
__all__ = [
    "BackendType",
    "CodeGenRequest",
    "CodeGenResult",
    "CodeGenerationError",
    "CodeGenerator",
    "CodeLanguage",
    "ComputationRequest",
    "ComputationResult",
    "EvaluationError",
    "ExpressionEvaluator",
    "SymbolicComputation",
    "SymbolicComputationError",
]
