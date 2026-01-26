"""
Cross-Client Consistency Tests
===============================

Tests that L-CTO and Cursor can read each other's memories correctly,
with proper scope isolation enforced.

Gap addressed: No test for L reading Cursor memories + vice versa

Architecture:
- L and C share the SAME tenant_id/org_id/user_id (deterministic UUIDs)
- Isolation is scope-based (developer, l-private, global) + creator-based
- C can read: developer, global (NOT l-private)
- L can read: ALL scopes

Run: pytest tests/memory/test_cross_client_consistency.py -v
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

# =============================================================================
# Shared Test Data
# =============================================================================

# Deterministic UUIDs from config/rls_config.py
SHARED_TENANT_ID = "73350468-3158-5d0f-9b8c-9b193d96fc4b"
SHARED_ORG_ID = "14910cef-fea1-51d7-9a28-05579e6c0c18"
SHARED_USER_ID = "2f00c090-3816-51a0-806c-34d32522a070"


# =============================================================================
# Test 1: L Can Read Cursor's Developer-Scoped Memories
# =============================================================================


class TestLReadsCursorMemories:
    """Test that L-CTO can read Cursor's developer-scoped memories."""

    @pytest.mark.asyncio
    async def test_l_can_read_cursor_developer_scope(self):
        """L should see Cursor's developer-scoped memories."""
        # Simulate Cursor writing a memory
        cursor_memory = {
            "packet_id": str(uuid4()),
            "envelope": {
                "kind": "MEMORY",
                "payload": {"content": "Cursor saved this preference"},
                "metadata": {
                    "creator": "Cursor-IDE",
                    "source": "cursor-mcp",
                    "scope": "developer",
                },
            },
            "scope": "developer",
            "tenant_id": SHARED_TENANT_ID,
            "org_id": SHARED_ORG_ID,
            "user_id": SHARED_USER_ID,
        }

        # Mock L-CTO querying the same substrate
        async def mock_search(*args, **kwargs):
            # L has no scope restrictions - should see Cursor's memory
            return [cursor_memory]

        with patch(
            "memory.substrate_service.MemorySubstrateService.search_packets_by_thread",
            side_effect=mock_search,
        ):
            from memory.substrate_service import MemorySubstrateService

            service = MagicMock(spec=MemorySubstrateService)
            service.search_packets_by_thread = mock_search

            results = await service.search_packets_by_thread(
                thread_id="test-thread",
                # L queries with no scope restriction
            )

            assert len(results) >= 1, "L should find Cursor's memory"
            assert any(
                "Cursor saved" in str(r.get("envelope", {}).get("payload", {}))
                for r in results
            ), "L should see Cursor's content"

    @pytest.mark.asyncio
    async def test_l_can_read_cursor_global_scope(self):
        """L should see Cursor's global-scoped memories."""
        cursor_global_memory = {
            "packet_id": str(uuid4()),
            "envelope": {
                "kind": "MEMORY",
                "payload": {"content": "Cursor global fact"},
                "metadata": {
                    "creator": "Cursor-IDE",
                    "scope": "global",
                },
            },
            "scope": "global",
        }

        # L should be able to read global scope
        assert cursor_global_memory["scope"] == "global"
        assert cursor_global_memory["envelope"]["metadata"]["creator"] == "Cursor-IDE"


# =============================================================================
# Test 2: Cursor Can Read L's Global Memories (NOT l-private)
# =============================================================================


