"""
Unit Tests for DI Runtime Config Loader

Tests YAML-based configuration loading with environment variable interpolation.

Version: 1.0.0
Created: 2026-01-22
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

# Import config loader
from config.di_runtime_config import (
    DIRuntimeConfigLoader,
    DIConfigError,
    get_runtime_config_loader,
    reset_runtime_config_loader,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_config_file():
    """Create temporary YAML config file."""
    content = """
memory_substrate:
  database_url: "${DATABASE_URL}"
  db_pool_size: 10
  embedding_provider:
    type: "openai"
    model: "text-embedding-3-large"
    api_key: "${OPENAI_API_KEY}"

feature_flags:
  enable_protocol_validation: true
  enable_lazy_dag_init: false
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(content)
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    temp_path.unlink()


@pytest.fixture
def empty_config_file():
    """Create empty YAML config file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("")
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    temp_path.unlink()


@pytest.fixture(autouse=True)
def reset_loader():
    """Reset singleton loader before each test."""
    reset_runtime_config_loader()
    yield
    reset_runtime_config_loader()


# ============================================================================
# Initialization Tests
# ============================================================================


def test_loader_initialization_with_existing_file(temp_config_file):
    """Test that loader initializes with existing config file."""
    loader = DIRuntimeConfigLoader(temp_config_file)
    assert loader._config_path == temp_config_file
    assert not loader._loaded


def test_loader_initialization_with_missing_file():
    """Test that loader initializes even with missing config file."""
    missing_path = Path("/tmp/nonexistent_config.yaml")
    loader = DIRuntimeConfigLoader(missing_path)
    assert loader._config_path == missing_path
    assert not loader._loaded


# ============================================================================
# Config Loading Tests
# ============================================================================


@patch.dict(
    os.environ,
    {"DATABASE_URL": "postgresql://localhost/test", "OPENAI_API_KEY": "test-key"},
)
def test_load_config_with_env_vars(temp_config_file):
    """Test that load() interpolates environment variables."""
    loader = DIRuntimeConfigLoader(temp_config_file)
    config = loader.load()

    assert config["memory_substrate"]["database_url"] == "postgresql://localhost/test"
    assert config["memory_substrate"]["embedding_provider"]["api_key"] == "test-key"
    assert loader._loaded


@patch.dict(os.environ, {}, clear=True)
def test_load_config_fails_on_missing_env_var(temp_config_file):
    """Test that load() fails loudly when referenced env var is missing."""
    loader = DIRuntimeConfigLoader(temp_config_file)

    with pytest.raises(DIConfigError, match="Environment variable 'DATABASE_URL'"):
        loader.load()


def test_load_config_with_missing_file():
    """Test that load() returns defaults when file is missing."""
    missing_path = Path("/tmp/nonexistent_config.yaml")
    loader = DIRuntimeConfigLoader(missing_path)

    config = loader.load()

    assert "memory_substrate" in config
    assert "feature_flags" in config
    assert loader._loaded


def test_load_config_with_empty_file(empty_config_file):
    """Test that load() returns defaults when file is empty."""
    loader = DIRuntimeConfigLoader(empty_config_file)

    config = loader.load()

    assert "memory_substrate" in config
    assert "feature_flags" in config


def test_load_config_caches_result(temp_config_file):
    """Test that load() caches result and doesn't reload."""
    with patch.dict(
        os.environ,
        {"DATABASE_URL": "postgresql://localhost/test", "OPENAI_API_KEY": "test-key"},
    ):
        loader = DIRuntimeConfigLoader(temp_config_file)

        config1 = loader.load()
        config2 = loader.load()

        assert config1 is config2  # Same object
        assert loader._loaded


# ============================================================================
# Environment Variable Interpolation Tests
# ============================================================================


@patch.dict(os.environ, {"TEST_VAR": "test_value"})
def test_interpolate_env_vars_in_string():
    """Test that _interpolate_env_vars handles strings."""
    loader = DIRuntimeConfigLoader(Path("/tmp/test.yaml"))

    result = loader._interpolate_env_vars("${TEST_VAR}")
    assert result == "test_value"


@patch.dict(os.environ, {"TEST_VAR": "test_value"})
def test_interpolate_env_vars_in_dict():
    """Test that _interpolate_env_vars handles nested dicts."""
    loader = DIRuntimeConfigLoader(Path("/tmp/test.yaml"))

    config = {
        "key1": "${TEST_VAR}",
        "key2": {
            "nested": "${TEST_VAR}",
        },
    }

    result = loader._interpolate_env_vars(config)

    assert result["key1"] == "test_value"
    assert result["key2"]["nested"] == "test_value"


@patch.dict(os.environ, {"TEST_VAR": "test_value"})
def test_interpolate_env_vars_in_list():
    """Test that _interpolate_env_vars handles lists."""
    loader = DIRuntimeConfigLoader(Path("/tmp/test.yaml"))

    config = ["${TEST_VAR}", "static_value", {"key": "${TEST_VAR}"}]

    result = loader._interpolate_env_vars(config)

    assert result[0] == "test_value"
    assert result[1] == "static_value"
    assert result[2]["key"] == "test_value"


