# ADR-0060: Observer Pattern for Agent Monitoring

## Status
Proposed (Deferred - Not Yet Implemented)

## Context
L9 has multiple agents (Igor, L-CTO, Research, Architect, Coder) that execute tasks asynchronously. Currently, there's no standardized way to:
1. Monitor agent state changes (idle → working → completed)
2. Track agent health and performance metrics
3. Notify interested parties of agent events
4. Implement reactive behaviors based on agent state
5. Debug agent execution flow

**Current limitations**:
- **Manual polling**: Must repeatedly check agent status
- **No notifications**: Can't react to agent state changes
- **Scattered logging**: Agent events logged inconsistently
- **Hard to debug**: No centralized view of agent activity
- **No metrics**: Can't track agent performance over time

**Use cases**:
- Dashboard showing real-time agent status
- Alerts when agents fail or hang
- Performance metrics (tasks/hour, success rate)
- Audit trail of agent actions
- Reactive workflows (agent A completes → trigger agent B)

## Decision
Implement the **Observer Pattern** to enable reactive monitoring of agent state changes through:
1. `AgentObserver` interface for observers
2. `ObservableAgent` mixin for agents
3. Event types: `state_changed`, `task_started`, `task_completed`, `task_failed`, `health_check`
4. Centralized `AgentMonitor` service for metrics collection
5. Integration with existing logging and metrics systems

## Proposed Implementation

### Observer Interface
```python
# core/patterns/observer.py

from abc import ABC, abstractmethod
from typing import Any, Dict

class AgentObserver(ABC):
    """Observer interface for agent events."""
    
    @abstractmethod
    async def on_agent_event(
        self,
        agent_id: str,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> None:
        """Called when observed agent emits event."""
        pass

class ObservableAgent:
    """Mixin for agents that emit events to observers."""
    
    def __init__(self):
        self._observers: List[AgentObserver] = []
    
    def attach_observer(self, observer: AgentObserver) -> None:
        """Attach observer to this agent."""
        if observer not in self._observers:
            self._observers.append(observer)
    
    def detach_observer(self, observer: AgentObserver) -> None:
        """Detach observer from this agent."""
        self._observers.remove(observer)
    
    async def _notify_observers(
        self,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> None:
        """Notify all observers of event."""
        for observer in self._observers:
            try:
                await observer.on_agent_event(
                    self.agent_id,
                    event_type,
                    event_data
                )
            except Exception as e:
                logger.error(f"Observer notification failed: {e}")
```

### Agent Integration
```python
# agents/base_agent.py

from core.patterns.observer import ObservableAgent

class BaseAgent(ObservableAgent):
    async def run(self, task: str, context: Dict) -> AgentResponse:
        # Notify task started
        await self._notify_observers("task_started", {
            "task": task,
            "timestamp": datetime.utcnow()
        })
        
        try:
            # Execute task
            result = await self._execute_task(task, context)
            
            # Notify task completed
            await self._notify_observers("task_completed", {
                "task": task,
                "result": result,
                "duration": ...,
                "timestamp": datetime.utcnow()
            })
            
            return result
        except Exception as e:
            # Notify task failed
            await self._notify_observers("task_failed", {
                "task": task,
                "error": str(e),
                "timestamp": datetime.utcnow()
            })
            raise
```

### Concrete Observers

#### 1. Logging Observer
```python
class LoggingObserver(AgentObserver):
    """Logs all agent events."""
    
    async def on_agent_event(self, agent_id, event_type, event_data):
        logger.info(
            f"Agent {agent_id} event: {event_type}",
            extra=event_data
        )
```

#### 2. Metrics Observer
```python
class MetricsObserver(AgentObserver):
    """Collects agent performance metrics."""
    
    async def on_agent_event(self, agent_id, event_type, event_data):
        if event_type == "task_completed":
            metrics.increment(f"agent.{agent_id}.tasks_completed")
            metrics.histogram(
                f"agent.{agent_id}.task_duration",
                event_data["duration"]
            )
```

#### 3. Dashboard Observer
```python
class DashboardObserver(AgentObserver):
    """Updates real-time dashboard."""
    
    async def on_agent_event(self, agent_id, event_type, event_data):
        await websocket_broadcast({
            "agent_id": agent_id,
            "event_type": event_type,
            "data": event_data
        })
```

#### 4. Alert Observer
```python
class AlertObserver(AgentObserver):
    """Sends alerts on failures."""
    
    async def on_agent_event(self, agent_id, event_type, event_data):
        if event_type == "task_failed":
            await send_slack_alert(
                f"Agent {agent_id} task failed: {event_data['error']}"
            )
```

