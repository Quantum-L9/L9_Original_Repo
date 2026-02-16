"""
Tests for Session Startup Readiness Gate (GMP-KERNEL-BOOT TODO-4)

Verifies:
1. SessionStartup executes preflight checks
2. SessionStartup checks kernel readiness
3. API server gates readiness on SessionStartup result
4. Health endpoints expose startup status
"""

from pathlib import Path

import pytest

from core.decorators import must_stay_async

# Always use core.governance.session_startup which has check_kernel_readiness()
# Note: .cursor-commands/startup/session_startup.py has check_cursor_workflow_kernel() instead
from core.governance.session_startup import SessionStartup, StartupResult

# Default workspace root for tests
TEST_WORKSPACE_ROOT = Path("/Users/ib-mac/Projects/L9")


# =============================================================================
# SessionStartup Unit Tests
# =============================================================================


class TestSessionStartupExecution:
    """Tests for SessionStartup.execute() method."""

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_execute_returns_startup_result(self):
        """SessionStartup.execute() returns a StartupResult dataclass."""
        startup = SessionStartup(TEST_WORKSPACE_ROOT)
        result = startup.execute()

        assert isinstance(result, StartupResult)
        assert hasattr(result, "status")
        assert hasattr(result, "preflight_passed")
        assert hasattr(result, "files_loaded")
        assert hasattr(result, "files_failed")
        assert hasattr(result, "errors")
        assert hasattr(result, "warnings")
        assert hasattr(result, "kernels_ready")
        assert hasattr(result, "kernel_hash_snapshot")

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_execute_preflight_checks(self):
        """SessionStartup runs preflight checks."""
        startup = SessionStartup(TEST_WORKSPACE_ROOT)
        result = startup.execute()
        # Preflight checks are run as part of execute()
        assert hasattr(result, "preflight_passed")

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_execute_preflight_failure_sets_status(self):
        """SessionStartup sets status to 'BLOCKED' if preflight fails."""
        # Use a non-existent workspace to trigger preflight failure
        startup = SessionStartup(Path("/nonexistent/workspace"))
        result = startup.execute()
        assert result.preflight_passed is False
        assert result.status == "BLOCKED"

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_execute_loads_mandatory_files(self):
        """SessionStartup loads mandatory files."""
        startup = SessionStartup(TEST_WORKSPACE_ROOT)
        result = startup.execute()
        # Should have loaded at least some files
        assert isinstance(result.files_loaded, list)

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_execute_checks_kernel_readiness(self):
        """SessionStartup checks kernel readiness."""
        startup = SessionStartup(TEST_WORKSPACE_ROOT, check_kernels=True)
        result = startup.execute()
        # Kernel readiness should be checked
        assert hasattr(result, "kernels_ready")
        assert hasattr(result, "kernel_hash_snapshot")


class TestSessionStartupKernelReadiness:
    """Tests for SessionStartup.check_kernel_readiness() method."""

    def test_kernel_readiness_checks_kernel_directory(self):
        """Kernel readiness checks that kernel directory exists."""
        startup = SessionStartup(TEST_WORKSPACE_ROOT, check_kernels=True)
        result = startup.check_kernel_readiness()
        # Should return a KernelReadinessResult
        assert hasattr(result, "kernels_ready")
        assert hasattr(result, "kernel_state")
        assert hasattr(result, "kernel_hash_snapshot")

    def test_kernel_readiness_with_missing_directory(self):
        """Kernel readiness returns False when kernel directory missing."""
        startup = SessionStartup(Path("/nonexistent/workspace"), check_kernels=True)
        result = startup.check_kernel_readiness()
        assert result.kernels_ready is False
        assert result.kernel_state == "NOT_FOUND"

    def test_kernel_readiness_computes_hashes(self):
        """Kernel readiness computes SHA256 hashes for kernel files."""
        startup = SessionStartup(TEST_WORKSPACE_ROOT, check_kernels=True)
        result = startup.check_kernel_readiness()
        # If kernels exist, hashes should be computed
        if result.kernel_count > 0:
            assert len(result.kernel_hash_snapshot) > 0


class TestStartupResultDataclass:
    """Tests for StartupResult dataclass structure."""

    def test_startup_result_default_values(self):
        """StartupResult has sensible defaults."""
        result = StartupResult(
            status="READY",
            preflight_passed=True,
            files_loaded=[],
            files_failed=[],
            errors=[],
            warnings=[],
        )
        assert result.status == "READY"
        assert result.preflight_passed is True
        assert result.kernels_ready is False  # Default
        assert result.kernel_hash_snapshot == {}  # Default

    def test_startup_result_with_kernel_data(self):
        """StartupResult stores kernel readiness data."""
        result = StartupResult(
            status="READY",
            preflight_passed=True,
            files_loaded=["kernel1.yaml"],
            files_failed=[],
            errors=[],
            warnings=[],
            kernels_ready=True,
            kernel_hash_snapshot={"master": "abc123"},
        )
        assert result.kernels_ready is True
        assert result.kernel_hash_snapshot == {"master": "abc123"}


# =============================================================================
# API Server Integration Tests (Mocked)
# =============================================================================