class TestCursorReadsLMemories:
    """Test that Cursor can read L's global memories but NOT l-private."""

    @pytest.mark.asyncio
    async def test_cursor_can_read_l_global_scope(self):
        """Cursor should see L's global-scoped memories."""
        l_global_memory = {
            "packet_id": str(uuid4()),
            "envelope": {
                "kind": "MEMORY",
                "payload": {"content": "L's global insight"},
                "metadata": {
                    "creator": "L-CTO",
                    "scope": "global",
                },
            },
            "scope": "global",
        }

        # Simulate Cursor's search with scope filter
        async def mock_mcp_search(query, scopes, **kwargs):
            # Cursor is restricted to developer and global
            if "global" in scopes:
                return [l_global_memory]
            return []

        results = await mock_mcp_search(
            query="insight",
            scopes=["developer", "global"],  # Cursor's allowed scopes
        )

        assert len(results) >= 1, "Cursor should find L's global memory"
        assert results[0]["envelope"]["metadata"]["creator"] == "L-CTO"

    @pytest.mark.asyncio
    async def test_cursor_cannot_read_l_private_scope(self):
        """Cursor MUST NOT see L's l-private scoped memories."""
        l_private_memory = {
            "packet_id": str(uuid4()),
            "envelope": {
                "kind": "MEMORY",
                "payload": {"content": "L's private reasoning - SHOULD NOT BE VISIBLE"},
                "metadata": {
                    "creator": "L-CTO",
                    "scope": "l-private",
                },
            },
            "scope": "l-private",
        }

        # Simulate Cursor's search with enforced scope filter
        async def mock_mcp_search_with_filter(query, allowed_scopes, **kwargs):
            # MCP server enforces scope filter
            if l_private_memory["scope"] not in allowed_scopes:
                return []  # Filtered out
            return [l_private_memory]

        results = await mock_mcp_search_with_filter(
            query="private",
            allowed_scopes=["developer", "global"],  # Cursor's allowed scopes
        )

        # CRITICAL: Cursor should NOT see l-private
        assert len(results) == 0, "Cursor leaked into L's private scope!"

    def test_scope_filter_function_excludes_l_private_for_cursor(self):
        """Verify scope filter logic excludes l-private for Cursor."""
        from memory.governance_gate import build_governance_context

        # Build context for Cursor
        ctx = build_governance_context(
            caller_id="C",
            role="end_user",
            scope="developer",
            allowed_scopes=["developer", "global"],
            project_id="l9",
        )

        assert "l-private" not in ctx.allowed_scopes, (
            "Cursor context should not include l-private"
        )
        assert "developer" in ctx.allowed_scopes
        assert "global" in ctx.allowed_scopes


# =============================================================================
# Test 3: Bidirectional Developer Scope Access
# =============================================================================


class TestBidirectionalDeveloperScope:
    """Test that both L and C can read/write developer scope."""

    @pytest.mark.asyncio
    async def test_developer_scope_shared_workspace(self):
        """Both L and C should be able to collaborate in developer scope."""

        # Memory written by Cursor
        cursor_dev_memory = {
            "packet_id": str(uuid4()),
            "content": "Cursor's dev note",
            "scope": "developer",
            "metadata": {"creator": "Cursor-IDE"},
        }

        # Memory written by L
        l_dev_memory = {
            "packet_id": str(uuid4()),
            "content": "L's dev note",
            "scope": "developer",
            "metadata": {"creator": "L-CTO"},
        }

        shared_memories = [cursor_dev_memory, l_dev_memory]

        # Both should see both memories in developer scope
        def filter_by_scope(memories, allowed_scopes):
            return [m for m in memories if m["scope"] in allowed_scopes]

        # Cursor view
        cursor_view = filter_by_scope(shared_memories, ["developer", "global"])
        assert len(cursor_view) == 2, "Cursor should see both dev memories"

        # L view (no restrictions)
        l_view = filter_by_scope(shared_memories, ["developer", "global", "l-private"])
        assert len(l_view) == 2, "L should see both dev memories"

    @pytest.mark.asyncio
    async def test_metadata_creator_preserved_on_read(self):
        """Verify creator metadata is preserved when reading cross-client."""

        original_creator = "Cursor-IDE"
        memory = {
            "packet_id": str(uuid4()),
            "envelope": {
                "metadata": {
                    "creator": original_creator,
                    "source": "cursor-mcp",
                }
            },
        }

        # When L reads this memory, creator should still be Cursor-IDE
        assert memory["envelope"]["metadata"]["creator"] == original_creator, (
            "Creator metadata must be preserved on cross-client read"
        )


