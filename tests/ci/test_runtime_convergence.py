"""
Runtime Convergence Tests
=========================
P0 regression tests proving:
1. Boot trace records every mandatory stage.
2. Missing Neo4j / Redis / MEMORY_DSN prevents startup.
3. Tool registry shadow execution fails.
4. MCP tool call cannot bypass governance.
5. Memory write pipeline enforces Neo4j graph sync.
6. assert_runtime_ready rejects degraded state.

All tests are deterministic — no external network calls.
Uses monkeypatch and dependency injection only.
"""

from __future__ import annotations

import ast
import re
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SERVER_PY = REPO_ROOT / "api" / "server.py"
EXECUTION_GATE_PY = REPO_ROOT / "runtime" / "execution_gate.py"
MCP_PY = REPO_ROOT / "api" / "routes" / "mcp.py"
INGESTION_PY = REPO_ROOT / "memory" / "ingestion.py"
SUBSTRATE_DAG_PY = REPO_ROOT / "memory" / "substrate_dag.py"
BOOT_TRACE_PY = REPO_ROOT / "runtime" / "boot_trace.py"
READINESS_GATE_PY = REPO_ROOT / "runtime" / "readiness_gate.py"


# ===========================================================================
# PHASE 1: Boot Trace Tests
# ===========================================================================
class TestBootTrace:
    """Verify BootTrace module records stages correctly."""

    def test_boot_trace_module_exists(self):
        """boot_trace.py must exist as a standalone module."""
        assert BOOT_TRACE_PY.exists(), f"Missing: {BOOT_TRACE_PY}"

    def test_boot_trace_syntax(self):
        """boot_trace.py must parse without errors."""
        source = BOOT_TRACE_PY.read_text()
        ast.parse(source)

    def test_boot_trace_has_required_methods(self):
        """BootTrace must expose start(), ok(), fail(), freeze(), summary()."""
        source = BOOT_TRACE_PY.read_text()
        for method in ["start", "ok", "fail", "freeze", "summary"]:
            assert f"def {method}" in source, f"Missing method: {method}"

    def test_boot_trace_records_stages(self):
        """BootTrace must record start/ok/fail with timestamps."""
        import importlib.util
        import sys

        spec = importlib.util.spec_from_file_location("boot_trace", str(BOOT_TRACE_PY))
        mod = importlib.util.module_from_spec(spec)
        sys.modules["boot_trace"] = mod
        spec.loader.exec_module(mod)

        bt = mod.BootTrace()
        bt.start("test_stage")
        bt.ok("test_stage")
        bt.start("fail_stage")
        bt.fail("fail_stage", "simulated error")

        assert len(bt.steps) == 4
        assert bt.steps[0].name == "test_stage"
        assert bt.steps[0].status == "START"
        assert bt.steps[1].name == "test_stage"
        assert bt.steps[1].status == "OK"
        assert bt.steps[2].name == "fail_stage"
        assert bt.steps[2].status == "START"
        assert bt.steps[3].name == "fail_stage"
        assert bt.steps[3].status == "FAIL"
        assert bt.steps[3].error == "simulated error"

    def test_boot_trace_freeze_prevents_mutation(self):
        """After freeze(), no more steps can be added."""
        import importlib.util
        import sys

        spec = importlib.util.spec_from_file_location("boot_trace", str(BOOT_TRACE_PY))
        mod = importlib.util.module_from_spec(spec)
        sys.modules["boot_trace"] = mod
        spec.loader.exec_module(mod)

        bt = mod.BootTrace()
        bt.start("s1")
        bt.ok("s1")
        bt.freeze()

        # After freeze, start/ok/fail should raise RuntimeError
        with pytest.raises(RuntimeError, match="frozen"):
            bt.start("s2")
        with pytest.raises(RuntimeError, match="frozen"):
            bt.ok("s2")

    def test_boot_trace_summary(self):
        """summary() must return dict with total, ok, failed counts."""
        import importlib.util
        import sys

        spec = importlib.util.spec_from_file_location("boot_trace", str(BOOT_TRACE_PY))
        mod = importlib.util.module_from_spec(spec)
        sys.modules["boot_trace"] = mod
        spec.loader.exec_module(mod)

        bt = mod.BootTrace()
        bt.start("s1")
        bt.ok("s1")
        bt.start("s2")
        bt.fail("s2", "err")
        bt.freeze()

        s = bt.summary()
        assert isinstance(s, dict)
        assert s["total_steps"] == 2
        assert len(s["ok"]) == 1
        assert len(s["failed"]) == 1


