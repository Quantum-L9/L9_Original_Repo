# ADR-0061: Composite Pattern for Agent Hierarchies

## Status
Proposed (Deferred - Not Yet Implemented)

## Context
L9 has a hierarchical agent structure: **Igor** (CEO) → **L** (CTO) → **Research/Architect/Coder** agents. Currently, this hierarchy is implicit in the code, making it difficult to:
1. Treat individual agents and agent groups uniformly
2. Delegate tasks to entire teams (e.g., "L-CTO team, build feature X")
3. Aggregate results from multiple agents
4. Implement recursive operations (e.g., "all agents, report status")
5. Dynamically compose agent teams

**Current limitations**:
- **No team abstraction**: Can't treat "L-CTO team" as single entity
- **Manual delegation**: Must explicitly call each sub-agent
- **No recursive operations**: Can't apply operation to entire hierarchy
- **Hard-coded structure**: Agent hierarchy is implicit, not explicit
- **No dynamic teams**: Can't create ad-hoc agent groups

**Use cases**:
- Delegate task to entire team: "L-CTO team, implement feature X"
- Aggregate team metrics: "What's the L-CTO team's success rate?"
- Recursive commands: "All agents, pause execution"
- Dynamic teams: Create "Refactoring Squad" with Architect + Coder
- Hierarchical reporting: "Igor, get status from all sub-agents"

## Decision
Implement the **Composite Pattern** to represent agent hierarchies as tree structures where:
1. Individual agents and agent groups share common interface (`AgentComponent`)
2. `AgentGroup` can contain agents or other groups (recursive composition)
3. Operations on groups are delegated to all members
4. Results from multiple agents are aggregated
5. Dynamic team composition is supported

## Proposed Implementation

### Component Interface
```python
# core/patterns/composite.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any

class AgentComponent(ABC):
    """Base component for both individual agents and agent groups."""
    
    @abstractmethod
    async def execute_task(
        self,
        task: str,
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Execute task (individual or delegated to group)."""
        pass
    
    @abstractmethod
    def get_agent_ids(self) -> List[str]:
        """Get all agent IDs in this component."""
        pass
    
    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """Get status (individual or aggregated)."""
        pass
    
    @abstractmethod
    def add_agent(self, agent: 'AgentComponent') -> None:
        """Add sub-agent (only for groups)."""
        pass
    
    @abstractmethod
    def remove_agent(self, agent_id: str) -> None:
        """Remove sub-agent (only for groups)."""
        pass
```

### Leaf: Individual Agent
```python
# agents/base_agent.py

class BaseAgent(AgentComponent):
    """Leaf node - individual agent."""
    
    async def execute_task(self, task: str, context: Dict) -> AgentResponse:
        # Execute task as usual
        return await self.run(task, context)
    
    def get_agent_ids(self) -> List[str]:
        return [self.agent_id]
    
    async def get_status(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "state": self.state,
            "current_task": self.current_task
        }
    
    def add_agent(self, agent: AgentComponent) -> None:
        raise NotImplementedError("Cannot add agents to leaf node")
    
    def remove_agent(self, agent_id: str) -> None:
        raise NotImplementedError("Cannot remove agents from leaf node")
```

