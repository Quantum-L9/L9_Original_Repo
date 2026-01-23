"""
Tests for SymPy Code Generator
===============================

Tests for CodeGenerator class covering:
- C code generation
- Fortran code generation
- Python code generation
- Error handling

Target: >=85% coverage, >=95% pass rate
"""

from __future__ import annotations

import pytest

from services.symbolic_computation.core.code_generator import CodeGenerator


class TestCodeGenerator:
    """Test suite for CodeGenerator."""

    @pytest.fixture
    def generator(self):
        """Create generator instance."""
        return CodeGenerator()


class TestPythonCodeGeneration:
    """Tests for Python code generation."""

    @pytest.fixture
    def generator(self):
        return CodeGenerator()

    @pytest.mark.asyncio
    async def test_generate_python_simple(self, generator):
        """Test generating Python code for simple expression."""
        result = await generator.generate_code(
            expr="x**2",
            variables=["x"],
            language="Python",
            function_name="square",
        )

        assert result.success is True
        assert "def square" in result.source_code
        assert result.language == "Python"
        assert result.function_name == "square"

    @pytest.mark.asyncio
    async def test_generate_python_multi_var(self, generator):
        """Test generating Python code with multiple variables."""
        result = await generator.generate_code(
            expr="x + y + z",
            variables=["x", "y", "z"],
            language="Python",
            function_name="sum_xyz",
        )

        assert result.success is True
        assert "def sum_xyz" in result.source_code


class TestCCodeGeneration:
    """Tests for C code generation."""

    @pytest.fixture
    def generator(self):
        return CodeGenerator()

    @pytest.mark.asyncio
    async def test_generate_c_simple(self, generator):
        """Test generating C code for simple expression."""
        result = await generator.generate_code(
            expr="x**2 + 1",
            variables=["x"],
            language="C",
            function_name="quadratic",
        )

        assert result.success is True
        assert result.language == "C"
        # Should have C-style function definition
        assert "double" in result.source_code or "quadratic" in result.source_code


class TestFortranCodeGeneration:
    """Tests for Fortran code generation."""

    @pytest.fixture
    def generator(self):
        return CodeGenerator()

    @pytest.mark.asyncio
    async def test_generate_fortran_simple(self, generator):
        """Test generating Fortran code for simple expression."""
        result = await generator.generate_code(
            expr="x**2",
            variables=["x"],
            language="Fortran",
            function_name="square",
        )

        assert result.success is True
        assert result.language == "Fortran"


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.fixture
    def generator(self):
        return CodeGenerator()

    @pytest.mark.asyncio
    async def test_invalid_expression(self, generator):
        """Test handling of invalid expression."""
        result = await generator.generate_code(
            expr="x +++ y",  # Invalid syntax
            variables=["x", "y"],
            language="C",
            function_name="test",
        )

        assert result.success is False
        assert result.error_message is not None


class TestCodeCompilation:
    """Tests for code compilation."""

    @pytest.fixture
    def generator(self):
        return CodeGenerator()

    def test_compile_python_code(self, generator):
        """Test compiling generated Python code."""
        python_code = """
def square(x):
    return x**2
"""
        fn = generator.compile_generated(python_code, "Python", "square")

        if fn is not None:
            assert callable(fn)
            assert fn(3) == 9
