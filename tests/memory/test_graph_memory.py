"""
Tests for Conversational Graph Memory (GMP-58)

Tests the Neo4j-backed conversation history storage.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from memory.graph_memory import (
    ConversationContext,
    ConversationGraphMemory,
    GraphMessage,
    MessageRole,
    TopicExtractor,
    get_graph_memory,
    query_history,
    store_message,
)


class TestTopicExtractor:
    """Test TopicExtractor functionality."""

    def test_extract_known_topics(self):
        """Test extracting known topics."""
        extractor = TopicExtractor()

        content = "I need help with the Neo4j database and memory system"
        topics = extractor.extract_topics(content)

        assert "neo4j" in topics
        assert "database" in topics
        assert "memory" in topics

    def test_extract_no_topics(self):
        """Test content with no matching topics."""
        extractor = TopicExtractor()

        content = "Hello, how are you today?"
        topics = extractor.extract_topics(content)

        assert len(topics) == 0

    def test_extract_gmp_entities(self):
        """Test extracting GMP references."""
        extractor = TopicExtractor()

        content = "Working on GMP-57 and GMP-58 today"
        entities = extractor.extract_entities(content)

        gmp_entities = [e for e in entities if e["type"] == "gmp"]
        assert len(gmp_entities) == 2
        assert any(e["value"] == "57" for e in gmp_entities)
        assert any(e["value"] == "58" for e in gmp_entities)

    def test_extract_file_entities(self):
        """Test extracting file paths."""
        extractor = TopicExtractor()

        content = "Check the file at /Users/test/memory/graph_memory.py"
        entities = extractor.extract_entities(content)

        file_entities = [e for e in entities if e["type"] == "file"]
        assert len(file_entities) == 1
        assert "graph_memory.py" in file_entities[0]["value"]

    def test_extract_function_entities(self):
        """Test extracting function definitions."""
        extractor = TopicExtractor()

        content = "def store_message(content): pass"
        entities = extractor.extract_entities(content)

        func_entities = [e for e in entities if e["type"] == "function"]
        assert len(func_entities) == 1
        assert func_entities[0]["value"] == "store_message"


class TestGraphMessage:
    """Test GraphMessage data class."""

    def test_message_creation(self):
        """Test creating a message."""
        message = GraphMessage(
            content="Hello world",
            role=MessageRole.USER,
            user_id="user-123",
        )

        assert message.content == "Hello world"
        assert message.role == MessageRole.USER
        assert message.user_id == "user-123"
        assert message.message_id is not None

    def test_message_with_topics(self):
        """Test message with topics."""
        message = GraphMessage(
            content="Test",
            topics=["memory", "database"],
        )

        assert "memory" in message.topics
        assert "database" in message.topics


class TestConversationContext:
    """Test ConversationContext data class."""

    def test_empty_context(self):
        """Test empty context formatting."""
        context = ConversationContext()

        prompt = context.to_prompt_context()

        assert "No relevant conversation history" in prompt

    def test_context_with_messages(self):
        """Test context with messages formatting."""
        context = ConversationContext(
            messages=[
                GraphMessage(
                    content="What is memory?",
                    role=MessageRole.USER,
                ),
                GraphMessage(
                    content="Memory is a storage system.",
                    role=MessageRole.ASSISTANT,
                ),
            ],
            topics=["memory"],
        )

        prompt = context.to_prompt_context()

        assert "Conversation History" in prompt
        assert "USER" in prompt
        assert "ASSISTANT" in prompt
        assert "What is memory?" in prompt
        assert "memory" in prompt.lower()


class TestConversationGraphMemory:
    """Test ConversationGraphMemory functionality."""

    @pytest.mark.asyncio
    async def test_store_message_fallback(self):
        """Test storing message without Neo4j (fallback mode)."""
        memory = ConversationGraphMemory()  # No Neo4j client

        message = await memory.store_message(
            content="How does authentication work?",
            role=MessageRole.USER,
            user_id="user-123",
            session_id=uuid4(),
        )

        assert message is not None
        assert message.content == "How does authentication work?"
        assert message.user_id == "user-123"
        assert "authentication" in message.topics

    @pytest.mark.asyncio
    async def test_store_conversation(self):
        """Test storing multiple messages as conversation."""
        memory = ConversationGraphMemory()

        messages = [
            {"content": "What is Neo4j?", "role": "user"},
            {"content": "Neo4j is a graph database.", "role": "assistant"},
            {"content": "How do I query it?", "role": "user"},
        ]

        stored = await memory.store_conversation(
            messages=messages,
            user_id="user-456",
        )

        assert len(stored) == 3
        assert stored[0].role == MessageRole.USER
        assert stored[1].role == MessageRole.ASSISTANT

    @pytest.mark.asyncio
    async def test_query_history_fallback(self):
        """Test querying history without Neo4j."""
        memory = ConversationGraphMemory()

        # Store some messages first
        session_id = uuid4()
        await memory.store_message(
            content="Tell me about memory systems",
            role=MessageRole.USER,
            user_id="user-789",
            session_id=session_id,
        )
        await memory.store_message(
            content="Memory systems store data...",
            role=MessageRole.ASSISTANT,
            user_id="user-789",
            session_id=session_id,
        )

        # Query history
        context = await memory.query_user_history(
            user_id="user-789",
            topic="memory",
        )

        assert len(context.messages) > 0
        assert any("memory" in m.content.lower() for m in context.messages)

    @pytest.mark.asyncio
    async def test_query_history_no_topic(self):
        """Test querying all history without topic filter."""
        memory = ConversationGraphMemory()

        session_id = uuid4()
        await memory.store_message(
            content="First message",
            role=MessageRole.USER,
            user_id="user-all",
            session_id=session_id,
        )
        await memory.store_message(
            content="Second message",
            role=MessageRole.USER,
            user_id="user-all",
            session_id=session_id,
        )

        context = await memory.query_user_history(user_id="user-all")

        assert len(context.messages) == 2

    @pytest.mark.asyncio
    async def test_get_conversation_context(self):
        """Test getting context for a session."""
        memory = ConversationGraphMemory()

        session_id = uuid4()
        await memory.store_message(
            content="Question about deployment",
            role=MessageRole.USER,
            session_id=session_id,
        )
        await memory.store_message(
            content="Deployment involves...",
            role=MessageRole.ASSISTANT,
            session_id=session_id,
        )

        context = await memory.get_conversation_context(session_id)

        assert len(context.messages) == 2
        assert "deployment" in context.topics

    @pytest.mark.asyncio
    async def test_topic_extraction_on_store(self):
        """Test that topics are extracted when storing."""
        memory = ConversationGraphMemory()

        message = await memory.store_message(
            content="I need help with Neo4j database queries and the memory system",
            role=MessageRole.USER,
        )

        assert "neo4j" in message.topics
        assert "database" in message.topics
        assert "memory" in message.topics


class TestConversationGraphMemoryWithNeo4j:
    """Test ConversationGraphMemory with mock Neo4j."""

    @pytest.mark.asyncio
    async def test_store_message_neo4j(self):
        """Test storing message with Neo4j."""
        mock_neo4j = MagicMock()
        mock_neo4j.is_available.return_value = True
        mock_neo4j.run_query = AsyncMock(return_value=[])

        memory = ConversationGraphMemory(neo4j_client=mock_neo4j)

        message = await memory.store_message(
            content="Test with Neo4j",
            role=MessageRole.USER,
            user_id="user-neo",
            session_id=uuid4(),
        )

        assert message is not None
        assert mock_neo4j.run_query.called

    @pytest.mark.asyncio
    async def test_query_history_neo4j(self):
        """Test querying history from Neo4j."""
        mock_neo4j = MagicMock()
        mock_neo4j.is_available.return_value = True
        mock_neo4j.run_query = AsyncMock(
            return_value=[
                {
                    "id": str(uuid4()),
                    "content": "Test message",
                    "role": "user",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "session_id": str(uuid4()),
                }
            ]
        )

        memory = ConversationGraphMemory(neo4j_client=mock_neo4j)

        context = await memory.query_user_history(user_id="user-neo")

        assert len(context.messages) > 0

    @pytest.mark.asyncio
    async def test_find_related_topics_neo4j(self):
        """Test finding related topics."""
        mock_neo4j = MagicMock()
        mock_neo4j.is_available.return_value = True
        mock_neo4j.run_query = AsyncMock(
            return_value=[
                {"related_topic": "database", "co_occurrences": 5},
                {"related_topic": "graph", "co_occurrences": 3},
            ]
        )

        memory = ConversationGraphMemory(neo4j_client=mock_neo4j)

        related = await memory.find_related_topics("neo4j")

        assert "database" in related
        assert "graph" in related

    @pytest.mark.asyncio
    async def test_link_sessions(self):
        """Test linking related sessions."""
        mock_neo4j = MagicMock()
        mock_neo4j.is_available.return_value = True
        mock_neo4j.run_query = AsyncMock(return_value=[])

        memory = ConversationGraphMemory(neo4j_client=mock_neo4j)

        result = await memory.link_related_sessions(
            session_id_1=uuid4(),
            session_id_2=uuid4(),
        )

        assert result is True


class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    @pytest.mark.asyncio
    async def test_get_graph_memory_singleton(self):
        """Test singleton behavior."""
        # Reset singleton
        import memory.graph_memory

        memory.graph_memory._graph_memory = None

        mem1 = await get_graph_memory()
        mem2 = await get_graph_memory()

        assert mem1 is mem2

    @pytest.mark.asyncio
    async def test_store_message_convenience(self):
        """Test store_message convenience function."""
        # Reset singleton
        import memory.graph_memory

        memory.graph_memory._graph_memory = None

        message = await store_message(
            content="Convenience function test",
            role="user",
            user_id="conv-user",
        )

        assert message is not None
        assert message.content == "Convenience function test"

    @pytest.mark.asyncio
    async def test_query_history_convenience(self):
        """Test query_history convenience function."""
        # Reset singleton and store a message first
        import memory.graph_memory

        memory.graph_memory._graph_memory = None

        await store_message(
            content="History test message",
            user_id="hist-user",
        )

        context = await query_history(user_id="hist-user")

        assert isinstance(context, ConversationContext)


class TestMessageRole:
    """Test MessageRole enum."""

    def test_role_values(self):
        """Test role enum values."""
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"
        assert MessageRole.SYSTEM.value == "system"
        assert MessageRole.TOOL.value == "tool"

    def test_role_from_string(self):
        """Test creating role from string."""
        role = MessageRole("user")
        assert role == MessageRole.USER