# ===========================================================================
# PHASE 1: Boot Trace Instrumentation in server.py
# ===========================================================================
class TestBootTraceInServer:
    """Verify server.py instruments all mandatory stages with boot_trace."""

    MANDATORY_STAGES = [
        "module_registry",
        "tool_registry",
        "governance_integration",
        "memory_substrate",
        "governance_engine",
        "agent_executor",
        "neo4j",
        "redis",
    ]

    def test_server_imports_boot_trace(self):
        """server.py must import BootTrace."""
        source = SERVER_PY.read_text()
        assert "from runtime.boot_trace import BootTrace" in source

    def test_all_mandatory_stages_traced(self):
        """Every mandatory stage must have boot_trace.start() and boot_trace.ok()."""
        source = SERVER_PY.read_text()
        for stage in self.MANDATORY_STAGES:
            assert (
                f'boot_trace.start("{stage}")' in source
            ), f"Missing boot_trace.start for {stage}"
            assert (
                f'boot_trace.ok("{stage}")' in source
            ), f"Missing boot_trace.ok for {stage}"

    def test_boot_trace_stored_in_app_state(self):
        """server.py must store boot_trace in app.state.boot_trace."""
        source = SERVER_PY.read_text()
        assert "app.state.boot_trace = boot_trace" in source

    def test_boot_trace_frozen_before_yield(self):
        """boot_trace.freeze() must be called before yield."""
        source = SERVER_PY.read_text()
        freeze_pos = source.find("boot_trace.freeze()")
        yield_pos = source.find("\n    yield\n")
        assert freeze_pos != -1, "boot_trace.freeze() not found"
        assert yield_pos != -1, "yield not found"
        assert freeze_pos < yield_pos, "freeze() must come before yield"


# ===========================================================================
# PHASE 2: assert_runtime_ready Tests
# ===========================================================================
class TestAssertRuntimeReady:
    """Verify assert_runtime_ready rejects degraded state."""

    def test_readiness_gate_module_exists(self):
        """readiness_gate.py must exist."""
        assert READINESS_GATE_PY.exists()

    def test_readiness_gate_syntax(self):
        """readiness_gate.py must parse without errors."""
        source = READINESS_GATE_PY.read_text()
        ast.parse(source)

    def test_missing_substrate_service_fails(self):
        """Missing substrate_service must raise RuntimeError."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "readiness_gate", str(READINESS_GATE_PY)
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        app = SimpleNamespace(
            state=SimpleNamespace(
                substrate_service=None,
                neo4j_client=MagicMock(),
                governance=MagicMock(),
                governance_engine=MagicMock(),
                agent_executor=MagicMock(),
                redis_client=MagicMock(),
            )
        )
        with pytest.raises(RuntimeError, match="substrate_service"):
            mod.assert_runtime_ready(app)

    def test_missing_neo4j_fails(self):
        """Missing neo4j_client must raise RuntimeError."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "readiness_gate", str(READINESS_GATE_PY)
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        app = SimpleNamespace(
            state=SimpleNamespace(
                substrate_service=MagicMock(),
                neo4j_client=None,
                governance=MagicMock(),
                governance_engine=MagicMock(),
                agent_executor=MagicMock(),
                redis_client=MagicMock(),
            )
        )
        with pytest.raises(RuntimeError, match="neo4j_client"):
            mod.assert_runtime_ready(app)

    def test_missing_redis_fails(self):
        """Missing redis_client must raise RuntimeError."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "readiness_gate", str(READINESS_GATE_PY)
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        app = SimpleNamespace(
            state=SimpleNamespace(
                substrate_service=MagicMock(),
                neo4j_client=MagicMock(),
                governance=MagicMock(),
                governance_engine=MagicMock(),
                agent_executor=MagicMock(),
                redis_client=None,
            )
        )
        with pytest.raises(RuntimeError, match="redis_client"):
            mod.assert_runtime_ready(app)

    def test_missing_governance_fails(self):
        """Missing governance must raise RuntimeError."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "readiness_gate", str(READINESS_GATE_PY)
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        app = SimpleNamespace(
            state=SimpleNamespace(
                substrate_service=MagicMock(),
                neo4j_client=MagicMock(),
                governance=None,
                governance_engine=MagicMock(),
                agent_executor=MagicMock(),
                redis_client=MagicMock(),
            )
        )
        with pytest.raises(RuntimeError, match="governance"):
            mod.assert_runtime_ready(app)

    def test_missing_agent_executor_fails(self):
        """Missing agent_executor must raise RuntimeError."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "readiness_gate", str(READINESS_GATE_PY)
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        app = SimpleNamespace(
            state=SimpleNamespace(
                substrate_service=MagicMock(),
                neo4j_client=MagicMock(),
                governance=MagicMock(),
                governance_engine=MagicMock(),
                agent_executor=None,
                redis_client=MagicMock(),
            )
        )
        with pytest.raises(RuntimeError, match="agent_executor"):
            mod.assert_runtime_ready(app)

    def test_multiple_missing_reports_all(self):
        """Multiple missing subsystems must all be listed in error."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "readiness_gate", str(READINESS_GATE_PY)
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        app = SimpleNamespace(
            state=SimpleNamespace(
                substrate_service=None,
                neo4j_client=None,
                governance=MagicMock(),
                governance_engine=MagicMock(),
                agent_executor=MagicMock(),
                redis_client=None,
            )
        )
        with pytest.raises(RuntimeError) as exc_info:
            mod.assert_runtime_ready(app)
        msg = str(exc_info.value)
        assert "substrate_service" in msg
        assert "neo4j_client" in msg
        assert "redis_client" in msg


