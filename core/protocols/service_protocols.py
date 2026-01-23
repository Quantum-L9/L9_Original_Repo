"""
Service Protocol Interfaces (ADR-0026)

Defines Protocol-based abstractions for key L9 services to enable
dependency inversion and loose coupling.

Usage:
    from core.protocols import MemoryService, LLMService
    
    class MyAgent:
        def __init__(self, memory: MemoryService, llm: LLMService):
            self.memory = memory
            self.llm = llm
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "ServiceProtocols",
    "module_version": "1.0.0",
    "layer": "Core/Protocols",
    "adr": "ADR-0026",
    "criticality": "high",
    "observability": {
        "metrics": ["protocol_implementations_count"],
        "logs": ["protocol_method_called"],
    },
}
# ============================================================================

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from core.schemas.packet_envelope_v2 import PacketEnvelopeV2


@runtime_checkable
class MemoryService(Protocol):
    """
    Protocol for memory/storage services.
    
    Implementations: SubstrateService, MemoryFacade
    """

    async def store(
        self,
        packet: PacketEnvelopeV2,
        *,
        session_id: str,
        agent_id: str,
    ) -> str:
        """
        Store a packet in memory.
        
        Args:
            packet: The packet to store
            session_id: Session identifier
            agent_id: Agent identifier
            
        Returns:
            Memory ID of stored packet
        """
        ...

    async def retrieve(
        self,
        memory_id: str,
        *,
        session_id: str,
    ) -> Optional[PacketEnvelopeV2]:
        """
        Retrieve a packet from memory by ID.
        
        Args:
            memory_id: Memory identifier
            session_id: Session identifier
            
        Returns:
            Retrieved packet or None if not found
        """
        ...

    async def search(
        self,
        query: str,
        *,
        session_id: str,
        limit: int = 10,
    ) -> List[PacketEnvelopeV2]:
        """
        Search memory using semantic search.
        
        Args:
            query: Search query
            session_id: Session identifier
            limit: Maximum results to return
            
        Returns:
            List of matching packets
        """
        ...


@runtime_checkable
class LLMService(Protocol):
    """
    Protocol for LLM/model services.
    
    Implementations: OpenAIClient, AnthropicClient, LocalLLM
    """

    async def complete(
        self,
        prompt: str,
        *,
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        """
        Generate text completion.
        
        Args:
            prompt: Input prompt
            model: Model identifier
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
        """
        ...

    async def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        model: str = "gpt-4",
        temperature: float = 0.7,
    ) -> str:
        """
        Generate chat completion.
        
        Args:
            messages: List of chat messages
            model: Model identifier
            temperature: Sampling temperature
            
        Returns:
            Generated response
        """
        ...

    async def embed(
        self,
        text: str,
        *,
        model: str = "text-embedding-ada-002",
    ) -> List[float]:
        """
        Generate text embedding.
        
        Args:
            text: Input text
            model: Embedding model identifier
            
        Returns:
            Embedding vector
        """
        ...


@runtime_checkable
class ToolRegistry(Protocol):
    """
    Protocol for tool registry services.
    
    Implementations: DynamicToolRegistry, StaticToolRegistry
    """

    def register_tool(
        self,
        name: str,
        func: Any,
        *,
        description: str,
        parameters: Dict[str, Any],
    ) -> None:
        """
        Register a tool.
        
        Args:
            name: Tool name
            func: Tool function
            description: Tool description
            parameters: Tool parameters schema
        """
        ...

    def get_tool(self, name: str) -> Optional[Any]:
        """
        Get a tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool function or None if not found
        """
        ...

    def list_tools(self) -> List[str]:
        """
        List all registered tool names.
        
        Returns:
            List of tool names
        """
        ...


@runtime_checkable
class GovernanceService(Protocol):
    """
    Protocol for governance/policy services.
    
    Implementations: GovernanceGate, PolicyEnforcer
    """

    async def check_policy(
        self,
        action: str,
        *,
        agent_id: str,
        context: Dict[str, Any],
    ) -> bool:
        """
        Check if action is allowed by policy.
        
        Args:
            action: Action to check
            agent_id: Agent identifier
            context: Action context
            
        Returns:
            True if allowed, False otherwise
        """
        ...

    async def enforce_limits(
        self,
        resource: str,
        *,
        agent_id: str,
        amount: float,
    ) -> bool:
        """
        Enforce resource limits.
        
        Args:
            resource: Resource type (e.g., "tokens", "api_calls")
            agent_id: Agent identifier
            amount: Amount to consume
            
        Returns:
            True if within limits, False otherwise
        """
        ...


@runtime_checkable
class WorldModelService(Protocol):
    """
    Protocol for world model services.
    
    Implementations: WorldModelEngine, GraphWorldModel
    """

    async def update_state(
        self,
        entity: str,
        *,
        properties: Dict[str, Any],
        session_id: str,
    ) -> None:
        """
        Update world model state.
        
        Args:
            entity: Entity identifier
            properties: Entity properties to update
            session_id: Session identifier
        """
        ...

    async def query_state(
        self,
        entity: str,
        *,
        session_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Query world model state.
        
        Args:
            entity: Entity identifier
            session_id: Session identifier
            
        Returns:
            Entity state or None if not found
        """
        ...

    async def query_relationships(
        self,
        entity: str,
        *,
        relationship_type: Optional[str] = None,
        session_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Query entity relationships.
        
        Args:
            entity: Entity identifier
            relationship_type: Filter by relationship type
            session_id: Session identifier
            
        Returns:
            List of relationships
        """
        ...


@runtime_checkable
class CacheService(Protocol):
    """
    Protocol for caching services.
    
    Implementations: RedisCache, MemoryCache
    """

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        ...

    async def set(
        self,
        key: str,
        value: Any,
        *,
        ttl: Optional[int] = None,
    ) -> None:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
        """
        ...

    async def delete(self, key: str) -> None:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
        """
        ...


# Export all protocols
__all__ = [
    "MemoryService",
    "LLMService",
    "ToolRegistry",
    "GovernanceService",
    "WorldModelService",
    "CacheService",
]
