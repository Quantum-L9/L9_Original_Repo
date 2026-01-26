"""
Symbolic Computation Module for AIOS

Production-ready SymPy utilities integration for semi-autonomous agents.
Provides symbolic-to-numeric conversion, code generation, and high-performance
mathematical computation capabilities.

Author: AIOS
Version: 1.0.0
"""

from .core import (
    CodeGenerator,
    ExpressionEvaluator,
    SymbolicComputation,
)
from .exceptions import (
    CodeGenerationError,
    EvaluationError,
    SymbolicComputationError,
)
from .models import (
    CodeGenRequest,
    CodeGenResult,
    ComputationRequest,
    ComputationResult,
)

__version__ = "1.0.0"
__all__ = [
    "SymbolicComputation",
    "ExpressionEvaluator",
    "CodeGenerator",
    "ComputationRequest",
    "ComputationResult",
    "CodeGenRequest",
    "CodeGenResult",
    "SymbolicComputationError",
    "EvaluationError",
    "CodeGenerationError",
]
