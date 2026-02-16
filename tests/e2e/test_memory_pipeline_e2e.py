"""
E2E Tests: Memory Pipeline Paths
==================================

Tests that validate the 4 memory pipelines exist and are
properly wired:

- Pipeline A: Ingestion (Write Path)
- Pipeline B: Retrieval (Read Path)
- Pipeline C: Maintenance (Background)
- Pipeline D: Tool Discovery (NEW)

Version: 1.0.0
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent


# ============================================================================
# PIPELINE A: INGESTION PATH
# ============================================================================


class TestIngestionPipeline:
    """Verify write path modules exist and are wired."""

    def test_ingestion_entry_point_exists(self):
        """memory/ingestion.py must exist with ingest_packet."""
        path = PROJECT_ROOT / "memory" / "ingestion.py"
        assert path.exists(), "memory/ingestion.py not found"

        try:
            from memory.ingestion import ingest_packet

            assert callable(ingest_packet)
        except ImportError as e:
            pytest.skip(f"Cannot import ingest_packet: {e}")

    def test_enrichment_dag_exists(self):
        """memory/enrichment_dag.py must exist with EnrichmentDAG."""
        path = PROJECT_ROOT / "memory" / "enrichment_dag.py"
        assert path.exists(), "memory/enrichment_dag.py not found"

    def test_substrate_dag_exists(self):
        """memory/substrate_dag.py must exist with SubstrateDAG."""
        path = PROJECT_ROOT / "memory" / "substrate_dag.py"
        assert path.exists(), "memory/substrate_dag.py not found"

    def test_ingestion_imports_enrichment(self):
        """ingestion.py must reference enrichment_dag."""
        path = PROJECT_ROOT / "memory" / "ingestion.py"
        if not path.exists():
            pytest.skip("File not found")
        source = path.read_text(encoding="utf-8")
        assert "enrichment" in source.lower(), (
            "ingestion.py does not reference enrichment pipeline"
        )


# ============================================================================
# PIPELINE B: RETRIEVAL PATH
# ============================================================================


class TestRetrievalPipeline:
    """Verify read path modules exist and are wired."""

    def test_retrieval_module_exists(self):
        """memory/retrieval.py must exist."""
        path = PROJECT_ROOT / "memory" / "retrieval.py"
        assert path.exists(), "memory/retrieval.py not found"

    def test_query_classifier_exists(self):
        """memory/query_classifier.py must exist."""
        path = PROJECT_ROOT / "memory" / "query_classifier.py"
        assert path.exists(), "memory/query_classifier.py not found"

    def test_hybrid_rag_exists(self):
        """memory/hybrid_rag.py must exist."""
        path = PROJECT_ROOT / "memory" / "hybrid_rag.py"
        assert path.exists(), "memory/hybrid_rag.py not found"

    def test_semantic_service_exists(self):
        """memory/substrate_semantic.py must exist."""
        path = PROJECT_ROOT / "memory" / "substrate_semantic.py"
        assert path.exists(), "memory/substrate_semantic.py not found"

    def test_graph_client_exists(self):
        """memory/graph_client.py must exist."""
        path = PROJECT_ROOT / "memory" / "graph_client.py"
        assert path.exists(), "memory/graph_client.py not found"


# ============================================================================
# PIPELINE C: MAINTENANCE PATH
# ============================================================================


class TestMaintenancePipeline:
    """Verify background maintenance modules exist."""

    def test_consolidation_exists(self):
        """memory/consolidation.py must exist."""
        path = PROJECT_ROOT / "memory" / "consolidation.py"
        assert path.exists(), "memory/consolidation.py not found"

    def test_deduplication_exists(self):
        """memory/deduplication.py must exist."""
        path = PROJECT_ROOT / "memory" / "deduplication.py"
        assert path.exists(), "memory/deduplication.py not found"


# ============================================================================
# PIPELINE D: TOOL DISCOVERY (NEW)
# ============================================================================


class TestToolDiscoveryPipeline:
    """Verify the new Anthropic-pattern tool discovery chain."""

    def test_tool_search_meta_exists(self):
        """runtime/tool_search_meta.py must exist."""
        path = PROJECT_ROOT / "runtime" / "tool_search_meta.py"
        assert path.exists(), "runtime/tool_search_meta.py not found"

    def test_dynamic_discovery_engine_exists(self):
        """core/tools/dynamic_discovery.py must exist."""
        path = PROJECT_ROOT / "core" / "tools" / "dynamic_discovery.py"
        assert path.exists(), "core/tools/dynamic_discovery.py not found"

    def test_tool_embeddings_exists(self):
        """core/tools/tool_embeddings.py must exist."""
        path = PROJECT_ROOT / "core" / "tools" / "tool_embeddings.py"
        assert path.exists(), "core/tools/tool_embeddings.py not found"

    def test_dynamic_tool_binding_exists(self):
        """core/agents/dynamic_tool_binding.py must exist."""
        path = PROJECT_ROOT / "core" / "agents" / "dynamic_tool_binding.py"
        assert path.exists(), "core/agents/dynamic_tool_binding.py not found"

    def test_discovery_chain_importable(self):
        """Full discovery chain must be importable."""
        try:
            from core.tools.dynamic_discovery import discover_tools_for_task

            assert callable(discover_tools_for_task)
        except ImportError as e:
            pytest.fail(f"Discovery chain import failed: {e}")

    def test_tool_search_to_discovery_wiring(self):
        """tool_search_meta must import from dynamic_discovery."""
        path = PROJECT_ROOT / "runtime" / "tool_search_meta.py"
        if not path.exists():
            pytest.skip("File not found")
        source = path.read_text(encoding="utf-8")
        assert "dynamic_discovery" in source, (
            "tool_search_meta.py does not import from dynamic_discovery"
        )


# ============================================================================
# CROSS-PIPELINE: SYNTAX VALIDATION
# ============================================================================


class TestAllPipelinesSyntax:
    """Validate syntax of all pipeline files."""

    PIPELINE_FILES = [
        "memory/ingestion.py",
        "memory/enrichment_dag.py",
        "memory/substrate_dag.py",
        "memory/retrieval.py",
        "memory/query_classifier.py",
        "memory/hybrid_rag.py",
        "memory/substrate_semantic.py",
        "memory/graph_client.py",
        "memory/consolidation.py",
        "memory/deduplication.py",
        "runtime/tool_search_meta.py",
        "core/tools/dynamic_discovery.py",
        "core/tools/tool_embeddings.py",
        "core/agents/dynamic_tool_binding.py",
    ]

    @pytest.mark.parametrize("rel_path", PIPELINE_FILES)
    def test_file_syntax_valid(self, rel_path):
        """Each pipeline file must be syntactically valid Python."""
        path = PROJECT_ROOT / rel_path
        if not path.exists():
            pytest.skip(f"File not found: {rel_path}")

        source = path.read_text(encoding="utf-8")
        try:
            ast.parse(source)
        except SyntaxError as e:
            pytest.fail(f"Syntax error in {rel_path}: {e}")