def test_interpolate_env_vars_preserves_non_var_strings():
    """Test that _interpolate_env_vars preserves strings that aren't env vars."""
    loader = DIRuntimeConfigLoader(Path("/tmp/test.yaml"))

    result = loader._interpolate_env_vars("regular_string")
    assert result == "regular_string"


@patch.dict(os.environ, {}, clear=True)
def test_interpolate_env_vars_fails_on_missing_var():
    """Test that _interpolate_env_vars fails when env var is missing."""
    loader = DIRuntimeConfigLoader(Path("/tmp/test.yaml"))

    with pytest.raises(DIConfigError, match="Environment variable 'MISSING_VAR'"):
        loader._interpolate_env_vars("${MISSING_VAR}")


# ============================================================================
# Config Extraction Tests
# ============================================================================


@patch.dict(
    os.environ,
    {"DATABASE_URL": "postgresql://localhost/test", "OPENAI_API_KEY": "test-key"},
)
def test_get_memory_substrate_config(temp_config_file):
    """Test that get_memory_substrate_config extracts flattened config."""
    loader = DIRuntimeConfigLoader(temp_config_file)

    config = loader.get_memory_substrate_config()

    assert config["database_url"] == "postgresql://localhost/test"
    assert config["db_pool_size"] == 10
    assert config["embedding_provider_type"] == "openai"
    assert config["embedding_model"] == "text-embedding-3-large"
    assert config["openai_api_key"] == "test-key"


@patch.dict(
    os.environ,
    {"DATABASE_URL": "postgresql://localhost/test", "OPENAI_API_KEY": "test-key"},
)
def test_get_embedding_config(temp_config_file):
    """Test that get_embedding_config extracts embedding section."""
    loader = DIRuntimeConfigLoader(temp_config_file)

    config = loader.get_embedding_config()

    assert config["type"] == "openai"
    assert config["model"] == "text-embedding-3-large"
    assert config["api_key"] == "test-key"


@patch.dict(
    os.environ,
    {"DATABASE_URL": "postgresql://localhost/test", "OPENAI_API_KEY": "test-key"},
)
def test_get_feature_flags(temp_config_file):
    """Test that get_feature_flags extracts feature flags."""
    loader = DIRuntimeConfigLoader(temp_config_file)

    flags = loader.get_feature_flags()

    assert flags["enable_protocol_validation"] is True
    assert flags["enable_lazy_dag_init"] is False


# ============================================================================
# Reload Tests
# ============================================================================


@patch.dict(
    os.environ,
    {"DATABASE_URL": "postgresql://localhost/test", "OPENAI_API_KEY": "test-key"},
)
def test_reload_reloads_config(temp_config_file):
    """Test that reload() reloads config from file."""
    loader = DIRuntimeConfigLoader(temp_config_file)

    config1 = loader.load()
    assert loader._loaded

    config2 = loader.reload()
    assert loader._loaded

    # Should be different objects (reloaded)
    assert config1 is not config2


# ============================================================================
# Singleton Tests
# ============================================================================


@patch.dict(
    os.environ,
    {"DATABASE_URL": "postgresql://localhost/test", "OPENAI_API_KEY": "test-key"},
)
def test_get_runtime_config_loader_returns_singleton(temp_config_file):
    """Test that get_runtime_config_loader returns singleton."""
    loader1 = get_runtime_config_loader(temp_config_file)
    loader2 = get_runtime_config_loader(temp_config_file)

    assert loader1 is loader2


def test_reset_runtime_config_loader_clears_singleton():
    """Test that reset_runtime_config_loader clears singleton."""
    loader1 = get_runtime_config_loader()
    reset_runtime_config_loader()
    loader2 = get_runtime_config_loader()

    assert loader1 is not loader2


# ============================================================================
# Default Config Tests
# ============================================================================


@patch.dict(
    os.environ, {"DATABASE_URL": "postgresql://prod/l9", "OPENAI_API_KEY": "prod-key"}
)
def test_default_config_uses_env_vars():
    """Test that _get_default_config uses environment variables."""
    loader = DIRuntimeConfigLoader(Path("/tmp/missing.yaml"))

    config = loader._get_default_config()

    assert config["memory_substrate"]["database_url"] == "postgresql://prod/l9"
    assert config["memory_substrate"]["embedding_provider"]["api_key"] == "prod-key"


@patch.dict(os.environ, {}, clear=True)
def test_default_config_provides_fallbacks():
    """Test that _get_default_config provides fallback values."""
    loader = DIRuntimeConfigLoader(Path("/tmp/missing.yaml"))

    config = loader._get_default_config()

    assert config["memory_substrate"]["database_url"] == "postgresql://localhost/l9"
    assert config["memory_substrate"]["db_pool_size"] == 5
    assert config["feature_flags"]["enable_protocol_validation"] is True


# ============================================================================
# DORA FOOTER
# ============================================================================
# tags: ["config", "dependency-injection", "testing", "unit-tests", "yaml"]
# keywords: ["config", "di", "loader", "runtime", "yaml"]
# last_modified: "2026-01-22T20:00:00Z"
# ============================================================================
