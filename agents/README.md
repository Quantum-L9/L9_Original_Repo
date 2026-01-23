# Agents Module

**Path:** `agents/`  
**Purpose:** Agent implementations and agent-related infrastructure for the L9 platform  
**Files:** 34 Python files  
**Last Updated:** 2026-01-18

---

## Overview

The `agents` module contains the core agent implementations and supporting infrastructure for the L9 Agentic Intelligence Platform. All agents in L9 must inherit from `BaseAgent` and operate under kernel governance.

## Architecture

### Core Components

- **`base_agent.py`** - Abstract base class for all L9 agents. Provides kernel integration, LLM calling, and governance hooks.
- **`agent_registry.py`** - Central registry for agent discovery and instantiation
- **`l_cto.py`** - L-CTO (Chief Technology Officer) agent implementation
- **`research_agent.py`** - Research and information gathering agent

### Subdirectories

| Directory | Purpose |
|---|---|
| `cursor/` | Cursor IDE integration and GMP (Guided Meta-Programming) system |
| `research_agent/` | Research agent implementation and facade |
| `email_agent/` | Email processing and interaction agent |
| `mac_agent/` | macOS-specific agent functionality |

## Key Concepts

### BaseAgent

All agents must inherit from `BaseAgent` which provides:

- **Kernel Awareness** - Integration with L9 kernel governance
- **LLM Integration** - Standardized LLM calling with retries and error handling
- **Memory Access** - Unified memory substrate integration
- **Tool Execution** - Kernel-governed tool invocation
- **Logging** - Structured logging with agent context

### Agent Lifecycle

```python
from agents.base_agent import BaseAgent

class MyAgent(BaseAgent):
    def __init__(self, kernel, ...):
        super().__init__(kernel)
        # Agent-specific initialization
    
    async def execute(self, task):
        # Agent logic here
        result = await self._make_llm_call(prompt)
        return result
```

### Kernel Governance

All agent actions are subject to kernel governance:

- **Policy Enforcement** - Agents cannot bypass kernel policies
- **Resource Limits** - Memory, compute, and API usage are governed
- **Audit Trail** - All agent actions are logged for compliance
- **Fail-Closed** - Agents fail safely if kernel is unavailable

## Usage

### Registering an Agent

```python
from agents.agent_registry import register_agent

# Register agent class using decorator
@register_agent(name="my_agent", role="custom", category="implementation")
class MyAgent(BaseAgent):
    pass

# Or get all registered agents
from agents.agent_registry import get_all_agents

agents = get_all_agents()
my_agent_cls = agents.get("my_agent")
agent = my_agent_cls(kernel)
```

### Executing Agent Tasks

```python
# Via kernel
result = await kernel.execute_agent_task(
    agent_name="l_cto",
    task="Analyze system architecture"
)

# Direct invocation
from agents.l_cto import LCTOAgent

agent = LCTOAgent(kernel)
result = await agent.execute(task)
```

## Development Guidelines

### Creating a New Agent

1. **Inherit from BaseAgent**
   ```python
   from agents.base_agent import BaseAgent
   
   class NewAgent(BaseAgent):
       def __init__(self, kernel, ...):
           super().__init__(kernel)
   ```

2. **Implement Required Methods**
   - `execute()` - Main agent logic
   - `validate_input()` - Input validation
   - `format_output()` - Output formatting

3. **Register the Agent**
   ```python
   from agents.agent_registry import register_agent
   
   @register_agent(name="new_agent", role="custom")
   class NewAgent(BaseAgent):
       pass
   ```

4. **Add Tests**
   - Create `tests/agents/test_new_agent.py`
   - Test kernel integration
   - Test error handling

### Best Practices

✅ **DO:**
- Always call `super().__init__(kernel)` in agent constructors
- Use `self._make_llm_call()` for LLM interactions
- Log all significant agent actions
- Handle errors gracefully with proper exceptions
- Write comprehensive docstrings

❌ **DON'T:**
- Bypass kernel governance
- Hardcode API keys or secrets
- Make blocking I/O calls in async functions
- Ignore error handling
- Create agents without tests

## Testing

```bash
# Run all agent tests
pytest tests/agents/

# Run specific agent tests
pytest tests/agents/test_l_cto.py

# Run with coverage
pytest tests/agents/ --cov=agents --cov-report=html
```

## Related Modules

- **`core/agents/`** - Core agent infrastructure (executor, prompt builder)
- **`runtime/`** - Agent runtime and task queue
- **`memory/`** - Memory substrate for agent state
- **`orchestration/`** - Multi-agent orchestration

## Configuration

Agent configuration is managed through:

- **`config/boot_overlay.yaml`** - Runtime configuration overrides
- **Environment Variables** - API keys and secrets
- **Kernel Policies** - Governance and resource limits

## Troubleshooting

### Common Issues

**Agent not found in registry:**
```python
# Ensure agent is registered
from agents.agent_registry import agent_registry, get_all_agents
print(agent_registry.list_ids())  # List all registered agent IDs
print(get_all_agents())  # Get dict of all agents
```

**Kernel governance errors:**
- Check kernel activation state
- Verify agent has required permissions
- Review kernel logs for policy violations

**LLM call failures:**
- Check API key configuration
- Verify rate limits
- Review error logs for specific issues

## Contributing

See the main [CONTRIBUTING.md](../CONTRIBUTING.md) for contribution guidelines.

### Agent-Specific Guidelines

- All new agents must have corresponding tests
- Agents must be documented with clear purpose and usage
- Breaking changes to `BaseAgent` require RFC process
- Performance-critical agents should include benchmarks

---

**Module Maintainer:** L-CTO Agent  
**Last Audit:** 2026-01-18  
**Status:** Production
