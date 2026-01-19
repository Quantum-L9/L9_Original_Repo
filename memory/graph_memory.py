"""
L9 Memory - Conversational Graph Memory
========================================

Store chat history as a graph in Neo4j for cross-session context.

Instead of storing chat as a simple list in Postgres, this creates
a rich graph structure with relationships like:
  - (:User)-[:PARTICIPATED_IN]->(:Session)
  - (:Session)-[:CONTAINS]->(:Message)
  - (:Message)-[:FOLLOWS]->(:Message)
  - (:Message)-[:MENTIONS]->(:Topic)

Benefits:
- Cross-session context: "What did I ask about last week?"
- Topic traversal: Find all conversations about a topic
- Relationship discovery: Connect related sessions
- Temporal queries: Trace conversation evolution

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Conversational Graph Memory",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-13T18:30:12Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "data_models",
    "module_name": "graph_memory",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j"],
        "memory_layers": ["semantic_memory"],
        "imported_by": ["memory.__init__", "tests.memory.test_graph_memory"],
    },
}
# ============================================================================

import re
import structlog
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


# =============================================================================
# Enums and Constants
# =============================================================================


class MessageRole(str, Enum):
    """Role of message sender."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class RelationshipType(str, Enum):
    """Graph relationship types."""

    PARTICIPATED_IN = "PARTICIPATED_IN"
    CONTAINS = "CONTAINS"
    FOLLOWS = "FOLLOWS"
    MENTIONS = "MENTIONS"
    REFERENCES = "REFERENCES"
    RELATED_TO = "RELATED_TO"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class GraphMessage:
    """Message stored in the graph."""

    message_id: UUID = field(default_factory=uuid4)
    content: str = ""
    role: MessageRole = MessageRole.USER
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Context
    session_id: Optional[UUID] = None
    user_id: Optional[str] = None

    # Extracted data
    topics: list[str] = field(default_factory=list)
    entities: list[dict[str, Any]] = field(default_factory=list)

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphSession:
    """Conversation session in the graph."""

    session_id: UUID = field(default_factory=uuid4)
    user_id: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None

    # Summary
    title: Optional[str] = None
    summary: Optional[str] = None
    message_count: int = 0

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationContext:
    """Retrieved conversation context."""

    messages: list[GraphMessage] = field(default_factory=list)
    related_sessions: list[GraphSession] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)

    # Query info
    query: Optional[str] = None
    user_id: Optional[str] = None
    time_range_start: Optional[datetime] = None
    time_range_end: Optional[datetime] = None

    def to_prompt_context(self) -> str:
        """Format as prompt context."""
        if not self.messages:
            return "No relevant conversation history found."

        lines = ["## Conversation History", ""]

        for msg in self.messages[-10:]:  # Last 10 messages
            role = msg.role.value.upper()
            timestamp = msg.timestamp.strftime("%Y-%m-%d %H:%M")
            lines.append(f"**[{timestamp}] {role}:** {msg.content[:500]}")

        if self.topics:
            lines.extend(["", f"**Related topics:** {', '.join(self.topics)}"])

        return "\n".join(lines)


# =============================================================================
# Topic Extractor
# =============================================================================


class TopicExtractor:
    """
    Extract topics from message content.

    Uses simple pattern matching (not NLP) for speed.
    """

    # Common topics to look for
    KNOWN_TOPICS = {
        "memory",
        "database",
        "neo4j",
        "postgres",
        "api",
        "authentication",
        "deployment",
        "docker",
        "testing",
        "debugging",
        "performance",
        "agent",
        "kernel",
        "executor",
        "tool",
        "graph",
        "vector",
        "embedding",
        "search",
        "query",
        "schema",
        "migration",
    }

    # Patterns for entity extraction
    PATTERNS = {
        "gmp": r"GMP-(\d+)",
        "file": r"(?:/[\w.-]+)+\.(?:py|ts|js|yaml|yml|json|md)",
        "function": r"(?:def|function|async def)\s+(\w+)",
        "class": r"class\s+(\w+)",
    }

    def extract_topics(self, content: str) -> list[str]:
        """Extract topics from content."""
        content_lower = content.lower()
        topics = []

        for topic in self.KNOWN_TOPICS:
            if topic in content_lower:
                topics.append(topic)

        return list(set(topics))

    def extract_entities(self, content: str) -> list[dict[str, Any]]:
        """Extract entities from content."""
        entities = []

        for entity_type, pattern in self.PATTERNS.items():
            for match in re.finditer(pattern, content, re.IGNORECASE):
                entities.append(
                    {
                        "type": entity_type,
                        "value": match.group(1) if match.groups() else match.group(),
                    }
                )

        return entities


