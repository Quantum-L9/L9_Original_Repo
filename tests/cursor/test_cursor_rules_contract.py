"""Tests for the version-controlled L9 Cursor Project Rules contract."""

from __future__ import annotations

from pathlib import Path

from ci.validate_cursor_rules import validate_repository, validate_rule

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_l9_cursor_rules_package_is_valid() -> None:
    """The committed rules package must satisfy the CI contract."""
    report = validate_repository(REPOSITORY_ROOT)

    assert report.valid, report.to_dict()
    assert len(report.rule_results) == 4


def test_cursor_rule_rejects_legacy_suite5_patterns(tmp_path: Path) -> None:
    """Legacy Suite 5 deployment instructions must not re-enter Cursor rules."""
    rule_path = tmp_path / "legacy-rule.mdc"
    rule_path.write_text(
        "---\n"
        "description: legacy rule\n"
        "alwaysApply: false\n"
        "l9_component_id: CUR-RUL-999\n"
        "component_name: Legacy Rule\n"
        "version: 1.0.0\n"
        "status: active\n"
        "governance_level: high\n"
        "purpose: Test legacy rejection\n"
        "---\n\n"
        "Deploy Cursor Governance Suite 5 using .cursorrules.\n",
        encoding="utf-8",
    )

    result = validate_rule(rule_path, tmp_path)

    assert not result.valid
    assert any("deprecated legacy pattern" in error for error in result.errors)


def test_cursor_rule_rejects_always_apply_glob_conflict(tmp_path: Path) -> None:
    """Always-applied rules must not silently carry ignored glob scope."""
    rule_path = tmp_path / "invalid-scope.mdc"
    rule_path.write_text(
        "---\n"
        "description: invalid scope rule\n"
        "globs: '**/*.py'\n"
        "alwaysApply: true\n"
        "l9_component_id: CUR-RUL-998\n"
        "component_name: Invalid Scope Rule\n"
        "version: 1.0.0\n"
        "status: active\n"
        "governance_level: high\n"
        "purpose: Test scope validation\n"
        "---\n\n"
        "This is intentionally invalid.\n",
        encoding="utf-8",
    )

    result = validate_rule(rule_path, tmp_path)

    assert not result.valid
    assert any("must not define globs" in error for error in result.errors)
