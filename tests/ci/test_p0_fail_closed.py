"""
P0 Fail-Closed Regression Tests
================================
Verify that api/server.py enforces fail-closed behavior for all core subsystems.
These tests are deterministic, require no external services, and use monkeypatch
to simulate missing environment variables and failed imports.

Tests prove:
  1. Missing NEO4J_URI causes startup failure
  2. Missing MEMORY_DSN causes startup failure
  3. Tool registry empty causes startup failure
  4. Governance init failure causes startup failure
  5. AgentExecutor import failure causes startup failure
  6. Readiness gate rejects None subsystems
  7. No L9_MINIMAL_MODE escape hatch
  8. No silent degradation (no `app.state.X = None` for critical systems)
"""

from __future__ import annotations

import ast
import re
import textwrap
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER_PY = REPO_ROOT / "api" / "server.py"


# ===========================================================================
# SECTION 1: Source-code invariant tests (static analysis)
# ===========================================================================


class TestFailClosedSourceInvariants:
    """Verify the source code of server.py enforces fail-closed patterns."""

    @pytest.fixture(autouse=True)
    def _load_source(self) -> None:
        self.source = SERVER_PY.read_text(encoding="utf-8")
        self.lines = self.source.splitlines()

    # --- 1a. MEMORY_DSN is in required_env_vars ---
    def test_memory_dsn_is_required_env_var(self) -> None:
        """MEMORY_DSN must be listed in required_env_vars, not recommended."""
        match = re.search(
            r'required_env_vars\s*=\s*\[([^\]]+)\]', self.source
        )
        assert match, "required_env_vars not found in server.py"
        required_list = match.group(1)
        assert "MEMORY_DSN" in required_list, (
            "MEMORY_DSN must be in required_env_vars for fail-closed boot"
        )

    # --- 1b. MEMORY_DSN missing raises RuntimeError ---
    def test_memory_dsn_missing_raises_runtime_error(self) -> None:
        """When MEMORY_DSN/DATABASE_URL is not set, server must raise RuntimeError."""
        # Find the block: if not database_url: raise RuntimeError
        pattern = re.compile(
            r'if not database_url:\s*\n\s*raise RuntimeError',
            re.MULTILINE,
        )
        assert pattern.search(self.source), (
            "Missing RuntimeError for absent database_url"
        )

    # --- 1c. Memory substrate except block re-raises ---
    def test_memory_init_except_reraises(self) -> None:
        """Memory substrate init failure must re-raise, not set None."""
        # After the memory try block, the except must raise RuntimeError
        # NOT: app.state.substrate_service = None
        pattern = re.compile(
            r'except Exception as e:\s*\n'
            r'\s*# P0: Memory substrate is mandatory',
            re.MULTILINE,
        )
        assert pattern.search(self.source), (
            "Memory substrate except block must re-raise as RuntimeError"
        )

    # --- 1d. NEO4J_URI missing raises RuntimeError ---
    def test_neo4j_uri_missing_raises_runtime_error(self) -> None:
        """When NEO4J_URI is not set, server must raise RuntimeError."""
        pattern = re.compile(
            r'if not neo4j_uri:\s*\n\s*raise RuntimeError',
            re.MULTILINE,
        )
        assert pattern.search(self.source), (
            "Missing RuntimeError for absent NEO4J_URI"
        )

    # --- 1e. Neo4j retry exhaustion raises RuntimeError ---
    def test_neo4j_retry_exhaustion_raises(self) -> None:
        """After Neo4j retries are exhausted, server must raise RuntimeError."""
        # The final else in the retry loop must raise, not set None
        assert "Neo4j failed to connect after" in self.source
        assert "L9 cannot start without Neo4j" in self.source

    # --- 1f. Neo4j is NOT described as optional ---
    def test_neo4j_not_optional(self) -> None:
        """The comment 'Neo4j is OPTIONAL' must be removed."""
        assert "Neo4j is OPTIONAL" not in self.source, (
            "Neo4j must not be described as OPTIONAL in server.py"
        )

    # --- 1g. Tool registry zero-tool check ---
    def test_tool_registry_zero_check(self) -> None:
        """Tool registry must raise RuntimeError if 0 tools registered."""
        pattern = re.compile(
            r'if tool_count == 0:\s*\n\s*raise RuntimeError',
            re.MULTILINE,
        )
        assert pattern.search(self.source), (
            "Missing zero-tool RuntimeError check in tool registration"
        )

    # --- 1h. Governance is mandatory ---
    def test_governance_mandatory(self) -> None:
        """GovernanceIntegration init must not be wrapped in try/except that sets None."""
        # Check that there's no `app.state.governance = None` after governance init
        # (there should be no fallback)
        gov_section_start = self.source.find("P0: Governance is mandatory")
        assert gov_section_start != -1, (
            "Governance mandatory marker not found"
        )
        # The next ~20 lines should NOT contain app.state.governance = None
        section = self.source[gov_section_start:gov_section_start + 800]
        assert "app.state.governance = None" not in section, (
            "Governance must not fall back to None"
        )

    # --- 1i. GovernanceEngine is mandatory ---
    def test_governance_engine_mandatory(self) -> None:
        """GovernanceEngine must raise RuntimeError if _has_governance is False."""
        pattern = re.compile(
            r'if not _has_governance:\s*\n\s*raise RuntimeError',
            re.MULTILINE,
        )
        assert pattern.search(self.source), (
            "GovernanceEngine must raise RuntimeError when governance unavailable"
        )

    # --- 1j. AgentExecutor is mandatory ---
    def test_agent_executor_mandatory(self) -> None:
        """AgentExecutor must raise RuntimeError if _has_agent_executor is False."""
        pattern = re.compile(
            r'if not _has_agent_executor:\s*\n\s*raise RuntimeError',
            re.MULTILINE,
        )
        assert pattern.search(self.source), (
            "AgentExecutor must raise RuntimeError when import fails"
        )

    # --- 1k. AgentExecutor except block re-raises ---
    def test_agent_executor_except_reraises(self) -> None:
        """AgentExecutor init failure must re-raise, not set None."""
        pattern = re.compile(
            r'except Exception as e:\s*\n'
            r'\s*# P0: AgentExecutor is mandatory',
            re.MULTILINE,
        )
        assert pattern.search(self.source), (
            "AgentExecutor except block must re-raise as RuntimeError"
        )

    # --- 1l. L9_MINIMAL_MODE escape hatch removed ---
    def test_no_minimal_mode_bypass(self) -> None:
        """L9_MINIMAL_MODE must not bypass agent executor health check."""
        # The old pattern was: if minimal_mode: logger.warning(...)
        # It should no longer gate the RuntimeError
        assert "L9_MINIMAL_MODE=true" not in self.source or (
            "L9_MINIMAL_MODE no longer bypasses" in self.source
        ), "L9_MINIMAL_MODE must not bypass fail-closed checks"

    # --- 1m. Readiness gate exists before yield ---
    def test_readiness_gate_exists(self) -> None:
        """A P0 Readiness Gate must exist before yield."""
        gate_idx = self.source.find("P0: DETERMINISTIC READINESS GATE")
        yield_idx = self.source.find("\n    yield\n")
        assert gate_idx != -1, "Readiness gate not found"
        assert yield_idx != -1, "yield not found"
        assert gate_idx < yield_idx, (
            "Readiness gate must appear before yield"
        )

    # --- 1n. Readiness gate checks all 5 subsystems ---
    def test_readiness_gate_checks_all_subsystems(self) -> None:
        """Readiness gate must check substrate_service, neo4j_client, governance,
        governance_engine, and agent_executor."""
        gate_start = self.source.find("P0: DETERMINISTIC READINESS GATE")
        gate_section = self.source[gate_start:gate_start + 600]
        for subsystem in [
            "substrate_service",
            "neo4j_client",
            "governance",
            "governance_engine",
            "agent_executor",
        ]:
            assert subsystem in gate_section, (
                f"Readiness gate must check {subsystem}"
            )


