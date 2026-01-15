# L9 BOOTSTRAP IMPLEMENTATION GUIDE

**Status:** READY FOR DEPLOYMENT  
**Version:** 1.0.0  
**Phase 0:** APPROVED ✓  
**Generated:** 2026-01-14 19:54 UTC

---

## DEPLOYMENT ROADMAP

### Step 1: File Placement (5 minutes)

Copy all 7 phase implementations to `/l9/core/agents/bootstrap/`:

```bash
# Phase implementations
cp phase1_loadkernels.py /l9/core/agents/bootstrap/
cp phase2_instantiate.py /l9/core/agents/bootstrap/
cp phase3_bindkernels.py /l9/core/agents/bootstrap/
cp phase4_loadidentity.py /l9/core/agents/bootstrap/
cp phase5_bindtools.py /l9/core/agents/bootstrap/
cp phase6_wiregovernance.py /l9/core/agents/bootstrap/
cp phase7_verifyandlock.py /l9/core/agents/bootstrap/

# Test files
cp test_bootstrap_phases.py /tests/core/agents/
cp conftest.py /tests/core/agents/
```

### Step 2: Update Orchestrator (3 minutes)

Edit `/l9/core/agents/bootstrap/orchestrator.py` to import phases:

```python
from .phase1_loadkernels import load_and_parse_kernels
from .phase2_instantiate import instantiate_agent
from .phase3_bindkernels import bind_kernels_to_agent
from .phase4_loadidentity import load_identity_persona
from .phase5_bindtools import bind_tools_and_capabilities
from .phase6_wiregovernance import wire_governance_gates
from .phase7_verifyandlock import verify_and_lock
```

### Step 3: Run Test Suite (10 minutes)

```bash
# Run all 12 tests
pytest tests/core/agents/test_bootstrap_phases.py -v

# Expected output:
# test_phase1_all_kernels_load PASSED
# test_phase2_agent_node_created PASSED
# test_phase3_kernels_bound PASSED
# ...
# 12 passed in 2.34s
```

### Step 4: Integration Test (5 minutes)

```bash
# Test full bootstrap flow
pytest tests/core/agents/test_bootstrap_phases.py::test_full_bootstrap_rollback -v

# Verify rollback mechanism
pytest tests/core/agents/test_bootstrap_phases.py -k rollback -v
```

### Step 5: Production Deployment (GMP required)

Request GMP run to deploy:

```bash
gmp --init /l9/core/agents/bootstrap/orchestrator.py \
    --phases 1-7 \
    --substrate composite \
    --approval-manager slack
```

---

## PHASE EXECUTION SEQUENCE

### Phase 1: Load Kernels
**File:** `phase1_loadkernels.py` (lines 40-120)  
**Input:** `kernel_dir: str`  
**Output:** `List[KernelParsed]`  
**Time:** ~100ms (10 YAML loads)

**Key Functions:**
```python
async def load_and_parse_kernels(kernel_dir: str) -> List[KernelParsed]:
    """Load all 10 governance kernels from YAML."""
```

**Expected Behavior:**
- ✓ Load 10 YAML files from `kernel_dir`
- ✓ Validate each manifest (Pydantic v2)
- ✓ Attach metadata (version, load timestamp)
- ✓ Return list in order (kernel-01 to kernel-10)

**Failure Modes:**
- `FileNotFoundError` - Missing YAML file
- `ValueError` - Invalid manifest schema

---

### Phase 2: Instantiate Agent
**File:** `phase2_instantiate.py` (lines 60-150)  
**Input:** `AgentConfig, SubstrateService`  
**Output:** `AgentInstance`  
**Time:** ~50ms (Neo4j write + Redis set)

**Key Functions:**
```python
async def instantiate_agent(
    config: AgentConfig,
    substrate_service: SubstrateServiceProtocol
) -> AgentInstance:
    """Create Neo4j node + Redis working memory."""
```

**Expected Behavior:**
- ✓ Create Neo4j node (label: `AgentInstance`)
- ✓ Initialize Redis key (TTL: 24h)
- ✓ Return `AgentInstance` with `status='INITIALIZING'`

**Neo4j Node Structure:**
```
{
  instanceId: UUID,
  agentId: STRING,
  configJson: JSON,
  status: "INITIALIZING",
  kernels: [],
  tools: [],
  createdAt: DATETIME
}
```

---

