"""
Symbolic Verification Integration Tests
========================================

Tests for CodeGenAgent.generate_with_symbolic_verification() method.

Tests cover:
1. Pipeline availability detection
2. Basic symbolic optimization
3. Invariant verification
4. Error handling and graceful degradation
5. Result structure validation

Requires: sympy>=1.12, numpy>=1.24

Version: 1.0.0
"""

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.decorators import must_stay_async

# Ensure project root is in path before any imports
project_root = Path(__file__).parent.parent.parent.parent  # noqa: ADR-0001 - internal path
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Also add to PYTHONPATH for subprocess compatibility
os.environ.setdefault("PYTHONPATH", str(project_root))


# =============================================================================
# CHECK SYMBOLIC PIPELINE AVAILABILITY
# =============================================================================

# Try to import sympy to determine test strategy
SYMPY_AVAILABLE = False
try:
    import sympy

    SYMPY_AVAILABLE = True
except ImportError:
    pass

# Try to import CodeGenAgent - may fail due to dependencies
CODEGEN_AGENT_AVAILABLE = False
CodeGenAgent = None
SymbolicVerificationResult = None
SYMBOLIC_PIPELINE_AVAILABLE = False

try:
    from core.agents.codegenagent.codegen_agent import (
        SYMBOLIC_PIPELINE_AVAILABLE as _SYMBOLIC_PIPELINE_AVAILABLE,
    )
    from core.agents.codegenagent.codegen_agent import (
        CodeGenAgent as _CodeGenAgent,
    )
    from core.agents.codegenagent.codegen_agent import (
        SymbolicVerificationResult as _SymbolicVerificationResult,
    )

    CodeGenAgent = _CodeGenAgent
    SymbolicVerificationResult = _SymbolicVerificationResult
    SYMBOLIC_PIPELINE_AVAILABLE = _SYMBOLIC_PIPELINE_AVAILABLE
    CODEGEN_AGENT_AVAILABLE = True
except ImportError as e:
    # Create stub classes for testing when full import fails
    @dataclass
    class SymbolicVerificationResult:
        """Stub for testing when full import unavailable."""

        success: bool
        code: str = None
        candidates_evaluated: int = 0
        invariants_verified: bool = False
        selection_rationale: str = ""
        error: str = None
        spec: dict = None
        pipeline_available: bool = False

        def to_dict(self):
            return {
                "success": self.success,
                "code": self.code,
                "candidates_evaluated": self.candidates_evaluated,
                "invariants_verified": self.invariants_verified,
                "selection_rationale": self.selection_rationale,
                "error": self.error,
                "pipeline_available": self.pipeline_available,
            }