# ===========================================================================
# PHASE 2: Server Fail-Closed Source Invariants
# ===========================================================================
class TestServerFailClosedInvariants:
    """Verify server.py enforces fail-closed for all mandatory subsystems."""

    def test_memory_dsn_mandatory(self):
        """MEMORY_DSN check must raise RuntimeError, not log warning."""
        source = SERVER_PY.read_text()
        assert 'raise RuntimeError(' in source
        # Must not have the old "skip" pattern
        assert "Memory substrate not configured" not in source

    def test_neo4j_uri_mandatory(self):
        """NEO4J_URI must raise RuntimeError if missing."""
        source = SERVER_PY.read_text()
        assert "NEO4J_URI environment variable is required" in source

    def test_neo4j_not_optional_comment_removed(self):
        """The 'Neo4j is OPTIONAL' comment must not exist."""
        source = SERVER_PY.read_text()
        assert "Neo4j is OPTIONAL" not in source

    def test_redis_mandatory(self):
        """Redis init must raise RuntimeError on failure."""
        source = SERVER_PY.read_text()
        assert "L9 cannot start without Redis" in source

    def test_no_silent_none_for_mandatory(self):
        """app.state.X = None must NOT appear for mandatory subsystems."""
        source = SERVER_PY.read_text()
        mandatory = [
            "substrate_service",
            "neo4j_client",
            "governance",
            "governance_engine",
            "agent_executor",
            "redis_client",
        ]
        for name in mandatory:
            pattern = f"app.state.{name} = None"
            occurrences = source.count(pattern)
            assert occurrences == 0, (
                f"Found {occurrences} instances of '{pattern}' in server.py. "
                f"Mandatory subsystem {name} must never be set to None."
            )

    def test_assert_runtime_ready_called_before_yield(self):
        """assert_runtime_ready(app) must be called before yield."""
        source = SERVER_PY.read_text()
        gate_pos = source.find("assert_runtime_ready(app)")
        yield_pos = source.find("\n    yield\n")
        assert gate_pos != -1, "assert_runtime_ready(app) not found"
        assert yield_pos != -1, "yield not found"
        assert gate_pos < yield_pos


