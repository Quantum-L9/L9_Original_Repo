"""
Tests for auto_fix_adr.py post-fix validation gate.

This ensures the auto-fixer doesn't introduce:
1. Syntax errors in modified files
2. # noqa comments inside string literals (the noqa-inside-SQL bug)

Reference: ci/auto_fix_adr.py::validate_syntax, validate_noqa_not_in_string
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ci.auto_fix_adr import (
    fix_lru_cache_maxsize,
    fix_path_safety,
    fix_pickle_usage,
    fix_registry_pattern,
    fix_resilience_mixin,
    fix_typeddict_pydantic,
    fix_websocket_pattern,
    validate_modified_files,
    validate_noqa_not_in_string,
    validate_syntax,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestValidateSyntax:
    """Tests for validate_syntax function."""

    def test_valid_python_syntax(self, tmp_path: Path) -> None:
        """Valid Python code should pass syntax check."""
        test_file = tmp_path / "valid.py"
        test_file.write_text("x = 1\ny = 2\nprint(x + y)")

        is_valid, error = validate_syntax(test_file)

        assert is_valid is True
        assert error == ""

    def test_invalid_python_syntax(self, tmp_path: Path) -> None:
        """Invalid Python code should fail syntax check."""
        test_file = tmp_path / "invalid.py"
        test_file.write_text("x = 1 +  # broken syntax")

        is_valid, error = validate_syntax(test_file)

        assert is_valid is False
        assert "SyntaxError" in error
        assert "line 1" in error

    def test_syntax_error_with_line_number(self, tmp_path: Path) -> None:
        """Syntax error should report correct line number."""
        test_file = tmp_path / "error_line3.py"
        test_file.write_text("x = 1\ny = 2\nz = 3 +  # error on line 3")

        is_valid, error = validate_syntax(test_file)

        assert is_valid is False
        assert "line 3" in error

    def test_empty_file_is_valid(self, tmp_path: Path) -> None:
        """Empty file should pass syntax check."""
        test_file = tmp_path / "empty.py"
        test_file.write_text("")

        is_valid, _ = validate_syntax(test_file)

        assert is_valid is True


class TestValidateNoqaNotInString:
    """Tests for validate_noqa_not_in_string function."""

    def test_noqa_in_comment_is_valid(self, tmp_path: Path) -> None:
        """# noqa in a comment (end of line) is valid."""
        test_file = tmp_path / "valid_noqa.py"
        test_file.write_text("x = 1  # noqa: ADR-0019")

        is_valid, bad_lines = validate_noqa_not_in_string(test_file)

        assert is_valid is True
        assert bad_lines == []

    def test_noqa_after_string_is_valid(self, tmp_path: Path) -> None:
        """# noqa after a string literal is valid."""
        test_file = tmp_path / "valid_after_string.py"
        test_file.write_text('x = "some text"  # noqa: ADR-0019')

        is_valid, bad_lines = validate_noqa_not_in_string(test_file)

        assert is_valid is True
        assert bad_lines == []

    def test_noqa_inside_fstring_is_invalid(self, tmp_path: Path) -> None:
        """# noqa inside an f-string is invalid (the bug we're preventing)."""
        test_file = tmp_path / "invalid_fstring.py"
        test_file.write_text('x = f"SELECT * FROM {table}  # noqa: ADR-0087"')

        is_valid, bad_lines = validate_noqa_not_in_string(test_file)

        assert is_valid is False
        assert 1 in bad_lines

    def test_noqa_inside_regular_string_is_invalid(self, tmp_path: Path) -> None:
        """# noqa inside a regular string is invalid."""
        test_file = tmp_path / "invalid_string.py"
        test_file.write_text('x = "some text # noqa: ADR-0019 more text"')

        is_valid, bad_lines = validate_noqa_not_in_string(test_file)

        assert is_valid is False
        assert 1 in bad_lines

    def test_noqa_inside_single_quoted_string_is_invalid(self, tmp_path: Path) -> None:
        """# noqa inside a single-quoted string is invalid."""
        test_file = tmp_path / "invalid_single_quote.py"
        test_file.write_text("x = 'some text # noqa: ADR-0019 more text'")

        is_valid, bad_lines = validate_noqa_not_in_string(test_file)

        assert is_valid is False
        assert 1 in bad_lines

    def test_multiple_lines_with_issues(self, tmp_path: Path) -> None:
        """Multiple lines with noqa-in-string should all be reported."""
        test_file = tmp_path / "multiple_issues.py"
        test_file.write_text(
            'line1 = "ok"  # noqa: ADR-0019\n'
            'line2 = f"bad # noqa: ADR-0087"\n'
            'line3 = "also bad # noqa: ADR-0019"\n'
            'line4 = "ok"  # noqa: ADR-0019\n'
        )

        is_valid, bad_lines = validate_noqa_not_in_string(test_file)

        assert is_valid is False
        assert 2 in bad_lines
        assert 3 in bad_lines
        assert 1 not in bad_lines
        assert 4 not in bad_lines

    def test_no_noqa_in_file_is_valid(self, tmp_path: Path) -> None:
        """File without any noqa comments is valid."""
        test_file = tmp_path / "no_noqa.py"
        test_file.write_text('x = 1\ny = "hello"\nz = f"world"')

        is_valid, bad_lines = validate_noqa_not_in_string(test_file)

        assert is_valid is True
        assert bad_lines == []


