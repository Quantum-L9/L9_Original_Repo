"""
Unit Tests for DI Runtime Config Loader

Tests YAML-based configuration loading with environment variable interpolation.

Version: 1.0.0
Created: 2026-01-24
GMP: 116 (PR #52)
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Import config loader
from config.di_runtime_config import (
    DIConfigError,
    DIRuntimeConfigLoader,
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


@patch.dict(
    os.environ,
    {"DATABASE_URL": "postgresql://localhost/test", "OPENAI_API_KEY": "test-key"},
)
def test_load_config_caches_result(temp_config_file):
    """Test that load() caches result and returns same dict on subsequent calls."""
    loader = DIRuntimeConfigLoader(temp_config_file)

    config1 = loader.load()
    config2 = loader.load()

    assert config1 is config2


# ============================================================================
# Memory Substrate Config Tests
# ============================================================================


@patch.dict(
    os.environ,
    {"DATABASE_URL": "postgresql://localhost/test", "OPENAI_API_KEY": "test-key"},
)
def test_get_memory_substrate_config(temp_config_file):
    """Test that get_memory_substrate_config() returns flattened config."""
    loader = DIRuntimeConfigLoader(temp_config_file)
    config = loader.get_memory_substrate_config()

    assert config["database_url"] == "postgresql://localhost/test"
    assert config["db_pool_size"] == 10
    assert config["embedding_provider_type"] == "openai"
    assert config["embedding_model"] == "text-embedding-3-large"
    assert config["openai_api_key"] == "test-key"


def test_get_memory_substrate_config_with_defaults():
    """Test that get_memory_substrate_config() returns defaults when file missing."""
    missing_path = Path("/tmp/nonexistent_config.yaml")
    loader = DIRuntimeConfigLoader(missing_path)

    config = loader.get_memory_substrate_config()

    assert config["db_pool_size"] == 5
    assert config["db_max_overflow"] == 10
    assert config["embedding_provider_type"] == "openai"


# ============================================================================
# Feature Flags Tests
# ============================================================================


@patch.dict(
    os.environ,
    {"DATABASE_URL": "postgresql://localhost/test", "OPENAI_API_KEY": "test-key"},
)
def test_get_feature_flags(temp_config_file):
    """Test that get_feature_flags() returns feature flags section."""
    loader = DIRuntimeConfigLoader(temp_config_file)
    flags = loader.get_feature_flags()

    assert flags["enable_protocol_validation"] is True
    assert flags["enable_lazy_dag_init"] is False


def test_get_feature_flags_with_defaults():
    """Test that get_feature_flags() returns defaults when file missing."""
    missing_path = Path("/tmp/nonexistent_config.yaml")
    loader = DIRuntimeConfigLoader(missing_path)

    flags = loader.get_feature_flags()

    assert flags["enable_protocol_validation"] is True
    assert flags["enable_lazy_dag_init"] is False


# ============================================================================
# Singleton Tests
# ============================================================================


def test_get_runtime_config_loader_returns_singleton():
    """Test that get_runtime_config_loader() returns same instance."""
    loader1 = get_runtime_config_loader()
    loader2 = get_runtime_config_loader()

    assert loader1 is loader2


def test_reset_runtime_config_loader():
    """Test that reset_runtime_config_loader() clears singleton."""
    loader1 = get_runtime_config_loader()
    reset_runtime_config_loader()
    loader2 = get_runtime_config_loader()

    assert loader1 is not loader2


# ============================================================================
# Reload Tests
# ============================================================================


@patch.dict(
    os.environ,
    {"DATABASE_URL": "postgresql://localhost/test", "OPENAI_API_KEY": "test-key"},
)
def test_reload_clears_cache(temp_config_file):
    """Test that reload() clears cache and reloads config."""
    loader = DIRuntimeConfigLoader(temp_config_file)

    config1 = loader.load()
    assert loader._loaded

    config2 = loader.reload()
    assert loader._loaded
    # Should have reloaded (but same content)
    assert config1 is not config2