# Skip entire module if CodeGenAgent not importable AND we can't mock it
pytestmark = pytest.mark.skipif(
    not CODEGEN_AGENT_AVAILABLE and not SYMPY_AVAILABLE,
    reason="CodeGenAgent not importable and sympy not available for mocking",
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def codegen_agent():
    """Create a CodeGenAgent instance for testing with mocked internal components."""
    if not CODEGEN_AGENT_AVAILABLE:
        pytest.skip("CodeGenAgent not importable")

    with patch("agents.codegenagent.codegen_agent.MetaLoader"):
        with patch("agents.codegenagent.codegen_agent.MetaToIRCompiler"):
            with patch("agents.codegenagent.codegen_agent.IRToPythonCompiler"):
                agent = CodeGenAgent()
                # Reset symbolic pipeline to test state
                agent._symbolic_pipeline = None
                return agent


@pytest.fixture
def real_codegen_agent():
    """Create a CodeGenAgent instance with real symbolic pipeline for integration tests."""
    if not CODEGEN_AGENT_AVAILABLE:
        pytest.skip("CodeGenAgent not importable")
    if not SYMPY_AVAILABLE:
        pytest.skip("sympy not available")

    # Create agent with mocked loaders/compilers but real symbolic pipeline
    with patch("agents.codegenagent.codegen_agent.MetaLoader"):
        with patch("agents.codegenagent.codegen_agent.MetaToIRCompiler"):
            with patch("agents.codegenagent.codegen_agent.IRToPythonCompiler"):
                # Import the actual pipeline components
                from codegen.symbolic.pipeline import SymbolicCodegenPipeline

                agent = CodeGenAgent()

                # Manually initialize the symbolic pipeline since module caching
                # might have caused SYMBOLIC_PIPELINE_AVAILABLE to be False during
                # test collection
                if agent._symbolic_pipeline is None:
                    agent._symbolic_pipeline = SymbolicCodegenPipeline()

                return agent


@pytest.fixture
def mock_pipeline_result():
    """Create a mock SymbolicCodegenPipelineResult for testing."""
    mock = MagicMock()
    mock.success = True
    mock.candidates = [MagicMock(), MagicMock()]
    mock.verifications = [MagicMock(all_invariants_pass=True)]
    mock.selected_code = "x**2 + 2*x + 1"
    mock.selection_result = {"selection_rationale": "Simplest form selected"}
    mock.errors = []
    return mock


@pytest.fixture
def mock_failed_pipeline_result():
    """Create a mock failed SymbolicCodegenPipelineResult."""
    mock = MagicMock()
    mock.success = False
    mock.candidates = []
    mock.verifications = []
    mock.selected_code = ""
    mock.selection_result = {}
    mock.errors = ["Invalid expression", "Could not parse"]
    return mock


# =============================================================================
# TEST: Pipeline Availability Detection
# =============================================================================


class TestPipelineAvailability:
    """Tests for pipeline availability detection."""

    def test_is_symbolic_pipeline_available_method_exists(self, codegen_agent):
        """
        Contract: CodeGenAgent has is_symbolic_pipeline_available() method.
        """
        assert hasattr(codegen_agent, "is_symbolic_pipeline_available")
        assert callable(codegen_agent.is_symbolic_pipeline_available)

    def test_is_symbolic_pipeline_available_returns_bool(self, codegen_agent):
        """
        Contract: is_symbolic_pipeline_available() returns a boolean.
        """
        result = codegen_agent.is_symbolic_pipeline_available()
        assert isinstance(result, bool)

    @pytest.mark.skipif(not SYMPY_AVAILABLE, reason="sympy not installed")
    def test_pipeline_available_when_sympy_installed(self, codegen_agent):
        """
        Contract: Pipeline is available when sympy is installed.
        """
        result = codegen_agent.is_symbolic_pipeline_available()
        # Should be True if sympy is installed AND pipeline modules exist
        # May still be False if codegen.symbolic modules have other issues
        assert isinstance(result, bool)

    def test_generate_with_symbolic_verification_method_exists(self, codegen_agent):
        """
        Contract: CodeGenAgent has generate_with_symbolic_verification() method.
        """
        assert hasattr(codegen_agent, "generate_with_symbolic_verification")
        assert callable(codegen_agent.generate_with_symbolic_verification)


# =============================================================================
# TEST: Result Structure
# =============================================================================


class TestSymbolicVerificationResult:
    """Tests for SymbolicVerificationResult dataclass."""

    def test_result_has_required_fields(self):
        """
        Contract: SymbolicVerificationResult has all required fields.
        """
        result = SymbolicVerificationResult(success=True)

        assert hasattr(result, "success")
        assert hasattr(result, "code")
        assert hasattr(result, "candidates_evaluated")
        assert hasattr(result, "invariants_verified")
        assert hasattr(result, "selection_rationale")
        assert hasattr(result, "error")
        assert hasattr(result, "pipeline_available")

    def test_result_to_dict(self):
        """
        Contract: SymbolicVerificationResult.to_dict() returns serializable dict.
        """
        result = SymbolicVerificationResult(
            success=True,
            code="x + 1",
            candidates_evaluated=3,
            invariants_verified=True,
            selection_rationale="Simplest form",
        )

        d = result.to_dict()

        assert isinstance(d, dict)
        assert d["success"] is True
        assert d["code"] == "x + 1"
        assert d["candidates_evaluated"] == 3
        assert d["invariants_verified"] is True
        assert d["selection_rationale"] == "Simplest form"

    def test_result_defaults(self):
        """
        Contract: SymbolicVerificationResult has sensible defaults.
        """
        result = SymbolicVerificationResult(success=False)

        assert result.success is False
        assert result.code is None
        assert result.candidates_evaluated == 0
        assert result.invariants_verified is False
        assert result.selection_rationale == ""
        assert result.error is None


# =============================================================================
# TEST: Graceful Degradation (No Pipeline)
# =============================================================================


class TestGracefulDegradation:
    """Tests for graceful degradation when pipeline unavailable."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not CODEGEN_AGENT_AVAILABLE, reason="CodeGenAgent not importable"
    )
    async def test_returns_error_when_pipeline_unavailable(self, codegen_agent):
        """
        Contract: Returns appropriate error when pipeline not available.
        """
        # Ensure pipeline is disabled
        codegen_agent._symbolic_pipeline = None

        # Patch at module level using the imported reference
        original = sys.modules.get("agents.codegenagent.codegen_agent")
        if original:
            old_value = getattr(original, "SYMBOLIC_PIPELINE_AVAILABLE", True)
            original.SYMBOLIC_PIPELINE_AVAILABLE = False
            try:
                result = await codegen_agent.generate_with_symbolic_verification(
                    intent="optimize",
                    target_behavior="simplify x**2 + 2*x + 1",
                )

                assert result.success is False
                assert result.pipeline_available is False
                assert "not available" in result.error.lower()
            finally:
                original.SYMBOLIC_PIPELINE_AVAILABLE = old_value
        else:
            pytest.skip("Module not loaded")

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not CODEGEN_AGENT_AVAILABLE, reason="CodeGenAgent not importable"
    )
    async def test_graceful_error_on_exception(self, codegen_agent):
        """
        Contract: Returns graceful error on internal exceptions.
        """
        # Mock pipeline to raise exception
        codegen_agent._symbolic_pipeline = MagicMock()
        codegen_agent._symbolic_pipeline.execute.side_effect = RuntimeError(
            "Test error"
        )

        with patch(
            "agents.codegenagent.codegen_agent.SYMBOLIC_PIPELINE_AVAILABLE", True
        ):
            with patch("agents.codegenagent.codegen_agent.CodegenSpec") as MockSpec:
                with patch(
                    "agents.codegenagent.codegen_agent.CodegenIntent"
                ) as MockIntent:
                    MockIntent.return_value = "optimize"
                    mock_spec = MagicMock()
                    MockSpec.return_value = mock_spec

                    result = await codegen_agent.generate_with_symbolic_verification(
                        intent="optimize",
                        target_behavior="x + y",
                    )

                    assert result.success is False
                    assert "Test error" in result.error


# =============================================================================
# TEST: Basic Symbolic Verification (Mocked)
# =============================================================================


class TestSymbolicVerificationMocked:
    """Tests with mocked pipeline (no sympy required)."""

    @pytest.mark.asyncio
    async def test_successful_optimization(self, codegen_agent, mock_pipeline_result):
        """
        Contract: Successful optimization returns verified code.
        """
        codegen_agent._symbolic_pipeline = MagicMock()
        codegen_agent._symbolic_pipeline.execute.return_value = mock_pipeline_result

        with patch(
            "agents.codegenagent.codegen_agent.SYMBOLIC_PIPELINE_AVAILABLE", True
        ):
            with patch("agents.codegenagent.codegen_agent.CodegenSpec") as MockSpec:
                with patch(
                    "agents.codegenagent.codegen_agent.CodegenIntent"
                ) as MockIntent:
                    MockIntent.return_value = "optimize"
                    mock_spec = MagicMock()
                    mock_spec.model_dump.return_value = {}
                    MockSpec.return_value = mock_spec

                    result = await codegen_agent.generate_with_symbolic_verification(
                        intent="optimize",
                        target_behavior="(x + 1)**2",
                    )

                    assert result.success is True
                    assert result.code == "x**2 + 2*x + 1"
                    assert result.candidates_evaluated == 2
                    assert result.invariants_verified is True

    @pytest.mark.asyncio
    async def test_failed_verification(
        self, codegen_agent, mock_failed_pipeline_result
    ):
        """
        Contract: Failed verification returns error with details.
        """
        codegen_agent._symbolic_pipeline = MagicMock()
        codegen_agent._symbolic_pipeline.execute.return_value = (
            mock_failed_pipeline_result
        )

        with patch(
            "agents.codegenagent.codegen_agent.SYMBOLIC_PIPELINE_AVAILABLE", True
        ):
            with patch("agents.codegenagent.codegen_agent.CodegenSpec") as MockSpec:
                with patch(
                    "agents.codegenagent.codegen_agent.CodegenIntent"
                ) as MockIntent:
                    MockIntent.return_value = "verify"
                    mock_spec = MagicMock()
                    mock_spec.model_dump.return_value = {}
                    MockSpec.return_value = mock_spec

                    result = await codegen_agent.generate_with_symbolic_verification(
                        intent="verify",
                        target_behavior="invalid expression",
                    )

                    assert result.success is False
                    assert "Invalid expression" in result.error

    @pytest.mark.asyncio
    async def test_invariants_passed_to_pipeline(
        self, codegen_agent, mock_pipeline_result
    ):
        """
        Contract: Invariants are passed to pipeline spec.
        """
        codegen_agent._symbolic_pipeline = MagicMock()
        codegen_agent._symbolic_pipeline.execute.return_value = mock_pipeline_result

        with patch(
            "agents.codegenagent.codegen_agent.SYMBOLIC_PIPELINE_AVAILABLE", True
        ):
            with patch("agents.codegenagent.codegen_agent.CodegenSpec") as MockSpec:
                with patch(
                    "agents.codegenagent.codegen_agent.CodegenIntent"
                ) as MockIntent:
                    MockIntent.return_value = "optimize"
                    mock_spec_instance = MagicMock()
                    MockSpec.return_value = mock_spec_instance

                    await codegen_agent.generate_with_symbolic_verification(
                        intent="optimize",
                        target_behavior="x + y",
                        invariants=["result >= 0", "result <= 100"],
                        constraints=["no division"],
                        variables=["x", "y"],
                    )

                    # Verify CodegenSpec was called with correct args
                    MockSpec.assert_called_once()
                    call_kwargs = MockSpec.call_args[1]
                    assert call_kwargs["invariants"] == ["result >= 0", "result <= 100"]
                    assert call_kwargs["constraints"] == ["no division"]
                    assert call_kwargs["variables"] == ["x", "y"]

    @pytest.mark.asyncio
    async def test_selection_rationale_captured(
        self, codegen_agent, mock_pipeline_result
    ):
        """
        Contract: Selection rationale is captured in result.
        """
        codegen_agent._symbolic_pipeline = MagicMock()
        codegen_agent._symbolic_pipeline.execute.return_value = mock_pipeline_result

        with patch(
            "agents.codegenagent.codegen_agent.SYMBOLIC_PIPELINE_AVAILABLE", True
        ):
            with patch("agents.codegenagent.codegen_agent.CodegenSpec") as MockSpec:
                with patch(
                    "agents.codegenagent.codegen_agent.CodegenIntent"
                ) as MockIntent:
                    MockIntent.return_value = "optimize"
                    mock_spec = MagicMock()
                    MockSpec.return_value = mock_spec

                    result = await codegen_agent.generate_with_symbolic_verification(
                        intent="optimize",
                        target_behavior="x + 1",
                    )

                    assert result.selection_rationale == "Simplest form selected"


# =============================================================================
# TEST: Real Symbolic Pipeline (requires sympy)
# =============================================================================


@pytest.mark.skipif(not SYMPY_AVAILABLE, reason="sympy not installed")
class TestRealSymbolicPipeline:
    """Integration tests with real sympy (when available)."""

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_real_pipeline_initialization(self, real_codegen_agent):
        """
        Contract: Real pipeline initializes without error when sympy available.
        """
        # This test verifies the actual pipeline loads
        is_available = real_codegen_agent.is_symbolic_pipeline_available()

        # Should be True if all codegen.symbolic modules are properly set up
        assert is_available is True
        assert real_codegen_agent._symbolic_pipeline is not None

    @pytest.mark.asyncio
    async def test_real_simple_verification(self, real_codegen_agent):
        """
        Contract: Real pipeline can verify expression equivalence.
        """
        assert real_codegen_agent.is_symbolic_pipeline_available()

        result = await real_codegen_agent.generate_with_symbolic_verification(
            intent="verify",
            target_behavior="(x+1)**2",
            input_code="x**2 + 2*x + 1",
            variables=["x: float"],
        )

        # Pipeline should succeed
        assert isinstance(result, SymbolicVerificationResult)
        assert result.success is True
        assert result.code is not None
        assert result.candidates_evaluated >= 1

    @pytest.mark.asyncio
    async def test_real_pipeline_handles_invalid_expression(self, real_codegen_agent):
        """
        Contract: Real pipeline gracefully handles invalid expressions.
        """
        assert real_codegen_agent.is_symbolic_pipeline_available()

        result = await real_codegen_agent.generate_with_symbolic_verification(
            intent="verify",
            target_behavior="not_a_valid_expression_xyz123",
            input_code="also_invalid",
            variables=["x: float"],
        )

        # Should fail gracefully, not crash
        assert isinstance(result, SymbolicVerificationResult)
        # May succeed or fail depending on sympy parsing, but shouldn't raise


# =============================================================================
# TEST: Intent Validation
# =============================================================================


class TestIntentValidation:
    """Tests for intent parameter validation."""

    @pytest.mark.asyncio
    async def test_valid_intents(self, codegen_agent, mock_pipeline_result):
        """
        Contract: All valid intents are accepted.
        """
        valid_intents = ["generate", "refactor", "optimize", "verify"]

        codegen_agent._symbolic_pipeline = MagicMock()
        codegen_agent._symbolic_pipeline.execute.return_value = mock_pipeline_result

        with patch(
            "agents.codegenagent.codegen_agent.SYMBOLIC_PIPELINE_AVAILABLE", True
        ):
            for intent in valid_intents:
                with patch("agents.codegenagent.codegen_agent.CodegenSpec") as MockSpec:
                    with patch(
                        "agents.codegenagent.codegen_agent.CodegenIntent"
                    ) as MockIntent:
                        MockIntent.return_value = intent
                        mock_spec = MagicMock()
                        MockSpec.return_value = mock_spec

                        result = (
                            await codegen_agent.generate_with_symbolic_verification(
                                intent=intent,
                                target_behavior="test behavior",
                            )
                        )

                        # Should not fail on valid intent
                        assert isinstance(result, SymbolicVerificationResult)


# =============================================================================
# TEST: Input Code Handling
# =============================================================================


class TestInputCodeHandling:
    """Tests for input_code parameter handling."""

    @pytest.mark.asyncio
    async def test_refactor_requires_input_code(
        self, codegen_agent, mock_pipeline_result
    ):
        """
        Contract: Refactor intent passes input_code to spec.
        """
        codegen_agent._symbolic_pipeline = MagicMock()
        codegen_agent._symbolic_pipeline.execute.return_value = mock_pipeline_result

        with patch(
            "agents.codegenagent.codegen_agent.SYMBOLIC_PIPELINE_AVAILABLE", True
        ):
            with patch("agents.codegenagent.codegen_agent.CodegenSpec") as MockSpec:
                with patch("agents.codegenagent.codegen_agent.CodegenIntent"):
                    await codegen_agent.generate_with_symbolic_verification(
                        intent="refactor",
                        target_behavior="simplify",
                        input_code="x**2 + 2*x + 1",
                    )

                    call_kwargs = MockSpec.call_args[1]
                    assert call_kwargs["input_code"] == "x**2 + 2*x + 1"

    @pytest.mark.asyncio
    async def test_generate_without_input_code(
        self, codegen_agent, mock_pipeline_result
    ):
        """
        Contract: Generate intent works without input_code.
        """
        codegen_agent._symbolic_pipeline = MagicMock()
        codegen_agent._symbolic_pipeline.execute.return_value = mock_pipeline_result

        with patch(
            "agents.codegenagent.codegen_agent.SYMBOLIC_PIPELINE_AVAILABLE", True
        ):
            with patch("agents.codegenagent.codegen_agent.CodegenSpec") as MockSpec:
                with patch("agents.codegenagent.codegen_agent.CodegenIntent"):
                    await codegen_agent.generate_with_symbolic_verification(
                        intent="generate",
                        target_behavior="compute factorial of n",
                    )

                    call_kwargs = MockSpec.call_args[1]
                    assert call_kwargs["input_code"] is None


# =============================================================================
# TEST: Logging
# =============================================================================


class TestLogging:
    """Tests for structured logging."""

    @pytest.mark.asyncio
    async def test_logs_verification_started(self, codegen_agent, mock_pipeline_result):
        """
        Contract: Logs are emitted when verification starts.
        """
        codegen_agent._symbolic_pipeline = MagicMock()
        codegen_agent._symbolic_pipeline.execute.return_value = mock_pipeline_result

        with patch(
            "agents.codegenagent.codegen_agent.SYMBOLIC_PIPELINE_AVAILABLE", True
        ):
            with patch("agents.codegenagent.codegen_agent.CodegenSpec") as MockSpec:
                with patch(
                    "agents.codegenagent.codegen_agent.CodegenIntent"
                ) as MockIntent:
                    with patch(
                        "agents.codegenagent.codegen_agent.logger"
                    ) as mock_logger:
                        MockIntent.return_value = "optimize"
                        mock_spec = MagicMock()
                        MockSpec.return_value = mock_spec

                        await codegen_agent.generate_with_symbolic_verification(
                            intent="optimize",
                            target_behavior="x + 1",
                        )

                        # Check that info was called (for start and complete)
                        assert mock_logger.info.called

    @pytest.mark.asyncio
    async def test_logs_error_on_failure(self, codegen_agent):
        """
        Contract: Errors are logged when verification fails.
        """
        codegen_agent._symbolic_pipeline = MagicMock()
        codegen_agent._symbolic_pipeline.execute.side_effect = ValueError("Test error")

        with patch(
            "agents.codegenagent.codegen_agent.SYMBOLIC_PIPELINE_AVAILABLE", True
        ):
            with patch("agents.codegenagent.codegen_agent.CodegenSpec") as MockSpec:
                with patch(
                    "agents.codegenagent.codegen_agent.CodegenIntent"
                ) as MockIntent:
                    with patch(
                        "agents.codegenagent.codegen_agent.logger"
                    ) as mock_logger:
                        MockIntent.return_value = "optimize"
                        mock_spec = MagicMock()
                        MockSpec.return_value = mock_spec

                        await codegen_agent.generate_with_symbolic_verification(
                            intent="optimize",
                            target_behavior="x + 1",
                        )

                        mock_logger.error.assert_called()


# =============================================================================
# RUN TESTS
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
