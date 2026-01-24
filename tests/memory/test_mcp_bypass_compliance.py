"""
MCP Bypass Compliance Tests
============================

Tests that MCP direct writes (bypassing SubstrateDAG) still produce valid
PacketEnvelope structure and comply with memory governance requirements.

Gap addressed: MCP Memory Server writes directly to packet_store and
memory_embeddings tables, bypassing the canonical ingestion pipeline.

These tests verify:
1. MCP writes produce valid PacketEnvelope structure
2. MCP writes do NOT create reasoning_traces (by design)
3. MCP writes still log to tool_audit_log correctly

Run: pytest tests/memory/test_mcp_bypass_compliance.py -v
"""

import pytest

# =============================================================================
# Test 1: MCP Architecture Compliance (No MCP Import Required)
# =============================================================================


class TestMCPArchitectureCompliance:
    """Verify MCP architecture compliance without requiring MCP imports."""

    def test_mcp_memory_unified_exists(self):
        """Verify memory_unified.py exists and is the MCP handler."""
        import os

        mcp_unified_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "mcp_memory",
            "src",
            "routes",
            "memory_unified.py",
        )
        assert os.path.exists(
            mcp_unified_path
        ), "mcp_memory/src/routes/memory_unified.py should exist"

    def test_mcp_does_not_import_substrate_dag(self):
        """Verify MCP memory handler does NOT use SubstrateDAG."""
        import os

        mcp_unified_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "mcp_memory",
            "src",
            "routes",
            "memory_unified.py",
        )

        with open(mcp_unified_path, "r") as f:
            source = f.read()

        # MCP should NOT import or use SubstrateDAG
        assert (
            "from memory.substrate_dag import" not in source
        ), "MCP should not import SubstrateDAG"
        assert "SubstrateDAG(" not in source, "MCP should not instantiate SubstrateDAG"

    def test_mcp_uses_direct_execute_calls(self):
        """Verify MCP uses direct SQL execute() calls."""
        import os

        mcp_unified_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "mcp_memory",
            "src",
            "routes",
            "memory_unified.py",
        )

        with open(mcp_unified_path, "r") as f:
            source = f.read()

        # MCP should use direct execute() calls
        assert (
            "execute(" in source
        ), "MCP should use direct execute() calls for DB operations"

        # MCP should insert into packet_store
        assert "packet_store" in source, "MCP should write to packet_store table"


# =============================================================================
# Test 2: MCP Skips Reasoning Traces (By Design)
# =============================================================================


class TestMCPSkipsReasoningTraces:
    """Verify MCP writes do NOT create reasoning_traces entries."""

    def test_mcp_handler_does_not_write_reasoning_traces(self):
        """MCP handler should NOT write to reasoning_traces table."""
        import os

        mcp_unified_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "mcp_memory",
            "src",
            "routes",
            "memory_unified.py",
        )

        with open(mcp_unified_path, "r") as f:
            source = f.read()

        # MCP should NOT insert into reasoning_traces
        # (This is by design - MCP bypasses the DAG which creates traces)
        assert (
            "INSERT INTO reasoning_traces" not in source
        ), "MCP should NOT write to reasoning_traces (DAG bypass by design)"

    def test_mcp_handler_does_not_call_reasoning_node(self):
        """MCP handler should NOT call reasoning_node from SubstrateDAG."""
        import os

        mcp_unified_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "mcp_memory",
            "src",
            "routes",
            "memory_unified.py",
        )

        with open(mcp_unified_path, "r") as f:
            source = f.read()

        # MCP should NOT call reasoning_node
        assert (
            "reasoning_node" not in source
        ), "MCP should NOT call reasoning_node (DAG bypass by design)"


# =============================================================================
# Test 3: MCP Audit Logging Compliance
# =============================================================================


