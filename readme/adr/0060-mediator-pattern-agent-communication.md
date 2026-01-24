# ADR 0060: Mediator Pattern for Agent Communication

## Status
Accepted

## Pattern
Agent-to-agent communication via centralized mediator, decoupling agents from direct dependencies.

## Files
- `core/coordination/agent_mediator.py` - Implementation
- `core/coordination/__init__.py` - Exports

## Context

Direct agent-to-agent communication creates tight coupling:
```python
# ❌ WRONG — Direct coupling
class ResearchAgent:
    def __init__(self, cto_agent: CTOAgent):
        self.cto = cto_agent
    
    async def complete_task(self, result):
        await self.cto.receive_result(result)  # Direct dependency
```

The Mediator pattern decouples agents by routing all communication through a central coordinator.

## Import Block
```python
from core.coordination.agent_mediator import (
    AgentMediator,
    get_agent_mediator,
    Message,
    MessageDeliveryStatus,
)
```

## Minimal Implementation
```python
from core.singleton_auto_registry import register_singleton

@register_singleton(
    category="coordination",
    lifecycle=SingletonLifecycle.LAZY,
    description="Agent-to-agent message mediator"
)
async def get_agent_mediator() -> AgentMediator:
    """Get singleton mediator instance."""
    global _mediator_instance
    if _mediator_instance is None:
        _mediator_instance = AgentMediator()
    return _mediator_instance


class AgentMediator:
    """Centralized mediator for agent communication."""
    
    def __init__(self):
        self.agents: dict[str, Any] = {}
        self.subscriptions: dict[str, list[Callable]] = defaultdict(list)
        self.message_queue: dict[str, list[Message]] = defaultdict(list)
    
    def register_agent(self, agent_id: str, agent: Any) -> None:
        """Register agent with mediator."""
        self.agents[agent_id] = agent
    
    async def send_message(
        self,
        from_agent: str,
        to_agent: str,
        message: dict[str, Any],
        message_type: str = "generic",
    ) -> str:
        """Send message between agents via mediator."""
        msg = Message(from_agent=from_agent, to_agent=to_agent, payload=message)
        
        if to_agent in self.agents:
            await self._deliver_message(to_agent, msg)
        else:
            self.message_queue[to_agent].append(msg)  # Queue for later
        
        return msg.id
    
    async def broadcast(
        self,
        from_agent: str,
        message: dict[str, Any],
    ) -> list[str]:
        """Broadcast to all agents."""
        return [
            await self.send_message(from_agent, agent_id, message)
            for agent_id in self.agents
            if agent_id != from_agent
        ]
```

## Usage Example
```python
from core.coordination.agent_mediator import get_agent_mediator

# Get singleton mediator
mediator = await get_agent_mediator()

# Register agents
mediator.register_agent("l-cto", cto_agent)
mediator.register_agent("research", research_agent)

# Send message (decoupled)
await mediator.send_message(
    from_agent="research",
    to_agent="l-cto",
    message={"task_complete": True, "result": data}
)

# Broadcast announcement
await mediator.broadcast(
    from_agent="igor",
    message={"announcement": "Maintenance in 1 hour"}
)
```

## Benefits
| Benefit | Impact |
|---------|--------|
| Decoupled agents | -50% coupling |
| Centralized routing | Easier debugging |
| Message queuing | Handles offline agents |
| Pub/sub support | Event-driven patterns |

## Rules
1. Agents MUST NOT import other agents directly
2. All inter-agent communication MUST go through mediator
3. Mediator MUST use `@register_singleton` (NOT simple `@singleton`)
4. Message delivery MUST be logged
5. Offline agents MUST have messages queued

## AI Guidance
**DO:**
- Use mediator for all agent-to-agent communication
- Register agents at startup
- Handle delivery failures gracefully

**DO NOT:**
- Import agents directly into other agents
- Use simple `@singleton` decorator (use `@register_singleton`)
- Skip message logging
- Assume agents are always online

## Related ADRs
- [ADR-0004: Singleton Auto-Registry](./0004-singleton-auto-registry.md) - Singleton pattern
- [ADR-0061: L9 Facade Pattern](./0061-l9-facade-simplified-api.md) - Uses mediator internally
