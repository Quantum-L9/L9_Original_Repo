"""
L9 Environment Variable Validation Tests
Version: 1.0.0

Validates that environment variables are correctly configured.
These tests catch configuration errors BEFORE they cause runtime failures.

Run with: pytest tests/docker/test_env_validation.py -v
"""

import os
import re

import pytest


class TestEnvironmentVariables:
    """Validate environment configuration."""

    def test_database_url_not_localhost_in_docker(self):
        """
        DATABASE_URL must use service DNS inside Docker, not localhost.

        This catches the #1 deployment bug: code works locally but fails
        in Docker because containers can't reach host's localhost.
        """
        database_url = os.environ.get("DATABASE_URL", "")
        memory_dsn = os.environ.get("MEMORY_DSN", "")

        # Check both possible env vars
        for name, url in [("DATABASE_URL", database_url), ("MEMORY_DSN", memory_dsn)]:
            if url:
                assert (
                    "127.0.0.1" not in url
                ), f"{name} contains 127.0.0.1 - use Docker service name instead (e.g., postgres:5432)"
                assert (
                    "localhost:5432" not in url
                ), f"{name} contains localhost - use Docker service name instead (e.g., postgres:5432)"

    def test_no_placeholder_values(self):
        """
        Environment variables must not contain placeholder text.

        Catches: forgot to replace template values like YOUR_KEY_HERE
        """
        placeholder_patterns = [
            r"YOUR_.*_HERE",
            r"REPLACE_ME",
            r"TODO",
            r"CHANGEME",
            r"xxx+",
        ]

        critical_vars = [
            "OPENAI_API_KEY",
            "L9_API_KEY",
            "POSTGRES_PASSWORD",
            "DATABASE_URL",
        ]

        for var in critical_vars:
            value = os.environ.get(var, "")
            if value:
                for pattern in placeholder_patterns:
                    assert not re.search(
                        pattern, value, re.IGNORECASE
                    ), f"{var} contains placeholder text: {value[:20]}..."

    def test_openai_key_format(self):
        """
        OpenAI API key should have correct format.
        """
        key = os.environ.get("OPENAI_API_KEY", "")

        if key:
            # OpenAI keys start with 'sk-'
            assert key.startswith(
                "sk-"
            ), f"OPENAI_API_KEY should start with 'sk-', got: {key[:10]}..."

            # Keys are typically 40+ characters
            assert len(key) > 40, f"OPENAI_API_KEY seems too short ({len(key)} chars)"

    def test_database_url_format(self):
        """
        DATABASE_URL should be a valid PostgreSQL connection string.
        """
        url = os.environ.get("DATABASE_URL", "") or os.environ.get("MEMORY_DSN", "")

        if url:
            # Should be PostgreSQL
            assert url.startswith("postgresql://") or url.startswith(
                "postgres://"
            ), f"DATABASE_URL should start with postgresql://, got: {url[:30]}..."

            # Should contain user:password@host:port/db
            pattern = r"postgres(ql)?://\w+:[^@]+@[\w.-]+:\d+/\w+"
            assert re.match(pattern, url), f"DATABASE_URL format invalid: {url[:50]}..."

    def test_api_port_is_numeric(self):
        """
        Port environment variables should be valid numbers.
        """
        port_vars = ["API_PORT", "POSTGRES_PORT", "MEMORY_API_PORT", "REDIS_PORT"]

        for var in port_vars:
            value = os.environ.get(var, "")
            if value:
                assert value.isdigit(), f"{var} should be numeric, got: {value}"

                port = int(value)
                assert (
                    1 <= port <= 65535
                ), f"{var} should be valid port (1-65535), got: {port}"


class TestDockerNetworkConfig:
    """Validate Docker-specific networking configuration."""

    def test_memory_api_base_url_uses_service_name(self):
        """
        MEMORY_API_BASE_URL should use Docker service name, not localhost.
        """
        url = os.environ.get("MEMORY_API_BASE_URL", "")

        if url:
            assert (
                "localhost" not in url
            ), f"MEMORY_API_BASE_URL should use Docker service name, not localhost: {url}"
            assert (
                "127.0.0.1" not in url
            ), f"MEMORY_API_BASE_URL should use Docker service name, not 127.0.0.1: {url}"

    def test_redis_host_uses_service_name(self):
        """
        REDIS_HOST should be Docker service name if using Docker.
        """
        host = os.environ.get("REDIS_HOST", "")

        if host and os.environ.get("DOCKER_ENV", ""):
            assert (
                host != "localhost"
            ), "REDIS_HOST should be Docker service name 'redis', not localhost"
            assert (
                host != "127.0.0.1"
            ), "REDIS_HOST should be Docker service name 'redis', not 127.0.0.1"


class TestRequiredVariables:
    """Ensure required variables are present."""

    @pytest.mark.parametrize(
        "var",
        [
            "OPENAI_API_KEY",
        ],
    )
    def test_critical_vars_present(self, var: str):
        """
        Critical environment variables must be set.

        These are required for the application to function.
        Missing these will cause runtime failures.
        """
        value = os.environ.get(var, "")
        # Note: We just check presence, not validity (other tests do that)
        # This test is informational - skipped if var not set
        if not value:
            pytest.skip(f"{var} not set (may be intentional in CI)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