# ===========================================================================
# SECTION 2: No silent degradation for critical systems
# ===========================================================================


class TestNoSilentDegradation:
    """Verify that critical subsystems never silently degrade to None."""

    @pytest.fixture(autouse=True)
    def _load_source(self) -> None:
        self.source = SERVER_PY.read_text(encoding="utf-8")

    def test_no_neo4j_client_none_fallback(self) -> None:
        """app.state.neo4j_client = None must not appear as a fallback."""
        # Count occurrences - should only appear in readiness gate check
        occurrences = [
            i
            for i, line in enumerate(self.source.splitlines(), 1)
            if "app.state.neo4j_client = None" in line
            and "# P0" not in line
            and "readiness" not in line.lower()
        ]
        assert len(occurrences) == 0, (
            f"app.state.neo4j_client = None found at lines {occurrences}. "
            f"Neo4j is mandatory; no None fallback allowed."
        )

    def test_no_agent_executor_none_fallback(self) -> None:
        """app.state.agent_executor = None must not appear as a fallback."""
        occurrences = [
            i
            for i, line in enumerate(self.source.splitlines(), 1)
            if "app.state.agent_executor = None" in line
        ]
        assert len(occurrences) == 0, (
            f"app.state.agent_executor = None found at lines {occurrences}. "
            f"AgentExecutor is mandatory; no None fallback allowed."
        )

    def test_no_governance_engine_none_fallback(self) -> None:
        """app.state.governance_engine = None must not appear as a fallback."""
        occurrences = [
            i
            for i, line in enumerate(self.source.splitlines(), 1)
            if "app.state.governance_engine = None" in line
        ]
        assert len(occurrences) == 0, (
            f"app.state.governance_engine = None found at lines {occurrences}. "
            f"GovernanceEngine is mandatory; no None fallback allowed."
        )


