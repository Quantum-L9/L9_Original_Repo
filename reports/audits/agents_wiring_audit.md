# Package Wiring Audit: agents

**Date:** 2026-02-14 05:36 UTC

## Level B: File Wiring — `agents`

Files checked: 6
- WIRED: 4
- PARTIAL: 2
- ORPHAN: 0
- ENTRYPOINT: 0
- TEST_ONLY: 0

| File | Ext Consumers | Test Consumers | Test File | Re-exported | Status |
|------|-------------:|---------------:|-----------|-------------|--------|
| `agents/agent_registry.py` | 1 | 1 | Y | - | PARTIAL |
| `agents/base_agent.py` | 2 | 4 | Y | Y | OK |
| `agents/l_cto.py` | 2 | 6 | Y | Y | OK |
| `agents/qa_agent.py` | 0 | 0 | - | Y | PARTIAL |
| `agents/reflection_agent.py` | 2 | 0 | - | Y | OK |
| `agents/research_agent_impl.py` | 2 | 0 | - | Y | OK |

## Level C: API Instantiation — `agents`

API Status: **HAS_API**
Symbols checked: 16
- USED: 9
- TEST_ONLY: 4
- UNUSED: 3

| Symbol | Ext | Test | Status |
|--------|----:|-----:|--------|
| `ArchitectAgentA` | 0 | 2 | TEST_ONLY |
| `ArchitectAgentB` | 0 | 2 | TEST_ONLY |
| `CoderAgentA` | 0 | 1 | TEST_ONLY |
| `CoderAgentB` | 0 | 0 | UNUSED |
| `create_l_cto_agent` | 0 | 1 | TEST_ONLY |
| `create_l_cto_research_agent` | 0 | 0 | UNUSED |
| `is_research_mode` | 0 | 0 | UNUSED |

**API-pattern symbols NOT in `__all__`:**
- `SynthesisEngine`
- `create_reflection_agent`
- `create_research_agent`
- `get_agent_snapshot`
- `get_agents_by_category`
- `get_agents_by_role`
- `get_all_agents`
