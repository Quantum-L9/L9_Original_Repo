from datetime import datetime

import pytest

from memory.graph_memory import ConversationGraphMemory
from memory.substrate_repository import SubstrateRepository


@pytest.mark.asyncio
async def test_semantic_search_requires_governance_context():
    repo = SubstrateRepository("postgresql://invalid")
    with pytest.raises(RuntimeError, match="Governance context required"):
        await repo.search_semantic_memory([0.1, 0.2, 0.3], top_k=1)


@pytest.mark.asyncio
async def test_semantic_fact_requires_governance_context():
    repo = SubstrateRepository("postgresql://invalid")
    with pytest.raises(RuntimeError, match="Governance context required"):
        await repo.insert_semantic_fact(fact_text="test fact")


@pytest.mark.asyncio
async def test_episodic_event_requires_governance_context():
    repo = SubstrateRepository("postgresql://invalid")
    with pytest.raises(RuntimeError, match="Governance context required"):
        await repo.insert_episodic_event(
            observation="test event",
            event_timestamp=datetime.utcnow(),
        )


@pytest.mark.asyncio
async def test_graph_memory_requires_neo4j():
    memory = ConversationGraphMemory(neo4j_client=None)
    with pytest.raises(RuntimeError, match="Neo4j not available"):
        await memory.store_message(content="hello", user_id="user-1")