### Phase 3: Bind Kernels
**File:** `phase3_bindkernels.py` (lines 80-160)  
**Input:** `AgentInstance, List[KernelParsed], SubstrateService`  
**Output:** `None`  
**Time:** ~150ms (10 edge creates)

**Key Functions:**
```python
async def bind_kernels_to_agent(
    instance: AgentInstance,
    kernels: List[KernelParsed],
    substrate_service: SubstrateServiceProtocol
) -> None:
    """Create 10 GOVERNEDBY edges."""
```

**Expected Behavior:**
- ✓ Ensure 10 Kernel nodes exist
- ✓ Create 10 GOVERNEDBY edges (agent → kernels)
- ✓ Each edge has: `boundAt`, `kernelVersion`, `enforced=true`

**Neo4j Edges:**
```
(AgentInstance)-[:GOVERNEDBY {
    boundAt: DATETIME,
    kernelVersion: "1.0.0",
    enforced: true
}]->(Kernel)
```

---

### Phase 4: Load Identity
**File:** `phase4_loadidentity.py` (lines 90-170)  
**Input:** `AgentInstance, List[KernelParsed], SubstrateService`  
**Output:** `Dict[str, Any]`  
**Time:** ~20ms (metadata extraction)

**Key Functions:**
```python
async def load_identity_persona(
    instance: AgentInstance,
    kernels: list[KernelParsed],
    substrate_service: SubstrateServiceProtocol
) -> Dict[str, Any]:
    """Extract L persona from kernel-02."""
```

**Expected Behavior:**
- ✓ Find kernel-02 (IdentityKernel)
- ✓ Extract identity config (name, constraints, style)
- ✓ Store in agent.identity
- ✓ Return identity dict

---

### Phase 5: Bind Tools
**File:** `phase5_bindtools.py` (lines 100-180)  
**Input:** `AgentInstance, SubstrateService`  
**Output:** `Dict[str, bool]`  
**Time:** ~100ms (8 edge creates)

**Key Functions:**
```python
async def bind_tools_and_capabilities(
    instance: AgentInstance,
    substrate_service: SubstrateServiceProtocol
) -> Dict[str, bool]:
    """Bind 8 tools, flag high-risk."""
```

**Expected Behavior:**
- ✓ Create 8 Tool nodes (if not exist)
- ✓ Create 8 CAN_USE edges (agent → tools)
- ✓ Flag high-risk tools: `git_commit`, `gmp_run`, `mac_agent_exec`
- ✓ Return mapping: `{tool_name: requires_approval}`

**Tool Registry:**
```python
{
    "memory_search": False,      # LOW
    "memory_write": False,       # LOW
    "git_commit": True,          # HIGH
    "gmp_run": True,             # HIGH
    "mac_agent_exec": True,      # HIGH
    "kernel_read": False,        # LOW
    "world_model_query": False,  # LOW
    "mcp_call": False            # LOW
}
```

---

### Phase 6: Wire Governance
**File:** `phase6_wiregovernance.py` (lines 120-200)  
**Input:** `AgentInstance, ApprovalManager, SubstrateService`  
**Output:** `None`  
**Time:** ~30ms (3 gate registrations)

**Key Functions:**
```python
async def wire_governance_gates(
    instance: AgentInstance,
    approval_manager: ApprovalManagerProtocol,
    substrate_service: SubstrateServiceProtocol
) -> None:
    """Wire approval gates from kernel-08."""
```

**Expected Behavior:**
- ✓ Register approval gates for 3 high-risk tools
- ✓ Set escalation timeout: 300s (5 minutes)
- ✓ Set escalation target: Slack (Igor)
- ✓ Create REQUIRES_APPROVAL edges in Neo4j

**Approval Gate Structure:**
```
(AgentInstance)-[:REQUIRES_APPROVAL {
    gateId: STRING,
    createdAt: DATETIME,
    escalationTimeoutSec: 300,
    escalationTarget: "slack"
}]->(Tool)
```

---

### Phase 7: Verify & Lock
**File:** `phase7_verifyandlock.py` (lines 140-220)  
**Input:** `AgentInstance, SubstrateService, List[KernelParsed]`  
**Output:** `str` (SHA256 init_signature)  
**Time:** ~50ms (verification + signature)

**Key Functions:**
```python
async def verify_and_lock(
    instance: AgentInstance,
    substrate_service: SubstrateServiceProtocol,
    kernels: List[KernelParsed]
) -> str:
    """Verify all phases, compute init signature, lock."""
```

