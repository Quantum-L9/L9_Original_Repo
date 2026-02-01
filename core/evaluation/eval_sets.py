"""
Evaluation Sets for L9 Agent Testing

Pre-defined evaluation sets for measuring agent performance
across different capability dimensions.

Usage:
    from core.evaluation import load_default_eval_sets

    evaluator = Evaluator(substrate, llm)
    load_default_eval_sets(evaluator)
    result = await evaluator.run_eval("L", "information_retrieval")
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Evaluation Sets",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T18:30:00Z",
    "updated_at": "2026-01-25T18:30:00Z",
    "layer": "foundation",
    "domain": "evaluation",
    "module_name": "eval_sets",
    "type": "data",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["core.evaluation.evaluator"],
    },
}
# ============================================================================

from typing import TYPE_CHECKING

from .evaluator import EvaluationExample

if TYPE_CHECKING:
    from .evaluator import Evaluator


# =============================================================================
# INFORMATION RETRIEVAL EVAL SET
# Tests: Web search, fact extraction, knowledge queries
# =============================================================================

INFORMATION_RETRIEVAL_EXAMPLES: list[EvaluationExample] = [
    EvaluationExample(
        input_text="What is the capital of France?",
        expected_output={"text": "Paris"},
        expected_tools=["search_web"],
    ),
    EvaluationExample(
        input_text="Who wrote 'Romeo and Juliet'?",
        expected_output={"text": "William Shakespeare"},
        expected_tools=["search_web"],
    ),
    EvaluationExample(
        input_text="What is the speed of light in meters per second?",
        expected_output={"text": "299,792,458"},
        expected_tools=["search_web"],
    ),
    EvaluationExample(
        input_text="What year did World War II end?",
        expected_output={"text": "1945"},
        expected_tools=["search_web"],
    ),
    EvaluationExample(
        input_text="What is Python's latest stable version?",
        expected_output={"text": "3.12"},
        expected_tools=["search_web"],
    ),
    EvaluationExample(
        input_text="What company created ChatGPT?",
        expected_output={"text": "OpenAI"},
        expected_tools=["search_web"],
    ),
    EvaluationExample(
        input_text="What is the population of Tokyo?",
        expected_output={"text": "approximately 14 million"},
        expected_tools=["search_web"],
    ),
    EvaluationExample(
        input_text="Who is the current CEO of Apple?",
        expected_output={"text": "Tim Cook"},
        expected_tools=["search_web"],
    ),
    EvaluationExample(
        input_text="What is the chemical formula for water?",
        expected_output={"text": "H2O"},
        expected_tools=[],  # Should answer from knowledge
    ),
    EvaluationExample(
        input_text="How many planets are in our solar system?",
        expected_output={"text": "8"},
        expected_tools=[],
    ),
]


# =============================================================================
# CODE ANALYSIS EVAL SET
# Tests: Python execution, code review, debugging
# =============================================================================

CODE_ANALYSIS_EXAMPLES: list[EvaluationExample] = [
    EvaluationExample(
        input_text="What does this Python code do: `[x**2 for x in range(5)]`?",
        expected_output={"text": "Creates a list of squares: [0, 1, 4, 9, 16]"},
        expected_tools=["execute_python"],
    ),
    EvaluationExample(
        input_text="Find the bug: `def add(a, b): return a - b`",
        expected_output={"text": "The function subtracts instead of adds"},
        expected_tools=[],
    ),
    EvaluationExample(
        input_text="What is the time complexity of binary search?",
        expected_output={"text": "O(log n)"},
        expected_tools=[],
    ),
    EvaluationExample(
        input_text="Calculate: 2**10",
        expected_output={"text": "1024"},
        expected_tools=["execute_python"],
    ),
    EvaluationExample(
        input_text="What does `async def` mean in Python?",
        expected_output={"text": "Defines an asynchronous coroutine function"},
        expected_tools=[],
    ),
    EvaluationExample(
        input_text="Sort this list in Python: [3, 1, 4, 1, 5, 9, 2, 6]",
        expected_output={"text": "[1, 1, 2, 3, 4, 5, 6, 9]"},
        expected_tools=["execute_python"],
    ),
    EvaluationExample(
        input_text="What is a decorator in Python?",
        expected_output={
            "text": "A function that modifies the behavior of another function"
        },
        expected_tools=[],
    ),
    EvaluationExample(
        input_text="Reverse the string 'hello'",
        expected_output={"text": "olleh"},
        expected_tools=["execute_python"],
    ),
    EvaluationExample(
        input_text="What does `if __name__ == '__main__':` do?",
        expected_output={"text": "Runs code only when script is executed directly"},
        expected_tools=[],
    ),
    EvaluationExample(
        input_text="Calculate factorial of 5",
        expected_output={"text": "120"},
        expected_tools=["execute_python"],
    ),
]


# =============================================================================
# MULTI-TOOL ORCHESTRATION EVAL SET
# Tests: Complex tasks requiring multiple tool calls
# =============================================================================

MULTI_TOOL_EXAMPLES: list[EvaluationExample] = [
    EvaluationExample(
        input_text="Search for Python best practices and summarize the top 3",
        expected_output={"text": "summarized best practices"},
        expected_tools=["search_web", "memory_write"],
    ),
    EvaluationExample(
        input_text="Find the current Bitcoin price and calculate 0.5 BTC value",
        expected_output={"text": "calculated value"},
        expected_tools=["search_web", "execute_python"],
    ),
    EvaluationExample(
        input_text="Search for FastAPI documentation and save key points to memory",
        expected_output={"text": "saved to memory"},
        expected_tools=["search_web", "memory_write"],
    ),
    EvaluationExample(
        input_text="What did we discuss earlier about Python?",
        expected_output={"text": "retrieved from memory"},
        expected_tools=["memory_search"],
    ),
    EvaluationExample(
        input_text="Find 3 recent AI papers and save their titles",
        expected_output={"text": "saved titles"},
        expected_tools=["search_web", "memory_write"],
    ),
    EvaluationExample(
        input_text="Calculate the area of a circle with radius from memory",
        expected_output={"text": "calculated area"},
        expected_tools=["memory_search", "execute_python"],
    ),
    EvaluationExample(
        input_text="Search for Docker commands and create a cheat sheet",
        expected_output={"text": "created cheat sheet"},
        expected_tools=["search_web", "memory_write"],
    ),
    EvaluationExample(
        input_text="Recall my preferences and search for related tools",
        expected_output={"text": "found tools based on preferences"},
        expected_tools=["memory_search", "search_web"],
    ),
    EvaluationExample(
        input_text="Find the weather and suggest activities",
        expected_output={"text": "suggested activities"},
        expected_tools=["search_web"],
    ),
    EvaluationExample(
        input_text="List my recent memories and categorize them",
        expected_output={"text": "categorized memories"},
        expected_tools=["memory_search"],
    ),
]


# =============================================================================
# MEMORY OPERATIONS EVAL SET
# Tests: Long conversation, memory persistence, context retrieval
# =============================================================================

MEMORY_OPERATIONS_EXAMPLES: list[EvaluationExample] = [
    EvaluationExample(
        input_text="Remember that my favorite color is blue",
        expected_output={"text": "I'll remember that"},
        expected_tools=["memory_write"],
    ),
    EvaluationExample(
        input_text="What is my favorite color?",
        expected_output={"text": "blue"},
        expected_tools=["memory_search"],
    ),
    EvaluationExample(
        input_text="Save this note: Meeting at 3pm tomorrow",
        expected_output={"text": "saved"},
        expected_tools=["memory_write"],
    ),
    EvaluationExample(
        input_text="What meetings do I have?",
        expected_output={"text": "3pm tomorrow"},
        expected_tools=["memory_search"],
    ),
    EvaluationExample(
        input_text="Remember I prefer dark mode in all applications",
        expected_output={"text": "noted"},
        expected_tools=["memory_write"],
    ),
    EvaluationExample(
        input_text="What are my UI preferences?",
        expected_output={"text": "dark mode"},
        expected_tools=["memory_search"],
    ),
    EvaluationExample(
        input_text="Forget my meeting note",
        expected_output={"text": "deleted"},
        expected_tools=["memory_delete"],
    ),
    EvaluationExample(
        input_text="What did I ask you to remember?",
        expected_output={"text": "list of remembered items"},
        expected_tools=["memory_search"],
    ),
    EvaluationExample(
        input_text="Update my favorite color to green",
        expected_output={"text": "updated"},
        expected_tools=["memory_write"],
    ),
    EvaluationExample(
        input_text="Search my memory for anything about colors",
        expected_output={"text": "green"},
        expected_tools=["memory_search"],
    ),
]


# =============================================================================
# LOADER FUNCTION
# =============================================================================


def load_default_eval_sets(evaluator: Evaluator) -> None:
    """
    Load all default evaluation sets into an evaluator instance.

    Args:
        evaluator: Evaluator instance to load sets into

    Usage:
        evaluator = Evaluator(substrate, llm)
        load_default_eval_sets(evaluator)
    """
    evaluator.define_eval_set(
        name="information_retrieval",
        examples=INFORMATION_RETRIEVAL_EXAMPLES,
        description="Tests web search, fact extraction, and knowledge queries",
    )

    evaluator.define_eval_set(
        name="code_analysis",
        examples=CODE_ANALYSIS_EXAMPLES,
        description="Tests Python execution, code review, and debugging",
    )

    evaluator.define_eval_set(
        name="multi_tool_orchestration",
        examples=MULTI_TOOL_EXAMPLES,
        description="Tests complex tasks requiring multiple tool calls",
    )

    evaluator.define_eval_set(
        name="memory_operations",
        examples=MEMORY_OPERATIONS_EXAMPLES,
        description="Tests memory persistence and context retrieval",
    )


# =============================================================================
# QUICK ACCESS
# =============================================================================

ALL_EVAL_SETS = {
    "information_retrieval": INFORMATION_RETRIEVAL_EXAMPLES,
    "code_analysis": CODE_ANALYSIS_EXAMPLES,
    "multi_tool_orchestration": MULTI_TOOL_EXAMPLES,
    "memory_operations": MEMORY_OPERATIONS_EXAMPLES,
}

EVAL_SET_DESCRIPTIONS = {
    "information_retrieval": "Web search, fact extraction, knowledge queries",
    "code_analysis": "Python execution, code review, debugging",
    "multi_tool_orchestration": "Complex tasks with multiple tools",
    "memory_operations": "Memory persistence, context retrieval",
}
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-187",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["api", "async", "cli", "core", "debugging", "foundation", "testing"],
    "keywords": [
        "agent",
        "default",
        "eval",
        "evaluation",
        "evaluator",
        "load",
        "sets",
        "substrate",
    ],
    "business_value": "Utility module for eval sets",
    "last_modified": "2026-01-31T22:21:47Z",
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
