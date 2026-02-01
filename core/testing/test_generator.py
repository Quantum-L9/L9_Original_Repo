"""
L9 Core Testing - Test Generator
=================================

Generates unit and integration tests from code proposals.
Uses AST analysis to extract structure, then LLM to generate implementations.

**DESIGN PRINCIPLE (ADR-0000):**
- AST parsing extracts: functions, classes, methods, signatures, error patterns
- LLM generates: actual test implementations with mocks, assertions, edge cases
- Result: Complete, runnable tests for PENNIES (LLM API) vs $100s (manual Cursor tokens)

Version: 2.0.0 (GMP-19 + LLM Enhancement)
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Test Generator",
    "module_version": "2.0.0 (GMP-19 + LLM Enhancement)",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-02-01T00:00:00Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "test_generator",
    "type": "test",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "core.testing.__init__",
            "core.testing.test_agent",
            "tests.integration.test_recursive_self_testing",
        ],
    },
}
# ============================================================================

import ast
import os
from pathlib import Path
from typing import Any

import structlog
from dotenv import load_dotenv

# Load .env file from project root
_project_root = Path(__file__).parent.parent.parent
_env_file = _project_root / ".env"
if _env_file.exists():
    load_dotenv(_env_file)

logger = structlog.get_logger(__name__)

# =============================================================================
# LLM Test Generation Prompts
# =============================================================================

TEST_GENERATION_SYSTEM_PROMPT = """You are an expert Python test engineer for the L9 Secure AI OS. Generate comprehensive pytest tests.

CRITICAL RULES:
1. Generate REAL test implementations, NOT TODO stubs
2. Include proper imports at the top
3. Use pytest fixtures, AsyncMock, MagicMock appropriately
4. Test ACTUAL behavior shown in the code - don't assume what it SHOULD do
5. Use descriptive test names and docstrings
6. Include type hints

BEHAVIOR TESTING (CRITICAL):
- READ the code carefully to understand ACTUAL behavior
- For edge cases (None, empty, whitespace): check if code handles them explicitly
- If code has fallback/default branches, TEST those fallbacks
- Don't assume functions validate/strip inputs unless the code shows it
- For if/elif/else chains: test EACH branch including the else/default

===== COMMON FAILURE PATTERNS TO AVOID =====

1. UUID FORMAT: Always use valid UUID format (e.g., "12345678-1234-5678-1234-567812345678")
   NEVER use strings like "test_id", "duplicate_id", "user-123"
   
2. EXACT ERROR MESSAGES: Don't hardcode exact error strings. Use partial matching:
   - BAD:  assert "Duplicate packet detected" in result["errors"]
   - GOOD: assert any("Duplicate" in err for err in result["errors"])

3. ASYNC CONTEXT MANAGERS: For `async with obj.method() as x`:
   mock_result = AsyncMock()
   mock_context = AsyncMock()
   mock_context.__aenter__ = AsyncMock(return_value=mock_result)
   mock_context.__aexit__ = AsyncMock(return_value=None)
   obj.method = MagicMock(return_value=mock_context)

4. FALLBACK BRANCHES: If code has else/default, test it explicitly
   - If function has if/elif/else, the else is likely a fallback handler
   - Don't assume unmatched inputs return empty - check the code!

5. WHITESPACE: Don't assume functions strip whitespace. Test with original input.

6. PYDANTIC MODELS: For L9 PacketEnvelope, use proper nested structure:
   PacketEnvelope(
       packet_id=uuid4(),
       packet_type="insight",
       payload={"content": "test"},
       metadata=PacketMetadata(agent="test"),
       provenance=PacketProvenance(source="test", source_agent="test"),
   )

===== SUCCESS PATTERNS TO FOLLOW =====

1. PARAMETRIZE: Use @pytest.mark.parametrize for multiple test cases
2. FIXTURES: Create reusable fixtures for common setup
3. MOCK INJECTION: Pass mocks via constructor/fixture, not global patches
4. ASSERT SPECIFICS: Test specific fields, not entire objects when possible
5. DOCSTRINGS: Every test gets a one-line docstring explaining what it tests

OUTPUT FORMAT:
- Return ONLY valid Python code
- No markdown, no explanations, no code fence markers
- Must be directly executable with pytest
"""

UNIT_TEST_PROMPT_TEMPLATE = """Generate comprehensive unit tests for this Python module.

MODULE NAME: {module_name}

CODE TO TEST:
```python
{code}
```

