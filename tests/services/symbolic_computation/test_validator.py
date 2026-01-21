"""
Tests for SymPy Expression Validator
=====================================

Tests for ExpressionValidator class covering:
- Length validation
- Dangerous function detection
- Syntax validation
- Sanitization

Target: >=85% coverage, >=95% pass rate
"""

from __future__ import annotations

import pytest

from services.symbolic_computation.core.validator import ExpressionValidator
from services.symbolic_computation.config import SymbolicComputationConfig


class TestExpressionValidator:
    """Test suite for ExpressionValidator."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return ExpressionValidator()

    @pytest.fixture
    def strict_validator(self):
        """Create strict validator that blocks all dangerous functions."""
        config = SymbolicComputationConfig(
            max_expression_length=100,
            allow_dangerous_functions=False,
        )
        return ExpressionValidator(config=config)


class TestValidExpressions:
    """Tests for valid expressions."""

    @pytest.fixture
    def validator(self):
        return ExpressionValidator()

    def test_valid_simple(self, validator):
        """Test that simple expression is valid."""
        result = validator.validate("x**2")

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_valid_polynomial(self, validator):
        """Test that polynomial is valid."""
        result = validator.validate("x**3 + 2*x**2 - x + 1")

        assert result.is_valid is True

    def test_valid_trigonometric(self, validator):
        """Test that trigonometric expression is valid."""
        result = validator.validate("sin(x) + cos(y)")

        assert result.is_valid is True

    def test_valid_with_constants(self, validator):
        """Test expression with constants."""
        result = validator.validate("3.14159 * r**2")

        assert result.is_valid is True


class TestLengthValidation:
    """Tests for expression length validation."""

    def test_within_limit(self):
        """Test expression within length limit."""
        config = SymbolicComputationConfig(max_expression_length=100)
        validator = ExpressionValidator(config=config)

        result = validator.validate("x**2")

        assert result.is_valid is True

    def test_exceeds_limit(self):
        """Test expression exceeding length limit."""
        config = SymbolicComputationConfig(max_expression_length=100)
        validator = ExpressionValidator(config=config)

        # Create an expression longer than 100 characters
        long_expr = "x**2 + " * 20 + "1"  # ~150 characters
        result = validator.validate(long_expr)

        assert result.is_valid is False
        assert any("length" in e.lower() for e in result.errors)


class TestDangerousFunctions:
    """Tests for dangerous function detection."""

    @pytest.fixture
    def validator(self):
        config = SymbolicComputationConfig(allow_dangerous_functions=False)
        return ExpressionValidator(config=config)

    def test_detect_eval(self, validator):
        """Test that eval() is detected."""
        result = validator.validate("eval('x**2')")

        assert result.is_valid is False
        assert "eval" in result.dangerous_functions_found

    def test_detect_exec(self, validator):
        """Test that exec() is detected."""
        result = validator.validate("exec('print(x)')")

        assert result.is_valid is False
        assert "exec" in result.dangerous_functions_found

    def test_detect_import(self, validator):
        """Test that __import__ is detected."""
        result = validator.validate("__import__('os')")

        assert result.is_valid is False
        assert "__import__" in result.dangerous_functions_found

    def test_detect_dunder(self, validator):
        """Test that dunder methods are detected."""
        result = validator.validate("x.__class__")

        assert result.is_valid is False


class TestSyntaxValidation:
    """Tests for syntax validation."""

    @pytest.fixture
    def validator(self):
        return ExpressionValidator()

    def test_valid_syntax(self, validator):
        """Test valid SymPy syntax."""
        result = validator.validate("x**2 + sin(x)")

        assert result.is_valid is True

    def test_unbalanced_parens(self, validator):
        """Test unbalanced parentheses detection."""
        result = validator.validate("(x**2 + 1")

        assert result.is_valid is False
        assert any("unclosed" in e.lower() or "unmatched" in e.lower() for e in result.errors)

    def test_mismatched_brackets(self, validator):
        """Test mismatched bracket detection."""
        result = validator.validate("x[0)")

        assert result.is_valid is False


class TestSanitization:
    """Tests for expression sanitization."""

    @pytest.fixture
    def validator(self):
        return ExpressionValidator()

    def test_sanitize_eval(self, validator):
        """Test that eval is sanitized."""
        sanitized = validator.sanitize("x + eval('1')")

        assert "eval" not in sanitized.lower()

    def test_sanitize_dunder(self, validator):
        """Test that dunder is sanitized."""
        sanitized = validator.sanitize("x.__class__")

        assert "__class__" not in sanitized

    def test_sanitize_comment(self, validator):
        """Test that comments are removed."""
        sanitized = validator.sanitize("x**2 # this is a comment")

        assert "#" not in sanitized
        assert "comment" not in sanitized


class TestVariableNameValidation:
    """Tests for variable name validation."""

    @pytest.fixture
    def validator(self):
        return ExpressionValidator()

    def test_valid_variable_names(self, validator):
        """Test valid variable names."""
        invalid = validator.validate_variable_names(["x", "y", "z", "var1", "_private"])

        assert len(invalid) == 0

    def test_invalid_variable_names(self, validator):
        """Test invalid variable names."""
        invalid = validator.validate_variable_names(["123abc", "my-var", "eval"])

        assert len(invalid) > 0
