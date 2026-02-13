"""
Memory Test Domain — shared fixtures for all memory tests.

Provides:
- gov_ctx: Governance context fixture (required by write_packet, semantic_search, etc.)
- governance_context_active: Autouse fixture that wraps tests in governance context
"""

from __future__ import annotations

import pytest

from memory.governance_gate import build_governance_context, governance_context


@pytest.fixture
def gov_ctx():
    """
    Build a test governance context with RLS UUIDs.

    Required by any test that calls:
    - MemorySubstrateService.write_packet()
    - MemorySubstrateService.semantic_search()
    - IngestionPipeline.ingest()
    - Any function decorated with @require_governance_context
    """
    return build_governance_context(
        caller_id="test",
        role="end_user",
        scope="developer",
        project_id="l9",
        allowed_scopes=["developer"],
        tenant_id="11111111-1111-1111-1111-111111111111",
        org_id="22222222-2222-2222-2222-222222222222",
        user_id="33333333-3333-3333-3333-333333333333",
    )