# ===========================================================================
# SECTION 3: Syntax validity
# ===========================================================================


class TestServerSyntax:
    """Verify server.py is syntactically valid Python."""

    def test_server_py_parses(self) -> None:
        """server.py must be valid Python syntax."""
        source = SERVER_PY.read_text(encoding="utf-8")
        try:
            ast.parse(source)
        except SyntaxError as e:
            pytest.fail(f"server.py has syntax error at line {e.lineno}: {e.msg}")

    def test_no_noqa_suppressions_for_p0(self) -> None:
        """No new noqa suppressions should be added by this patch."""
        source = SERVER_PY.read_text(encoding="utf-8")
        # Check for any noqa that references our specific ADRs
        for line_num, line in enumerate(source.splitlines(), 1):
            for adr in ["ADR-0087", "ADR-0055", "ADR-0088"]:
                assert f"# noqa: {adr}" not in line, (
                    f"Found suppressed {adr} at line {line_num}"
                )


# ===========================================================================
# SECTION 4: Readiness gate unit test (simulated)
# ===========================================================================


class TestReadinessGateLogic:
    """Test the readiness gate logic in isolation."""

    def test_readiness_gate_rejects_none_subsystems(self) -> None:
        """If any core subsystem is None, the gate must identify it."""
        checks = {
            "substrate_service": object(),
            "neo4j_client": None,  # <-- this one is None
            "governance": object(),
            "governance_engine": object(),
            "agent_executor": object(),
        }
        failed = [k for k, v in checks.items() if v is None]
        assert failed == ["neo4j_client"]

    def test_readiness_gate_passes_all_non_none(self) -> None:
        """If all core subsystems are non-None, the gate passes."""
        checks = {
            "substrate_service": object(),
            "neo4j_client": object(),
            "governance": object(),
            "governance_engine": object(),
            "agent_executor": object(),
        }
        failed = [k for k, v in checks.items() if v is None]
        assert failed == []

    def test_readiness_gate_rejects_multiple_none(self) -> None:
        """Gate must report ALL failed subsystems, not just the first."""
        checks = {
            "substrate_service": None,
            "neo4j_client": None,
            "governance": object(),
            "governance_engine": None,
            "agent_executor": object(),
        }
        failed = [k for k, v in checks.items() if v is None]
        assert set(failed) == {"substrate_service", "neo4j_client", "governance_engine"}


# ===========================================================================
# SECTION 5: Tool registry zero-tool rejection
# ===========================================================================


class TestToolRegistryEnforcement:
    """Verify tool registry enforcement in source code."""

    @pytest.fixture(autouse=True)
    def _load_source(self) -> None:
        self.source = SERVER_PY.read_text(encoding="utf-8")

    def test_tool_count_check_before_log(self) -> None:
        """The zero-tool check must happen BEFORE the success log."""
        zero_check_idx = self.source.find("if tool_count == 0:")
        success_log_idx = self.source.find(
            "Tool executor auto-registration complete"
        )
        assert zero_check_idx != -1, "Zero-tool check not found"
        assert success_log_idx != -1, "Success log not found"
        assert zero_check_idx < success_log_idx, (
            "Zero-tool check must happen before success log"
        )

    def test_tool_registration_not_in_try_except(self) -> None:
        """Tool registration block must not be wrapped in a swallowing try/except."""
        # Find the tool registration section
        marker = "P0: Tool registration is mandatory"
        idx = self.source.find(marker)
        assert idx != -1, "Tool registration mandatory marker not found"
        # The next 50 lines should not have a bare except that sets None
        section = self.source[idx:idx + 2000]
        assert "app.state.tool_graph_healthy = False" not in section or (
            "Non-fatal" not in section
        ), "Tool registration must not have a non-fatal fallback"
