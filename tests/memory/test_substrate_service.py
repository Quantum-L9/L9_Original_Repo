from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from memory.substrate_repository import SubstrateRepository
from memory.substrate_semantic import EmbeddingProvider, StubEmbeddingProvider
from memory.substrate_service import MemorySubstrateService


@pytest.fixture
def mock_repository() -> MagicMock:
    return MagicMock(spec=SubstrateRepository)


@pytest.fixture
def mock_embedding_provider() -> MagicMock:
    mock = MagicMock(spec=EmbeddingProvider)
    mock.dimensions = 1536
    mock.embed_text = AsyncMock(return_value=[0.1] * 1536)
    mock.embed_batch = AsyncMock(return_value=[[0.1] * 1536])
    return mock


@pytest.fixture
def service(
    mock_repository: MagicMock, mock_embedding_provider: MagicMock
) -> MemorySubstrateService:
    return MemorySubstrateService(
        repository=mock_repository, embedding_provider=mock_embedding_provider
    )


def test_memory_substrate_service_initialization_with_valid_provider(
    mock_repository: MagicMock, mock_embedding_provider: MagicMock
) -> None:
    service = MemorySubstrateService(
        repository=mock_repository, embedding_provider=mock_embedding_provider
    )
    assert service._repository == mock_repository
    assert service._embedding_provider == mock_embedding_provider


def test_memory_substrate_service_initialization_without_embedding_provider(
    mock_repository: MagicMock,
) -> None:
    with pytest.raises(
        RuntimeError, match=r"Embedding provider required; missing embedding context\."
    ):
        MemorySubstrateService(repository=mock_repository, embedding_provider=None)


def test_memory_substrate_service_initialization_with_stub_provider(
    mock_repository: MagicMock,
) -> None:
    with pytest.raises(
        RuntimeError,
        match=r"StubEmbeddingProvider is not allowed in enforcement mode\.",
    ):
        MemorySubstrateService(
            repository=mock_repository, embedding_provider=StubEmbeddingProvider()
        )


@pytest.mark.asyncio
async def test_set_session_scope(service: MemorySubstrateService) -> None:
    tenant_id = "tenant-uuid"
    org_id = "org-uuid"
    user_id = "user-uuid"
    role = "end_user"

    # Mock async context manager properly
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()
    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_context.__aexit__ = AsyncMock(return_value=None)
    service._repository.acquire = MagicMock(return_value=mock_context)

    await service.set_session_scope(tenant_id, org_id, user_id, role)

    service._repository.acquire.assert_called_once()
    mock_conn.execute.assert_called_once_with(
        """SELECT l9_set_scope($1::uuid, $2::uuid, $3::uuid, $4::text)""",
        tenant_id,
        org_id,
        user_id,
        role,
    )


@pytest.mark.asyncio
async def test_set_session_scope_with_exception(
    service: MemorySubstrateService,
) -> None:
    from contextlib import asynccontextmanager

    tenant_id = "tenant-uuid"
    org_id = "org-uuid"
    user_id = "user-uuid"
    role = "end_user"

    @asynccontextmanager
    async def _failing_acquire():
        raise Exception("Database error")
        yield  # noqa: unreachable — required for generator protocol

    service._repository.acquire = _failing_acquire

    with pytest.raises(RuntimeError):
        await service.set_session_scope(tenant_id, org_id, user_id, role)


def test_require_rls_context_valid(service: MemorySubstrateService) -> None:
    with patch(
        "memory.substrate_service.require_governance_context",
        return_value=MagicMock(tenant_id="1", org_id="1", user_id="1"),
    ):
        ctx = service._require_rls_context("test_operation")
        assert ctx.tenant_id == "1"


def test_require_rls_context_missing_tenant_id(service: MemorySubstrateService) -> None:
    with patch(
        "memory.substrate_service.require_governance_context",
        return_value=MagicMock(tenant_id=None, org_id="1", user_id="1"),
    ):
        with pytest.raises(
            RuntimeError,
            match="RLS scope required for memory operation: test_operation",
        ):
            service._require_rls_context("test_operation")


def test_require_rls_context_missing_org_id(service: MemorySubstrateService) -> None:
    with patch(
        "memory.substrate_service.require_governance_context",
        return_value=MagicMock(tenant_id="1", org_id=None, user_id="1"),
    ):
        with pytest.raises(
            RuntimeError,
            match="RLS scope required for memory operation: test_operation",
        ):
            service._require_rls_context("test_operation")


def test_require_rls_context_missing_user_id(service: MemorySubstrateService) -> None:
    with patch(
        "memory.substrate_service.require_governance_context",
        return_value=MagicMock(tenant_id="1", org_id="1", user_id=None),
    ):
        with pytest.raises(
            RuntimeError,
            match="RLS scope required for memory operation: test_operation",
        ):
            service._require_rls_context("test_operation")
