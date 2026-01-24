"""
L9 Facade - Simplified API for L9 AIOS

Implements the Facade design pattern to provide a simple, unified interface
to the complex L9 AIOS subsystems. This makes it easier for developers to
interact with L9 without needing to understand all internal details.

Benefits:
- Simple, intuitive API for common operations
- Hides complexity of internal subsystems
- Reduces learning curve for new developers
- Provides sensible defaults
- Easier to maintain and evolve internal architecture

Usage:
    from core.facade.l9_facade import L9
    
    # Initialize L9 with defaults
    l9 = L9()
    
    # Run a task with L-CTO agent
    result = await l9.run_task(
        "Research async patterns in Python",
        agent="l-cto"
    )
    
    # Create a new agent
    agent = l9.create_agent(
        name="CustomAgent",
        role="Data Analyst",
        capabilities=["analysis", "visualization"]
    )
    
    # Query memory
    memories = await l9.query_memory(
        "What did we learn about async patterns?",
        agent_id="l-cto"
    )
    
    # Execute a tool
    result = await l9.execute_tool(
        "slack_send",
        channel="#general",
        message="Task complete!"
    )
"""

import asyncio
from typing import Any, Dict, List, Optional

import structlog

from core.agents.base_agent import BaseAgent
from core.coordination.agent_mediator import get_mediator
from core.patterns.singleton import singleton
from core.schemas.packet_envelope import PacketEnvelope
from core.tools.registry_adapter import ExecutorToolRegistry
from memory.client import MemoryClient

logger = structlog.get_logger(__name__)


