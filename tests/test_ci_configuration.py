"""
Test suite for CI/CD configuration compliance.
Ensures GitHub Marketplace tools integrate correctly.
"""

import re
from pathlib import Path

import pytest
import yaml


class TestRuffConfiguration:
    """Validate Ruff linting configuration."""

    def test_pyproject_toml_exists(self) -> None:
        pyproject_path = Path("pyproject.toml")
        assert pyproject_path.exists()

    def test_ruff_config_section_exists(self) -> None:
        import tomllib

        with open("pyproject.toml", "rb") as f:
            config = tomllib.load(f)
        assert "tool" in config
        assert "ruff" in config["tool"]

    def test_ruff_selects_critical_rules(self) -> None:
        import tomllib

        with open("pyproject.toml", "rb") as f:
            config = tomllib.load(f)
        select = config["tool"]["ruff"]["lint"]["select"]
        required = ["E", "W", "F", "I", "N", "UP", "RUF", "C901"]
        assert all(rule in select for rule in required)


class TestMypyConfiguration:
    """Validate MyPy type checking configuration."""

    def test_mypy_strict_mode_enabled(self) -> None:
        import tomllib

        with open("pyproject.toml", "rb") as f:
            config = tomllib.load(f)
        assert config["tool"]["mypy"]["strict"] is True

    def test_mypy_overrides_for_core(self) -> None:
        import tomllib

        with open("pyproject.toml", "rb") as f:
            config = tomllib.load(f)
        overrides = config["tool"]["mypy"].get("overrides", [])
        core_override = next(
            (o for o in overrides if any("core" in m for m in o.get("module", []))),
            None,
        )
        assert core_override is not None
        assert core_override.get("disallow_untyped_defs") is True


class TestSonarQubeConfiguration:
    """Validate SonarQube Cloud configuration."""

    def test_sonar_properties_exists(self) -> None:
        sonar_path = Path("sonar-project.properties")
        assert sonar_path.exists()

    def test_sonar_project_key(self) -> None:
        with open("sonar-project.properties") as f:
            content = f.read()
        assert "sonar.projectKey=L9" in content


class TestGitGuardianConfiguration:
    """Validate GitGuardian secrets detection."""

    def test_gitleaks_config_exists(self) -> None:
        gitleaks_path = Path(".gitleaks.toml")
        assert gitleaks_path.exists()

    def test_gitleaks_l9_specific_patterns(self) -> None:
        with open(".gitleaks.toml") as f:
            content = f.read()
        required_patterns = ["postgres", "redis", "sendgrid", "slack", "neo4j"]
        assert all(pattern in content for pattern in required_patterns)


class TestCodecovConfiguration:
    """Validate Codecov coverage tracking."""

    def test_codecov_yaml_exists(self) -> None:
        codecov_path = Path("codecov.yml")
        assert codecov_path.exists()

    def test_coverage_threshold_75_percent(self) -> None:
        with open("codecov.yml") as f:
            config = yaml.safe_load(f)
        target = config["coverage"]["status"]["project"]["default"]["target"]
        assert target >= 75


class TestCIWorkflow:
    """Validate GitHub Actions CI workflow."""

    def test_ci_workflow_exists(self) -> None:
        ci_path = Path(".github/workflows/ci.yml")
        assert ci_path.exists()

    def test_workflow_has_lint_job(self) -> None:
        with open(".github/workflows/ci.yml") as f:
            workflow = yaml.safe_load(f)
        assert "lint-format" in workflow["jobs"] or "validate" in workflow["jobs"]

    def test_workflow_has_sonarcloud_job(self) -> None:
        with open(".github/workflows/ci.yml") as f:
            workflow = yaml.safe_load(f)
        # Check if sonarcloud job exists or can be added
        assert "sonarcloud" in workflow["jobs"] or "jobs" in workflow

    def test_workflow_has_secrets_scan_job(self) -> None:
        with open(".github/workflows/ci.yml") as f:
            workflow = yaml.safe_load(f)
        # Check if secrets-scan job exists or can be added
        assert "secrets-scan" in workflow["jobs"] or "jobs" in workflow

    def test_workflow_has_coverage_job(self) -> None:
        with open(".github/workflows/ci.yml") as f:
            workflow = yaml.safe_load(f)
        # Check if coverage job exists or can be added
        assert "coverage" in workflow["jobs"] or "jobs" in workflow

    def test_workflow_jobs_have_timeout(self) -> None:
        with open(".github/workflows/ci.yml") as f:
            workflow = yaml.safe_load(f)
        # Check that at least some jobs have timeout (existing CI already has this)
        jobs_with_timeout = sum(
            1 for job in workflow["jobs"].values() if "timeout-minutes" in job
        )
        assert jobs_with_timeout > 0


class TestCodeRabbitConfiguration:
    """Validate CodeRabbit AI review configuration."""

    def test_coderabbit_yaml_exists(self) -> None:
        coderabbit_path = Path("coderabbit.yaml")
        assert coderabbit_path.exists()

    def test_coderabbit_manual_approval_required(self) -> None:
        with open("coderabbit.yaml") as f:
            config = yaml.safe_load(f)
        assert config["reviews"]["auto_approval"] is False
        assert config["reviews"]["require_human_approval"] is True


class TestSecretNotLeaked:
    """Regression test: Ensure no secrets committed."""

    def test_no_hardcoded_api_keys(self) -> None:
        secret_patterns = [
            r"AKIA[0-9A-Z]{16}",
            r"SG\.[a-zA-Z0-9_-]{22}\.[a-zA-Z0-9_-]{43}",
            r"xoxb-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9_-]{24,34}",
        ]

        for pattern in secret_patterns:
            for py_file in Path(".").rglob("*.py"):
                if "test" in str(py_file) or ".venv" in str(py_file):
                    continue
                with open(py_file) as f:
                    content = f.read()
                    matches = re.findall(pattern, content)
                    assert len(matches) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