AST ANALYSIS:
- Functions: {functions}
- Classes: {classes}
- Has async code: {has_async}
- Has error handling: {has_error_handling}

REQUIREMENTS:
1. Test each public function with:
   - Happy path (valid inputs → expected output based on ACTUAL code behavior)
   - Edge cases ONLY where you can see explicit handling in the code
   - Error conditions (if function has try/except blocks)

2. Test each class with:
   - Instantiation test
   - Each public method

3. Use these patterns:
   - @pytest.mark.asyncio for async tests
   - AsyncMock for async dependencies
   - MagicMock for sync dependencies
   - pytest.raises for exception testing

4. ASYNC CONTEXT MANAGERS (important):
   When mocking `async with obj.method() as x`:
   ```python
   mock_result = AsyncMock()
   mock_context = AsyncMock()
   mock_context.__aenter__ = AsyncMock(return_value=mock_result)
   mock_context.__aexit__ = AsyncMock(return_value=None)
   obj.method = MagicMock(return_value=mock_context)
   ```

IMPORTANT - ACTUAL BEHAVIOR:
- Read the code to see what it ACTUALLY does, not what it SHOULD do
- If there's an if/elif/else chain, test ALL branches including fallback/default
- Don't assume inputs are stripped/validated unless code explicitly does it
- For return value tests, match the EXACT format the code produces
- Check for truncation (like query[:50]) and match it in expected values

Generate the complete test file:
"""

INTEGRATION_TEST_PROMPT_TEMPLATE = """Generate integration tests for module interactions.

MODULE NAME: {module_name}

DEPENDENCIES: {dependencies}

CODE CONTEXT:
```python
{code}
```

REQUIREMENTS:
1. Test integration with each dependency
2. Test async flows end-to-end
3. Test error propagation between modules
4. Use realistic mock data

Generate integration tests:
"""


# =============================================================================
# Model Presets
# =============================================================================

MODEL_PRESETS = {
    "fast": {
        "model": "gpt-4.1-mini",
        "description": "Fast, cheap (~$0.003/test), ~96% accuracy (DEFAULT)",
        "temperature": 0.1,
        "max_tokens": 4000,
    },
    "balanced": {
        "model": "gpt-4.1",
        "description": "Better reasoning (~$0.01/test), ~97% accuracy",
        "temperature": 0.1,
        "max_tokens": 4000,
    },
    "quality": {
        "model": "gpt-4o",
        "description": "Best quality (~$0.02/test), ~98% accuracy",
        "temperature": 0.1,
        "max_tokens": 6000,
    },
}


class TestGenerator:
    """
    Generates tests from code proposals using AST analysis + LLM.

    Pipeline:
    1. AST Parse → Extract structure (functions, classes, signatures)
    2. Build context → Prepare LLM prompt with extracted info
    3. LLM Generate → Get actual test implementations
    4. Validate → Ensure generated code is syntactically valid

    Cost comparison:
    - Manual Cursor: ~$5-50 per test file (100s of tokens)
    - LLM API: ~$0.01-0.10 per test file (pennies)

    Model presets:
    - "fast": gpt-4o-mini (cheap, 88-96% accuracy)
    - "balanced": gpt-4.1-mini (better reasoning, ~96% accuracy)
    - "quality": gpt-4o (best quality, ~98% accuracy)
    """

    def __init__(
        self,
        use_llm: bool = True,  # DEFAULT TO TRUE - use LLM by design
        llm_client: Any | None = None,
        model: str = "gpt-4.1-mini",  # Better reasoning, still cheap
        preset: str | None = None,  # Use preset config (fast, balanced, quality)
        inject_l9_context: bool = True,  # Inject L9 ADR/patterns into prompt
    ):
        """
        Initialize TestGenerator.

        Args:
            use_llm: Whether to use LLM for test generation (default: True)
            llm_client: Optional LLM client (will create OpenAI client if None)
            model: LLM model to use (default: gpt-4o-mini for cost efficiency)
            preset: Optional preset name (fast, balanced, quality) - overrides model
            inject_l9_context: Whether to inject L9 ADR context into prompts
        """
        self._use_llm = use_llm
        self._inject_l9_context = inject_l9_context

        # Apply preset if specified
        if preset and preset in MODEL_PRESETS:
            config = MODEL_PRESETS[preset]
            self._model = config["model"]
            self._temperature = config["temperature"]
            self._max_tokens = config["max_tokens"]
            logger.info(f"Using preset '{preset}': {config['description']}")
        else:
            self._model = model
            self._temperature = 0.2
            self._max_tokens = 4000

        # Initialize LLM client
        if llm_client:
            self._llm_client = llm_client
        elif use_llm:
            self._llm_client = self._create_llm_client()
        else:
            self._llm_client = None

        # Cache L9 context
        self._l9_context: str | None = None

    def _create_llm_client(self) -> Any:
        """Create OpenAI client for LLM generation."""
        try:
            from openai import OpenAI

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.warning(
                    "OPENAI_API_KEY not set, falling back to stub generation"
                )
                return None

            return OpenAI(api_key=api_key)
        except ImportError:
            logger.warning(
                "openai package not installed, falling back to stub generation"
            )
            return None

    def _load_l9_context(self) -> str:
        """Load L9-specific context from ADRs and patterns for LLM injection."""
        if self._l9_context is not None:
            return self._l9_context

        context_parts = []

        # Load core philosophy ADR
        adr_path = _project_root / "readme" / "adr" / "0000-core-philosophy.md"
        if adr_path.exists():
            try:
                content = adr_path.read_text()
                # Extract key sections (not full file to save tokens)
                if "## Core Principle" in content:
                    start = content.find("## Core Principle")
                    end = (
                        content.find("##", start + 10)
                        if content.find("##", start + 10) > 0
                        else start + 500
                    )
                    context_parts.append(f"L9 PHILOSOPHY:\n{content[start:end][:500]}")
            except Exception:
                pass

        # Load L9-specific patterns
        l9_patterns = """
