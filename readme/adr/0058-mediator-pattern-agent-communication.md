# ADR-0058: Mediator Pattern for Agent Communication

## Status
Accepted (Implemented in PR #53)

## Context
L9's multi-agent architecture has agents that need to communicate with each other (Igor → L → Research/Architect/Coder). Previously, agents communicated directly, creating tight coupling and making it difficult to:
1. Add new agents without modifying existing ones
2. Track message flow across agents
3. Handle offline agents (message queuing)
4. Implement broadcast messages
5. Debug inter-agent communication

**Problems with direct communication**:
- **Tight coupling**: Each agent needs references to all other agents
- **N×N connections**: Adding agent requires updating N other agents
- **No message persistence**: Messages lost if recipient offline
- **No centralized logging**: Hard to debug message flow
- **No routing logic**: Can't implement message filtering or transformation

## Decision
Implement the **Mediator Pattern** to decouple agent-to-agent communication through a central `AgentMediator` that:
1. Routes messages between agents
2. Queues messages for offline agents
3. Supports direct messaging and broadcasting
4. Tracks message delivery and acknowledgments
5. Provides subscription-based message filtering

## Implementation

### Mediator Location
`core/coordination/agent_mediator.py` (400+ lines)

### Architecture
```
┌─────────┐     ┌──────────────────┐     ┌─────────┐
│ Agent A │────▶│  AgentMediator   │────▶│ Agent B │
└─────────┘     │                  │     └─────────┘
                │  - register()    │
┌─────────┐     │  - send()        │     ┌─────────┐
│ Agent C │────▶│  - broadcast()   │────▶│ Agent D │
└─────────┘     │  - subscribe()   │     └─────────┘
                └──────────────────┘
```

### Core API
```python
from core.coordination.agent_mediator import get_mediator

# Get singleton mediator
mediator = get_mediator()

# Register agents
mediator.register_agent("l-cto", l_cto_agent)
mediator.register_agent("research", research_agent)

# Send direct message
message_id = await mediator.send_message(
    from_agent="l-cto",
    to_agent="research",
    message={"task": "Research async patterns"},
    message_type="task_assignment"
)

# Broadcast to all agents
message_ids = await mediator.broadcast(
    from_agent="igor",
    message={"announcement": "Maintenance in 1 hour"},
    message_type="system_announcement"
)

# Subscribe to message types
mediator.subscribe("research", "task_assignment")

# Check agent status
is_online = mediator.get_agent_status("research")

# Get queued messages
messages = mediator.get_queued_messages("research")
```

### Features

#### 1. Message Queuing
Messages sent to offline agents are queued and delivered when agent comes online.

#### 2. Delivery Tracking
Each message gets unique ID and delivery status (pending/delivered/failed).

#### 3. Subscriptions
Agents can subscribe to specific message types, filtering irrelevant messages.

#### 4. Broadcasting
Send message to all registered agents with one call.

#### 5. Acknowledgments
Agents can acknowledge message receipt for reliable delivery.

## Consequences

### Positive
- **-50% coupling**: Agents don't need references to each other
- **Scalability**: Add agents without modifying existing ones
- **Reliability**: Message queuing for offline agents
- **Observability**: Centralized message logging
- **Flexibility**: Easy to add routing rules, transformations, filters
- **Testing**: Can mock mediator for unit tests

### Negative
- **Single point of failure**: If mediator crashes, all communication stops
- **Latency**: Extra hop adds ~1ms per message
- **Complexity**: One more component to understand

### Neutral
- **Singleton**: Uses `@singleton` pattern (ADR-0056)
- **Async-first**: All methods are async

## Usage Patterns

### Pattern 1: Task Assignment
```python
# Igor assigns task to L-CTO
await mediator.send_message(
    from_agent="igor",
    to_agent="l-cto",
    message={
        "task_id": "T-123",
        "description": "Implement feature X",
        "priority": "high"
    },
    message_type="task_assignment"
)
```

### Pattern 2: Status Updates
```python
# Research agent broadcasts progress
await mediator.broadcast(
    from_agent="research",
    message={
        "task_id": "T-123",
        "status": "in_progress",
        "progress": 0.5
    },
    message_type="status_update"
)
```

### Pattern 3: Request-Response
```python
# L-CTO requests info from Research
response_future = await mediator.send_message(
    from_agent="l-cto",
    to_agent="research",
    message={"query": "What's the status of T-123?"},
    message_type="info_request"
)

# Research responds
await mediator.send_message(
    from_agent="research",
    to_agent="l-cto",
    message={"status": "completed"},
    message_type="info_response"
)
```

## Rules

### HARD RULES
1. **ALL inter-agent communication MUST go through mediator**
2. **NO direct agent-to-agent calls** (except within same kernel)
3. **Agents MUST register with mediator** before sending/receiving

### Best Practices
- Use descriptive `message_type` for filtering
- Include `correlation_id` for request-response patterns
- Handle message delivery failures gracefully
- Subscribe only to relevant message types

## Verification
```bash
# Test mediator
python3 -c "
from core.coordination.agent_mediator import get_mediator

mediator = get_mediator()
mediator.register_agent('test1', None)
mediator.register_agent('test2', None)

import asyncio
async def test():
    msg_id = await mediator.send_message(
        from_agent='test1',
        to_agent='test2',
        message={'hello': 'world'}
    )
    print(f'✅ Message sent: {msg_id}')

asyncio.run(test())
"
```

## Alternatives Considered

### 1. Direct agent references
```python
class LCTOAgent:
    def __init__(self, research_agent, architect_agent):
        self.research = research_agent
        self.architect = architect_agent
    
    async def delegate_task(self):
        await self.research.process_task(...)
```
**Rejected**: Tight coupling, hard to scale

### 2. Event bus (pub/sub only)
```python
event_bus.publish("task.assigned", task_data)
```
**Rejected**: No direct messaging, no message queuing

### 3. Message queue (RabbitMQ, Kafka)
**Rejected**: Overkill for in-process communication, adds infrastructure dependency

### 4. Actor model (Pykka, Thespian)
**Rejected**: Too heavyweight, requires rewriting agents

## Relationship to Other ADRs
- **ADR-0056 (Singleton Pattern)**: Mediator is singleton
- **ADR-0006 (Packet Envelope)**: Messages can use PacketEnvelope format
- **ADR-0013 (Governance Authority Hierarchy)**: Mediator respects agent hierarchy

## Future Enhancements
1. **Message persistence**: Store messages in database for audit trail
2. **Message TTL**: Expire old queued messages
3. **Priority queues**: High-priority messages delivered first
4. **Message transformation**: Transform messages based on recipient
5. **Circuit breaker**: Disable agents that repeatedly fail

## Migration Path
1. ✅ **Phase 1** (PR #53): Implement mediator, register core agents
2. **Phase 2** (Future): Migrate direct agent calls to mediator
3. **Phase 3** (Future): Add message persistence and advanced features

## References
- Gang of Four: Mediator Pattern
- PR #53: Design Pattern Improvements
- Design Pattern Audit Report: `L9_DESIGN_PATTERN_AUDIT_REPORT.md`

## Notes
- Mediator is **NOT** a message broker (no persistence, no clustering)
- For distributed systems, consider migrating to RabbitMQ/Kafka later
- Message queues are in-memory, cleared on restart

---
**Created**: 2026-01-23  
**Author**: L9 Design Pattern Audit  
**GMP**: design-patterns-pr53
