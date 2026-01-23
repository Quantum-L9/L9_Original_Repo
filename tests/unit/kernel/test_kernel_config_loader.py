"""
Tests for runtime.kernel_config_loader
======================================

Comprehensive test suite for kernel configuration loading.

Test Coverage:
- ✅ Config loading from YAML
- ✅ Environment-specific overrides
- ✅ Validation (required fields, types, values)
- ✅ Feature flags (enable/disable config loading)
- ✅ Fallback to hard-coded config
- ✅ Error handling (missing file, invalid YAML)

Version: 1.0.0
Author: L9 Kernel Team
Related PR: #23 (builds on PR #22 DI/DIP foundation)
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from runtime.kernel_config_loader import (FALLBACK_CONFIG,
                                          apply_environment_overrides,
                                          get_environment, get_kernel_order,
                                          get_minimum_kernel_count,
                                          get_required_kernels,
                                          is_config_loading_enabled,
                                          load_kernel_config,
                                          should_use_env_overrides,
                                          validate_config)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def valid_config():
    """Valid kernel configuration."""
    return {
        "kernel_order": [
            "private/kernels/00_system/01_master_kernel.yaml",
            "private/kernels/00_system/02_identity_kernel.yaml",
        ],
        "required_kernels": {
            "master": "01_master_kernel",
            "identity": "02_identity_kernel",
        },
        "minimum_kernel_count": 2,
        "validation": {
            "enable_integrity_check": True,
            "strict_required_kernels": True,
        },
        "feature_flags": {
            "enable_config_loading": True,
            "enable_env_overrides": True,
        },
    }


@pytest.fixture
def config_with_env_overrides():
    """Config with environment-specific overrides."""
    return {
        "kernel_order": [
            "private/kernels/00_system/01_master_kernel.yaml",
            "private/kernels/00_system/02_identity_kernel.yaml",
        ],
        "required_kernels": {
            "master": "01_master_kernel",
            "identity": "02_identity_kernel",
        },
        "minimum_kernel_count": 2,
        "environments": {
            "dev": {
                "kernel_order": [
                    "private/kernels/00_system/01_master_kernel.yaml",
                ],
                "minimum_kernel_count": 1,
            },
            "test": {
                "kernel_order": [
                    "private/kernels/00_system/01_master_kernel.yaml",
                ],
                "minimum_kernel_count": 1,
            },
        },
    }


# =============================================================================
# Test: Config Loading
# =============================================================================


def test_load_kernel_config_success(valid_config, tmp_path):
    """Test successful config loading from YAML."""
    # Create temp config file
    config_file = tmp_path / "kernel_discovery.yaml"
    with open(config_file, "w") as f:
        yaml.dump(valid_config, f)

    # Load config
    with patch(
        "runtime.kernel_config_loader.get_config_path", return_value=config_file
    ):
        config = load_kernel_config()

    # Verify
    assert config["kernel_order"] == valid_config["kernel_order"]
    assert config["required_kernels"] == valid_config["required_kernels"]
    assert config["minimum_kernel_count"] == valid_config["minimum_kernel_count"]


def test_load_kernel_config_file_not_found():
    """Test fallback when config file not found."""
    with patch(
        "runtime.kernel_config_loader.get_config_path",
        return_value=Path("/nonexistent/path.yaml"),
    ):
        config = load_kernel_config()

    # Should fall back to FALLBACK_CONFIG
    assert config == FALLBACK_CONFIG


def test_load_kernel_config_invalid_yaml(tmp_path):
    """Test fallback when YAML is invalid."""
    # Create temp config file with invalid YAML
    config_file = tmp_path / "kernel_discovery.yaml"
    with open(config_file, "w") as f:
        f.write("invalid: yaml: content: [")

    # Load config
    with patch(
        "runtime.kernel_config_loader.get_config_path", return_value=config_file
    ):
        config = load_kernel_config()

    # Should fall back to FALLBACK_CONFIG
    assert config == FALLBACK_CONFIG


# =============================================================================
# Test: Environment Overrides
# =============================================================================


def test_apply_environment_overrides_dev(config_with_env_overrides):
    """Test applying dev environment overrides."""
    config = apply_environment_overrides(config_with_env_overrides, "dev")

    # Verify overrides applied
    assert len(config["kernel_order"]) == 1
    assert config["minimum_kernel_count"] == 1


def test_apply_environment_overrides_test(config_with_env_overrides):
    """Test applying test environment overrides."""
    config = apply_environment_overrides(config_with_env_overrides, "test")

    # Verify overrides applied
    assert len(config["kernel_order"]) == 1
    assert config["minimum_kernel_count"] == 1


def test_apply_environment_overrides_no_env(config_with_env_overrides):
    """Test no overrides when environment not found."""
    config = apply_environment_overrides(config_with_env_overrides, "nonexistent")

    # Verify no overrides applied
    assert len(config["kernel_order"]) == 2
    assert config["minimum_kernel_count"] == 2


def test_load_kernel_config_with_env_override(config_with_env_overrides, tmp_path):
    """Test loading config with environment override."""
    # Create temp config file
    config_file = tmp_path / "kernel_discovery.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config_with_env_overrides, f)

    # Load config for dev environment
    with patch(
        "runtime.kernel_config_loader.get_config_path", return_value=config_file
    ):
        config = load_kernel_config(env="dev")

    # Verify dev overrides applied
    assert len(config["kernel_order"]) == 1
    assert config["minimum_kernel_count"] == 1


# =============================================================================
# Test: Validation
# =============================================================================


def test_validate_config_success(valid_config):
    """Test validation of valid config."""
    errors = validate_config(valid_config)
    assert len(errors) == 0


def test_validate_config_missing_kernel_order():
    """Test validation fails when kernel_order missing."""
    config = {
        "required_kernels": {},
        "minimum_kernel_count": 1,
    }
    errors = validate_config(config)
    assert any("kernel_order" in error for error in errors)


def test_validate_config_missing_required_kernels():
    """Test validation fails when required_kernels missing."""
    config = {
        "kernel_order": [],
        "minimum_kernel_count": 1,
    }
    errors = validate_config(config)
    assert any("required_kernels" in error for error in errors)


def test_validate_config_missing_minimum_kernel_count():
    """Test validation fails when minimum_kernel_count missing."""
    config = {
        "kernel_order": [],
        "required_kernels": {},
    }
    errors = validate_config(config)
    assert any("minimum_kernel_count" in error for error in errors)


def test_validate_config_invalid_kernel_order_type():
    """Test validation fails when kernel_order is not a list."""
    config = {
        "kernel_order": "not a list",
        "required_kernels": {},
        "minimum_kernel_count": 1,
    }
    errors = validate_config(config)
    assert any("kernel_order must be a list" in error for error in errors)


def test_validate_config_empty_kernel_order():
    """Test validation fails when kernel_order is empty."""
    config = {
        "kernel_order": [],
        "required_kernels": {},
        "minimum_kernel_count": 1,
    }
    errors = validate_config(config)
    assert any("kernel_order cannot be empty" in error for error in errors)


def test_validate_config_invalid_minimum_kernel_count():
    """Test validation fails when minimum_kernel_count < 1."""
    config = {
        "kernel_order": ["kernel1.yaml"],
        "required_kernels": {},
        "minimum_kernel_count": 0,
    }
    errors = validate_config(config)
    assert any("minimum_kernel_count must be >= 1" in error for error in errors)


# =============================================================================
# Test: Feature Flags
# =============================================================================


def test_is_config_loading_enabled_true():
    """Test config loading enabled when feature flag is true."""
    config = {"feature_flags": {"enable_config_loading": True}}
    assert is_config_loading_enabled(config) is True


def test_is_config_loading_enabled_false():
    """Test config loading disabled when feature flag is false."""
    config = {"feature_flags": {"enable_config_loading": False}}
    assert is_config_loading_enabled(config) is False


def test_is_config_loading_enabled_default():
    """Test config loading enabled by default."""
    config = {}
    assert is_config_loading_enabled(config) is True


def test_should_use_env_overrides_true():
    """Test env overrides enabled when feature flag is true."""
    config = {"feature_flags": {"enable_env_overrides": True}}
    assert should_use_env_overrides(config) is True


def test_should_use_env_overrides_false():
    """Test env overrides disabled when feature flag is false."""
    config = {"feature_flags": {"enable_env_overrides": False}}
    assert should_use_env_overrides(config) is False


def test_load_kernel_config_disabled_feature_flag(valid_config, tmp_path):
    """Test fallback when config loading feature flag is disabled."""
    # Disable config loading
    valid_config["feature_flags"]["enable_config_loading"] = False

    # Create temp config file
    config_file = tmp_path / "kernel_discovery.yaml"
    with open(config_file, "w") as f:
        yaml.dump(valid_config, f)

    # Load config
    with patch(
        "runtime.kernel_config_loader.get_config_path", return_value=config_file
    ):
        config = load_kernel_config()

    # Should fall back to FALLBACK_CONFIG
    assert config == FALLBACK_CONFIG


# =============================================================================
# Test: Environment Detection
# =============================================================================


def test_get_environment_default():
    """Test default environment is production."""
    with patch.dict(os.environ, {}, clear=True):
        env = get_environment()
    assert env == "production"


def test_get_environment_from_env_var():
    """Test environment from L9_ENV variable."""
    with patch.dict(os.environ, {"L9_ENV": "dev"}):
        env = get_environment()
    assert env == "dev"


# =============================================================================
# Test: Convenience Functions
# =============================================================================


def test_get_kernel_order(valid_config, tmp_path):
    """Test get_kernel_order convenience function."""
    # Create temp config file
    config_file = tmp_path / "kernel_discovery.yaml"
    with open(config_file, "w") as f:
        yaml.dump(valid_config, f)

    # Get kernel order
    with patch(
        "runtime.kernel_config_loader.get_config_path", return_value=config_file
    ):
        kernel_order = get_kernel_order()

    assert kernel_order == valid_config["kernel_order"]


def test_get_required_kernels(valid_config, tmp_path):
    """Test get_required_kernels convenience function."""
    # Create temp config file
    config_file = tmp_path / "kernel_discovery.yaml"
    with open(config_file, "w") as f:
        yaml.dump(valid_config, f)

    # Get required kernels
    with patch(
        "runtime.kernel_config_loader.get_config_path", return_value=config_file
    ):
        required_kernels = get_required_kernels()

    assert required_kernels == valid_config["required_kernels"]


def test_get_minimum_kernel_count(valid_config, tmp_path):
    """Test get_minimum_kernel_count convenience function."""
    # Create temp config file
    config_file = tmp_path / "kernel_discovery.yaml"
    with open(config_file, "w") as f:
        yaml.dump(valid_config, f)

    # Get minimum kernel count
    with patch(
        "runtime.kernel_config_loader.get_config_path", return_value=config_file
    ):
        minimum_count = get_minimum_kernel_count()

    assert minimum_count == valid_config["minimum_kernel_count"]


# =============================================================================
# Test: Fallback Config
# =============================================================================


def test_fallback_config_structure():
    """Test FALLBACK_CONFIG has required structure."""
    assert "kernel_order" in FALLBACK_CONFIG
    assert "required_kernels" in FALLBACK_CONFIG
    assert "minimum_kernel_count" in FALLBACK_CONFIG
    assert isinstance(FALLBACK_CONFIG["kernel_order"], list)
    assert isinstance(FALLBACK_CONFIG["required_kernels"], dict)
    assert isinstance(FALLBACK_CONFIG["minimum_kernel_count"], int)


def test_fallback_config_validation():
    """Test FALLBACK_CONFIG passes validation."""
    errors = validate_config(FALLBACK_CONFIG)
    assert len(errors) == 0