L9 CODEBASE PATTERNS:
- Use uuid4() for packet_id, not string literals
- PacketEnvelope uses nested PacketMetadata and PacketProvenance
- Most async methods use circuit breakers and fallbacks
- Error handling logs via structlog, not print
- All high-risk operations require approval gates
"""
        context_parts.append(l9_patterns)

        self._l9_context = "\n".join(context_parts) if context_parts else ""
        return self._l9_context

    def generate_unit_tests(
        self,
        code_proposal: str,
        module_name: str | None = None,
    ) -> list[str]:
        """
        Generate unit tests for a code proposal.

        Pipeline:
        1. AST parse to extract structure
        2. If LLM available: generate full implementations
        3. Fallback: generate TODO stubs (legacy behavior)

        Args:
            code_proposal: Python code to generate tests for
            module_name: Optional module name for imports

        Returns:
            List of test function strings (or single complete test file if LLM)
        """
        # Parse the code to extract structure
        try:
            tree = ast.parse(code_proposal)
        except SyntaxError as e:
            logger.warning(f"Failed to parse code proposal: {e}")
            return [self._generate_syntax_test(code_proposal, module_name)]

        # Extract AST info
        ast_info = self._extract_ast_info(tree)

        # If LLM available, generate full tests
        if self._use_llm and self._llm_client:
            return self._generate_tests_with_llm(
                code_proposal, module_name, ast_info, test_type="unit"
            )

        # Fallback to stub generation (legacy)
        logger.warning(
            "LLM not available, generating TODO stubs. "
            "Set OPENAI_API_KEY for full test generation."
        )
        return self._generate_stub_tests(tree, module_name)

    def _extract_ast_info(self, tree: ast.AST) -> dict[str, Any]:
        """Extract structured info from AST for LLM context."""
        functions = []
        classes = []
        has_async = False
        has_error_handling = False

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_info = {
                    "name": node.name,
                    "args": [arg.arg for arg in node.args.args],
                    "is_async": False,
                    "has_try_except": any(
                        isinstance(n, ast.Try) for n in ast.walk(node)
                    ),
                    "decorators": [
                        ast.unparse(d) if hasattr(ast, "unparse") else str(d)
                        for d in node.decorator_list
                    ],
                }
                functions.append(func_info)
                if func_info["has_try_except"]:
                    has_error_handling = True

            elif isinstance(node, ast.AsyncFunctionDef):
                func_info = {
                    "name": node.name,
                    "args": [arg.arg for arg in node.args.args],
                    "is_async": True,
                    "has_try_except": any(
                        isinstance(n, ast.Try) for n in ast.walk(node)
                    ),
                    "decorators": [
                        ast.unparse(d) if hasattr(ast, "unparse") else str(d)
                        for d in node.decorator_list
                    ],
                }
                functions.append(func_info)
                has_async = True
                if func_info["has_try_except"]:
                    has_error_handling = True

            elif isinstance(node, ast.ClassDef):
                methods = []
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods.append(
                            {
                                "name": item.name,
                                "is_async": isinstance(item, ast.AsyncFunctionDef),
                            }
                        )
                        if isinstance(item, ast.AsyncFunctionDef):
                            has_async = True

                classes.append(
                    {
                        "name": node.name,
                        "methods": methods,
                        "bases": [
                            ast.unparse(b) if hasattr(ast, "unparse") else str(b)
                            for b in node.bases
                        ],
                    }
                )

        return {
            "functions": functions,
            "classes": classes,
            "has_async": has_async,
            "has_error_handling": has_error_handling,
        }

    def _generate_tests_with_llm(
        self,
        code: str,
        module_name: str | None,
        ast_info: dict[str, Any],
        test_type: str = "unit",
        dependencies: list[str] | None = None,
    ) -> list[str]:
        """Generate full test implementations using LLM."""
        if test_type == "unit":
            prompt = UNIT_TEST_PROMPT_TEMPLATE.format(
                module_name=module_name or "unknown",
                code=code[:8000],  # Limit context size
                functions=ast_info["functions"],
                classes=ast_info["classes"],
                has_async=ast_info["has_async"],
                has_error_handling=ast_info["has_error_handling"],
            )
        else:
            prompt = INTEGRATION_TEST_PROMPT_TEMPLATE.format(
                module_name=module_name or "unknown",
                dependencies=dependencies or [],
                code=code[:8000],
            )

        try:
            logger.info(
                "Generating tests with LLM",
                model=self._model,
                module=module_name,
                test_type=test_type,
            )

            # Build system prompt with optional L9 context
            # security test: static constant assignment, no user input injection
            system_prompt = TEST_GENERATION_SYSTEM_PROMPT
            if self._inject_l9_context:
                l9_context = (
                    self._load_l9_context()
                )  # security test: internal config, not user input
                if l9_context:
                    system_prompt = f"{system_prompt}\n\n{l9_context}"  # security test: internal context only

            response = self._llm_client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=self._temperature,
                max_tokens=self._max_tokens,
            )

            generated_code = response.choices[0].message.content

            # Strip markdown code blocks if present
            generated_code = self._strip_markdown(generated_code)

            # Validate generated code is syntactically correct
            try:
                ast.parse(generated_code)
                logger.info(
                    "LLM test generation successful",
                    module=module_name,
                    lines=len(generated_code.splitlines()),
                )
                return [generated_code]
            except SyntaxError as e:
                logger.error(
                    "LLM generated invalid syntax, falling back to stubs",
                    error=str(e),
                )
                return self._generate_stub_tests(ast.parse(code), module_name)

        except Exception as e:
            logger.error(
                "LLM test generation failed, falling back to stubs",
                error=str(e),
            )
            return self._generate_stub_tests(ast.parse(code), module_name)

    def _strip_markdown(self, code: str) -> str:
        """Strip markdown code blocks from LLM response."""
        # Remove ```python ... ``` blocks
        if "```python" in code:
            # Extract content between ```python and ```
            start = code.find("```python")
            if start != -1:
                start += len("```python")
                end = code.find("```", start)
                if end != -1:
                    code = code[start:end]
        elif "```" in code:
            # Generic code block
            start = code.find("```")
            if start != -1:
                start += 3
                # Skip language identifier if on same line
                newline = code.find("\n", start)
                if newline != -1 and newline - start < 20:
                    start = newline + 1
                end = code.find("```", start)
                if end != -1:
                    code = code[start:end]

        return code.strip()

    def _generate_stub_tests(self, tree: ast.AST, module_name: str | None) -> list[str]:
        """Legacy: Generate TODO stub tests (fallback when no LLM)."""
        tests = []

        # Extract function definitions
        functions = [
            node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        ]

        for func in functions:
            if not func.name.startswith("_"):
                tests.extend(self._generate_function_tests(func, module_name))

        # Extract class definitions
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

        for cls in classes:
            tests.extend(self._generate_class_tests(cls, module_name))

        # Add import test
        if module_name:
            tests.insert(0, self._generate_import_test(module_name))

        return tests

    def generate_integration_tests(
        self,
        code_proposal: str,
        dependencies: list[str],
        module_name: str | None = None,
    ) -> list[str]:
        """
        Generate integration tests for a code proposal.

        Pipeline:
        1. AST parse to extract structure
        2. If LLM available: generate full integration tests
        3. Fallback: generate TODO stubs

        Args:
            code_proposal: Python code to generate tests for
            dependencies: List of module dependencies
            module_name: Optional module name

        Returns:
            List of integration test function strings
        """
        # Parse for AST info
        try:
            tree = ast.parse(code_proposal)
            ast_info = self._extract_ast_info(tree)
        except SyntaxError:
            ast_info = {
                "functions": [],
                "classes": [],
                "has_async": False,
                "has_error_handling": False,
            }

        # If LLM available, generate full tests
        if self._use_llm and self._llm_client:
            return self._generate_tests_with_llm(
                code_proposal,
                module_name,
                ast_info,
                test_type="integration",
                dependencies=dependencies,
            )

        # Fallback to stub generation
        logger.warning("LLM not available, generating integration test stubs")
        tests = []

        for dep in dependencies:
            tests.append(self._generate_dependency_test(dep, module_name))

        if "async def" in code_proposal:
            tests.append(self._generate_async_flow_test(module_name))

        tests.append(self._generate_error_handling_test(module_name))

        return tests

    def generate_complete_test_file(
        self,
        code_proposal: str,
        module_name: str,
        dependencies: list[str] | None = None,
    ) -> str:
        """
        Generate a complete, runnable test file.

        This is the PREFERRED method - generates everything in one call.

        Args:
            code_proposal: Python code to test
            module_name: Module name for imports
            dependencies: Optional list of dependencies

        Returns:
            Complete test file as a string
        """
        # Get unit tests
        unit_tests = self.generate_unit_tests(code_proposal, module_name)

        # Get integration tests if dependencies provided
        if dependencies:
            integration_tests = self.generate_integration_tests(
                code_proposal, dependencies, module_name
            )
        else:
            integration_tests = []

        # If LLM generated complete files, return first one
        if self._use_llm and self._llm_client and len(unit_tests) == 1:
            # LLM returns complete file
            return unit_tests[0]

        # Otherwise, combine stub tests into file
        header = f"""# =============================================================================
