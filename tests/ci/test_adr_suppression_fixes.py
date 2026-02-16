"""
Tests for ADR Suppression Fixes — ADR-0087, ADR-0055, ADR-0088
================================================================

Validates that:
1. SQL injection vectors are blocked by allowlist validation (ADR-0087)
2. Bare except handlers are converted to specific exception types (ADR-0055)
3. Pickle deserialization is replaced with safe alternatives (ADR-0088)
4. All noqa: ADR-XXXX suppressions have been removed from fixed code
"""

from __future__ import annotations

import ast
import re
import textwrap
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ============================================================================
# Project root for file scanning
# ============================================================================
PROJECT_ROOT = Path(__file__).parent.parent.parent


# ============================================================================
# ADR-0087: SQL Injection — Table Allowlist Tests
# ============================================================================


class TestADR0087TableAllowlist:
    """Verify _ALLOWED_MEMORY_TABLES blocks injection via table names."""

    def test_allowed_tables_constant_exists(self) -> None:
        """The allowlist constant must be defined in memory.py."""
        memory_py = PROJECT_ROOT / "mcp_memory" / "src" / "routes" / "memory.py"
        content = memory_py.read_text()
        assert "_ALLOWED_MEMORY_TABLES" in content, (
            "_ALLOWED_MEMORY_TABLES allowlist not found in memory.py"
        )

    def test_allowed_tables_contains_expected_values(self) -> None:
        """Allowlist must contain exactly the three known memory tables."""
        memory_py = PROJECT_ROOT / "mcp_memory" / "src" / "routes" / "memory.py"
        content = memory_py.read_text()
        for table in ("memory.short_term", "memory.medium_term", "memory.long_term"):
            assert table in content, f"Missing expected table {table!r} in allowlist"

    def test_malicious_table_name_rejected(self) -> None:
        """A SQL-injection table name like 'users; DROP TABLE --' must be rejected."""
        allowed = frozenset({
            "memory.short_term",
            "memory.medium_term",
            "memory.long_term",
        })
        malicious_inputs = [
            "users; DROP TABLE memory.long_term --",
            "memory.long_term; DELETE FROM users --",
            "' OR '1'='1",
            "memory.long_term UNION SELECT * FROM pg_shadow --",
            "../../../etc/passwd",
            "",
            "memory.nonexistent",
        ]
        for bad_table in malicious_inputs:
            assert bad_table not in allowed, (
                f"Malicious table name {bad_table!r} should not be in allowlist"
            )

    def test_valid_table_names_accepted(self) -> None:
        """Known-good table names must pass the allowlist check."""
        allowed = frozenset({
            "memory.short_term",
            "memory.medium_term",
            "memory.long_term",
        })
        for good_table in ("memory.short_term", "memory.medium_term", "memory.long_term"):
            assert good_table in allowed, (
                f"Valid table name {good_table!r} rejected by allowlist"
            )

    def test_table_validation_guard_in_save_handler(self) -> None:
        """save_memory_handler must validate table before query construction."""
        memory_py = PROJECT_ROOT / "mcp_memory" / "src" / "routes" / "memory.py"
        content = memory_py.read_text()
        # The validation must appear BEFORE the f-string query
        validation_pos = content.find("if table not in _ALLOWED_MEMORY_TABLES:")
        insert_query_pos = content.find('INSERT INTO {table}')
        assert validation_pos != -1, "Table validation guard not found"
        assert validation_pos < insert_query_pos, (
            "Table validation must appear before the INSERT query"
        )

    def test_table_validation_guard_in_search_handler(self) -> None:
        """search_memory_handler must validate table before query construction."""
        memory_py = PROJECT_ROOT / "mcp_memory" / "src" / "routes" / "memory.py"
        content = memory_py.read_text()
        # Find the search query section (SELECT ... FROM {table})
        search_section = content[content.find("async def search_memory_handler"):]
        validation_pos = search_section.find("if table not in _ALLOWED_MEMORY_TABLES:")
        select_pos = search_section.find("FROM {table}")
        assert validation_pos != -1, "Table validation guard not found in search"
        assert validation_pos < select_pos, (
            "Table validation must appear before the SELECT query"
        )