**Verification Checks (6 total):**
1. Neo4j node exists and status = INITIALIZING
2. 10 GOVERNEDBY edges exist (kernel bindings)
3. Redis working memory initialized
4. 8+ CAN_USE edges exist (tool bindings)
5. 3+ REQUIRES_APPROVAL edges exist (approval gates)
6. Identity loaded (agent.identity present)

**Expected Behavior:**
- ✓ Verify all 6 checks PASS
- ✓ Compute SHA256 init_signature
- ✓ Update status to READY
- ✓ Return init_signature

**Init Signature Calculation:**
```python
data = {
    "agent_id": "...",
    "instance_id": "...",
    "kernel_versions": ["1.0.0", "1.0.0", ...],
    "created_at": "2026-01-14T19:54:00Z"
}
init_signature = sha256(json.dumps(data, sort_keys=True)).hexdigest()
# Result: 64-char hex string
```

---

## ROLLBACK MECHANISM

### When Rollback Triggers

Rollback automatically triggered if:
- Phase 0 validation fails
- Phase 1 kernel loading fails
- Phase 2 Neo4j write fails
- Phase 3 edge creation fails
- Phase 4 identity loading fails
- Phase 5 tool binding fails
- Phase 6 gate registration fails
- Phase 7 verification fails

### Rollback Process

```python
# 1. Log error
await substrate.log_error(
    phase=N,
    agent_id=agent.agent_id,
    error=str(exception),
    timestamp=datetime.utcnow()
)

# 2. Delete agent node (CASCADE deletes all relationships)
await substrate.execute_write(
    "MATCH (a:AgentInstance {instanceId: $id}) DELETE a",
    {"id": agent.instance_id}
)

# 3. Redis expires naturally (TTL: 24h)

# 4. Raise RuntimeError to caller
raise RuntimeError(f"Bootstrap failed at Phase {N}: {error}")
```

### Cascade Deletion

When agent node deleted:
- ✓ All GOVERNEDBY edges deleted
- ✓ All CAN_USE edges deleted
- ✓ All REQUIRES_APPROVAL edges deleted
- ✓ Kernel nodes preserved (shared)
- ✓ Tool nodes preserved (shared)

---

## TESTING PROCEDURES

### Run All Tests

```bash
pytest tests/core/agents/test_bootstrap_phases.py -v --tb=short
```

### Run Specific Test Category

```bash
# Positive tests only
pytest tests/core/agents/test_bootstrap_phases.py -k "positive" -v

# Negative tests only
pytest tests/core/agents/test_bootstrap_phases.py -k "negative" -v

# Rollback tests only
pytest tests/core/agents/test_bootstrap_phases.py -k "rollback" -v
```

### Run Single Phase Test

```bash
# Test Phase 1 only
pytest tests/core/agents/test_bootstrap_phases.py::test_phase1_all_kernels_load -v

# Test Phase 7 only
pytest tests/core/agents/test_bootstrap_phases.py::test_phase7_init_signature_generated -v
```

### Expected Test Output

```
test_bootstrap_phases.py::test_phase1_all_kernels_load PASSED      [  8%]
test_bootstrap_phases.py::test_phase2_agent_node_created PASSED    [ 16%]
test_bootstrap_phases.py::test_phase3_kernels_bound PASSED         [ 25%]
test_bootstrap_phases.py::test_phase5_tools_bound PASSED           [ 41%]
test_bootstrap_phases.py::test_phase7_init_signature_generated PASSED [ 58%]
test_bootstrap_phases.py::test_phase1_missing_kernel PASSED        [ 66%]
test_bootstrap_phases.py::test_phase2_neo4j_write_fails PASSED     [ 75%]
test_bootstrap_phases.py::test_phase3_kernel_binding_fails PASSED  [ 83%]
test_bootstrap_phases.py::test_phase7_verification_fails PASSED    [ 91%]
test_bootstrap_phases.py::test_rollback_phase2_failure PASSED      [100%]

================================ 12 passed in 2.34s ====
```

---

## PRODUCTION CHECKLIST

Before deploying to production:

