# ADR 0007: 7-Phase Bootstrap Ceremony

## Status
Accepted

## Pattern
Agent initialization follows strict 7-phase sequence; each phase has preconditions and postconditions.

## Files
- `core/agents/bootstrap/` - Phase implementations
- `core/agents/bootstrap/orchestrator.py` - Phase coordinator
- `api/server.py:bootstrap_agent()` - Entry point
- `private/kernels/00_system/*.yaml` - 10 governance kernels

## Phase Sequence
```
bootstrap_agent(config, substrate)
    │
    ├─ Phase 0: validate_agent_blueprint()    → Validate config schema
    ├─ Phase 1: load_and_parse_kernels()      → Load 10 YAML kernels
    ├─ Phase 2: instantiate_agent()           → Create AgentInstance
    ├─ Phase 3: bind_kernels_to_agent()       → Attach kernels to agent
    ├─ Phase 4: load_identity_persona()       → Load L's identity
    ├─ Phase 5: bind_tools_and_capabilities() → Wire tools + memory
    ├─ Phase 6: wire_governance_gates()       → Approval gate enforcement
    └─ Phase 7: verify_and_lock()             → Lock config + signature
```

## 10 Governance Kernels
| # | Kernel | Purpose |
|---|--------|---------|
| 01 | master_kernel | Top-level orchestration |
| 02 | identity_kernel | L's identity/persona |
| 03 | cognitive_kernel | Reasoning patterns |
| 04 | behavioral_kernel | Action constraints |
| 05 | memory_kernel | Memory access rules |
| 06 | worldmodel_kernel | World model integration |
| 07 | execution_kernel | Task execution flow |
| 08 | safety_kernel | Engineering safety |
| 09 | developer_kernel | Code quality rules |
| 10 | packet_protocol_kernel | Packet standards |

## Feature Flag
```python
L9_NEW_AGENT_INIT=true   # Use 7-phase bootstrap
L9_NEW_AGENT_INIT=false  # Legacy initialization (deprecated)
```

## Rules
1. Phases MUST execute in order (0→7)
2. Phase failure blocks subsequent phases
3. All 10 kernels required for Phase 1
4. Phase 7 locks configuration (immutable after)
5. Kernel hashes verified for integrity

## AI Guidance
**DO:**
- Add new initialization logic to appropriate phase
- Verify phase preconditions before execution
- Emit checkpoint packet after Phase 7

**DO NOT:**
- Skip phases or reorder them
- Initialize agent without bootstrap ceremony
- Modify config after Phase 7 lock
- Reduce kernel count below 10
