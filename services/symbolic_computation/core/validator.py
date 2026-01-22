"""
SymPy Expression Validator
===========================

Validate and sanitize SymPy expressions before evaluation.
Enforces security constraints and governance policies.

Version: 6.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Validator",
    "module_version": "6.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "operations",
    "domain": "symbolic_computation",
    "module_name": "validator",
    "type": "validator",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "services.symbolic_computation.api.routes",
            "services.symbolic_computation.core.__init__",
            "services.symbolic_computation.tools.symbolic_tool",
            "tests.services.symbolic_computation.test_integration",
            "tests.services.symbolic_computation.test_validator",
        ],
    },
}
# ============================================================================

import re
from typing import List, Optional

import structlog
from sympy import sympify

from services.symbolic_computation.config import (SymbolicComputationConfig,
                                                  get_config)
from services.symbolic_computation.core.models import ValidationResult

logger = structlog.get_logger(__name__)


class ExpressionValidator:
    """
    Validate SymPy expressions for safety and correctness.

    Enforces:
    - Maximum expression length
    - Dangerous function blocking (eval, exec, etc.)
    - Syntax validation
    - Variable naming constraints

    Security note: All expressions MUST be validated before evaluation
    to prevent code injection and resource exhaustion attacks.

    Example:
        validator = ExpressionValidator()
        result = validator.validate("x**2 + sin(x)")
        if result.is_valid:
            # Safe to evaluate
            pass
    """

    # Dangerous functions that should never be allowed
    ALWAYS_BLOCKED = {
        "eval",
        "exec",
        "__import__",
        "open",
        "compile",
        "getattr",
        "setattr",
        "delattr",
        "globals",
        "locals",
        "vars",
        "input",
        "breakpoint",
    }

    # Functions that may be blocked based on config
    POTENTIALLY_DANGEROUS = {
        "System",  # SymPy's system of equations (can be expensive)
        "Integral",  # Symbolic integration (can be slow)
        "Sum",  # Symbolic summation (can be slow)
        "Product",  # Symbolic product (can be slow)
        "Limit",  # Symbolic limits (can be slow)
    }

    # Valid variable name pattern
    VARIABLE_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

    def __init__(
        self,
        config: Optional[SymbolicComputationConfig] = None,
    ):
        """
        Initialize the validator.

        Args:
            config: Configuration instance (uses global if not provided)
        """
        self.config = config or get_config()
        self.logger = logger.bind(component="expression_validator")

        # Build blocked function set
        self._blocked_functions = self.ALWAYS_BLOCKED.copy()
        if not self.config.allow_dangerous_functions:
            self._blocked_functions.update(set(self.config.dangerous_functions))

        self.logger.info(
            "validator_initialized",
            max_length=self.config.max_expression_length,
            allow_dangerous=self.config.allow_dangerous_functions,
            blocked_count=len(self._blocked_functions),
        )

    def validate(self, expr: str) -> ValidationResult:
        """
        Validate an expression for safety and correctness.

        Args:
            expr: SymPy expression as string

        Returns:
            ValidationResult with validation status and details
        """
        errors: List[str] = []
        warnings: List[str] = []
        dangerous_found: List[str] = []

        self.logger.debug(
            "validating_expression",
            expr_len=len(expr),
        )

        # Check 1: Expression length
        if len(expr) > self.config.max_expression_length:
            errors.append(
                f"Expression length {len(expr)} exceeds maximum "
                f"{self.config.max_expression_length}"
            )

        # Check 2: Dangerous functions
        dangerous = self.check_dangerous_functions(expr)
        if dangerous:
            dangerous_found.extend(dangerous)
            errors.append(
                f"Expression contains dangerous functions: {', '.join(dangerous)}"
            )

        # Check 3: Potentially expensive functions (warning only)
        expensive = self._check_expensive_functions(expr)
        if expensive:
            warnings.append(
                f"Expression contains potentially expensive functions: "
                f"{', '.join(expensive)}. Consider adding timeout."
            )

        # Check 4: Syntax validation
        syntax_error = self._validate_syntax(expr)
        if syntax_error:
            errors.append(f"Syntax error: {syntax_error}")

        # Check 5: Balanced parentheses/brackets
        balance_error = self._check_balanced(expr)
        if balance_error:
            errors.append(balance_error)

        is_valid = len(errors) == 0

        result = ValidationResult(
            is_valid=is_valid,
            expression_length=len(expr),
            dangerous_functions_found=dangerous_found,
            errors=errors,
            warnings=warnings,
        )

        self.logger.info(
            "expression_validated",
            is_valid=is_valid,
            num_errors=len(errors),
            num_warnings=len(warnings),
        )

        return result

    def check_dangerous_functions(self, expr: str) -> List[str]:
        """
        Find dangerous functions in expression.

        Args:
            expr: Expression string to check

        Returns:
            List of dangerous function names found
        """
        found = []

        # Check for function calls using regex
        # Match: function_name(
        pattern = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(")

        for match in pattern.finditer(expr):
            func_name = match.group(1)
            if func_name.lower() in {f.lower() for f in self._blocked_functions}:
                found.append(func_name)

        # Also check for dunder methods
        dunder_pattern = re.compile(r"__[a-zA-Z_]+__")
        for match in dunder_pattern.finditer(expr):
            found.append(match.group(0))

        return found

    def _check_expensive_functions(self, expr: str) -> List[str]:
        """Check for potentially expensive symbolic functions."""
        found = []

        for func in self.POTENTIALLY_DANGEROUS:
            if func in expr:
                found.append(func)

        return found

    def _validate_syntax(self, expr: str) -> Optional[str]:
        """Validate SymPy syntax by attempting to parse."""
        try:
            sympify(expr)
            return None
        except Exception as e:
            return str(e)

    def _check_balanced(self, expr: str) -> Optional[str]:
        """Check for balanced parentheses and brackets."""
        stack = []
        pairs = {"(": ")", "[": "]", "{": "}"}

        for i, char in enumerate(expr):
            if char in pairs:
                stack.append((char, i))
            elif char in pairs.values():
                if not stack:
                    return f"Unmatched '{char}' at position {i}"
                open_char, _ = stack.pop()
                if pairs[open_char] != char:
                    return f"Mismatched brackets at position {i}"

        if stack:
            char, pos = stack[0]
            return f"Unclosed '{char}' at position {pos}"

        return None

    def validate_variable_names(self, variables: List[str]) -> List[str]:
        """
        Validate variable names.

        Args:
            variables: List of variable names to validate

        Returns:
            List of invalid variable names
        """
        invalid = []

        for var in variables:
            if not self.VARIABLE_PATTERN.match(var):
                invalid.append(var)
            elif var in self._blocked_functions:
                invalid.append(var)

        return invalid

    def sanitize(self, expr: str) -> str:
        """
        Sanitize expression by removing potentially dangerous content.

        Note: This is a best-effort sanitization. Always validate
        after sanitization.

        Args:
            expr: Expression to sanitize

        Returns:
            Sanitized expression
        """
        sanitized = expr

        # Remove dangerous function calls
        for func in self._blocked_functions:
            pattern = re.compile(rf"\b{re.escape(func)}\s*\([^)]*\)", re.IGNORECASE)
            sanitized = pattern.sub("0", sanitized)

        # Remove dunder methods
        sanitized = re.sub(r"__[a-zA-Z_]+__", "0", sanitized)

        # Remove inline comments (Python-style)
        sanitized = re.sub(r"#.*$", "", sanitized, flags=re.MULTILINE)

        return sanitized.strip()


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SER-OPER-022",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "debugging",
        "event-driven",
        "logging",
        "operations",
        "symbolic-computation",
        "validation",
        "validator",
    ],
    "keywords": [
        "check",
        "dangerous",
        "expression",
        "functions",
        "governance",
        "names",
        "sanitize",
        "sympy",
    ],
    "business_value": "Implements ExpressionValidator for validator functionality",
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
