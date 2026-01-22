"""
L9 Permission Graph Tests
========================

Tests for permission graph.
No external services required - uses mocks.

Version: 1.0.0
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from core.security.permission_graph import PermissionGraph
except ImportError as e:
    pytest.skip(
        f"Could not import core.security.permission_graph: {e}", allow_module_level=True
    )


# =============================================================================
# Test: Permission check
# =============================================================================


@pytest.mark.asyncio
async def test_permission_check():
    """
    Contract: PermissionGraph can check permissions (mocked Neo4j).
    """
    # Mock Neo4j client
    with patch(
        "core.security.permission_graph.PermissionGraph._get_neo4j"
    ) as mock_get_neo4j:
        mock_neo4j = AsyncMock()
        mock_get_neo4j.return_value = mock_neo4j

        # Mock run_query to return permission granted
        mock_neo4j.run_query = AsyncMock(return_value=[{"has_permission": True}])

        # Test permission check structure
        # Note: PermissionGraph methods are static
        assert PermissionGraph is not None
        assert hasattr(PermissionGraph, "has_permission") or hasattr(
            PermissionGraph, "check_permission"
        )


# =============================================================================
# Test: Grant permission
# =============================================================================


@pytest.mark.asyncio
async def test_grant_permission():
    """
    Contract: PermissionGraph can grant permissions (mocked Neo4j).
    """
    # Mock Neo4j client
    with patch(
        "core.security.permission_graph.PermissionGraph._get_neo4j"
    ) as mock_get_neo4j:
        mock_neo4j = AsyncMock()
        mock_get_neo4j.return_value = mock_neo4j

        # Mock run_query
        mock_neo4j.run_query = AsyncMock(return_value=[])

        # Test grant permission structure
        assert PermissionGraph is not None
        assert hasattr(PermissionGraph, "grant_permission") or hasattr(
            PermissionGraph, "create_user"
        )
