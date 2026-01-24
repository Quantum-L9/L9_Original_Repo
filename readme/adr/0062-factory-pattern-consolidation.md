# ADR-0062: Factory Pattern Consolidation

## Status
Proposed (Deferred - Not Yet Implemented)

## Context
L9 has 87 factory-like functions scattered across the codebase (`create_*`, `build_*`, `make_*`, `get_*`), but only 5 use explicit Factory classes. This inconsistency creates:
1. **Naming confusion**: `create_agent` vs `build_agent` vs `make_agent` vs `get_agent`
2. **No centralized creation**: Agent creation logic scattered across 20+ files
3. **Hard to test**: Can't easily mock object creation
4. **No lifecycle management**: Objects created but not properly initialized/closed
5. **Duplication**: Similar creation logic repeated in multiple places

**Current state** (from audit):
- 87 informal factory functions (`create_*`, `build_*`, etc.)
- 5 explicit Factory classes (`AgentFactory`, `ToolFactory`, etc.)
- No standardized factory pattern
- No centralized registry of factories

**Problems**:
- **Inconsistent naming**: 4 different prefixes for factory functions
- **Scattered logic**: Agent creation in 20+ files
- **No dependency injection**: Hard-coded dependencies
- **Testing difficulty**: Can't mock object creation
- **No lifecycle hooks**: Objects not properly initialized

## Decision
**Consolidate all factory functions into explicit Factory classes** following a standardized pattern:
1. One factory per major entity type (Agent, Tool, Orchestrator, Memory, etc.)
2. Factories implement `BaseFactory` interface
3. Centralized `FactoryRegistry` for factory discovery
4. Standardized lifecycle hooks (create, initialize, configure, destroy)
5. Support for dependency injection
6. Factory methods return fully initialized objects

## Proposed Implementation

### Base Factory Interface
```python
# core/patterns/factory.py

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Dict, Any

T = TypeVar('T')

class BaseFactory(ABC, Generic[T]):
    """Base factory interface for all L9 factories."""
    
    @abstractmethod
    async def create(
        self,
        type_id: str,
        config: Dict[str, Any] = None,
        **kwargs
    ) -> T:
        """Create and initialize object of type T."""
        pass
    
    @abstractmethod
    def list_types(self) -> List[str]:
        """List all supported type IDs."""
        pass
    
    @abstractmethod
    def get_type_info(self, type_id: str) -> Dict[str, Any]:
        """Get metadata about a type."""
        pass
    
    async def _initialize(self, obj: T) -> T:
        """Initialize object after creation (lifecycle hook)."""
        if hasattr(obj, 'initialize'):
            await obj.initialize()
        return obj
    
    async def _configure(self, obj: T, config: Dict[str, Any]) -> T:
        """Configure object (lifecycle hook)."""
        if hasattr(obj, 'configure'):
            await obj.configure(config)
        return obj
```

### Factory Registry
```python
# core/patterns/factory_registry.py

from core.patterns.singleton import singleton

@singleton
class FactoryRegistry:
    """Centralized registry of all factories."""
    
    def __init__(self):
        self._factories: Dict[str, BaseFactory] = {}
    
    def register_factory(
        self,
        entity_type: str,
        factory: BaseFactory
    ) -> None:
        """Register factory for entity type."""
        self._factories[entity_type] = factory
    
    def get_factory(self, entity_type: str) -> BaseFactory:
        """Get factory for entity type."""
        if entity_type not in self._factories:
            raise ValueError(f"No factory registered for {entity_type}")
        return self._factories[entity_type]
    
    def list_factories(self) -> List[str]:
        """List all registered factories."""
        return list(self._factories.keys())
```