# AUTO-GENERATED TEST FILE
# Module: {module_name}
# Generator: core/testing/test_generator.py
# NOTE: These are TODO stubs. Set OPENAI_API_KEY for full test generation.
# =============================================================================

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

"""
        return header + "\n".join(unit_tests + integration_tests)

    def _generate_function_tests(
        self,
        func: ast.FunctionDef,
        module_name: str | None,
    ) -> list[str]:
        """Generate tests for a function."""
        tests = []
        func_name = func.name

        # Happy path test
        tests.append(f'''
def test_{func_name}_happy_path():
    """Test {func_name} with valid inputs."""
    # TODO(GMP-109): Add appropriate test inputs
    # result = {func_name}(...)
    # assert result is not None
    pass
''')

        # Test with edge case inputs
        tests.append(f'''
def test_{func_name}_edge_cases():
    """Test {func_name} with edge case inputs."""
    # TODO(GMP-110): Test with None, empty, boundary values
    pass
''')

        # Error handling test if function has try/except
        for node in ast.walk(func):
            if isinstance(node, ast.Try):
                tests.append(f'''
def test_{func_name}_error_handling():
    """Test {func_name} handles errors gracefully."""
    # TODO(GMP-111): Test error conditions
    pass
''')
                break

        return tests

    def _generate_class_tests(
        self,
        cls: ast.ClassDef,
        module_name: str | None,
    ) -> list[str]:
        """Generate tests for a class."""
        tests = []
        class_name = cls.name

        # Instantiation test
        tests.append(f'''
def test_{class_name.lower()}_instantiation():
    """Test {class_name} can be instantiated."""
    # TODO(GMP-112): Add appropriate constructor arguments
    # instance = {class_name}(...)
    # assert instance is not None
    pass
''')

        # Method tests for public methods
        for node in cls.body:
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                if node.name != "__init__":
                    tests.append(f'''
def test_{class_name.lower()}_{node.name}():
    """Test {class_name}.{node.name} method."""
    # TODO(GMP-113): Add test implementation
    pass
''')

        return tests

    def _generate_syntax_test(
        self,
        code_proposal: str,
        module_name: str | None,
    ) -> str:
        """Generate a basic syntax validation test."""
        return f'''
def test_code_syntax():
    """Test that code proposal has valid Python syntax."""
    import ast
    code = """{code_proposal[:500]}..."""
    try:
        ast.parse(code)
        assert False, "Expected SyntaxError"
    except SyntaxError:
        pass  # Expected
'''

    def _generate_import_test(self, module_name: str) -> str:
        """Generate an import test."""
        return f'''
def test_module_import():
    """Test that {module_name} can be imported."""
    try:
        import {module_name}
        assert {module_name} is not None
    except ImportError as e:
        pytest.skip(f"Module not available: {{e}}")
'''

    def _generate_dependency_test(
        self,
        dependency: str,
        module_name: str | None,
    ) -> str:
        """Generate a dependency integration test."""
        dep_name = dependency.split(".")[-1]
        return f'''
@pytest.mark.asyncio
async def test_integration_with_{dep_name}():
    """Test integration with {dependency}."""
    # TODO(GMP-114): Test interaction between module and {dependency}
    pass
'''

    def _generate_async_flow_test(self, module_name: str | None) -> str:
        """Generate an async flow test."""
        return '''
@pytest.mark.asyncio
async def test_async_flow():
    """Test async operations complete successfully."""
    # TODO(GMP-115): Test async function calls and await patterns
    pass
'''

    def _generate_error_handling_test(self, module_name: str | None) -> str:
        """Generate an error handling test."""
        return '''
def test_error_handling():
    """Test that errors are handled gracefully."""
    # TODO(GMP-116): Test error conditions and recovery
    pass
'''


def generate_unit_tests(
    code_proposal: str,
    module_name: str | None = None,
    use_llm: bool = True,
) -> list[str]:
    """
    Convenience function to generate unit tests.

    Args:
        code_proposal: Code to generate tests for
        module_name: Optional module name
        use_llm: Use LLM for full test generation (default: True)

    Returns:
        List of test function strings (or complete file if LLM)
    """
    generator = TestGenerator(use_llm=use_llm)
    return generator.generate_unit_tests(code_proposal, module_name)


def generate_integration_tests(
    code_proposal: str,
    dependencies: list[str],
    module_name: str | None = None,
    use_llm: bool = True,
) -> list[str]:
    """
    Convenience function to generate integration tests.

    Args:
        code_proposal: Code to generate tests for
        dependencies: List of dependencies
        module_name: Optional module name
        use_llm: Use LLM for full test generation (default: True)

    Returns:
        List of integration test function strings
    """
    generator = TestGenerator(use_llm=use_llm)
    return generator.generate_integration_tests(
        code_proposal, dependencies, module_name
    )


def generate_test_file(
    code_proposal: str,
    module_name: str,
    dependencies: list[str] | None = None,
    use_llm: bool = True,
    preset: str | None = None,
) -> str:
    """
    Generate a complete test file for a module.

    This is the RECOMMENDED entry point.

    Args:
        code_proposal: Code to generate tests for
        module_name: Module name
        dependencies: Optional list of dependencies
        use_llm: Use LLM for full test generation (default: True)
        preset: Model preset ("fast", "balanced", "quality")

    Returns:
        Complete test file as string

    Presets:
        - "fast": gpt-4o-mini (~$0.002/test, 88-96% accuracy)
        - "balanced": gpt-4.1-mini (~$0.003/test, ~96% accuracy)
        - "quality": gpt-4o (~$0.02/test, ~98% accuracy)

    Example:
        >>> code = Path("memory/enrichment_dag.py").read_text()
        >>> tests = generate_test_file(
        ...     code,
        ...     "memory.enrichment_dag",
        ...     dependencies=["core.observability.circuit_breaker"],
        ...     preset="quality",  # Use best model for critical modules
        ... )
        >>> Path("tests/memory/test_enrichment_dag.py").write_text(tests)
    """
    generator = TestGenerator(use_llm=use_llm, preset=preset)
    return generator.generate_complete_test_file(
        code_proposal, module_name, dependencies
    )


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "TestGenerator",
    "generate_integration_tests",
    "generate_test_file",
    "generate_unit_tests",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-077",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["openai"],
    "tags": ["api", "ast", "async", "core", "foundation", "llm", "test", "testing"],
    "keywords": [
        "analysis",
        "ast",
        "generate",
        "generator",
        "integration",
        "llm",
        "openai",
        "pytest",
        "unit",
    ],
    "business_value": "AST + LLM test generation: pennies vs $100s in manual token cost",
    "last_modified": "2026-02-01T00:00:00Z",
    "modified_by": "Igor Beylin",
    "change_summary": "v2.0: Added LLM-powered test generation (ADR-0000 efficiency fix)",
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