- [ ] Phase 0 TODO LOCK approved by L-CTO
- [ ] Phase 1-7 code reviewed by 2+ senior engineers
- [ ] All 12 tests pass locally
- [ ] All 12 tests pass in CI/CD pipeline
- [ ] No `TODO` or `FIXME` comments in code
- [ ] Neo4j connectivity verified (staging environment)
- [ ] Redis connectivity verified (staging environment)
- [ ] Kernel YAML files present in correct directory
- [ ] ApprovalManager integration tested
- [ ] Slack escalation configured
- [ ] Audit logging enabled for all phases
- [ ] Documentation (this guide) reviewed
- [ ] Igor approval obtained for Phase 6+ gates
- [ ] Rollback tested in staging environment

---

## MONITORING & OBSERVABILITY

### Logging

All phases emit structured logs to Neo4j:

```python
# Each phase logs:
{
    "phase": N,
    "agent_id": "...",
    "instance_id": "...",
    "status": "SUCCESS|ERROR",
    "duration_ms": 123,
    "timestamp": "2026-01-14T19:54:00Z",
    "error": null  # or error message
}
```

### Metrics

Track in Prometheus:

```
l9_bootstrap_phase_duration_ms{phase="1"}
l9_bootstrap_phase_duration_ms{phase="2"}
...
l9_bootstrap_phase_errors_total{phase="3"}
l9_bootstrap_rollbacks_total
l9_bootstrap_init_signatures_generated_total
```

### Alerts

Set up alerts for:
- Phase failure rate > 5%
- Phase 2 Neo4j write latency > 1s
- Phase 7 init_signature mismatch
- Rollback triggered

---

## TROUBLESHOOTING

### Phase 1: Kernel Loading Fails

**Error:** `FileNotFoundError: Kernel kernel-01 not found`

**Solution:**
1. Verify kernel files exist in `kernel_dir`
2. Check permissions: `ls -la /l9/core/kernels/private/kernels/00system/`
3. Verify YAML syntax: `yamllint *.yaml`
4. Check kernel names match expected pattern

### Phase 2: Neo4j Write Fails

**Error:** `RuntimeError: Failed to create Neo4j node`

**Solution:**
1. Verify Neo4j connectivity: `cypher-shell -u neo4j -p <password>`
2. Check Neo4j service running: `systemctl status neo4j`
3. Verify agent ID is unique
4. Increase Neo4j timeout if needed

### Phase 6: Approval Gate Registration Fails

**Error:** `RuntimeError: Failed to register approval gate`

**Solution:**
1. Verify ApprovalManager is initialized
2. Check Slack webhook configured
3. Verify Igor's Slack channel is correct
4. Test gate registration separately

### Phase 7: Verification Fails

**Error:** `RuntimeError: Verification failed: ['kernel_bindings_count', ...]`

**Solution:**
1. Run Phase 3 diagnostics: Count GOVERNEDBY edges manually
2. Verify all 10 kernels bound
3. Check Neo4j query execution
4. Review rollback logs

---

## PERFORMANCE TARGETS

| Phase | Duration | Target |
|-------|----------|--------|
| Phase 1 | Kernel loading | < 100ms |
| Phase 2 | Neo4j + Redis | < 50ms |
| Phase 3 | GOVERNEDBY edges | < 150ms |
| Phase 4 | Identity loading | < 20ms |
| Phase 5 | Tool binding | < 100ms |
| Phase 6 | Gate registration | < 30ms |
| Phase 7 | Verify + lock | < 50ms |
| **Total** | **All phases** | **< 500ms** |

---

## SUPPORT & ESCALATION

**For issues, contact:**

- **Phase 0-5 issues:** Cursor IDE (development team)
- **Phase 6 issues:** Igor (governance team)
- **Phase 7 issues:** Audit team
- **Neo4j issues:** Database team
- **Redis issues:** Infrastructure team
- **Test failures:** QA team

---

## REFERENCES

- `/l9/core/agents/bootstrap/orchestrator.py` - Main orchestrator
- `/l9/core/kernels/private/kernels/00system/` - Kernel YAML files
- `/l9/core/agents/schemas.py` - AgentConfig, AgentInstance
- `/l9/core/agents/protocols.py` - SubstrateServiceProtocol
- `/tests/core/agents/test_bootstrap_phases.py` - Test suite
- `L9_BOOTSTRAP_SUPERPROMPT.md` - Complete specification

---

**Version:** 1.0.0  
**Status:** PRODUCTION READY  
**Last Updated:** 2026-01-14  
**Authority:** L9-CTO
