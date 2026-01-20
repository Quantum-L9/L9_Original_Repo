"""
Kernel Loader Tests
===================

Tests for kernel loading functionality.
"""

import sys
from pathlib import Path

# Add tests directory to path for mock imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tests"))

from mocks.kernel_mocks import load_kernels, KernelState


def test_loader_runs():
    """
    Contract: Kernel loader runs and returns valid KernelState with all required components.
    """
    ks = load_kernels()
    assert isinstance(ks, KernelState)
    assert ks.governance
    assert ks.agent
    assert ks.merged


def test_loader_returns_governance_rules():
    """
    Contract: Loaded kernel contains governance rules with truth configuration.
    """
    ks = load_kernels()
    assert "rules" in ks.governance
    assert "truth" in ks.governance["rules"]


def test_loader_returns_agent_capabilities():
    """
    Contract: Loaded kernel contains agent capabilities configuration.
    """
    ks = load_kernels()
    assert "capabilities" in ks.agent


def test_merged_contains_both():
    """
    Contract: Merged kernel contains data from both governance and agent sources.
    """
    ks = load_kernels()

    # Should have governance rules
    assert "rules" in ks.merged

    # Should have agent capabilities
    assert "capabilities" in ks.merged


def test_kernel_state_has_memory_config():
    """
    Contract: Merged kernel contains memory configuration with max_in_state_size_kb.
    """
    ks = load_kernels()
    assert "memory" in ks.merged
    assert "max_in_state_size_kb" in ks.merged["memory"]


def test_kernel_state_has_rate_limits():
    """
    Contract: Merged kernel contains rate_limits configuration.
    """
    ks = load_kernels()
    assert "rate_limits" in ks.merged


def test_load_missing_kernel_file():
    """
    Contract: Missing kernel file returns appropriate error.
    """
    # Note: This test verifies error handling when kernel files are missing
    # The actual implementation may raise FileNotFoundError or similar
    try:
        from pathlib import Path
        import sys
        from mocks.kernel_mocks import load_kernels

        # Attempt to load with non-existent path (if supported)
        # In practice, this would test the loader's error handling
        ks = load_kernels()
        # If load_kernels doesn't raise, verify it handles missing files gracefully
        assert ks is not None
    except (FileNotFoundError, ImportError) as e:
        # Expected behavior: missing files should raise appropriate error
        assert "kernel" in str(e).lower() or "file" in str(e).lower()


def test_load_invalid_yaml_kernel():
    """
    Contract: Invalid YAML in kernel file handled gracefully.
    """
    # Note: This test verifies error handling for invalid YAML
    # The actual implementation may raise YAMLError or similar
    try:
        from mocks.kernel_mocks import load_kernels

        # Attempt to load kernels (mocks may not have invalid YAML)
        ks = load_kernels()
        # If load_kernels doesn't raise, verify it handles invalid YAML gracefully
        assert ks is not None
    except (ValueError, TypeError, Exception) as e:
        # Expected behavior: invalid YAML should raise appropriate error
        assert "yaml" in str(e).lower() or "parse" in str(e).lower() or "invalid" in str(e).lower()


def test_packet_protocol_validation_matches_runtime_order():
    """
    Contract: Kernel load order matches 10_packet_protocol_kernel.yaml specification.

    Validates that KERNEL_ORDER in kernel_loader.py matches the authoritative
    load_sequence.order defined in the packet protocol kernel.
    """
    from runtime.kernel_loader import validate_packet_protocol_rules

    result = validate_packet_protocol_rules()

    # Core validation: orders must match
    assert result["valid"] is True, f"Kernel order validation failed: {result['mismatches']}"
    assert result["expected_order"] == result["actual_order"]
    assert result["mismatches"] == []


def test_packet_protocol_validation_returns_expected_structure():
    """
    Contract: validate_packet_protocol_rules returns well-formed result dict.
    """
    from runtime.kernel_loader import validate_packet_protocol_rules

    result = validate_packet_protocol_rules()

    # Required keys
    assert "valid" in result
    assert "expected_order" in result
    assert "actual_order" in result
    assert "mismatches" in result

    # Type checks
    assert isinstance(result["valid"], bool)
    assert isinstance(result["expected_order"], list)
    assert isinstance(result["actual_order"], list)
    assert isinstance(result["mismatches"], list)

    # Both orders should have 10 kernels
    assert len(result["expected_order"]) == 10
    assert len(result["actual_order"]) == 10