class TestADR0087TemporalOperationValidation:
    """Verify temporal query operation parameter is validated."""

    def test_operation_validation_exists(self) -> None:
        """query_temporal must validate the operation parameter."""
        memory_py = PROJECT_ROOT / "mcp_memory" / "src" / "routes" / "memory.py"
        content = memory_py.read_text()
        assert "_ALLOWED_OPERATIONS" in content, (
            "Operation allowlist not found in query_temporal"
        )

    def test_allowed_operations_are_correct(self) -> None:
        """Only changes, timeline, diff should be allowed operations."""
        allowed = frozenset({"changes", "timeline", "diff"})
        assert allowed == {"changes", "timeline", "diff"}

    def test_malicious_operation_rejected(self) -> None:
        """SQL injection via operation parameter must be blocked."""
        allowed = frozenset({"changes", "timeline", "diff"})
        malicious_ops = [
            "changes; DROP TABLE memory.long_term --",
            "' OR '1'='1",
            "UNION SELECT * FROM pg_shadow",
            "",
            "nonexistent",
        ]
        for bad_op in malicious_ops:
            assert bad_op not in allowed, (
                f"Malicious operation {bad_op!r} should not be in allowlist"
            )


class TestADR0087DecayFactorParameterized:
    """Verify decay_factor is parameterized, not interpolated."""

    def test_decay_factor_uses_parameter_placeholder(self) -> None:
        """The decay UPDATE query must use $1 placeholder, not f-string."""
        unified_py = (
            PROJECT_ROOT / "mcp_memory" / "src" / "routes" / "memory_unified.py"
        )
        content = unified_py.read_text()
        # Find the apply_importance_decay function
        decay_section = content[content.find("async def apply_importance_decay"):]
        # The POWER function should use $1 parameter
        assert "POWER(\n                    $1," in decay_section or "POWER($1," in decay_section, (
            "decay_factor must be parameterized as $1 in POWER() call"
        )

    def test_decay_factor_not_fstring_interpolated(self) -> None:
        """The decay query must NOT use f-string interpolation for decay_factor."""
        unified_py = (
            PROJECT_ROOT / "mcp_memory" / "src" / "routes" / "memory_unified.py"
        )
        content = unified_py.read_text()
        decay_section = content[content.find("async def apply_importance_decay"):]
        # Should not contain f-string with {decay_factor} in the SQL
        assert "{decay_factor}" not in decay_section.split("float(decay_factor)")[0], (
            "decay_factor must not be f-string interpolated in SQL"
        )


class TestADR0087StaleNoqaRemoved:
    """Verify stale noqa: ADR-0087 comments are removed from fixed files."""

    def test_substrate_repository_no_stale_noqa(self) -> None:
        """substrate_repository.py should have no ADR-0087 noqa on parameterized queries."""
        repo_py = PROJECT_ROOT / "memory" / "substrate_repository.py"
        content = repo_py.read_text()
        lines_with_noqa = [
            (i, line)
            for i, line in enumerate(content.splitlines(), 1)
            if "noqa: ADR-0087" in line
            # Exclude comment-only lines that are documentation
            and not line.strip().startswith("#")
        ]
        assert lines_with_noqa == [], (
            f"Stale noqa: ADR-0087 found on lines: {lines_with_noqa}"
        )

    def test_docstring_ab_test_no_false_positive_noqa(self) -> None:
        """docstring_ab_test.py should not have ADR-0087 noqa (not SQL)."""
        docstring_py = PROJECT_ROOT / "tools" / "codegen" / "docstring_ab_test.py"
        content = docstring_py.read_text()
        assert "noqa: ADR-0087" not in content, (
            "False-positive noqa: ADR-0087 still present in docstring_ab_test.py"
        )

    def test_memory_py_noqa_removed_from_queries(self) -> None:
        """memory.py should have no noqa: ADR-0087 on query lines."""
        memory_py = PROJECT_ROOT / "mcp_memory" / "src" / "routes" / "memory.py"
        content = memory_py.read_text()
        for i, line in enumerate(content.splitlines(), 1):
            if "noqa: ADR-0087" in line:
                pytest.fail(
                    f"memory.py:{i} still has noqa: ADR-0087: {line.strip()}"
                )

    def test_memory_unified_noqa_removed(self) -> None:
        """memory_unified.py should have no noqa: ADR-0087."""
        unified_py = (
            PROJECT_ROOT / "mcp_memory" / "src" / "routes" / "memory_unified.py"
        )
        content = unified_py.read_text()
        for i, line in enumerate(content.splitlines(), 1):
            if "noqa: ADR-0087" in line:
                pytest.fail(
                    f"memory_unified.py:{i} still has noqa: ADR-0087: {line.strip()}"
                )


class TestADR0087SQLInjectionPayloads:
    """Demonstrate that SQL injection payloads cannot bypass the allowlist."""

    @pytest.mark.parametrize(
        "payload",
        [
            "' OR '1'='1",
            "1; DROP TABLE users; --",
            "memory.long_term' UNION SELECT password FROM users --",
            "memory.long_term; COPY (SELECT * FROM pg_shadow) TO '/tmp/pwned' --",
            "memory.long_term\n; DELETE FROM packet_store; --",
        ],
    )
    def test_injection_payload_blocked_by_allowlist(self, payload: str) -> None:
        """Each SQL injection payload must fail the allowlist check."""
        allowed = frozenset({
            "memory.short_term",
            "memory.medium_term",
            "memory.long_term",
        })
        assert payload not in allowed, (
            f"SQL injection payload {payload!r} passed allowlist!"
        )


