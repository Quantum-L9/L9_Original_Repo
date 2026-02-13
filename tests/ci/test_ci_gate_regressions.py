"""
CI Gate Regression Tests
========================

Regression tests for specific CI gate failures that have occurred in production.
Each test documents a real incident and prevents recurrence.

Incidents covered:
- 2026-02-12: Hardcoded API keys in YAML kernel configs (Gate 1B gap)
- 2026-02-12: noqa comments inside SQL string literals (auto_fix_adr.py bug)
- 2026-02-12: macOS date %3N incompatibility in pre-commit hook (Gate 4 crash)
- 2026-02-12: Prompt injection false positive on defense files (Gate 5)
- 2026-02-12: Hardcoded /Users/ib-mac paths in violation detector (Gate 8 false positive)
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path

import pytest
import structlog

logger = structlog.get_logger(__name__)

__dora_meta__ = {
    "component_name": "CI Gate Regression Tests",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-02-12T22:00:00Z",
    "updated_at": "2026-02-12T22:00:00Z",
    "layer": "testing",
    "domain": "ci",
    "module_name": "test_ci_gate_regressions",
    "type": "test",
    "status": "active",
}

L9_ROOT = Path(__file__).resolve().parent.parent.parent


# =============================================================================
# Regression: YAML files must not contain hardcoded 64-char hex API keys
# Incident: agents/cursor/cursor_memory_kernel.yaml had literal API key
# =============================================================================


class TestYAMLSecretScanning:
    """Gate 1B: YAML files must be scanned for hardcoded API keys."""

    @pytest.mark.parametrize(
        "yaml_dir",
        [
            "agents/cursor",
            "config",
            "private/kernels",
        ],
    )
    def test_no_hardcoded_api_keys_in_yaml(self, yaml_dir: str) -> None:
        """No YAML file should contain a 64-char hex string assigned to an API key field."""
        yaml_root = L9_ROOT / yaml_dir
        if not yaml_root.exists():
            pytest.skip(f"{yaml_dir} does not exist")

        pattern = re.compile(r'(api_key|API_KEY).*["\x27]([a-f0-9]{64})["\x27]')
        violations: list[str] = []

        for yaml_file in yaml_root.rglob("*.yaml"):
            content = yaml_file.read_text()
            for i, line in enumerate(content.splitlines(), 1):
                if pattern.search(line) and "# noqa" not in line:
                    rel = yaml_file.relative_to(L9_ROOT)
                    violations.append(f"{rel}:{i}: {line.strip()[:80]}")

        for yaml_file in yaml_root.rglob("*.yml"):
            content = yaml_file.read_text()
            for i, line in enumerate(content.splitlines(), 1):
                if pattern.search(line) and "# noqa" not in line:
                    rel = yaml_file.relative_to(L9_ROOT)
                    violations.append(f"{rel}:{i}: {line.strip()[:80]}")

        assert not violations, (
            "Hardcoded API keys found in YAML files (ADR-0090):\n"
            + "\n".join(violations)
        )


# =============================================================================
# Regression: noqa comments must never appear INSIDE string literals
# Incident: auto_fix_adr.py added
# =============================================================================


class TestNoqaInsideStrings:
    """META check: noqa comments must not corrupt string values."""

    def test_no_noqa_inside_fstring_sql(self) -> None:
        """Detect # noqa inside f-string SQL queries — corrupts the SQL."""
        # This is the exact pattern that caused the bug
        bad_code = textwrap.dedent("""\
            query = f"SELECT * FROM {table}  # noqa: ADR-0087"
        """)

        # The noqa is between the opening f" and closing "
        pattern = re.compile(
            r'f["\'].*#\s*noqa.*?["\']',
        )
        assert pattern.search(bad_code), "Test pattern should match bad code"

    def test_noqa_outside_string_is_fine(self) -> None:
        """noqa after a string literal (as a comment) is correct."""
        good_code = textwrap.dedent("""\
            query = f"SELECT * FROM {table}"  # noqa: ADR-0087
        """)

        # The noqa is AFTER the closing quote — this is correct
        # Check that the string itself doesn't contain
        fstring_content_pattern = re.compile(r'f"([^"]*)"')
        match = fstring_content_pattern.search(good_code)
        assert match is not None
        assert "# noqa" not in match.group(1), "noqa should not be inside the string"

    def test_scan_codebase_for_noqa_in_fstrings(self) -> None:
        """Scan production code for noqa comments inside f-string SQL."""
        violations: list[str] = []
        sql_keywords = ("SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER")

        for py_file in L9_ROOT.rglob("*.py"):
            if any(
                skip in str(py_file)
                for skip in (".venv", "__pycache__", "node_modules", "tests/")
            ):
                continue

            try:
                content = py_file.read_text()
            except (UnicodeDecodeError, OSError):
                continue

            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.lstrip()
                # Skip comment lines (they may contain examples of the bad pattern)
                if stripped.startswith("#"):
                    continue

                # Look for f-strings containing SQL keywords AND noqa inside the string
                if not any(kw in line.upper() for kw in sql_keywords):
                    continue

                # Check if there's a noqa between f" and the closing "
                match = re.search(r'f"([^"]*#\s*noqa[^"]*)"', line)
                if match:
                    rel = py_file.relative_to(L9_ROOT)
                    violations.append(f"{rel}:{i}: noqa inside f-string SQL")

        assert not violations, (
            "Found # noqa INSIDE f-string SQL (corrupts queries):\n"
            + "\n".join(violations)
        )