# =============================================================================
# Graph Memory Service
# =============================================================================


class ConversationGraphMemory:
    """
    Store and query conversation history as a Neo4j graph.

    Usage:
        memory = ConversationGraphMemory(neo4j_client)

        # Store a message
        await memory.store_message(
            user_id="user-123",
            session_id=session_id,
            content="How does authentication work?",
            role=MessageRole.USER,
        )

        # Query history
        context = await memory.query_user_history(
            user_id="user-123",
            topic="authentication",
        )

        # Get conversation context
        context = await memory.get_conversation_context(session_id)
    """

    def __init__(
        self,
        neo4j_client: Optional[Any] = None,
        topic_extractor: Optional[TopicExtractor] = None,
    ):
        """
        Initialize graph memory.

        Args:
            neo4j_client: Neo4jClient for graph operations
            topic_extractor: Optional custom topic extractor
        """
        self._neo4j = neo4j_client
        self._extractor = topic_extractor or TopicExtractor()

        # In-memory fallback for testing
        self._memory_fallback: dict[str, list[GraphMessage]] = {}
        self._sessions_fallback: dict[str, GraphSession] = {}

        logger.info("ConversationGraphMemory initialized")

    def _is_available(self) -> bool:
        """Check if Neo4j is available."""
        return self._neo4j is not None and self._neo4j.is_available()

    async def store_message(
        self,
        content: str,
        role: MessageRole = MessageRole.USER,
        user_id: Optional[str] = None,
        session_id: Optional[UUID] = None,
        previous_message_id: Optional[UUID] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> GraphMessage:
        """
        Store a message in the graph.

        Creates nodes and relationships:
        - (:Message) node
        - (:User)-[:PARTICIPATED_IN]->(:Session)
        - (:Session)-[:CONTAINS]->(:Message)
        - (:Message)-[:FOLLOWS]->(:Message)
        - (:Message)-[:MENTIONS]->(:Topic)

        Args:
            content: Message content
            role: Message role (user/assistant/system/tool)
            user_id: User identifier
            session_id: Session identifier
            previous_message_id: Previous message for FOLLOWS relationship
            metadata: Additional metadata

        Returns:
            GraphMessage with extracted topics and entities
        """
        # Create message
        message = GraphMessage(
            content=content,
            role=role,
            user_id=user_id,
            session_id=session_id,
            metadata=metadata or {},
        )

        # Extract topics and entities
        message.topics = self._extractor.extract_topics(content)
        message.entities = self._extractor.extract_entities(content)

        if self._is_available():
            await self._store_message_neo4j(message, previous_message_id)
        else:
            self._store_message_fallback(message)

        logger.debug(
            "Stored message",
            message_id=str(message.message_id),
            topics=message.topics,
        )

        return message

    async def _store_message_neo4j(
        self,
        message: GraphMessage,
        previous_message_id: Optional[UUID],
    ) -> None:
        """Store message in Neo4j."""
        # Ensure session exists
        if message.session_id:
            await self._ensure_session_exists(message.session_id, message.user_id)

        # Create message node
        query = """
        CREATE (m:Message {
            id: $message_id,
            content: $content,
            role: $role,
            timestamp: datetime($timestamp),
            user_id: $user_id,
            session_id: $session_id
        })
        RETURN m.id as id
        """

        await self._neo4j.run_query(
            query,
            {
                "message_id": str(message.message_id),
                "content": message.content[:5000],  # Limit content size
                "role": message.role.value,
                "timestamp": message.timestamp.isoformat(),
                "user_id": message.user_id,
                "session_id": str(message.session_id) if message.session_id else None,
            },
        )

        # Create FOLLOWS relationship
        if previous_message_id:
            await self._neo4j.run_query(
                """
                MATCH (prev:Message {id: $prev_id})
                MATCH (curr:Message {id: $curr_id})
                MERGE (curr)-[:FOLLOWS]->(prev)
            """,
                {
                    "prev_id": str(previous_message_id),
                    "curr_id": str(message.message_id),
                },
            )

        # Create Session CONTAINS Message relationship
        if message.session_id:
            await self._neo4j.run_query(
                """
                MATCH (s:Session {id: $session_id})
                MATCH (m:Message {id: $message_id})
                MERGE (s)-[:CONTAINS]->(m)
            """,
                {
                    "session_id": str(message.session_id),
                    "message_id": str(message.message_id),
                },
            )

        # Create Topic nodes and MENTIONS relationships
        for topic in message.topics:
            await self._neo4j.run_query(
                """
                MERGE (t:Topic {name: $topic})
                WITH t
                MATCH (m:Message {id: $message_id})
                MERGE (m)-[:MENTIONS]->(t)
            """,
                {
                    "topic": topic,
                    "message_id": str(message.message_id),
                },
            )

    async def _ensure_session_exists(
        self,
        session_id: UUID,
        user_id: Optional[str],
    ) -> None:
        """Ensure session and user nodes exist."""
        # Create session
        await self._neo4j.run_query(
            """
            MERGE (s:Session {id: $session_id})
            ON CREATE SET s.started_at = datetime()
        """,
            {"session_id": str(session_id)},
        )

        # Create user and relationship
        if user_id:
            await self._neo4j.run_query(
                """
                MERGE (u:User {id: $user_id})
                WITH u
                MATCH (s:Session {id: $session_id})
                MERGE (u)-[:PARTICIPATED_IN]->(s)
            """,
                {
                    "user_id": user_id,
                    "session_id": str(session_id),
                },
            )

    def _store_message_fallback(self, message: GraphMessage) -> None:
        """Store message in memory fallback."""
        session_key = str(message.session_id) if message.session_id else "default"

        if session_key not in self._memory_fallback:
            self._memory_fallback[session_key] = []

        self._memory_fallback[session_key].append(message)

    async def store_conversation(
        self,
        messages: list[dict[str, Any]],
        user_id: Optional[str] = None,
        session_id: Optional[UUID] = None,
    ) -> list[GraphMessage]:
        """
        Store multiple messages as a conversation.

        Args:
            messages: List of {content, role} dicts
            user_id: User identifier
            session_id: Session identifier (generated if not provided)

        Returns:
            List of stored GraphMessages
        """
        session_id = session_id or uuid4()
        stored: list[GraphMessage] = []
        previous_id: Optional[UUID] = None

        for msg in messages:
            content = msg.get("content", "")
            role = MessageRole(msg.get("role", "user"))

            graph_msg = await self.store_message(
                content=content,
                role=role,
                user_id=user_id,
                session_id=session_id,
                previous_message_id=previous_id,
            )

            stored.append(graph_msg)
            previous_id = graph_msg.message_id

        logger.info(f"Stored conversation with {len(stored)} messages")
        return stored

    async def query_user_history(
        self,
        user_id: str,
        topic: Optional[str] = None,
        time_range_days: int = 30,
        limit: int = 20,
    ) -> ConversationContext:
        """
        Query user's conversation history.

        "What did I ask about [topic] recently?"

        Args:
            user_id: User identifier
            topic: Optional topic filter
            time_range_days: How far back to search
            limit: Maximum messages to return

        Returns:
            ConversationContext with matching messages
        """
        context = ConversationContext(
            user_id=user_id,
            query=topic,
        )

        if self._is_available():
            context = await self._query_history_neo4j(
                user_id, topic, time_range_days, limit
            )
        else:
            context = self._query_history_fallback(
                user_id, topic, time_range_days, limit
            )

        return context

    async def _query_history_neo4j(
        self,
        user_id: str,
        topic: Optional[str],
        time_range_days: int,
        limit: int,
    ) -> ConversationContext:
        """Query history from Neo4j."""
        context = ConversationContext(user_id=user_id, query=topic)

        if topic:
            # Query with topic filter
            query = """
            MATCH (u:User {id: $user_id})-[:PARTICIPATED_IN]->(s:Session)-[:CONTAINS]->(m:Message)
            WHERE m.timestamp > datetime() - duration({days: $days})
            OPTIONAL MATCH (m)-[:MENTIONS]->(t:Topic {name: $topic})
            WHERE t IS NOT NULL
            RETURN m.id as id, m.content as content, m.role as role, 
                   m.timestamp as timestamp, s.id as session_id
            ORDER BY m.timestamp DESC
            LIMIT $limit
            """
            params = {
                "user_id": user_id,
                "topic": topic.lower(),
                "days": time_range_days,
                "limit": limit,
            }
        else:
            # Query without topic filter
            query = """
            MATCH (u:User {id: $user_id})-[:PARTICIPATED_IN]->(s:Session)-[:CONTAINS]->(m:Message)
            WHERE m.timestamp > datetime() - duration({days: $days})
            RETURN m.id as id, m.content as content, m.role as role,
                   m.timestamp as timestamp, s.id as session_id
            ORDER BY m.timestamp DESC
            LIMIT $limit
            """
            params = {
                "user_id": user_id,
                "days": time_range_days,
                "limit": limit,
            }

        try:
            results = await self._neo4j.run_query(query, params)

            for r in results:
                context.messages.append(
                    GraphMessage(
                        message_id=UUID(r["id"]) if r.get("id") else uuid4(),
                        content=r.get("content", ""),
                        role=MessageRole(r.get("role", "user")),
                        session_id=UUID(r["session_id"])
                        if r.get("session_id")
                        else None,
                    )
                )

            # Get related topics
            if context.messages:
                topic_query = """
                MATCH (u:User {id: $user_id})-[:PARTICIPATED_IN]->(:Session)-[:CONTAINS]->(m:Message)-[:MENTIONS]->(t:Topic)
                RETURN DISTINCT t.name as topic
                LIMIT 10
                """
                topic_results = await self._neo4j.run_query(
                    topic_query, {"user_id": user_id}
                )
                context.topics = [r["topic"] for r in topic_results if r.get("topic")]

        except Exception as e:
            logger.error(f"Neo4j history query failed: {e}")

        return context

    def _query_history_fallback(
        self,
        user_id: str,
        topic: Optional[str],
        time_range_days: int,
        limit: int,
    ) -> ConversationContext:
        """Query history from memory fallback."""
        context = ConversationContext(user_id=user_id, query=topic)

        all_messages: list[GraphMessage] = []
        for messages in self._memory_fallback.values():
            all_messages.extend(messages)

        # Filter by user
        user_messages = [m for m in all_messages if m.user_id == user_id]

        # Filter by topic if provided
        if topic:
            topic_lower = topic.lower()
            user_messages = [
                m
                for m in user_messages
                if topic_lower in m.content.lower() or topic_lower in m.topics
            ]

        # Sort by timestamp and limit
        user_messages.sort(key=lambda m: m.timestamp, reverse=True)
        context.messages = user_messages[:limit]

        # Collect topics
        topics = set()
        for m in context.messages:
            topics.update(m.topics)
        context.topics = list(topics)

        return context

    async def get_conversation_context(
        self,
        session_id: UUID,
        limit: int = 20,
    ) -> ConversationContext:
        """
        Get context for a specific conversation session.

        Args:
            session_id: Session identifier
            limit: Maximum messages to return

        Returns:
            ConversationContext with session messages
        """
        context = ConversationContext()

        if self._is_available():
            query = """
            MATCH (s:Session {id: $session_id})-[:CONTAINS]->(m:Message)
            OPTIONAL MATCH (m)-[:MENTIONS]->(t:Topic)
            RETURN m.id as id, m.content as content, m.role as role,
                   m.timestamp as timestamp, collect(DISTINCT t.name) as topics
            ORDER BY m.timestamp ASC
            LIMIT $limit
            """

            try:
                results = await self._neo4j.run_query(
                    query,
                    {
                        "session_id": str(session_id),
                        "limit": limit,
                    },
                )

                all_topics = set()
                for r in results:
                    msg = GraphMessage(
                        message_id=UUID(r["id"]) if r.get("id") else uuid4(),
                        content=r.get("content", ""),
                        role=MessageRole(r.get("role", "user")),
                        session_id=session_id,
                        topics=r.get("topics", []),
                    )
                    context.messages.append(msg)
                    all_topics.update(msg.topics)

                context.topics = list(all_topics)

            except Exception as e:
                logger.error(f"Neo4j context query failed: {e}")
        else:
            # Fallback
            session_key = str(session_id)
            if session_key in self._memory_fallback:
                context.messages = self._memory_fallback[session_key][:limit]

                topics = set()
                for m in context.messages:
                    topics.update(m.topics)
                context.topics = list(topics)

        return context

    async def find_related_topics(
        self,
        topic: str,
        limit: int = 10,
    ) -> list[str]:
        """
        Find topics related to a given topic.

        Traverses the graph to find co-occurring topics.

        Args:
            topic: Topic to find relations for
            limit: Maximum topics to return

        Returns:
            List of related topic names
        """
        if not self._is_available():
            return []

        query = """
        MATCH (t1:Topic {name: $topic})<-[:MENTIONS]-(m:Message)-[:MENTIONS]->(t2:Topic)
        WHERE t1 <> t2
        RETURN t2.name as related_topic, count(m) as co_occurrences
        ORDER BY co_occurrences DESC
        LIMIT $limit
        """

        try:
            results = await self._neo4j.run_query(
                query,
                {
                    "topic": topic.lower(),
                    "limit": limit,
                },
            )

            return [r["related_topic"] for r in results if r.get("related_topic")]

        except Exception as e:
            logger.error(f"Related topics query failed: {e}")
            return []

    async def link_related_sessions(
        self,
        session_id_1: UUID,
        session_id_2: UUID,
        relationship_type: str = "RELATED_TO",
    ) -> bool:
        """
        Create a relationship between two sessions.

        Args:
            session_id_1: First session
            session_id_2: Second session
            relationship_type: Type of relationship

        Returns:
            True if relationship created
        """
        if not self._is_available():
            return False

        try:
            await self._neo4j.run_query(
                f"""
                MATCH (s1:Session {{id: $id1}})
                MATCH (s2:Session {{id: $id2}})
                MERGE (s1)-[:{relationship_type}]->(s2)
            """,
                {
                    "id1": str(session_id_1),
                    "id2": str(session_id_2),
                },
            )
            return True
        except Exception as e:
            logger.error(f"Session linking failed: {e}")
            return False


# =============================================================================
# Singleton Factory
# =============================================================================


_graph_memory: Optional[ConversationGraphMemory] = None


@must_stay_async("callers use await")
async def get_graph_memory(
    neo4j_client: Optional[Any] = None,
) -> ConversationGraphMemory:
    """Get or create singleton graph memory."""
    global _graph_memory

    if _graph_memory is None:
        _graph_memory = ConversationGraphMemory(neo4j_client=neo4j_client)

    return _graph_memory


async def store_message(
    content: str,
    role: str = "user",
    user_id: Optional[str] = None,
    session_id: Optional[UUID] = None,
) -> GraphMessage:
    """Convenience function to store a message."""
    memory = await get_graph_memory()
    return await memory.store_message(
        content=content,
        role=MessageRole(role),
        user_id=user_id,
        session_id=session_id,
    )


async def query_history(
    user_id: str,
    topic: Optional[str] = None,
    limit: int = 20,
) -> ConversationContext:
    """Convenience function to query history."""
    memory = await get_graph_memory()
    return await memory.query_user_history(
        user_id=user_id,
        topic=topic,
        limit=limit,
    )


__all__ = [
    # Enums
    "MessageRole",
    "RelationshipType",
    # Data classes
    "GraphMessage",
    "GraphSession",
    "ConversationContext",
    # Main class
    "ConversationGraphMemory",
    "TopicExtractor",
    # Factory functions
    "get_graph_memory",
    "store_message",
    "query_history",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-051",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": [
        "api",
        "async",
        "auth",
        "data-models",
        "dataclass",
        "debugging",
        "graph-db",
        "learning",
        "logging",
        "messaging",
    ],
    "keywords": [
        "about",
        "chat",
        "conversation",
        "conversational",
        "cross",
        "entities",
        "extract",
        "extractor",
    ],
    "business_value": "Provides graph memory components including MessageRole, RelationshipType, GraphMessage",
    "last_modified": "2026-01-17T23:47:56Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