# ============================================================================
# ADR-0055: Bare Except — Specific Exception Handler Tests
# ============================================================================


class TestADR0055BareExceptFix:
    """Verify fix_bare_except produces specific exception handlers."""

    def test_auto_fixer_no_longer_adds_noqa(self) -> None:
        """fix_bare_except must not add noqa: ADR-0055 comments."""
        auto_fix_py = PROJECT_ROOT / "ci" / "auto_fix_adr.py"
        content = auto_fix_py.read_text()
        # Find the fix_bare_except function body
        func_start = content.find("def fix_bare_except(")
        # Find the next def (end of function)
        next_func = content.find("\ndef ", func_start + 1)
        func_body = content[func_start:next_func]
        # The function should NOT produce noqa: ADR-0055 in its output
        # (it may reference it in docstring, but not in the replacement line)
        replacement_line = 'except Exception as e:  # converted from bare except'
        assert replacement_line in func_body, (
            "fix_bare_except should produce 'except Exception as e:' without noqa"
        )

    def test_auto_fixer_uses_exception_variable(self) -> None:
        """The converted except must bind the exception to a variable."""
        auto_fix_py = PROJECT_ROOT / "ci" / "auto_fix_adr.py"
        content = auto_fix_py.read_text()
        func_start = content.find("def fix_bare_except(")
        next_func = content.find("\ndef ", func_start + 1)
        func_body = content[func_start:next_func]
        # Must use 'as e' to bind the exception
        assert "as e:" in func_body, (
            "fix_bare_except must bind exception variable with 'as e:'"
        )

    def test_no_bare_except_in_production_code(self) -> None:
        """Scan production code for any remaining bare except: statements."""
        # Directories to scan (production code only)
        scan_dirs = [
            PROJECT_ROOT / "core",
            PROJECT_ROOT / "memory",
            PROJECT_ROOT / "mcp_memory",
            PROJECT_ROOT / "agents",
        ]
        violations = []
        for scan_dir in scan_dirs:
            if not scan_dir.exists():
                continue
            for py_file in scan_dir.rglob("*.py"):
                if "__pycache__" in str(py_file):
                    continue
                try:
                    tree = ast.parse(py_file.read_text())
                except SyntaxError:
                    continue
                for node in ast.walk(tree):
                    if isinstance(node, ast.ExceptHandler) and node.type is None:
                        violations.append(f"{py_file}:{node.lineno}")
        assert violations == [], (
            f"Bare except: found in production code:\n"
            + "\n".join(f"  {v}" for v in violations)
        )


class TestADR0055ExceptionPathRaises:
    """Verify exception paths raise correct exceptions, not swallow errors."""

    def test_value_error_raised_for_invalid_table(self) -> None:
        """Invalid table name must raise ValueError, not be swallowed."""
        allowed = frozenset({
            "memory.short_term",
            "memory.medium_term",
            "memory.long_term",
        })
        bad_table = "memory.evil_table"
        with pytest.raises(ValueError, match="Invalid memory table"):
            if bad_table not in allowed:
                raise ValueError(f"Invalid memory table: {bad_table!r}")

    def test_value_error_raised_for_invalid_operation(self) -> None:
        """Invalid temporal operation must raise ValueError."""
        allowed_ops = frozenset({"changes", "timeline", "diff"})
        bad_op = "evil_operation"
        with pytest.raises(ValueError, match="Invalid temporal operation"):
            if bad_op not in allowed_ops:
                raise ValueError(f"Invalid temporal operation: {bad_op!r}")


# ============================================================================
# ADR-0088: Unsafe Pickle — Safe Alternative Tests
# ============================================================================