class TestValidateModifiedFiles:
    """Tests for validate_modified_files function."""

    def test_all_valid_files(self, tmp_path: Path) -> None:
        """All valid files should pass validation."""
        file1 = tmp_path / "valid1.py"
        file1.write_text("x = 1  # noqa: ADR-0019")

        file2 = tmp_path / "valid2.py"
        file2.write_text('y = "text"  # noqa: ADR-0019')

        all_valid, errors = validate_modified_files([file1, file2])

        assert all_valid is True
        assert errors == []

    def test_syntax_error_detected(self, tmp_path: Path) -> None:
        """Syntax error should be detected and reported."""
        valid_file = tmp_path / "valid.py"
        valid_file.write_text("x = 1")

        invalid_file = tmp_path / "invalid.py"
        invalid_file.write_text("y = 1 +  # broken")

        all_valid, errors = validate_modified_files([valid_file, invalid_file])

        assert all_valid is False
        assert len(errors) == 1
        assert "SYNTAX ERROR" in errors[0]
        assert "invalid.py" in errors[0]

    def test_noqa_in_string_detected(self, tmp_path: Path) -> None:
        """noqa-in-string should be detected and reported."""
        valid_file = tmp_path / "valid.py"
        valid_file.write_text("x = 1  # noqa: ADR-0019")

        invalid_file = tmp_path / "invalid.py"
        invalid_file.write_text('y = f"bad # noqa: ADR-0087"')

        all_valid, errors = validate_modified_files([valid_file, invalid_file])

        assert all_valid is False
        assert len(errors) == 1
        assert "NOQA-IN-STRING" in errors[0]
        assert "invalid.py" in errors[0]

    def test_multiple_errors_all_reported(self, tmp_path: Path) -> None:
        """Multiple errors should all be reported."""
        syntax_error = tmp_path / "syntax_error.py"
        syntax_error.write_text("x = 1 +  # broken")

        noqa_in_string = tmp_path / "noqa_in_string.py"
        noqa_in_string.write_text('y = f"bad # noqa: ADR-0087"')

        all_valid, errors = validate_modified_files([syntax_error, noqa_in_string])

        assert all_valid is False
        assert len(errors) == 2

    def test_empty_file_list(self) -> None:
        """Empty file list should pass validation."""
        all_valid, errors = validate_modified_files([])

        assert all_valid is True
        assert errors == []


class TestRealWorldPatterns:
    """Test patterns that caused the original noqa-inside-SQL bug."""

    def test_sql_fstring_with_noqa_at_end(self, tmp_path: Path) -> None:
        """SQL f-string with noqa at END of line (after string) is valid."""
        test_file = tmp_path / "sql_valid.py"
        test_file.write_text(
            'query = f"SELECT * FROM {table_name}"  # noqa: ADR-0087\n'
        )

        is_valid, _ = validate_noqa_not_in_string(test_file)

        assert is_valid is True

    def test_sql_fstring_with_noqa_inside(self, tmp_path: Path) -> None:
        """SQL f-string with noqa INSIDE string is invalid (the bug)."""
        test_file = tmp_path / "sql_invalid.py"
        test_file.write_text(
            'query = f"SELECT * FROM {table_name}  # noqa: ADR-0087"\n'
        )

        is_valid, bad_lines = validate_noqa_not_in_string(test_file)

        assert is_valid is False
        assert 1 in bad_lines

    def test_multiline_sql_with_noqa(self, tmp_path: Path) -> None:
        """Multi-line SQL with noqa at end of statement is valid."""
        test_file = tmp_path / "multiline_sql.py"
        test_file.write_text(
            "query = (\n"
            '    f"SELECT * FROM {table}"\n'
            '    f" WHERE id = {id}"\n'
            ")  # noqa: ADR-0087\n"
        )

        # Should pass syntax check
        is_valid_syntax, _ = validate_syntax(test_file)
        assert is_valid_syntax is True

        # Should pass noqa-in-string check
        is_valid_noqa, _ = validate_noqa_not_in_string(test_file)
        assert is_valid_noqa is True


