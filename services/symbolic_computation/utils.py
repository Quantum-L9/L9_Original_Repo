"""
Utility functions for symbolic computation module.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Utils",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "operations",
    "domain": "symbolic_computation",
    "module_name": "utils",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from typing import Dict, List

import sympy as sp
from sympy.utilities.memoization import recurrence_memo


def validate_expression(expression: str) -> bool:
    """
    Validate SymPy expression syntax.

    Args:
        expression: Expression string to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        sp.sympify(expression)
        return True
    except (sp.SympifyError, SyntaxError):
        return False


def extract_variables(expression: str) -> List[str]:
    """
    Extract variable names from expression.

    Args:
        expression: SymPy expression string

    Returns:
        List of variable names
    """
    try:
        expr = sp.sympify(expression)
        symbols = expr.free_symbols
        return sorted([str(sym) for sym in symbols])
    except Exception:
        return []


def simplify_expression(expression: str) -> str:
    """
    Simplify symbolic expression.

    Args:
        expression: Expression to simplify

    Returns:
        Simplified expression string
    """
    try:
        expr = sp.sympify(expression)
        simplified = sp.simplify(expr)
        return str(simplified)
    except Exception as e:
        raise ValueError(f"Failed to simplify expression: {str(e)}")


def optimize_expression(expression: str) -> str:
    """
    Optimize expression using common subexpression elimination.

    Args:
        expression: Expression to optimize

    Returns:
        Optimized expression
    """
    try:
        expr = sp.sympify(expression)
        from sympy.simplify.cse_main import cse

        # Apply CSE
        replacements, reduced = cse(expr)

        if not replacements:
            return str(expr)

        # Reconstruct optimized expression
        # This is a simplified version
        return str(reduced[0] if reduced else expr)

    except Exception as e:
        raise ValueError(f"Failed to optimize expression: {str(e)}")


@recurrence_memo([1, 1])
def fibonacci(n: int) -> int:
    """
    Fibonacci using SymPy memoization decorator.

    Demonstrates recurrence_memo utility.

    Args:
        n: Fibonacci number to compute

    Returns:
        nth Fibonacci number
    """
    return fibonacci(n - 1) + fibonacci(n - 2)


def generate_test_cases(
    variables: List[str], num_cases: int = 10
) -> List[Dict[str, float]]:
    """
    Generate test cases for symbolic expressions.

    Args:
        variables: List of variable names
        num_cases: Number of test cases to generate

    Returns:
        List of test case dictionaries
    """
    import random

    test_cases = []
    for _ in range(num_cases):
        case = {var: random.uniform(-10, 10) for var in variables}
        test_cases.append(case)

    return test_cases


class ExpressionOptimizer:
    """Advanced expression optimization utilities."""

    @staticmethod
    def common_subexpression_elimination(expression: str) -> tuple:
        """
        Apply CSE to expression.

        Args:
            expression: Expression to optimize

        Returns:
            Tuple of (replacements, reduced_expression)
        """
        from sympy.simplify.cse_main import cse

        expr = sp.sympify(expression)
        return cse(expr)

    @staticmethod
    def count_operations(expression: str) -> Dict[str, int]:
        """
        Count operations in expression.

        Args:
            expression: Expression to analyze

        Returns:
            Dictionary of operation counts
        """
        expr = sp.sympify(expression)

        ops = {
            "Add": 0,
            "Mul": 0,
            "Pow": 0,
            "Function": 0,
        }

        for arg in sp.preorder_traversal(expr):
            op_type = type(arg).__name__
            if op_type in ops:
                ops[op_type] += 1

        return ops


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SER-OPER-018",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["operations", "symbolic-computation", "testing", "utility"],
    "keywords": [
        "cases",
        "common",
        "count",
        "elimination",
        "expression",
        "extract",
        "fibonacci",
        "generate",
    ],
    "business_value": "Implements ExpressionOptimizer for utils functionality",
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
