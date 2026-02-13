"""
Comprehensive examples for symbolic computation module.

Demonstrates all features and integration patterns.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Examples Symbolic Computation",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-06T16:58:23Z",
    "layer": "foundation",
    "domain": "code_generation",
    "module_name": "examples_symbolic_computation",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import asyncio
from symbolic_computation import SymbolicComputation
from symbolic_computation.core import ExpressionEvaluator, CodeGenerator
from symbolic_computation.models import (
    ComputationRequest,
    CodeGenRequest,
    BackendType,
    CodeLanguage,
)
from symbolic_computation.utils import (
    validate_expression,
    extract_variables,
    simplify_expression,
    optimize_expression,
)


# Example 1: Basic Expression Evaluation
async def example_basic_evaluation():
    """Demonstrate basic expression evaluation."""
    print("\n=== Example 1: Basic Evaluation ===")  # noqa: ADR-0019

    engine = SymbolicComputation()

    # Simple expression
    result = await engine.compute(
        expression="x**2 + 2*x + 1", variables={"x": 3.0}, backend="numpy"
    )

    print(f"Expression: x**2 + 2*x + 1")  # noqa: ADR-0019
    print(f"Value at x=3: {result.result}")  # noqa: ADR-0019
    print(f"Execution time: {result.execution_time_ms:.2f}ms")  # noqa: ADR-0019


# Example 2: Multi-Variable Expressions
async def example_multi_variable():
    """Demonstrate multi-variable expressions."""
    print("\n=== Example 2: Multi-Variable ===")  # noqa: ADR-0019

    engine = SymbolicComputation()

    # Distance formula
    result = await engine.compute(
        expression="sqrt((x2-x1)**2 + (y2-y1)**2)",
        variables={
            "x1": 0.0,
            "y1": 0.0,
            "x2": 3.0,
            "y2": 4.0,
        },
        backend="numpy",
    )

    print(f"Distance between (0,0) and (3,4): {result.result}")  # noqa: ADR-0019


# Example 3: Trigonometric Functions
async def example_trigonometric():
    """Demonstrate trigonometric functions."""
    print("\n=== Example 3: Trigonometric Functions ===")  # noqa: ADR-0019

    engine = SymbolicComputation()

    import math

    result = await engine.compute(
        expression="sin(x)**2 + cos(x)**2",
        variables={"x": math.pi / 4},
        backend="numpy",
    )

    print(f"sin²(π/4) + cos²(π/4) = {result.result}")  # noqa: ADR-0019
    print("Should equal 1.0 (Pythagorean identity)")  # noqa: ADR-0019


# Example 4: Array/Vector Operations
async def example_array_operations():
    """Demonstrate array operations with NumPy backend."""
    print("\n=== Example 4: Array Operations ===")  # noqa: ADR-0019

    import numpy as np

    evaluator = ExpressionEvaluator()

    request = ComputationRequest(
        expression="x**2",
        variables=["x"],
        backend=BackendType.NUMPY,
        values={"x": np.array([1, 2, 3, 4, 5])},
    )

    result = await evaluator.evaluate(request)

    print(f"x² for x = [1,2,3,4,5]:")  # noqa: ADR-0019
    print(f"Result: {result.result}")  # noqa: ADR-0019


# Example 5: Code Generation - C
async def example_codegen_c():
    """Demonstrate C code generation."""
    print("\n=== Example 5: C Code Generation ===")  # noqa: ADR-0019

    engine = SymbolicComputation()

    result = await engine.generate_code(
        expression="a*x**2 + b*x + c",
        variables=["x", "a", "b", "c"],
        language="C",
        function_name="quadratic",
    )

    print("Generated C code:")  # noqa: ADR-0019
    print(result.source_code[:500])  # First 500 chars  # noqa: ADR-0019


# Example 6: Code Generation - Fortran
async def example_codegen_fortran():
    """Demonstrate Fortran code generation."""
    print("\n=== Example 6: Fortran Code Generation ===")  # noqa: ADR-0019

    codegen = CodeGenerator()

    request = CodeGenRequest(
        expression="sqrt(x**2 + y**2 + z**2)",
        variables=["x", "y", "z"],
        language=CodeLanguage.FORTRAN,
        function_name="vector_magnitude",
    )

    result = await codegen.generate(request)

    if result.success:
        print("Fortran code generated successfully!")  # noqa: ADR-0019
        print(result.source_code[:500])  # noqa: ADR-0019


# Example 7: Expression Validation and Simplification
def example_expression_utils():
    """Demonstrate expression utilities."""
    print("\n=== Example 7: Expression Utilities ===")  # noqa: ADR-0019

    # Validation
    expr1 = "x + y + z"
    expr2 = "invalid ** ** syntax"

    print(f"'{expr1}' is valid: {validate_expression(expr1)}")  # noqa: ADR-0019
    print(f"'{expr2}' is valid: {validate_expression(expr2)}")  # noqa: ADR-0019

    # Extract variables
    vars = extract_variables("a*x**2 + b*x + c")
    print(f"\nVariables in 'a*x**2 + b*x + c': {vars}")  # noqa: ADR-0019

    # Simplification
    simplified = simplify_expression("x + x + x + y + y")
    print(f"\nSimplified 'x + x + x + y + y': {simplified}")  # noqa: ADR-0019


# Example 8: Expression Optimization (CSE)
def example_optimization():
    """Demonstrate expression optimization."""
    print("\n=== Example 8: Expression Optimization ===")  # noqa: ADR-0019

    original = "sin(x)**2 + 2*sin(x)**2 + cos(x)**2"
    print(f"Original: {original}")  # noqa: ADR-0019

    # This would use common subexpression elimination
    # to avoid computing sin(x)**2 multiple times
    optimized = optimize_expression(original)
    print(f"Optimized: {optimized}")  # noqa: ADR-0019


# Example 9: Caching Performance
async def example_caching():
    """Demonstrate caching performance."""
    print("\n=== Example 9: Caching Performance ===")  # noqa: ADR-0019

    evaluator = ExpressionEvaluator(cache_size=128)

    request = ComputationRequest(
        expression="sin(x)*cos(x) + tan(x)**2",
        variables=["x"],
        backend=BackendType.NUMPY,
        values={"x": 1.0},
    )

    # First evaluation - compiles expression
    result1 = await evaluator.evaluate(request)
    time1 = result1.execution_time_ms

    # Second evaluation - uses cached function
    request.values = {"x": 2.0}
    result2 = await evaluator.evaluate(request)
    time2 = result2.execution_time_ms

    print(f"First evaluation: {time1:.4f}ms")  # noqa: ADR-0019
    print(f"Second evaluation: {time2:.4f}ms")  # noqa: ADR-0019
    print(f"Speedup: {time1 / time2:.2f}x (includes lambdify caching)")  # noqa: ADR-0019


# Example 10: Health Check
async def example_health_check():
    """Demonstrate health check."""
    print("\n=== Example 10: Health Check ===")  # noqa: ADR-0019

    engine = SymbolicComputation()

    health = await engine.health_check()

    print(f"Status: {health['status']}")  # noqa: ADR-0019
    print(f"Metrics: {health.get('evaluator_metrics', {})}")  # noqa: ADR-0019


# Example 11: Error Handling
async def example_error_handling():
    """Demonstrate error handling."""
    print("\n=== Example 11: Error Handling ===")  # noqa: ADR-0019

    engine = SymbolicComputation()

    # Invalid expression
    result = await engine.compute(
        expression="invalid ** syntax", variables={"x": 1.0}, backend="numpy"
    )

    print(f"Success: {result.success}")  # noqa: ADR-0019
    print(f"Error: {result.error_message}")  # noqa: ADR-0019


# Example 12: Integration Pattern for AIOS Agent
class MathAgent:
    """Example agent using symbolic computation."""

    def __init__(self):
        """Initialize agent with symbolic engine."""
        self.symbolic = SymbolicComputation()
        self.expression_cache = {}

    async def evaluate_formula(self, formula: str, params: dict):
        """
        Evaluate mathematical formula.

        Args:
            formula: Mathematical expression
            params: Parameter values

        Returns:
            Numerical result
        """
        result = await self.symbolic.compute(
            expression=formula, variables=params, backend="numpy"
        )

        if result.success:
            # Store in agent's memory
            self.expression_cache[formula] = result
            return result.result
        else:
            raise ValueError(f"Evaluation failed: {result.error_message}")

    async def generate_optimized_code(self, formula: str, vars: list):
        """
        Generate optimized code for formula.

        Args:
            formula: Mathematical expression
            vars: Variable names

        Returns:
            Generated code
        """
        code_result = await self.symbolic.generate_code(
            expression=formula,
            variables=vars,
            language="C",
            function_name="agent_computation",
            compile=False,
        )

        return code_result.source_code


async def example_agent_integration():
    """Demonstrate agent integration."""
    print("\n=== Example 12: Agent Integration ===")  # noqa: ADR-0019

    agent = MathAgent()

    # Agent evaluates physics formula
    result = await agent.evaluate_formula(
        formula="0.5 * m * v**2",  # Kinetic energy
        params={"m": 10.0, "v": 5.0},
    )

    print(f"Kinetic energy: {result} Joules")  # noqa: ADR-0019

    # Agent generates code for repeated use
    code = await agent.generate_optimized_code(
        formula="0.5 * m * v**2", vars=["m", "v"]
    )

    print("\nGenerated code for agent's use:")  # noqa: ADR-0019
    print(code[:300])  # noqa: ADR-0019


# Example 13: Batch Evaluation
async def example_batch_evaluation():
    """Demonstrate batch evaluation."""
    print("\n=== Example 13: Batch Evaluation ===")  # noqa: ADR-0019

    engine = SymbolicComputation()

    # Evaluate same expression with different values
    expression = "x**2 + y**2"
    test_cases = [
        {"x": 1.0, "y": 1.0},
        {"x": 2.0, "y": 2.0},
        {"x": 3.0, "y": 3.0},
    ]

    results = []
    for case in test_cases:
        result = await engine.compute(expression, case)
        results.append(result.result)

    print(f"Expression: {expression}")  # noqa: ADR-0019
    for i, (case, result) in enumerate(zip(test_cases, results)):
        print(f"  Case {i + 1}: {case} → {result}")  # noqa: ADR-0019


# Main execution
async def run_all_examples():
    """Run all examples."""
    print("=" * 60)  # noqa: ADR-0019
    print("SYMBOLIC COMPUTATION MODULE - COMPREHENSIVE EXAMPLES")  # noqa: ADR-0019
    print("=" * 60)  # noqa: ADR-0019

    await example_basic_evaluation()
    await example_multi_variable()
    await example_trigonometric()
    await example_array_operations()
    await example_codegen_c()
    await example_codegen_fortran()

    example_expression_utils()
    example_optimization()

    await example_caching()
    await example_health_check()
    await example_error_handling()
    await example_agent_integration()
    await example_batch_evaluation()

    print("\n" + "=" * 60)  # noqa: ADR-0019
    print("All examples completed successfully!")  # noqa: ADR-0019
    print("=" * 60)  # noqa: ADR-0019


if __name__ == "__main__":
    asyncio.run(run_all_examples())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COD-FOUN-006",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "batch-processing",
        "caching",
        "code-generation",
        "foundation",
        "messaging",
        "metrics",
        "service",
        "testing",
    ],
    "keywords": [
        "agent",
        "all",
        "array",
        "basic",
        "batch",
        "caching",
        "check",
        "codegen",
    ],
    "business_value": "Implements MathAgent for examples symbolic computation functionality",
    "last_modified": "2026-01-06T16:58:23Z",
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