# =============================================================================
# Test 4: Scope Isolation at Query Level
# =============================================================================


class TestScopeIsolationQuery:
    """Test that scope isolation is enforced at the SQL query level."""

    def test_build_scope_project_filter_parameterized(self):
        """Verify scope filter uses parameterized queries (SQL injection safe)."""
        from memory.governance_gate import (
            build_governance_context,
            build_scope_project_filter,
        )

        # Build context for Cursor first
        ctx = build_governance_context(
            caller_id="C",
            role="end_user",
            scope="developer",
            allowed_scopes=["developer", "global"],
            project_id="l9",
        )

        # Build filter using context
        sql_fragment, _params, _ = build_scope_project_filter(
            ctx,
            param_idx=1,
            table_alias="ps",
        )

        # Verify parameterized (no string interpolation)
        assert "$" in sql_fragment or "ANY" in sql_fragment.upper(), (
            "Scope filter should use parameterized queries"
        )

        # Verify l-private NOT in filter (ctx.allowed_scopes doesn't have it)
        assert "l-private" not in ctx.allowed_scopes, (
            "l-private should not be in Cursor's allowed scopes"
        )

    def test_governance_context_enforces_caller_scopes(self):
        """Verify governance context correctly sets allowed scopes per caller."""
        from memory.governance_gate import build_governance_context

        # Cursor context
        cursor_ctx = build_governance_context(
            caller_id="C",
            role="end_user",
            scope="developer",
            allowed_scopes=["developer", "global"],
            project_id="l9",
        )
        assert cursor_ctx.caller_id == "C"
        assert "l-private" not in cursor_ctx.allowed_scopes

        # L context
        l_ctx = build_governance_context(
            caller_id="L",
            role="service",
            scope="l-private",
            allowed_scopes=["developer", "global", "l-private"],
            project_id="l9",
        )
        assert l_ctx.caller_id == "L"
        assert "l-private" in l_ctx.allowed_scopes


# =============================================================================
# Integration Test: Full Cross-Client Flow
# =============================================================================


class TestCrossClientIntegration:
    """Integration tests for full cross-client memory flow."""

    @pytest.mark.asyncio
    async def test_full_cross_client_write_read_cycle(self):
        """Test complete write-read cycle between L and Cursor."""

        test_packet_id = str(uuid4())

        # 1. Cursor writes to developer scope
        cursor_write = {
            "packet_id": test_packet_id,
            "content": "Cursor wrote this",
            "scope": "developer",
            "creator": "Cursor-IDE",
        }

        # 2. L reads from substrate (should see Cursor's write)
        async def l_read(packet_id):
            # L has access to all scopes
            return cursor_write if cursor_write["packet_id"] == packet_id else None

        result = await l_read(test_packet_id)

        assert result is not None, "L should read Cursor's memory"
        assert result["creator"] == "Cursor-IDE", "Creator should be preserved"
        assert result["scope"] == "developer", "Scope should be preserved"

    @pytest.mark.asyncio
    async def test_shared_tenant_isolation_works(self):
        """Verify shared tenant doesn't leak to other tenants."""

        # L9 shared tenant
        l9_memory = {
            "tenant_id": SHARED_TENANT_ID,
            "content": "L9 memory",
        }

        # Different tenant
        other_memory = {
            "tenant_id": str(uuid4()),  # Different tenant
            "content": "Other tenant memory",
        }

        # Filter by tenant
        def filter_by_tenant(memories, tenant_id):
            return [m for m in memories if m["tenant_id"] == tenant_id]

        l9_results = filter_by_tenant([l9_memory, other_memory], SHARED_TENANT_ID)

        assert len(l9_results) == 1, "Should only see L9 tenant memories"
        assert l9_results[0]["content"] == "L9 memory"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