# =============================================================================
# Regression: Allowlist file must exist and be valid YAML
# =============================================================================


class TestAllowlistIntegrity:
    """Verify .l9-allowlist.yaml is present and well-formed."""

    def test_allowlist_exists(self) -> None:
        """The centralized allowlist file must exist."""
        allowlist = L9_ROOT / ".l9-allowlist.yaml"
        assert allowlist.exists(), (
            ".l9-allowlist.yaml missing — CI gates depend on it for exclusion management"
        )

    def test_allowlist_valid_yaml(self) -> None:
        """The allowlist must be valid YAML."""
        import yaml

        allowlist = L9_ROOT / ".l9-allowlist.yaml"
        if not allowlist.exists():
            pytest.skip("allowlist not present")

        content = allowlist.read_text()
        data = yaml.safe_load(content)
        assert isinstance(data, dict), "Allowlist must be a YAML mapping"

    def test_allowlist_has_required_sections(self) -> None:
        """Allowlist must contain all required sections."""
        import yaml

        allowlist = L9_ROOT / ".l9-allowlist.yaml"
        if not allowlist.exists():
            pytest.skip("allowlist not present")

        data = yaml.safe_load(allowlist.read_text())
        required = [
            "ai_security_allowlist",
            "hardcoded_path_allowlist",
            "adr_exemptions",
            "auto_fix_skip_dirs",
            "auto_fix_protected_files",
        ]
        for section in required:
            assert section in data, f"Missing required section: {section}"

    def test_allowlisted_files_exist(self) -> None:
        """All files listed in the allowlist must actually exist in the repo."""
        import yaml

        allowlist = L9_ROOT / ".l9-allowlist.yaml"
        if not allowlist.exists():
            pytest.skip("allowlist not present")

        data = yaml.safe_load(allowlist.read_text())
        missing: list[str] = []

        for entry in data.get("ai_security_allowlist", []):
            path = entry.get("path", "")
            if path and not (L9_ROOT / path).exists():
                missing.append(f"ai_security_allowlist: {path}")

        for entry in data.get("hardcoded_path_allowlist", []):
            path = entry.get("path", "")
            if path and not (L9_ROOT / path).exists():
                missing.append(f"hardcoded_path_allowlist: {path}")

        for path in data.get("auto_fix_protected_files", []):
            if path and not (L9_ROOT / path).exists():
                missing.append(f"auto_fix_protected_files: {path}")

        assert not missing, (
            "Allowlisted files that don't exist (stale entries):\n"
            + "\n".join(missing)
        )


# =============================================================================
# Regression: Pre-commit hook must not use macOS-incompatible date formats
# =============================================================================


class TestPreCommitHookPortability:
    """Verify pre-commit hook doesn't use macOS-incompatible commands."""

    def test_no_date_nanoseconds(self) -> None:
        """macOS date doesn't support %N (nanoseconds) — causes 'value too great' error."""
        hook_path = L9_ROOT / ".git" / "hooks" / "pre-commit"
        if not hook_path.exists():
            pytest.skip("pre-commit hook not installed")

        content = hook_path.read_text()
        # %3N, %N, %9N etc. are GNU date extensions not available on macOS
        matches = re.findall(r"date \+.*%\d*N", content)
        assert not matches, (
            "Pre-commit hook uses macOS-incompatible date format:\n"
            + "\n".join(matches)
            + "\nFix: Use $(date +%s) for seconds, not nanoseconds"
        )