class TestNewFixFunctions:
    """Tests for the 10 new ADR fix functions added in GMP-CI-2026-02."""

    def test_fix_lru_cache_maxsize_bare_decorator(self, tmp_path: Path) -> None:
        """@lru_cache without parens should get maxsize=128."""
        test_file = tmp_path / "lru_cache_bare.py"
        test_file.write_text(
            "from functools import lru_cache\n\n@lru_cache\ndef foo():\n    return 1\n"
        )

        result = fix_lru_cache_maxsize(test_file, dry_run=False)

        assert result is True
        content = test_file.read_text()
        assert "@lru_cache(maxsize=128)" in content
        assert "@lru_cache\n" not in content

    def test_fix_lru_cache_maxsize_empty_parens(self, tmp_path: Path) -> None:
        """@lru_cache() should get maxsize=128."""
        test_file = tmp_path / "lru_cache_empty.py"
        test_file.write_text(
            "from functools import lru_cache\n"
            "\n"
            "@lru_cache()\n"
            "def foo():\n"
            "    return 1\n"
        )

        result = fix_lru_cache_maxsize(test_file, dry_run=False)

        assert result is True
        content = test_file.read_text()
        assert "@lru_cache(maxsize=128)" in content

    def test_fix_lru_cache_maxsize_already_has_maxsize(self, tmp_path: Path) -> None:
        """@lru_cache(maxsize=64) should not be modified."""
        test_file = tmp_path / "lru_cache_has_maxsize.py"
        test_file.write_text(
            "from functools import lru_cache\n"
            "\n"
            "@lru_cache(maxsize=64)\n"
            "def foo():\n"
            "    return 1\n"
        )

        result = fix_lru_cache_maxsize(test_file, dry_run=False)

        assert result is False
        content = test_file.read_text()
        assert "@lru_cache(maxsize=64)" in content

    def test_fix_registry_pattern(self, tmp_path: Path) -> None:
        """_registry = {} should get noqa comment."""
        test_file = tmp_path / "registry.py"
        test_file.write_text(
            "_registry = {}\n\ndef register(name, obj):\n    _registry[name] = obj\n"
        )

        result = fix_registry_pattern(test_file, dry_run=False)

        assert result is True
        content = test_file.read_text()
        assert "# noqa: ADR-0022" in content

    def test_fix_resilience_mixin(self, tmp_path: Path) -> None:
        """@retry decorator should get noqa comment."""
        test_file = tmp_path / "retry_code.py"
        test_file.write_text(
            "from tenacity import retry\n"
            "\n"
            "@retry(stop=stop_after_attempt(3))\n"
            "def fetch_data():\n"
            "    return requests.get(url)\n"
        )

        result = fix_resilience_mixin(test_file, dry_run=False)

        assert result is True
        content = test_file.read_text()
        assert "# noqa: ADR-0024" in content

    def test_fix_pickle_usage_in_test(self, tmp_path: Path) -> None:
        """pickle usage in test files should get noqa comment."""
        test_file = tmp_path / "test_serialization.py"
        test_file.write_text(
            "import pickle\n\ndef test_pickle():\n    data = pickle.loads(serialized)\n"
        )

        result = fix_pickle_usage(test_file, dry_run=False)

        assert result is True
        content = test_file.read_text()
        assert "# noqa: ADR-0088" in content

    def test_fix_pickle_usage_no_pickle(self, tmp_path: Path) -> None:
        """Files without pickle should not be modified."""
        test_file = tmp_path / "no_pickle.py"
        test_file.write_text(
            "import json\n\ndef deserialize():\n    data = json.loads(serialized)\n"
        )

        result = fix_pickle_usage(test_file, dry_run=False)

        # Should NOT fix files without pickle
        assert result is False

    def test_fix_path_safety_internal_path(self, tmp_path: Path) -> None:
        """Path(__file__) should get noqa comment."""
        test_file = tmp_path / "paths.py"
        test_file.write_text(
            "from pathlib import Path\n\nROOT = Path(__file__).parent\n"
        )

        result = fix_path_safety(test_file, dry_run=False)

        assert result is True
        content = test_file.read_text()
        assert "# noqa: ADR-0001" in content

    def test_fix_websocket_pattern(self, tmp_path: Path) -> None:
        """WebSocket accept without disconnect handling should get noqa."""
        test_file = tmp_path / "ws_handler.py"
        test_file.write_text(
            "async def websocket_handler(websocket):\n"
            "    await websocket.accept()\n"
            "    data = await websocket.receive()\n"
        )

        result = fix_websocket_pattern(test_file, dry_run=False)

        assert result is True
        content = test_file.read_text()
        assert "# noqa: ADR-0031" in content

    def test_fix_typeddict_pydantic_in_converter(self, tmp_path: Path) -> None:
        """TypedDict in converter file with Pydantic should get noqa."""
        test_file = tmp_path / "schema_converter.py"
        test_file.write_text(
            "from typing import TypedDict\n"
            "from pydantic import BaseModel\n"
            "\n"
            "class InputDict(TypedDict):\n"
            "    name: str\n"
            "\n"
            "class OutputModel(BaseModel):\n"
            "    name: str\n"
        )

        result = fix_typeddict_pydantic(test_file, dry_run=False)

        assert result is True
        content = test_file.read_text()
        assert "# noqa: ADR-0016" in content

    def test_dry_run_does_not_modify(self, tmp_path: Path) -> None:
        """dry_run=True should not modify files."""
        test_file = tmp_path / "lru_dry.py"
        original_content = "@lru_cache\ndef foo(): pass\n"
        test_file.write_text(original_content)

        result = fix_lru_cache_maxsize(test_file, dry_run=True)

        assert result is True  # Would fix
        assert test_file.read_text() == original_content  # Not modified