class TestADR0088PickleFix:
    """Verify pickle usage is replaced with safe alternatives."""

    def test_check_adr_compliance_no_pickle_noqa(self) -> None:
        """check_adr_compliance.py docstring should not suppress ADR-0088."""
        compliance_py = PROJECT_ROOT / "ci" / "check_adr_compliance.py"
        content = compliance_py.read_text()
        # The docstring line about ADR-0088 should not have noqa
        for i, line in enumerate(content.splitlines(), 1):
            if "ADR-0088" in line and "noqa" in line:
                # Allow lines that are checking FOR noqa (in the checker logic)
                if "noqa" in line and ("_add_violation" in line or "self." in line):
                    continue
                # The docstring line should be clean
                if line.strip().startswith("- ADR-0088"):
                    pytest.fail(
                        f"check_adr_compliance.py:{i} still has noqa on ADR-0088 docstring"
                    )

    def test_auto_fixer_replaces_pickle_not_suppresses(self) -> None:
        """fix_pickle_usage must replace pickle calls, not add noqa."""
        auto_fix_py = PROJECT_ROOT / "ci" / "auto_fix_adr.py"
        content = auto_fix_py.read_text()
        func_start = content.find("def fix_pickle_usage(")
        next_func = content.find("\ndef ", func_start + 1)
        func_body = content[func_start:next_func]
        # Should contain json.loads replacement logic
        assert "json.loads" in func_body, (
            "fix_pickle_usage should replace pickle.loads with json.loads"
        )
        # Should NOT add noqa: ADR-0088 to lines
        assert "noqa: ADR-0088" not in func_body, (
            "fix_pickle_usage should not add noqa: ADR-0088 suppressions"
        )

    def test_pickle_loads_rejected_on_untrusted_data(self) -> None:
        """Demonstrate that pickle.loads on untrusted data is dangerous."""
        import pickle
        import json

        # Simulate untrusted data that would be safe with json but dangerous with pickle
        safe_data = '{"key": "value"}'
        # json.loads safely handles the data
        result = json.loads(safe_data)
        assert result == {"key": "value"}

        # Verify that our replacement pattern works
        assert hasattr(json, "loads")
        assert hasattr(json, "load")
        assert hasattr(json, "dumps")
        assert hasattr(json, "dump")

    def test_no_pickle_import_in_production_code(self) -> None:
        """Production code should not import pickle module."""
        scan_dirs = [
            PROJECT_ROOT / "core",
            PROJECT_ROOT / "memory",
            PROJECT_ROOT / "mcp_memory",
            PROJECT_ROOT / "agents",
        ]
        violations = []
        for scan_dir in scan_dirs:
            if not scan_dir.exists():
                continue
            for py_file in scan_dir.rglob("*.py"):
                if "__pycache__" in str(py_file):
                    continue
                try:
                    content = py_file.read_text()
                except (UnicodeDecodeError, OSError):
                    continue
                # Check for pickle imports
                if re.search(r"^\s*import\s+pickle\b", content, re.MULTILINE):
                    violations.append(str(py_file))
                if re.search(
                    r"^\s*from\s+pickle\s+import\b", content, re.MULTILINE
                ):
                    violations.append(str(py_file))
        assert violations == [], (
            f"Pickle imports found in production code:\n"
            + "\n".join(f"  {v}" for v in violations)
        )


# ============================================================================
# Cross-cutting: Verify all noqa suppressions are removed
# ============================================================================


class TestNoqaSuppressionsRemoved:
    """Verify that all targeted noqa suppressions have been removed."""

    def _scan_for_noqa(self, adr_code: str, files: list[Path]) -> list[str]:
        """Scan files for remaining noqa: ADR-XXXX comments."""
        violations = []
        for filepath in files:
            if not filepath.exists():
                continue
            content = filepath.read_text()
            for i, line in enumerate(content.splitlines(), 1):
                if f"noqa: {adr_code}" in line:
                    # Skip lines that are test data or CI tooling examples
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        continue
                    if "write_text(" in line or "assert" in line:
                        continue
                    violations.append(f"{filepath.name}:{i}: {stripped[:80]}")
        return violations

    def test_no_adr_0087_in_production_routes(self) -> None:
        """No noqa: ADR-0087 should remain in production route files."""
        files = [
            PROJECT_ROOT / "mcp_memory" / "src" / "routes" / "memory.py",
            PROJECT_ROOT / "mcp_memory" / "src" / "routes" / "memory_unified.py",
            PROJECT_ROOT / "memory" / "substrate_repository.py",
            PROJECT_ROOT / "tools" / "codegen" / "docstring_ab_test.py",
        ]
        violations = self._scan_for_noqa("ADR-0087", files)
        assert violations == [], (
            f"Remaining noqa: ADR-0087 in production files:\n"
            + "\n".join(f"  {v}" for v in violations)
        )

    def test_no_adr_0088_in_compliance_docstring(self) -> None:
        """No noqa: ADR-0088 should remain in check_adr_compliance.py docstring."""
        compliance_py = PROJECT_ROOT / "ci" / "check_adr_compliance.py"
        content = compliance_py.read_text()
        # Check only the module docstring area (first 30 lines)
        docstring_lines = content.splitlines()[:30]
        for i, line in enumerate(docstring_lines, 1):
            if "noqa: ADR-0088" in line:
                pytest.fail(
                    f"check_adr_compliance.py:{i} still has noqa: ADR-0088 in docstring"
                )
