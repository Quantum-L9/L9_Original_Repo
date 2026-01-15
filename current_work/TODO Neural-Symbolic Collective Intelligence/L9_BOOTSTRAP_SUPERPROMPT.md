# L9 BOOTSTRAP INITIALIZATION SUPERPROMPT

**Status:** Phase 0 TODO LOCK APPROVED ✓  
**Version:** 1.0.0  
**Generated:** 2026-01-14  
**Authority:** L9-CTO (Igor approval required for Phase 6+ execution)

---

## EXECUTIVE SUMMARY

This document codifies the **7-phase atomic agent bootstrapping system** for L9. All phases must succeed or the entire initialization rolls back (Neo4j CASCADE deletion).

**Critical Invariants:**
- All phases logged to Neo4j (immutable audit trail)
- Redis working memory TTL = 24h (expires if not finalized)
- High-risk tools require Igor approval (Phase 6)
- SHA256 init_signature locks configuration post-Phase 7

---

## PHASE ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                   PHASE 0: VALIDATE                             │
│  ✓ Config schema, Agent ID uniqueness, Kernel availability    │
│  ✗ Error → Prevent Phase 1                                     │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│                   PHASE 1: LOAD KERNELS                         │
│  ✓ Load 10 YAML kernels, validate manifests, attach metadata  │
│  Returns: List[KernelParsed] → Phase 2                         │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│               PHASE 2: INSTANTIATE AGENT                        │
│  ✓ Create Neo4j node + Redis working memory (24h TTL)         │
│  Returns: AgentInstance(status=INITIALIZING) → Phase 3         │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│              PHASE 3: BIND KERNELS                              │
│  ✓ Create 10 GOVERNEDBY edges (agent → kernels)                │
│  Each kernel enforces: identity, behavior, execution, safety   │
│  → Phase 4                                                      │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│            PHASE 4: LOAD IDENTITY                               │
│  ✓ Extract L persona from kernel-02 (IdentityKernel)           │
│  → Phase 5                                                      │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│            PHASE 5: BIND TOOLS                                  │
│  ✓ Register 8 tools, flag high-risk (git_commit, gmp_run,      │
│    mac_agent_exec)                                              │
│  → Phase 6                                                      │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│         PHASE 6: WIRE GOVERNANCE GATES                          │
│  ✓ Attach approval rules from kernel-08 (SafetyKernel)         │
│  ✓ 5-min timeout, escalate to Slack if no Igor approval       │
│  → Phase 7                                                      │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│           PHASE 7: VERIFY & LOCK                                │
│  ✓ Verify all 6 checks passed                                  │
│  ✓ Compute SHA256 init_signature                               │
│  ✓ Set status = READY                                          │
│  Returns: init_signature (audit trail key)                     │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                      DONE
                      Agent(status=READY)
                      Init signature locked
```

---

## VERIFICATION CHECKLIST (Phase 7)

All 6 checks MUST pass or initialization fails:

```python
verification_checks = {
    "neo4j_node_exists": bool(agent_node),           # T1
    "kernel_bindings_count": edges_count == 10,      # T2
    "redis_working_memory": bool(has_redis),         # T2
    "tool_bindings_count": tools_count >= 8,         # T2
    "approval_gates_count": gates_count >= 3,        # T2
    "identity_loaded": bool(agent.identity)          # T2
}

if not all(verification_checks.values()):
    raise RuntimeError(f"Failed: {[k for k,v in checks.items() if not v]}")
```

---

## ROLLBACK STRATEGY

**Trigger:** Any phase fails → Immediate rollback  
**Mechanism:** Neo4j CASCADE delete on agent node  
**Side Effects:**
- All relationships deleted (GOVERNEDBY, CAN_USE, REQUIRES_APPROVAL)
- Kernel nodes preserved (shared across agents)
- Redis keys expire after TTL (24h)
- Audit log entry created (failure recorded)

**Example:**
```cypher
MATCH (a:AgentInstance {instanceId: $id})
DELETE a  -- CASCADE deletes all relationships
```

---

## KERNEL STACK (10 KERNELS)

| # | Name | Purpose | Key Responsibility |
|---|------|---------|-------------------|
| 01 | MasterKernel | Sovereignty, governance identity | L is CTO, final authority |
| 02 | IdentityKernel | L persona, communication style | Name, constraints, tone |
| 03 | CognitiveKernel | Reasoning modes, episodic recall | How L thinks, learns |
| 04 | BehavioralKernel | Response patterns, interaction | How L responds |
| 05 | MemoryKernel | Memory layer governance | What L remembers |
| 06 | WorldModelKernel | World state, causal relationships | L's understanding of reality |
| 07 | ExecutionKernel | Deterministic execution flow | How L executes plans |
| 08 | SafetyKernel | Engineering safety, approval gates | High-risk tool approvals |
| 09 | DeveloperKernel | Code execution, spec-first patterns | L's development style |
| 10 | PacketProtocolKernel | Packet envelope protocol | Event/packet structure |

---

## HIGH-RISK TOOLS (Require Igor Approval)

```python
HIGH_RISK_TOOLS = {
    "git_commit": True,           # Modifies codebase
    "gmp_run": True,              # Executes arbitrary GMP commands
    "mac_agent_exec": True,       # Executes on macOS system
    
    # Low-risk (auto-allowed):
    "memory_search": False,
    "memory_write": False,
    "kernel_read": False,
    "world_model_query": False,
    "mcp_call": False
}
```

**Approval Flow:**
1. Agent requests high-risk tool execution
2. Approval manager checks gate (Phase 6 wiring)
3. If gate requires approval → Slack notification to Igor
4. Igor approves/rejects within 5 minutes
5. If timeout → Auto-escalate to Igor's critical channel

---

## AUDIT TRAIL (Neo4j Nodes & Edges)

### Nodes Created

```cypher
CREATE (a:AgentInstance {
    instanceId: UUID,
    agentId: STRING,
    configJson: JSON,
    status: "INITIALIZING|READY|ERROR",
    kernels: [KERNEL_IDS],
    tools: [TOOL_NAMES],
    identity: JSON,
    initSignature: SHA256,
    createdAt: DATETIME,
    readyAt: DATETIME
})
```

### Edges Created

```cypher
-- Phase 3: Kernel bindings
(agent)-[:GOVERNEDBY {
    boundAt: DATETIME,
    kernelVersion: STRING,
    enforced: BOOLEAN
}]->(kernel)

