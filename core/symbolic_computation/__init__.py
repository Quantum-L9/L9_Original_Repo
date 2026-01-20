"""
Symbolic Computation Module for AIOS

Production-ready SymPy utilities integration for semi-autonomous agents.
Provides symbolic-to-numeric conversion, code generation, and high-performance
mathematical computation capabilities.

Author: AIOS
Version: 1.0.0
"""

from .core import (
    SymbolicComputation,
    ExpressionEvaluator,
    CodeGenerator,
)
from .models import (
    ComputationRequest,
    ComputationResult,
    CodeGenRequest,
    CodeGenResult,
)
from .exceptions import (
    SymbolicComputationError,
    EvaluationError,
    CodeGenerationError,
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