### Agent Factory (Example)
```python
# core/agents/agent_factory.py

from core.patterns.factory import BaseFactory
from agents.base_agent import BaseAgent

class AgentFactory(BaseFactory[BaseAgent]):
    """Factory for creating agents."""
    
    def __init__(self):
        self._agent_classes = {
            "l-cto": LCTOAgent,
            "research": ResearchAgent,
            "architect": ArchitectAgent,
            "coder": CoderAgent,
            "igor": IgorAgent
        }
    
    async def create(
        self,
        type_id: str,
        config: Dict[str, Any] = None,
        **kwargs
    ) -> BaseAgent:
        """Create agent by type ID."""
        if type_id not in self._agent_classes:
            raise ValueError(f"Unknown agent type: {type_id}")
        
        # Get agent class
        agent_class = self._agent_classes[type_id]
        
        # Create agent instance
        agent = agent_class(**kwargs)
        
        # Initialize agent
        agent = await self._initialize(agent)
        
        # Configure agent
        if config:
            agent = await self._configure(agent, config)
        
        return agent
    
    def list_types(self) -> List[str]:
        """List all agent types."""
        return list(self._agent_classes.keys())
    
    def get_type_info(self, type_id: str) -> Dict[str, Any]:
        """Get agent type metadata."""
        agent_class = self._agent_classes.get(type_id)
        if not agent_class:
            return {}
        
        return {
            "type_id": type_id,
            "class": agent_class.__name__,
            "description": agent_class.__doc__,
            "capabilities": getattr(agent_class, 'capabilities', [])
        }
```

### Tool Factory (Example)
```python
# core/tools/tool_factory.py

class ToolFactory(BaseFactory[Tool]):
    """Factory for creating tools."""
    
    def __init__(self):
        self._tool_registry = get_tool_registry()
    
    async def create(
        self,
        type_id: str,
        config: Dict[str, Any] = None,
        **kwargs
    ) -> Tool:
        """Create tool by tool ID."""
        tool_def = self._tool_registry.get(type_id)
        if not tool_def:
            raise ValueError(f"Unknown tool: {type_id}")
        
        # Create tool instance
        tool = Tool(
            tool_id=type_id,
            definition=tool_def,
            **kwargs
        )
        
        # Initialize and configure
        tool = await self._initialize(tool)
        if config:
            tool = await self._configure(tool, config)
        
        return tool
    
    def list_types(self) -> List[str]:
        """List all tool IDs."""
        return self._tool_registry.list_tools()
    
    def get_type_info(self, type_id: str) -> Dict[str, Any]:
        """Get tool metadata."""
        return self._tool_registry.get_tool_info(type_id)
```

## Usage Examples

### Example 1: Create Agent
```python
from core.patterns.factory_registry import FactoryRegistry

# Get agent factory
registry = FactoryRegistry()
agent_factory = registry.get_factory("agent")

# Create agent
research_agent = await agent_factory.create(
    "research",
    config={"max_retries": 3, "timeout": 30}
)

# Agent is fully initialized and configured
result = await research_agent.run("Research async patterns", {})
```

### Example 2: Create Tool
```python
# Get tool factory
tool_factory = registry.get_factory("tool")

# Create tool
slack_tool = await tool_factory.create(
    "slack_send",
    config={"webhook_url": "https://..."}
)

# Tool is ready to use
await slack_tool.execute(channel="#general", message="Hello")
```

### Example 3: List Available Types
```python
# List all agent types
agent_types = agent_factory.list_types()
print(f"Available agents: {agent_types}")

# Get agent info
info = agent_factory.get_type_info("research")
print(f"Research agent: {info['description']}")
```

### Example 4: Dependency Injection
```python
# Create agent with injected dependencies
agent = await agent_factory.create(
    "research",
    memory_client=memory_client,
    tool_registry=tool_registry,
    config={"max_retries": 3}
)
```

## Standardized Naming

### Factory Classes
- `AgentFactory` - Creates agents
- `ToolFactory` - Creates tools
- `OrchestratorFactory` - Creates orchestrators
- `MemoryFactory` - Creates memory clients
- `KernelFactory` - Creates kernels

### Factory Methods
- `create(type_id, config, **kwargs)` - Create object
- `list_types()` - List available types
- `get_type_info(type_id)` - Get type metadata

