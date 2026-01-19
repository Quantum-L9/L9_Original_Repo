import pytest

from memory.substrate_repository import SubstrateRepository
from memory.substrate_semantic import create_embedding_provider, embed_text
from memory.substrate_service import MemorySubstrateService


def test_memory_substrate_requires_embedding_provider() -> None:
    repository = SubstrateRepository("postgresql://user:pass@localhost/db")
    with pytest.raises(RuntimeError, match="Embedding provider is required"):
        MemorySubstrateService(repository=repository)


def test_create_embedding_provider_rejects_stub() -> None:
    with pytest.raises(RuntimeError, match="Stub embedding provider is not permitted"):
        create_embedding_provider(provider_type="stub")


@pytest.mark.asyncio
async def test_embed_text_requires_provider_or_api_key() -> None:
    with pytest.raises(RuntimeError, match="Embedding provider or API key is required"):
        await embed_text("test")