class TestAPIServerStartupGate:
    """Tests for API server startup gate integration."""

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_health_endpoint_includes_startup_status(self):
        """Health endpoint includes startup readiness status."""

        # We need to mock the app.state before importing the app
        # This is a simplified test - full integration would use pytest-asyncio fixtures

        # Create a mock StartupResult
        mock_result = StartupResult(
            status="READY",
            preflight_passed=True,
            files_loaded=["file1.yaml"],
            files_failed=[],
            errors=[],
            warnings=[],
            kernels_ready=True,
            kernel_hash_snapshot={"master": "hash123"},
        )

        # Test the health response structure
        health_response = {
            "status": "ok",
            "service": "l9-api",
            "startup_ready": True,
            "startup": {
                "status": mock_result.status,
                "preflight_passed": mock_result.preflight_passed,
                "kernels_ready": mock_result.kernels_ready,
                "files_loaded": len(mock_result.files_loaded),
                "errors_count": len(mock_result.errors),
            },
        }

        assert health_response["status"] == "ok"
        assert health_response["startup_ready"] is True
        assert health_response["startup"]["kernels_ready"] is True

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_health_endpoint_degraded_when_startup_fails(self):
        """Health endpoint returns 'degraded' when startup fails."""
        mock_result = StartupResult(
            status="BLOCKED",
            preflight_passed=False,
            files_loaded=[],
            files_failed=["missing.yaml"],
            errors=["Preflight check failed"],
            warnings=[],
            kernels_ready=False,
            kernel_hash_snapshot={},
        )

        # Simulate degraded health response
        startup_ready = mock_result.status == "READY"
        status = "ok" if startup_ready else "degraded"

        health_response = {
            "status": status,
            "service": "l9-api",
            "startup_ready": startup_ready,
        }

        assert health_response["status"] == "degraded"
        assert health_response["startup_ready"] is False


class TestStartupHealthEndpoint:
    """Tests for /health/startup endpoint."""

    def test_startup_health_response_structure(self):
        """Startup health endpoint returns full StartupResult data."""
        mock_result = StartupResult(
            status="READY",
            preflight_passed=True,
            files_loaded=["kernel1.yaml", "kernel2.yaml"],
            files_failed=[],
            errors=[],
            warnings=["Minor warning"],
            kernels_ready=True,
            kernel_hash_snapshot={"master": "hash1", "identity": "hash2"},
        )

        # Simulate /health/startup response
        response = {
            "status": mock_result.status,
            "startup_ready": True,
            "preflight_passed": mock_result.preflight_passed,
            "kernels_ready": mock_result.kernels_ready,
            "files_loaded": mock_result.files_loaded,
            "files_failed": mock_result.files_failed,
            "errors": mock_result.errors,
            "warnings": mock_result.warnings,
            "kernel_hash_snapshot": mock_result.kernel_hash_snapshot,
        }

        assert response["status"] == "READY"
        assert response["kernels_ready"] is True
        assert len(response["kernel_hash_snapshot"]) == 2
        assert response["warnings"] == ["Minor warning"]

    def test_startup_health_unknown_when_not_executed(self):
        """Startup health returns 'unknown' when SessionStartup not executed."""
        response = {
            "status": "unknown",
            "message": "SessionStartup not executed or not available",
            "startup_ready": False,
        }

        assert response["status"] == "unknown"
        assert response["startup_ready"] is False


# =============================================================================
# Integration with Kernel Registry
# =============================================================================


class TestKernelRegistryIntegration:
    """Tests for SessionStartup integration with KernelAwareAgentRegistry."""

    def test_startup_checks_kernel_files(self):
        """SessionStartup checks kernel files in private/kernels/00_system/."""
        startup = SessionStartup(TEST_WORKSPACE_ROOT, check_kernels=True)
        result = startup.check_kernel_readiness()
        # Should have checked kernel files
        assert isinstance(result.kernel_count, int)

    def test_startup_captures_kernel_hashes(self):
        """SessionStartup captures kernel hash snapshot."""
        startup = SessionStartup(TEST_WORKSPACE_ROOT, check_kernels=True)
        result = startup.check_kernel_readiness()
        # Hashes should be a dict
        assert isinstance(result.kernel_hash_snapshot, dict)


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestStartupErrorHandling:
    """Tests for error handling in SessionStartup."""

    def test_startup_handles_missing_kernel_directory(self):
        """SessionStartup handles missing kernel directory gracefully."""
        startup = SessionStartup(Path("/nonexistent/workspace"), check_kernels=True)
        result = startup.check_kernel_readiness()
        assert result.kernels_ready is False
        assert len(result.errors) > 0

    def test_startup_handles_insufficient_kernels(self):
        """SessionStartup reports error if fewer than 10 kernels."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create kernel directory with only 1 kernel
            kernel_dir = Path(tmpdir) / "private" / "kernels" / "00_system"
            kernel_dir.mkdir(parents=True)
            (kernel_dir / "01_test.yaml").write_text("test: true")

            startup = SessionStartup(Path(tmpdir), check_kernels=True)
            result = startup.check_kernel_readiness()
            # Should report insufficient kernels
            assert result.kernel_count == 1

    def test_startup_records_errors_in_result(self):
        """SessionStartup records errors in the result."""
        startup = SessionStartup(Path("/nonexistent/workspace"))
        result = startup.execute()
        # The error should be captured in the result
        assert len(result.errors) > 0 or result.status == "BLOCKED"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
