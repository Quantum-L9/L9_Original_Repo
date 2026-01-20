"""
Tests for L9 Secrets Protocols
================================

Production-ready test suite for secrets management abstractions.

Version: 1.0.0
GMP: security-remediation-phase1
"""

import pytest

from core.abstractions.secrets_protocols import SecretsClient
from core.secrets.env_secrets_client import EnvSecretsClient


class TestEnvSecretsClient:
    """Test suite for EnvSecretsClient."""

    @pytest.mark.asyncio
    async def test_get_secret_from_env(self, monkeypatch):
        """Test retrieving a secret from environment variables."""
        monkeypatch.setenv("TEST_SECRET", "test_value")
        client = EnvSecretsClient()

        value = await client.get_secret("TEST_SECRET")
        assert value == "test_value"

    @pytest.mark.asyncio
    async def test_get_secret_not_found(self):
        """Test retrieving a non-existent secret."""
        client = EnvSecretsClient()

        value = await client.get_secret("NONEXISTENT_SECRET")
        assert value is None

    @pytest.mark.asyncio
    async def test_get_secret_caching(self, monkeypatch):
        """Test that secrets are cached after first retrieval."""
        monkeypatch.setenv("CACHED_SECRET", "cached_value")
        client = EnvSecretsClient()

        # First call should read from environment
        value1 = await client.get_secret("CACHED_SECRET")
        assert value1 == "cached_value"

        # Remove from environment
        monkeypatch.delenv("CACHED_SECRET")

        # Second call should still return cached value
        value2 = await client.get_secret("CACHED_SECRET")
        assert value2 == "cached_value"

    @pytest.mark.asyncio
    async def test_set_secret_not_supported(self):
        """Test that set_secret is not supported for environment variables."""
        client = EnvSecretsClient()

        result = await client.set_secret("TEST_KEY", "test_value")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_secret_not_supported(self):
        """Test that delete_secret is not supported for environment variables."""
        client = EnvSecretsClient()

        result = await client.delete_secret("TEST_KEY")
        assert result is False

    @pytest.mark.asyncio
    async def test_rotate_secret_not_supported(self):
        """Test that rotate_secret is not supported for environment variables."""
        client = EnvSecretsClient()

        result = await client.rotate_secret("TEST_KEY")
        assert result is False

    def test_protocol_compliance(self):
        """Test that EnvSecretsClient implements SecretsClient protocol."""
        client = EnvSecretsClient()
        assert isinstance(client, SecretsClient)