### Centralized Monitor
```python
# core/monitoring/agent_monitor.py

class AgentMonitor(AgentObserver):
    """Centralized agent monitoring service."""
    
    def __init__(self):
        self._agent_states: Dict[str, AgentState] = {}
        self._metrics: Dict[str, AgentMetrics] = {}
    
    async def on_agent_event(self, agent_id, event_type, event_data):
        # Update agent state
        self._update_state(agent_id, event_type, event_data)
        
        # Collect metrics
        self._collect_metrics(agent_id, event_type, event_data)
        
        # Store event in database
        await self._store_event(agent_id, event_type, event_data)
    
    def get_agent_state(self, agent_id: str) -> AgentState:
        """Get current agent state."""
        return self._agent_states.get(agent_id)
    
    def get_agent_metrics(self, agent_id: str) -> AgentMetrics:
        """Get agent performance metrics."""
        return self._metrics.get(agent_id)
```

## Event Types

### Core Events
- `state_changed` - Agent state transition (idle/working/completed/failed)
- `task_started` - Agent started task
- `task_completed` - Agent completed task successfully
- `task_failed` - Agent task failed
- `health_check` - Periodic health status

### Extended Events (Future)
- `tool_executed` - Agent executed tool
- `memory_accessed` - Agent queried memory
- `agent_message_sent` - Agent sent message to another agent
- `resource_usage` - CPU/memory usage snapshot

## Consequences

### Positive
- **Reactive monitoring**: Real-time agent status updates
- **Decoupled observers**: Add monitoring without modifying agents
- **Extensible**: Easy to add new observer types
- **Performance tracking**: Automatic metrics collection
- **Better debugging**: Centralized event log
- **Alerting**: Proactive failure detection

### Negative
- **Performance overhead**: Each event notifies all observers (~1-5ms)
- **Memory usage**: Storing event history
- **Complexity**: One more pattern to understand

### Neutral
- **Async-first**: All notifications are async
- **Fire-and-forget**: Observer failures don't block agent

## Rules

### HARD RULES
1. **Agents MUST inherit from `ObservableAgent`**
2. **Observers MUST NOT block agent execution** (async, fire-and-forget)
3. **Observer failures MUST be logged but not propagate**

### Best Practices
- Attach observers during agent initialization
- Keep observer logic lightweight (< 10ms)
- Use async operations in observers
- Log observer failures for debugging

## Alternatives Considered

### 1. Polling-based monitoring
```python
while True:
    status = agent.get_status()
    if status.changed:
        handle_change(status)
    await asyncio.sleep(1)
```
**Rejected**: Inefficient, delayed notifications, high CPU usage

### 2. Callback functions
```python
agent.on_task_complete(lambda result: handle_result(result))
```
**Rejected**: Not as flexible as observer pattern, harder to manage multiple callbacks

### 3. Event bus (pub/sub)
```python
event_bus.subscribe("agent.task_completed", handler)
```
**Rejected**: More complex than needed for agent monitoring

## Relationship to Other ADRs
- **ADR-0058 (Mediator Pattern)**: Observers can use mediator for cross-agent reactions
- **ADR-0006 (Packet Envelope)**: Events can be wrapped in PacketEnvelope
- **ADR-0019 (Structlog)**: Logging observer uses structlog

## Implementation Roadmap

### Phase 1: Core Pattern (2 hours)
- [ ] Create `AgentObserver` interface
- [ ] Create `ObservableAgent` mixin
- [ ] Add to `BaseAgent`

### Phase 2: Basic Observers (1 hour)
- [ ] Implement `LoggingObserver`
- [ ] Implement `MetricsObserver`

### Phase 3: Centralized Monitor (2 hours)
- [ ] Implement `AgentMonitor` service
- [ ] Add database persistence
- [ ] Create API endpoints

### Phase 4: Advanced Features (3 hours)
- [ ] Dashboard observer with WebSocket
- [ ] Alert observer with Slack integration
- [ ] Performance profiling observer

**Total effort**: ~8 hours

## Verification
```bash
# Test observer pattern
python3 -c "
from agents.base_agent import BaseAgent
from core.patterns.observer import AgentObserver

class TestObserver(AgentObserver):
    def __init__(self):
        self.events = []
    
    async def on_agent_event(self, agent_id, event_type, event_data):
        self.events.append((agent_id, event_type))

import asyncio
async def test():
    agent = BaseAgent()
    observer = TestObserver()
    agent.attach_observer(observer)
    
    await agent.run('test task', {})
    
    assert len(observer.events) >= 2  # task_started, task_completed
    print(f'✅ Observer received {len(observer.events)} events')

asyncio.run(test())
"
```

## References
- Gang of Four: Observer Pattern
- Design Pattern Audit Report: `L9_DESIGN_PATTERN_AUDIT_REPORT.md` (Item #7)
- Python `asyncio` event loop patterns

## Notes
- Observer pattern is also known as "Publish-Subscribe" or "Event Listener"
- For distributed systems, consider using Redis pub/sub or RabbitMQ
- Observer notifications are fire-and-forget (don't wait for completion)

---
**Created**: 2026-01-23  
**Author**: L9 Design Pattern Audit  
**Status**: PROPOSED (Not yet implemented)  
**Priority**: MEDIUM  
**Effort**: 8 hours  
**GMP**: design-patterns-deferred
