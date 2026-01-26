"""
L9 Evaluation Framework

Harvested from: L9-Implementation-Suite-Ready-to-Deploy.md
Provides: Continuous evaluation, LLM-as-judge scoring, CI/CD integration.
"""

from __future__ import annotations

from .eval_sets import (
    ALL_EVAL_SETS,
    CODE_ANALYSIS_EXAMPLES,
    EVAL_SET_DESCRIPTIONS,
    INFORMATION_RETRIEVAL_EXAMPLES,
    MEMORY_OPERATIONS_EXAMPLES,
    MULTI_TOOL_EXAMPLES,
    load_default_eval_sets,
)
from .evaluator import (
    EvaluationExample,
    EvaluationResult,
    EvaluationSet,
    Evaluator,
    RegressionError,
    ci_eval_gate,
)

__all__ = [
    "ALL_EVAL_SETS",
    "CODE_ANALYSIS_EXAMPLES",
    "EVAL_SET_DESCRIPTIONS",
    "INFORMATION_RETRIEVAL_EXAMPLES",
    "MEMORY_OPERATIONS_EXAMPLES",
    "MULTI_TOOL_EXAMPLES",
    "EvaluationExample",
    "EvaluationResult",
    "EvaluationSet",
    "Evaluator",
    "RegressionError",
    "ci_eval_gate",
    "load_default_eval_sets",
]