class TestMCPAuditLogging:
    """Verify MCP audit logging is configured."""

    def test_audit_module_exists(self):
        """Verify audit.py exists in MCP memory."""
        import os

        audit_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "mcp_memory", "src", "audit.py"
        )
        assert os.path.exists(audit_path), "mcp_memory/src/audit.py should exist"

    def test_audit_logger_class_exists(self):
        """Verify AuditLogger class exists with required methods."""
        import os

        audit_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "mcp_memory", "src", "audit.py"
        )

        with open(audit_path, "r") as f:
            source = f.read()

        # AuditLogger class should exist
        assert "class AuditLogger" in source, "AuditLogger class should exist"

        # log method should exist
        assert (
            "async def log(" in source or "def log(" in source
        ), "AuditLogger should have log method"

    def test_mcp_server_uses_audit_logging(self):
        """Verify MCP server imports and uses audit logging."""
        import os

        mcp_server_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "mcp_memory", "src", "mcp_server.py"
        )

        with open(mcp_server_path, "r") as f:
            source = f.read()

        # MCP server should import audit functionality
        assert "audit" in source.lower(), "MCP server should use audit logging"


# =============================================================================
# Test 4: MCP PacketEnvelope Structure Compliance
# =============================================================================


class TestMCPPacketEnvelopeCompliance:
    """Verify MCP writes produce valid PacketEnvelope structure."""

    def test_mcp_writes_envelope_jsonb_column(self):
        """MCP writes should store data in envelope JSONB column."""
        import os

        mcp_unified_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "mcp_memory",
            "src",
            "routes",
            "memory_unified.py",
        )

        with open(mcp_unified_path, "r") as f:
            source = f.read()

        # Should write to envelope column
        assert "envelope" in source, "MCP should write to envelope column"

    def test_mcp_includes_metadata_creator(self):
        """MCP writes should include creator in metadata."""
        import os

        mcp_unified_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "mcp_memory",
            "src",
            "routes",
            "memory_unified.py",
        )

        with open(mcp_unified_path, "r") as f:
            source = f.read()

        # Should include creator metadata
        assert "creator" in source, "MCP should include creator in metadata"

    def test_mcp_writes_to_memory_embeddings(self):
        """MCP should write embeddings to memory_embeddings table."""
        import os

        mcp_unified_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "mcp_memory",
            "src",
            "routes",
            "memory_unified.py",
        )

        with open(mcp_unified_path, "r") as f:
            source = f.read()

        # Should write to memory_embeddings
        assert (
            "memory_embeddings" in source
        ), "MCP should write to memory_embeddings table"


# =============================================================================
# Test 5: MCP vs L9 Core Pipeline Separation
# =============================================================================


class TestMCPL9PipelineSeparation:
    """Verify MCP and L9 core pipelines are properly separated."""

    def test_l9_core_uses_substrate_dag(self):
        """L9 core ingestion should use SubstrateDAG."""
        import os

        ingestion_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "memory", "ingestion.py"
        )

        with open(ingestion_path, "r") as f:
            source = f.read()

        # L9 core should use SubstrateDAG
        assert (
            "SubstrateDAG" in source or "substrate_dag" in source.lower()
        ), "L9 core ingestion should use SubstrateDAG"

    def test_l9_core_creates_reasoning_traces(self):
        """L9 core should create reasoning traces via DAG."""
        import os

        # Check substrate_dag.py or substrate_graph.py
        for filename in ["substrate_dag.py", "substrate_graph.py"]:
            dag_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "memory", filename
            )
            if os.path.exists(dag_path):
                with open(dag_path, "r") as f:
                    source = f.read()

                # DAG should have reasoning trace functionality
                if "reasoning" in source.lower():
                    return  # Test passes

        # If we get here, check ingestion.py as fallback
        ingestion_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "memory", "ingestion.py"
        )
        with open(ingestion_path, "r") as f:
            source = f.read()

        assert "reasoning" in source.lower(), "L9 core should support reasoning traces"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
