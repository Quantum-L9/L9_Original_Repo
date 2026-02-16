# Dead Code Triage: `agents`

**Date:** 2026-02-14 05:42 UTC

## Symbol Classification

**USED** (9): `AgentConfig`, `AgentMessage`, `AgentResponse`, `AgentRole`, `BaseAgent`, `LCTOAgent`, `QAAgent`, `ReflectionAgent`, `ResearchAgent`
**INTERNAL_ONLY** (4): `ArchitectAgentA`, `ArchitectAgentB`, `CoderAgentA`, `CoderAgentB`
**TEST_ONLY** (1): `create_l_cto_agent`
**ZERO_REF** (2): `create_l_cto_research_agent`, `is_research_mode`

## File Classification

**WIRED** (5):
- `agents/agent_registry.py`
- `agents/base_agent.py`
- `agents/l_cto.py`
- `agents/reflection_agent.py`
- `agents/research_agent_impl.py`
**ASPIRATIONAL** (1):
- `agents/qa_agent.py`

## Recommended Actions

### Remove 4 internal-only symbols from `__all__`
These are used within the package but not externally. Remove from `__all__` to reduce API surface noise.

### Review 2 zero-reference symbols
These have no references anywhere (not even internal). Either wire them or remove from `__all__`.