### Composite: Agent Group
```python
# core/agents/agent_group.py

class AgentGroup(AgentComponent):
    """Composite node - group of agents."""
    
    def __init__(
        self,
        group_id: str,
        strategy: str = "parallel"  # parallel, sequential, round_robin
    ):
        self.group_id = group_id
        self.strategy = strategy
        self._agents: List[AgentComponent] = []
    
    def add_agent(self, agent: AgentComponent) -> None:
        """Add agent or sub-group to this group."""
        if agent not in self._agents:
            self._agents.append(agent)
    
    def remove_agent(self, agent_id: str) -> None:
        """Remove agent or sub-group from this group."""
        self._agents = [
            a for a in self._agents
            if agent_id not in a.get_agent_ids()
        ]
    
    def get_agent_ids(self) -> List[str]:
        """Get all agent IDs in this group (recursive)."""
        ids = []
        for agent in self._agents:
            ids.extend(agent.get_agent_ids())
        return ids
    
    async def execute_task(
        self,
        task: str,
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Execute task using delegation strategy."""
        if self.strategy == "parallel":
            return await self._execute_parallel(task, context)
        elif self.strategy == "sequential":
            return await self._execute_sequential(task, context)
        elif self.strategy == "round_robin":
            return await self._execute_round_robin(task, context)
    
    async def _execute_parallel(self, task, context):
        """Execute task on all agents in parallel."""
        tasks = [
            agent.execute_task(task, context)
            for agent in self._agents
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return self._aggregate_results(results)
    
    async def _execute_sequential(self, task, context):
        """Execute task on agents sequentially."""
        results = []
        for agent in self._agents:
            result = await agent.execute_task(task, context)
            results.append(result)
        return self._aggregate_results(results)
    
    async def _execute_round_robin(self, task, context):
        """Execute task on next agent in rotation."""
        agent = self._agents[self._round_robin_index]
        self._round_robin_index = (self._round_robin_index + 1) % len(self._agents)
        return await agent.execute_task(task, context)
    
    def _aggregate_results(self, results: List[AgentResponse]) -> AgentResponse:
        """Aggregate results from multiple agents."""
        return AgentResponse(
            success=all(r.success for r in results if isinstance(r, AgentResponse)),
            data={
                "group_id": self.group_id,
                "results": [r.data for r in results if isinstance(r, AgentResponse)],
                "errors": [str(r) for r in results if isinstance(r, Exception)]
            }
        )
    
    async def get_status(self) -> Dict[str, Any]:
        """Get aggregated status from all agents."""
        statuses = await asyncio.gather(*[
            agent.get_status() for agent in self._agents
        ])
        return {
            "group_id": self.group_id,
            "agent_count": len(self._agents),
            "agent_statuses": statuses
        }
```

## Usage Examples

### Example 1: L-CTO Team
```python
# Create L-CTO team
l_cto_team = AgentGroup("l-cto-team", strategy="parallel")
l_cto_team.add_agent(research_agent)
l_cto_team.add_agent(architect_agent)
l_cto_team.add_agent(coder_agent)

# Delegate task to entire team
result = await l_cto_team.execute_task(
    "Implement async retry pattern",
    context={}
)

# Get team status
status = await l_cto_team.get_status()
print(f"Team has {status['agent_count']} agents")
```

### Example 2: Hierarchical Structure
```python
# Create full hierarchy
l9_org = AgentGroup("l9-organization", strategy="sequential")

# Add Igor (CEO)
l9_org.add_agent(igor_agent)

# Create L-CTO team
l_cto_team = AgentGroup("l-cto-team", strategy="parallel")
l_cto_team.add_agent(research_agent)
l_cto_team.add_agent(architect_agent)
l_cto_team.add_agent(coder_agent)

# Add L-CTO team to organization
l9_org.add_agent(l_cto_team)

# Delegate to entire organization
result = await l9_org.execute_task("Build feature X", {})
```

### Example 3: Dynamic Teams
```python
# Create ad-hoc refactoring squad
refactoring_squad = AgentGroup("refactoring-squad", strategy="sequential")
refactoring_squad.add_agent(architect_agent)  # Design refactoring
refactoring_squad.add_agent(coder_agent)      # Implement refactoring

# Execute refactoring
result = await refactoring_squad.execute_task(
    "Refactor tool registry",
    context={}
)
```

### Example 4: Recursive Operations
```python
# Get status from entire organization (recursive)
org_status = await l9_org.get_status()

# Get all agent IDs in organization (recursive)
all_agents = l9_org.get_agent_ids()
print(f"Organization has {len(all_agents)} agents")
```

## Delegation Strategies

### 1. Parallel (Default)
Execute task on all agents simultaneously, aggregate results.
- **Use case**: Research from multiple sources, parallel code generation
- **Pros**: Fastest execution
- **Cons**: High resource usage

### 2. Sequential
Execute task on agents one at a time, in order.
- **Use case**: Pipeline workflows (Research → Architect → Coder)
- **Pros**: Predictable order, lower resource usage
- **Cons**: Slower execution

### 3. Round Robin
Execute task on next agent in rotation.
- **Use case**: Load balancing across multiple identical agents
- **Pros**: Even distribution
- **Cons**: Only one agent executes per task