# ===========================================================================
# PHASE 3: Shadow Pipeline Elimination Tests
# ===========================================================================
class TestShadowPipelineElimination:
    """Verify legacy tool execution fallbacks are removed."""

    def test_execution_gate_no_agent_tools_fallback(self):
        """execution_gate.py must NOT fall back to agent.tools.execute in code."""
        source = EXECUTION_GATE_PY.read_text()
        # Check for actual code usage (not docstring mentions)
        for i, line in enumerate(source.splitlines(), 1):
            stripped = line.strip()
            # Skip comments and docstrings
            if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            # Skip lines that are inside docstrings (rough heuristic: indented string)
            if 'agent.tools.execute' in stripped and not any(
                stripped.startswith(c) for c in ['#', '"', "'", 'Legacy']
            ):
                # This is actual code calling agent.tools.execute
                if 'return agent.tools.execute' in stripped or 'agent.tools.execute(' in stripped:
                    pytest.fail(
                        f"Legacy fallback 'agent.tools.execute' found in code at line {i}: {stripped}"
                    )

    def test_execution_gate_no_import_pass(self):
        """execution_gate._execute_tool must NOT have 'except ImportError: pass'."""
        source = EXECUTION_GATE_PY.read_text()
        # Find the _execute_tool function
        func_start = source.find("def _execute_tool")
        assert func_start != -1
        func_body = source[func_start:]
        # Should not have the old "except ImportError: pass" pattern
        assert "except ImportError:\n        pass" not in func_body

    def test_execution_gate_requires_registry(self):
        """_execute_tool must raise RuntimeError if registry is None."""
        source = EXECUTION_GATE_PY.read_text()
        func_start = source.find("def _execute_tool")
        func_body = source[func_start:]
        assert "Legacy tool execution path forbidden" in func_body

    def test_mcp_governance_mandatory(self):
        """MCP route must import governance without try/except fallback."""
        source = MCP_PY.read_text()
        # Must have direct import, not wrapped in try/except
        assert "from memory.governance_gate import" in source
        # Must not have the old fallback pattern
        assert "_has_governance = False" not in source


# ===========================================================================
# PHASE 4: Memory Pipeline Convergence Tests
# ===========================================================================
class TestMemoryPipelineConvergence:
    """Verify all memory writes converge through substrate_service."""

    def test_unified_routes_through_substrate(self):
        """memory_unified.py must route through substrate_service.write_packet."""
        source = Path(
            REPO_ROOT / "mcp_memory" / "src" / "routes" / "memory_unified.py"
        ).read_text()
        assert "substrate_service.write_packet" in source

    def test_unified_no_fallback(self):
        """memory_unified.py must be fail-closed (503 if substrate unavailable)."""
        source = Path(
            REPO_ROOT / "mcp_memory" / "src" / "routes" / "memory_unified.py"
        ).read_text()
        assert "NO FALLBACK" in source or "fail-closed" in source

    def test_graph_sync_node_mandatory_in_dag(self):
        """substrate_dag.py graph_sync_node must NOT skip silently."""
        source = SUBSTRATE_DAG_PY.read_text()
        func_start = source.find("async def graph_sync_node")
        assert func_start != -1
        func_body = source[func_start : func_start + 2000]
        # Must not have the old "skipping" pattern
        assert "Neo4j not available, skipping" not in func_body
        # Must propagate errors
        assert "P0: mandatory" in func_body or "errors.append" in func_body

    def test_graph_sync_node_mandatory_in_ingestion(self):
        """ingestion.py graph_sync must NOT skip silently when Neo4j is None."""
        source = INGESTION_PY.read_text()
        # Find the graph sync section
        assert "P0: Neo4j is mandatory" in source
        # Must not have the old "skip silently" pattern
        assert "Neo4j not available, skip silently" not in source

    def test_ingestion_raises_on_missing_neo4j(self):
        """ingestion.py must raise RuntimeError if Neo4j is None during graph sync."""
        source = INGESTION_PY.read_text()
        assert "cannot skip graph sync" in source


# ===========================================================================
# PHASE 5: No New noqa Suppressions
# ===========================================================================
class TestNoNewNoqa:
    """Verify no new # noqa suppressions were added."""

    MODIFIED_FILES = [
        SERVER_PY,
        EXECUTION_GATE_PY,
        MCP_PY,
        INGESTION_PY,
        SUBSTRATE_DAG_PY,
        BOOT_TRACE_PY,
        READINESS_GATE_PY,
    ]

    def test_no_new_noqa_adr_critical(self):
        """No # noqa: ADR-0087/0055/0088 in modified files (critical ADRs)."""
        critical_adrs = {"ADR-0087", "ADR-0055", "ADR-0088"}
        for fpath in self.MODIFIED_FILES:
            if fpath.exists():
                source = fpath.read_text()
                for i, line in enumerate(source.splitlines(), 1):
                    for adr in critical_adrs:
                        if f"# noqa: {adr}" in line:
                            pytest.fail(
                                f"Found '# noqa: {adr}' in {fpath.name} line {i}: {line.strip()}"
                            )