-- Phase 5: Tool bindings
(agent)-[:CAN_USE {
    boundAt: DATETIME,
    requiresApproval: BOOLEAN
}]->(tool)

-- Phase 6: Approval gates
(agent)-[:REQUIRES_APPROVAL {
    gateId: STRING,
    createdAt: DATETIME,
    escalationTimeoutSec: INTEGER,
    escalationTarget: STRING
}]->(tool)
```

---

## ERROR HANDLING

### Phase Failure Pattern

```python
try:
    result = await phase_N_function(...)
except Exception as e:
    # Log error
    await substrate.log_error(
        phase=N,
        agent_id=agent.agent_id,
        error=str(e),
        timestamp=datetime.utcnow()
    )
    
    # Trigger rollback
    await substrate.cascade_delete(agent.instance_id)
    
    # Raise to caller
    raise RuntimeError(f"Phase {N} failed: {e}")
```

### Recoverable Errors

| Error | Phase | Recovery |
|-------|-------|----------|
| Missing kernel file | 1 | Verify YAML paths |
| Neo4j connection lost | 2-7 | Retry 3x with backoff |
| Redis timeout | 2 | Initialize working memory |
| Approval timeout | 6 | Escalate to Igor |

---

## DEPLOYMENT CHECKLIST

- [ ] Phase 0: Validate function implemented
- [ ] Phase 1: Kernel loader tested with all 10 kernels
- [ ] Phase 2: Neo4j node creation + Redis TTL verified
- [ ] Phase 3: GOVERNEDBY edges created (10 edges)
- [ ] Phase 4: Identity loading from kernel-02
- [ ] Phase 5: Tool binding + high-risk flags set
- [ ] Phase 6: Approval gates wired to SafetyKernel
- [ ] Phase 7: Verification checks (6 checks) + init signature computed
- [ ] Rollback: CASCADE delete tested
- [ ] Test suite: 12 test cases pass (5 positive + 5 negative + 2 rollback)
- [ ] Audit trail: All 7 phases logged to Neo4j
- [ ] Documentation: This superprompt + inline code comments

---

## QUICK REFERENCE: FILE LOCATIONS

**Bootstrap orchestrator:**
```
/l9/core/agents/bootstrap/orchestrator.py
```

**Phase implementations:**
```
/l9/core/agents/bootstrap/phase1_loadkernels.py (lines 40-120)
/l9/core/agents/bootstrap/phase2_instantiate.py (lines 60-150)
/l9/core/agents/bootstrap/phase3_bindkernels.py (lines 80-160)
/l9/core/agents/bootstrap/phase4_loadidentity.py (lines 90-170)
/l9/core/agents/bootstrap/phase5_bindtools.py (lines 100-180)
/l9/core/agents/bootstrap/phase6_wiregovernance.py (lines 120-200)
/l9/core/agents/bootstrap/phase7_verifyandlock.py (lines 140-220)
```

**Tests:**
```
/tests/core/agents/test_bootstrap_phases.py (12 test cases)
/tests/core/agents/conftest.py (fixtures)
```

---

## AUTHORITY MODEL

**Who can approve each phase?**

| Phase | Approval Required | Authority |
|-------|------------------|-----------|
| 0-5 | L-CTO Review | Cursor IDE (development) |
| 6 | Igor Sign-off | Igor (governance gates) |
| 7 | Audit Trail | Automated (verification) |

**High-Risk Tool Execution (Phase 6 gates):**
- Tool request → Approval manager → Igor (Slack)
- Igor approves within 5 minutes → Tool executes
- Igor denies → Tool blocked, logged
- Timeout → Auto-escalate

---

## FUTURE EVOLUTION (GMP 3.5+)

**Kernel Hot-Reload (Phase 8?):**
- Load kernel updates without re-bootstrap
- Propagate changes to running agents
- Maintain init_signature integrity

**Capability Evolution:**
- Add new tools post-Phase 5
- Modify approval gates post-Phase 6
- Update kernel versions in place

**Multi-Agent Coordination:**
- Bootstrap multiple agents atomically
- Shared kernel versions across agents
- Cross-agent approval gates

---

## REFERENCES

- **ISO 42001:** AI Management Systems (Plan-Do-Check-Act)
- **NIST AI RMF:** Govern-Map-Measure-Manage functions
- **EU Annex 22:** Data independence, acceptance criteria
- **OpenAI Levels:** Tier 1 (monitoring) → Tier 3 (conditional automation)

---

**Document Hash:** `51fe6f263a608850`  
**Last Updated:** 2026-01-14 19:54 UTC  
**Next Review:** After Phase 1 implementation
