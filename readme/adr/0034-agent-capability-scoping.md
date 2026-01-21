# ADR 0034: Agent Capability Scoping

## Status
Accepted

## Pattern
Agent capabilities scoped by tenant ID; L uses `l-cto`, Cursor uses `cursor-ide`; capabilities differ per agent.

## Files
- `core/tools/tool_graph.py` - `L9_TENANT_ID = 'l-cto'`
- `agents/cursor/cursor_memory_kernel.py` - `CURSOR_TENANT_ID = 'cursor-ide'`
- `core/schemas/capabilities.py` - Capability definitions
- `core/governance/approval_manager.py` - Approval flow

## Import Block
```python
import os
from enum import Enum
from dataclasses import dataclass

# Tenant IDs
L9_TENANT_ID = os.getenv("L9_TENANT_ID", "l-cto")
CURSOR_TENANT_ID = "cursor-ide"
```

## Minimal Implementation
```python
import os
from enum import Enum
from dataclasses import dataclass, field
from typing import Set
import structlog

logger = structlog.get_logger(__name__)

# Tenant IDs
L9_TENANT_ID = os.getenv("L9_TENANT_ID", "l-cto")
CURSOR_TENANT_ID = "cursor-ide"


class Capability(str, Enum):
    """Agent capabilities."""
    MEMORY_READ = "memory_read"
    MEMORY_WRITE = "memory_write"
    TOOL_EXECUTE = "tool_execute"
    TOOL_EXECUTE_SAFE = "tool_execute_safe"
    GIT_COMMIT = "git_commit"
    GIT_PUSH = "git_push"
    FILE_DELETE = "file_delete"
    SHELL_EXECUTE = "shell_execute"
    DEPLOY = "deploy"


@dataclass
class AgentCapabilities:
    """Capability profile for an agent."""
    agent_id: str
    tenant_id: str
    capabilities: Set[Capability] = field(default_factory=set)
    requires_approval_for: Set[Capability] = field(default_factory=set)


# Capability profiles
L_CTO_CAPABILITIES = AgentCapabilities(
    agent_id="l-cto",
    tenant_id=L9_TENANT_ID,
    capabilities={
        Capability.MEMORY_READ,
        Capability.MEMORY_WRITE,
        Capability.TOOL_EXECUTE,
        Capability.GIT_COMMIT,
        Capability.FILE_DELETE,
        Capability.SHELL_EXECUTE,
    },
    requires_approval_for={
        Capability.GIT_PUSH,
        Capability.DEPLOY,
    },
)

CURSOR_CAPABILITIES = AgentCapabilities(
    agent_id="cursor-ide",
    tenant_id=CURSOR_TENANT_ID,
    capabilities={
        Capability.MEMORY_READ,
        Capability.MEMORY_WRITE,
        Capability.TOOL_EXECUTE_SAFE,
    },
    requires_approval_for={
        Capability.TOOL_EXECUTE,
        Capability.GIT_COMMIT,
    },
)

RESEARCH_CAPABILITIES = AgentCapabilities(
    agent_id="research-agent",
    tenant_id=L9_TENANT_ID,
    capabilities={
        Capability.MEMORY_READ,
        Capability.TOOL_EXECUTE_SAFE,
    },
    requires_approval_for={
        Capability.MEMORY_WRITE,
    },
)


def check_capability(
    agent: AgentCapabilities,
    capability: Capability,
) -> tuple[bool, bool]:
    """
    Check if agent has capability.
    
    Returns:
        (has_capability, requires_approval)
    """
    has_cap = capability in agent.capabilities
    needs_approval = capability in agent.requires_approval_for
    
    return has_cap or needs_approval, needs_approval


async def dispatch_tool(
    agent_id: str,
    tool_id: str,
    tool_capability: Capability,
) -> dict:
    """Dispatch tool with capability check."""
    agent = get_agent_capabilities(agent_id)
    
    has_cap, needs_approval = check_capability(agent, tool_capability)
    
    if not has_cap:
        logger.warning(
            "capability.denied",
            agent_id=agent_id,
            capability=tool_capability.value,
        )
        raise CapabilityDenied(
            f"Agent {agent_id} cannot execute {tool_id}"
        )
    
    if needs_approval:
        approval = await request_igor_approval(agent_id, tool_id)
        if not approval.approved:
            raise ApprovalRequired(tool_id)
    
    return await execute_tool(tool_id)
```

## Usage Example
```python
from core.schemas.capabilities import (
    check_capability,
    Capability,
    L_CTO_CAPABILITIES,
    CURSOR_CAPABILITIES,
)

# Check L-CTO capabilities
has_git, needs_approval = check_capability(
    L_CTO_CAPABILITIES,
    Capability.GIT_COMMIT,
)
# (True, False) — L-CTO can commit without approval

# Check Cursor capabilities
has_git, needs_approval = check_capability(
    CURSOR_CAPABILITIES,
    Capability.GIT_COMMIT,
)
# (True, True) — Cursor needs approval for commit

# Check denied capability
has_shell, _ = check_capability(
    CURSOR_CAPABILITIES,
    Capability.SHELL_EXECUTE,
)
# (False, False) — Cursor cannot execute shell at all


# In tool dispatch
async def handle_tool_request(agent_id: str, tool_id: str):
    agent = get_agent_capabilities(agent_id)
    
    if tool_id == "git_commit":
        has_cap, needs_approval = check_capability(
            agent, Capability.GIT_COMMIT
        )
        
        if not has_cap:
            return {"error": "Capability denied"}
        
        if needs_approval:
            return {"status": "pending_approval"}
        
        return await execute_git_commit()
```

## Capability Matrix
| Capability | L-CTO | Cursor | Research | Mac |
|------------|-------|--------|----------|-----|
| memory_read | ✅ | ✅ | ✅ | ❌ |
| memory_write | ✅ | ✅ | ⚠️ | ❌ |
| tool_execute | ✅ | ⚠️ | ❌ | ❌ |
| tool_execute_safe | ✅ | ✅ | ✅ | ❌ |
| git_commit | ✅ | ⚠️ | ❌ | ❌ |
| git_push | ⚠️ | ❌ | ❌ | ❌ |
| file_delete | ✅ | ❌ | ❌ | ❌ |
| shell_execute | ✅ | ❌ | ❌ | ⚠️ |
| deploy | ⚠️ | ❌ | ❌ | ❌ |

✅ = Has capability
⚠️ = Requires Igor approval
❌ = Denied

## Authority Hierarchy
```
Igor (Human)
    │ FULL access, approves all high-risk
    ▼
L-CTO (l-cto tenant)
    │ Almost full, needs Igor for git_push/deploy
    ▼
Cursor IDE (cursor-ide tenant)
    │ Read + write memory, limited tools
    ▼
Research Agents
    │ Read only, specific safe tools
    ▼
Mac Agent
    │ Shell only with approval
```

## Rules
1. ALWAYS check tenant_id before operations
2. L-CTO uses `l-cto` tenant
3. Cursor uses `cursor-ide` tenant
4. Check capability before tool dispatch
5. High-risk tools need Igor approval regardless

## AI Guidance
**DO:**
- Check agent capabilities before dispatch
- Use correct tenant ID for each agent
- Respect capability matrix
- Log capability denials

**DO NOT:**
- Skip capability checks
- Give Cursor L-CTO capabilities
- Auto-approve high-risk tools
- Mix tenant IDs between agents