@singleton
class L9:
    """
    Simplified facade for L9 AIOS.
    
    Provides a clean, simple API for common L9 operations without
    requiring deep knowledge of internal subsystems.
    """
    
    def __init__(self):
        """Initialize L9 facade with default configuration."""
        self._agents: Dict[str, BaseAgent] = {}
        self._mediator = get_mediator()
        self._tool_registry = ExecutorToolRegistry()
        self._memory_client: Optional[MemoryClient] = None
        self._initialized = False
        
        logger.info("L9 Facade initialized")
    
    async def initialize(
        self,
        memory_enabled: bool = True,
        tool_registry_enabled: bool = True
    ) -> None:
        """
        Initialize L9 subsystems.
        
        Args:
            memory_enabled: Whether to enable memory substrate
            tool_registry_enabled: Whether to enable tool registry
        """
        if self._initialized:
            logger.warning("L9 already initialized")
            return
        
        # Initialize memory client
        if memory_enabled:
            try:
                self._memory_client = MemoryClient()
                logger.info("Memory client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize memory client: {e}")
        
        # Tool registry is already initialized in __init__
        if tool_registry_enabled:
            logger.info("Tool registry enabled")
        
        self._initialized = True
        logger.info("L9 initialization complete")
    
    def register_agent(self, agent_id: str, agent: BaseAgent) -> None:
        """
        Register an agent with L9.
        
        Args:
            agent_id: Unique agent identifier
            agent: Agent instance
        """
        self._agents[agent_id] = agent
        self._mediator.register_agent(agent_id, agent)
        logger.info(f"Agent registered: {agent_id}")
    
    async def run_task(
        self,
        task: str,
        agent: str = "l-cto",
        context: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> PacketEnvelope:
        """
        Run a task with a specified agent.
        
        Args:
            task: Task description
            agent: Agent ID to run the task (default: "l-cto")
            context: Additional context for the task
            timeout: Timeout in seconds (None = no timeout)
            
        Returns:
            PacketEnvelope with task result
            
        Raises:
            ValueError: If agent not found
            TimeoutError: If task exceeds timeout
        """
        if agent not in self._agents:
            raise ValueError(f"Agent '{agent}' not registered")
        
        logger.info(f"Running task with {agent}", task=task)
        
        agent_instance = self._agents[agent]
        
        # Run with timeout if specified
        if timeout:
            try:
                result = await asyncio.wait_for(
                    agent_instance.run(task, context or {}),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                raise TimeoutError(f"Task exceeded timeout of {timeout}s")
        else:
            result = await agent_instance.run(task, context or {})
        
        return result
    
    async def send_message(
        self,
        from_agent: str,
        to_agent: str,
        message: Dict[str, Any],
        message_type: str = "generic"
    ) -> str:
        """
        Send a message between agents.
        
        Args:
            from_agent: Sender agent ID
            to_agent: Recipient agent ID
            message: Message payload
            message_type: Type of message
            
        Returns:
            Message ID
        """
        return await self._mediator.send_message(
            from_agent=from_agent,
            to_agent=to_agent,
            message=message,
            message_type=message_type
        )
    
    async def broadcast(
        self,
        from_agent: str,
        message: Dict[str, Any],
        message_type: str = "broadcast"
    ) -> List[str]:
        """
        Broadcast a message to all agents.
        
        Args:
            from_agent: Sender agent ID
            message: Message payload
            message_type: Type of message
            
        Returns:
            List of message IDs
        """
        return await self._mediator.broadcast(
            from_agent=from_agent,
            message=message,
            message_type=message_type
        )
    
    async def execute_tool(
        self,
        tool_name: str,
        **kwargs
    ) -> Any:
        """
        Execute a tool by name.
        
        Args:
            tool_name: Name of tool to execute
            **kwargs: Tool arguments
            
        Returns:
            Tool execution result
            
        Raises:
            ValueError: If tool not found
        """
        logger.info(f"Executing tool: {tool_name}")
        
        # Get tool from registry
        tool = self._tool_registry._registry.get(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        # Execute tool
        result = await self._tool_registry.dispatch_tool_call(
            tool_id=tool_name,
            arguments=kwargs,
            agent_id="l9-facade"
        )
        
        return result
    
    async def query_memory(
        self,
        query: str,
        agent_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Query the memory substrate.
        
        Args:
            query: Search query
            agent_id: Filter by agent ID (None = all agents)
            limit: Maximum number of results
            
        Returns:
            List of memory entries
            
        Raises:
            RuntimeError: If memory client not initialized
        """
        if not self._memory_client:
            raise RuntimeError("Memory client not initialized")
        
        logger.info(f"Querying memory", query=query, agent_id=agent_id)
        
        # Query memory (simplified - actual implementation may vary)
        results = await self._memory_client.search(
            query=query,
            agent_id=agent_id,
            limit=limit
        )
        
        return results
    
    async def store_memory(
        self,
        agent_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store a memory entry.
        
        Args:
            agent_id: Agent ID
            content: Memory content
            metadata: Additional metadata
            
        Returns:
            Memory entry ID
            
        Raises:
            RuntimeError: If memory client not initialized
        """
        if not self._memory_client:
            raise RuntimeError("Memory client not initialized")
        
        logger.info(f"Storing memory for {agent_id}")
        
        # Store memory (simplified - actual implementation may vary)
        memory_id = await self._memory_client.store(
            agent_id=agent_id,
            content=content,
            metadata=metadata or {}
        )
        
        return memory_id
    
    def list_agents(self) -> List[str]:
        """
        List all registered agents.
        
        Returns:
            List of agent IDs
        """
        return list(self._agents.keys())
    
    def list_tools(self) -> List[str]:
        """
        List all available tools.
        
        Returns:
            List of tool names
        """
        return list(self._tool_registry._registry.keys())
    
    def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """
        Get status of an agent.
        
        Args:
            agent_id: Agent to check
            
        Returns:
            Agent status dictionary
        """
        if agent_id not in self._agents:
            return {"exists": False}
        
        return {
            "exists": True,
            "online": self._mediator.get_agent_status(agent_id),
            "queued_messages": self._mediator.get_queued_message_count(agent_id)
        }
    
    async def shutdown(self) -> None:
        """Gracefully shutdown L9 and all subsystems."""
        logger.info("Shutting down L9")
        
        # Unregister all agents
        for agent_id in list(self._agents.keys()):
            self._mediator.unregister_agent(agent_id)
        
        # Close memory client
        if self._memory_client:
            await self._memory_client.close()
        
        logger.info("L9 shutdown complete")


# Convenience functions for quick access

async def run_task(task: str, agent: str = "l-cto", **kwargs) -> PacketEnvelope:
    """
    Quick function to run a task with L9.
    
    Args:
        task: Task description
        agent: Agent ID (default: "l-cto")
        **kwargs: Additional arguments
        
    Returns:
        Task result
    """
    l9 = L9()
    if not l9._initialized:
        await l9.initialize()
    return await l9.run_task(task, agent, **kwargs)


async def execute_tool(tool_name: str, **kwargs) -> Any:
    """
    Quick function to execute a tool.
    
    Args:
        tool_name: Tool to execute
        **kwargs: Tool arguments
        
    Returns:
        Tool result
    """
    l9 = L9()
    if not l9._initialized:
        await l9.initialize()
    return await l9.execute_tool(tool_name, **kwargs)


async def query_memory(query: str, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Quick function to query memory.
    
    Args:
        query: Search query
        agent_id: Filter by agent (optional)
        
    Returns:
        Memory results
    """
    l9 = L9()
    if not l9._initialized:
        await l9.initialize()
    return await l9.query_memory(query, agent_id)