### 4. Custom (Future)
User-defined delegation logic.

## Consequences

### Positive
- **Uniform interface**: Treat individual agents and groups the same
- **Recursive operations**: Apply operation to entire hierarchy
- **Dynamic composition**: Create ad-hoc teams at runtime
- **Flexible delegation**: Multiple strategies (parallel, sequential, round-robin)
- **Aggregated results**: Automatic result aggregation
- **Better abstraction**: Explicit agent hierarchy

### Negative
- **Complexity**: One more abstraction layer
- **Performance overhead**: Delegation adds latency (~5-10ms)
- **Memory usage**: Storing group structure

### Neutral
- **Coexists with direct calls**: Can still call agents directly
- **Async-first**: All operations are async

## Rules

### HARD RULES
1. **All agents MUST implement `AgentComponent` interface**
2. **Groups MUST NOT modify agent state** (delegation only)
3. **Recursive operations MUST have depth limit** (prevent infinite loops)

### Best Practices
- Use parallel strategy for independent tasks
- Use sequential strategy for pipeline workflows
- Limit group depth to 3 levels (avoid deep hierarchies)
- Cache group status (don't recompute every time)

## Alternatives Considered

### 1. Manual delegation
```python
results = []
for agent in [research, architect, coder]:
    result = await agent.run(task, context)
    results.append(result)
```
**Rejected**: Not reusable, no abstraction

### 2. Inheritance-based hierarchy
```python
class LCTOAgent(BaseAgent):
    def __init__(self):
        self.research = ResearchAgent()
        self.architect = ArchitectAgent()
```
**Rejected**: Tight coupling, not flexible

### 3. Configuration-based hierarchy
```yaml
l-cto-team:
  agents:
    - research
    - architect
    - coder
  strategy: parallel
```
**Rejected**: Less flexible than code-based composition

## Relationship to Other ADRs
- **ADR-0058 (Mediator Pattern)**: Groups can use mediator for agent communication
- **ADR-0013 (Governance Authority Hierarchy)**: Composite pattern makes hierarchy explicit

## Implementation Roadmap

### Phase 1: Core Pattern (2 hours)
- [ ] Create `AgentComponent` interface
- [ ] Update `BaseAgent` to implement interface
- [ ] Create `AgentGroup` class

### Phase 2: Delegation Strategies (2 hours)
- [ ] Implement parallel strategy
- [ ] Implement sequential strategy
- [ ] Implement round-robin strategy

### Phase 3: Integration (2 hours)
- [ ] Create L-CTO team group
- [ ] Update orchestration to use groups
- [ ] Add API endpoints for group operations

### Phase 4: Advanced Features (3 hours)
- [ ] Custom delegation strategies
- [ ] Group metrics and monitoring
- [ ] Dynamic team composition UI

**Total effort**: ~9 hours

## Verification
```bash
# Test composite pattern
python3 -c "
from agents.base_agent import BaseAgent
from core.agents.agent_group import AgentGroup

class TestAgent(BaseAgent):
    def __init__(self, agent_id):
        self.agent_id = agent_id
    
    async def execute_task(self, task, context):
        return {'agent_id': self.agent_id, 'result': 'success'}

import asyncio
async def test():
    # Create group
    group = AgentGroup('test-group', strategy='parallel')
    group.add_agent(TestAgent('agent1'))
    group.add_agent(TestAgent('agent2'))
    
    # Execute task on group
    result = await group.execute_task('test task', {})
    
    assert len(result.data['results']) == 2
    print(f'✅ Composite pattern working: {result.data}')

asyncio.run(test())
"
```

## References
- Gang of Four: Composite Pattern
- Design Pattern Audit Report: `L9_DESIGN_PATTERN_AUDIT_REPORT.md` (Item #8)
- Tree data structures

## Notes
- Composite pattern is also known as "Part-Whole Hierarchy"
- Groups can contain other groups (recursive composition)
- Delegation strategies can be changed at runtime

---
**Created**: 2026-01-23  
**Author**: L9 Design Pattern Audit  
**Status**: PROPOSED (Not yet implemented)  
**Priority**: LOW  
**Effort**: 9 hours  
**GMP**: design-patterns-deferred