### Lifecycle Hooks
- `_initialize(obj)` - Initialize object
- `_configure(obj, config)` - Configure object
- `_destroy(obj)` - Cleanup object (future)

## Migration Strategy

### Phase 1: Create Factories (3 hours)
- [ ] Create `BaseFactory` interface
- [ ] Create `FactoryRegistry`
- [ ] Implement `AgentFactory`
- [ ] Implement `ToolFactory`

### Phase 2: Migrate Existing Code (2 hours)
- [ ] Replace `create_agent()` with `AgentFactory.create()`
- [ ] Replace `create_tool()` with `ToolFactory.create()`
- [ ] Update tests to use factories

### Phase 3: Deprecate Old Functions (1 hour)
- [ ] Add deprecation warnings to old `create_*` functions
- [ ] Update documentation to use factories
- [ ] Remove old functions after 2 releases

**Total effort**: ~6 hours

## Consequences

### Positive
- **Consistency**: All creation logic in one place
- **Testability**: Easy to mock factories
- **Lifecycle management**: Automatic initialization/configuration
- **Discoverability**: `list_types()` shows what's available
- **Dependency injection**: Pass dependencies to factory
- **Extensibility**: Easy to add new types

### Negative
- **Migration effort**: Need to update 87 factory functions
- **Learning curve**: Developers must learn factory pattern
- **Indirection**: One more layer between caller and object

### Neutral
- **Coexists with direct instantiation**: Can still use `Agent()` directly
- **Async-first**: All factory methods are async

## Rules

### HARD RULES
1. **All factories MUST inherit from `BaseFactory`**
2. **Factory methods MUST return fully initialized objects**
3. **NO direct instantiation in production code** (use factories)

### Best Practices
- Use factories for all object creation
- Pass dependencies via factory `create()` method
- Use `list_types()` for discovery
- Keep factory logic simple (no business logic)

## Alternatives Considered

### 1. Keep informal factory functions
**Rejected**: Inconsistent, hard to maintain

### 2. Abstract Factory pattern
```python
class CloudProviderFactory(ABC):
    @abstractmethod
    def create_storage(self): pass
    
    @abstractmethod
    def create_compute(self): pass

class AWSFactory(CloudProviderFactory):
    def create_storage(self): return S3Storage()
    def create_compute(self): return EC2Compute()
```
**Deferred**: Useful for multi-provider support (see ADR-0063 - Abstract Factory)

### 3. Dependency injection container
```python
container.register(AgentFactory)
container.register(ToolFactory)
agent = container.resolve("research-agent")
```
**Deferred**: Overkill for current needs, consider for future

## Relationship to Other ADRs
- **ADR-0052 (DI/DIP Foundation)**: Factories support dependency injection
- **ADR-0056 (Singleton Pattern)**: FactoryRegistry is singleton
- **ADR-0004 (Singleton Auto-Registry)**: Factories can register singletons

## Verification
```bash
# Test factory pattern
python3 -c "
from core.agents.agent_factory import AgentFactory
from core.patterns.factory_registry import FactoryRegistry

import asyncio
async def test():
    # Register factory
    registry = FactoryRegistry()
    registry.register_factory('agent', AgentFactory())
    
    # Get factory
    factory = registry.get_factory('agent')
    
    # List types
    types = factory.list_types()
    print(f'Available agents: {types}')
    
    # Create agent
    agent = await factory.create('research')
    print(f'✅ Created agent: {agent.agent_id}')

asyncio.run(test())
"
```

## References
- Gang of Four: Factory Method Pattern
- Design Pattern Audit Report: `L9_DESIGN_PATTERN_AUDIT_REPORT.md` (Item #9)
- Dependency Injection principles

## Notes
- Factory pattern is also known as "Virtual Constructor"
- Factories should NOT contain business logic
- For multi-provider support, see ADR-0063 (Abstract Factory)

---
**Created**: 2026-01-23  
**Author**: L9 Design Pattern Audit  
**Status**: PROPOSED (Not yet implemented)  
**Priority**: LOW  
**Effort**: 6 hours  
**GMP**: design-patterns-deferred
