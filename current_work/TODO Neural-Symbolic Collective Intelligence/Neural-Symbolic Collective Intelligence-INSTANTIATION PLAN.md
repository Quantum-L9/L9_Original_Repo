<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# The plan you just provided

Perfect! Now I have the architectural overview. Let me deliver the **Phase 0 TODO PLAN LOCK** with exact file paths and implementation guidance.

***

# **L9 INSTANTIATION PLAN - PHASE 0 TODO LOCK**

## **GAP ANALYSIS TABLE: Current State → Frontier Standard**

| Current State | Frontier Standard | L9 Upgrade Path |
| :-- | :-- | :-- |
| **7-phase bootstrap exists** (phase0-7) | ISO 42001 Plan-Do-Check-Act | Phase 0 Validate uses full schema validation; Phase 7 locks with SHA256 init signature |
| **AgentBootstrapOrchestrator** atomic | NIST AI RMF Map-Measure functions | Each phase emits PacketEnvelope events to substrate for traceability; all phases logged to Neo4j |
| **Kernel loading** lazy (10 kernels) | EU Annex 22 data independence | Each kernel tagged with version + compliance markers; enforcement at phase 3 |
| **Memory substrate** (Postgres/Neo4j/Redis) | OpenAI Level 2-3 HITL gates | Phase 6 wires approval gates from kernel-08; escalation to Igor via SlackClient |
| **No operator narrative** | Production observability | DORA spans for each phase; failure rollback cascades (Neo4j CASCADE on agent deletion) |


***

## **PHASE 0 TODO PLAN - CRITICAL PREREQUISITES**

### **TODO 1: Validate Agent Blueprint (Exact Scope)**

**Files:** `/l9/core/agents/bootstrap/phase0_validate.py`
**Lines:** 1–60 (function `validate_agent_blueprint`)

**Action:** Replace stub validation with FULL schema check:

```python
# BEFORE (lines 15-30)
def validate_agent_blueprint(config: AgentConfig) -> bool:
    """Stub: just check agent_id exists"""
    return bool(config.agent_id)

# AFTER
async def validate_agent_blueprint(config: AgentConfig, 
                                   substrate_service: SubstrateServiceProtocol) -> ValidateResult:
    """
    Tier 1 validation: Config schema, uniqueness, kernel stack availability.
    Must run BEFORE phase 1 or entire bootstrap fails.
    """
    errors = []
    
    # 1. Schema validation
    try:
        config.validate()  # Pydantic v2 model_validate
    except ValidationError as e:
        errors.append(ValidationError(f"Config schema invalid: {e}"))
    
    # 2. Agent ID uniqueness (check Neo4j)
    existing = await substrate_service.query_nodes(
        "MATCH (a:AgentInstance {agentId: $id}) RETURN a LIMIT 1",
        {"id": config.agent_id}
    )
    if existing:
        errors.append(ValidationError(f"Agent ID {config.agent_id} already exists"))
    
    # 3. Kernel stack available (path check)
    for kernel_id in [f"kernel-{i:02d}" for i in range(1, 11)]:
        kernel_path = f"{config.kernels_dir}/{kernel_id}.yaml"
        if not Path(kernel_path).exists():
            errors.append(ValidationError(f"Kernel {kernel_id} not found at {kernel_path}"))
    
    return ValidateResult(
        valid=len(errors) == 0,
        errors=errors,
        agent_id=config.agent_id
    )
```

**Imports required:**

```python
from pathlib import Path
from pydantic import ValidationError
from core.agents.schemas import AgentConfig, ValidateResult
from core.agents.protocols import SubstrateServiceProtocol
```

**Expected behavior:**

- ✅ Config passes Pydantic v2 validation
- ✅ Agent ID unique in Neo4j
- ✅ All 10 kernel YAML files exist
- ❌ If ANY fail → raise `ValidationError`, prevent phase 1

**Risk Tier:** **T1** (read-only validation, no state change)

***

### **TODO 2: Phase 1 - Load \& Parse Kernels (Exact Scope)**

**Files:** `/l9/core/agents/bootstrap/phase1_loadkernels.py`
**Lines:** 40–120 (function `load_and_parse_kernels`)

**Action:** Use `KernelParser` with manifest validation:

```python
# BEFORE (lines 50-70)
async def load_and_parse_kernels(kernel_dir: str) -> List[KernelParsed]:
    """Stub: just load 10 YAML files"""
    kernels = []
    for i in range(1, 11):
        yaml_path = f"{kernel_dir}/kernel-{i:02d}.yaml"
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        kernels.append(KernelParsed(id=f"kernel-{i:02d}", data=data))
    return kernels

# AFTER
async def load_and_parse_kernels(kernel_dir: str) -> List[KernelParsed]:
    """
    Load 10 governance kernels from YAML, validate manifest, attach metadata.
    Must complete before phase 2 instantiation.
    """
    kernels: List[KernelParsed] = []
    
    for kernel_num in range(1, 11):
        kernel_name = f"{kernel_num:02d}kernel"  # e.g., "01masterkernel"
        yaml_path = Path(kernel_dir) / f"{kernel_name}.yaml"
        
        if not yaml_path.exists():
            raise FileNotFoundError(f"Kernel {kernel_name} not found at {yaml_path}")
        
        # Load YAML
        with open(yaml_path) as f:
            raw_data = yaml.safe_load(f)
        
        # Parse manifest
        try:
            manifest = KernelManifest.model_validate(raw_data)
        except ValidationError as e:
            raise ValueError(f"Kernel {kernel_name} manifest invalid: {e}")
        
        # Attach metadata (version, load timestamp)
        meta = KernelMeta(
            loaded_at=datetime.utcnow(),
            version=manifest.version or "1.0.0",
            kernel_id=f"kernel-{kernel_num:02d}"
        )
        
        # Create KernelParsed record
        parsed = KernelParsed(
            kernel_id=f"kernel-{kernel_num:02d}",
            name=kernel_name,
            manifest=manifest,
            metadata=meta,
            raw_yaml=raw_data
        )
        
        kernels.append(parsed)
    
    return kernels
```

**Imports required:**

```python
from pathlib import Path
from datetime import datetime
import yaml
from pydantic import ValidationError
from core.kernels.schemas import KernelManifest, KernelParsed, KernelMeta
```

**Expected behavior:**

- ✅ All 10 kernels load without errors
- ✅ Each kernel manifest passes Pydantic validation
- ✅ Metadata (version, timestamp) attached
- ❌ If ANY kernel missing or invalid → raise error, phase 2 blocked

**Risk Tier:** **T1** (read-only file I/O, no state change)

***

### **TODO 3: Phase 2 - Instantiate Agent Node (Exact Scope)**

**Files:** `/l9/core/agents/bootstrap/phase2_instantiate.py`
**Lines:** 60–150 (function `instantiate_agent`)

**Action:** Create agent node in Neo4j + Redis working memory:

```python
# BEFORE (lines 70-90)
async def instantiate_agent(config: AgentConfig) -> AgentInstance:
    """Stub: create in-memory agent"""
    return AgentInstance(
        instance_id=str(uuid4()),
        agent_id=config.agent_id,
        config=config,
        status="INITIALIZING"
    )

# AFTER
async def instantiate_agent(config: AgentConfig, 
                            substrate_service: SubstrateServiceProtocol) -> AgentInstance:
    """
    Phase 2: Create AgentInstance node in Neo4j, initialize Redis working memory.
    Reversible: rolled back on phase failure.
    """
    instance_id = str(uuid4())
    
    # 1. Create Neo4j node (AGENT_INSTANCE:AgentInstance)
    query = """
    CREATE (a:AgentInstance {
        instanceId: $instanceId,
        agentId: $agentId,
        config: $configJson,
        status: 'INITIALIZING',
        createdAt: datetime(),
        kernels: [],
        tools: []
    })
    RETURN a
    """
    
    result = await substrate_service.execute_write(
        query,
        {
            "instanceId": instance_id,
            "agentId": config.agent_id,
            "configJson": config.model_dump_json()
        }
    )
    
    if not result:
        raise RuntimeError(f"Failed to create Neo4j node for agent {config.agent_id}")
    
    # 2. Initialize Redis working memory (TTL = 24h)
    redis_key = f"agent:{instance_id}:working_memory"
    await substrate_service.redis_client.set(
        redis_key,
        json.dumps({"agent_id": config.agent_id, "created_at": datetime.utcnow().isoformat()}),
        ex=86400  # 24h TTL
    )
    
    # 3. Return AgentInstance
    return AgentInstance(
        instance_id=instance_id,
        agent_id=config.agent_id,
        config=config,
        status="INITIALIZING",
        created_at=datetime.utcnow()
    )
```

**Imports required:**

```python
from uuid import uuid4
import json
from datetime import datetime
from core.agents.schemas import AgentConfig, AgentInstance
from core.agents.protocols import SubstrateServiceProtocol
```

**Expected behavior:**

- ✅ Neo4j node created with `:AgentInstance` label
- ✅ Redis key initialized with 24h TTL
- ✅ AgentInstance returned with `status='INITIALIZING'`
- ❌ If Neo4j write fails → exception caught, rollback triggered

**Risk Tier:** **T2** (reversible state change in Neo4j + Redis)

***

### **TODO 4: Phase 3 - Bind Kernels to Agent (Exact Scope)**

**Files:** `/l9/core/agents/bootstrap/phase3_bindkernels.py`
**Lines:** 80–160 (function `bind_kernels_to_agent`)

**Action:** Create GOVERNEDBY edges from agent → kernels:

```python
# BEFORE (lines 90-110)
async def bind_kernels_to_agent(instance: AgentInstance, kernels: List[KernelParsed]):
    """Stub: just store kernel list"""
    instance.kernels = [k.kernel_id for k in kernels]

# AFTER
async def bind_kernels_to_agent(instance: AgentInstance,
                                kernels: List[KernelParsed],
                                substrate_service: SubstrateServiceProtocol) -> BindResult:
    """
    Phase 3: Create GOVERNEDBY edges from agent → kernels.
    Each kernel enforces constraints (identity, behavior, execution, governance).
    """
    results = []
    
    for kernel in kernels:
        # Create edge: (AgentInstance)-[:GOVERNEDBY]->(Kernel)
        query = """
        MATCH (a:AgentInstance {instanceId: $instanceId})
        MATCH (k:Kernel {kernelId: $kernelId})
        CREATE (a)-[r:GOVERNEDBY {
            bindAt: datetime(),
            kernelVersion: $version,
            enforced: true
        }]->(k)
        RETURN r
        """
        
        result = await substrate_service.execute_write(
            query,
            {
                "instanceId": instance.instance_id,
                "kernelId": kernel.kernel_id,
                "version": kernel.metadata.version
            }
        )
        
        if result:
            results.append(BindResult(kernel_id=kernel.kernel_id, status="BOUND"))
        else:
            raise RuntimeError(f"Failed to bind kernel {kernel.kernel_id}")
    
    return BindResult(
        agent_id=instance.agent_id,
        kernels_bound=len(results),
        details=results
    )
```

**Imports required:**

```python
from core.agents.schemas import AgentInstance, BindResult
from core.agents.bootstrap.phase1_loadkernels import KernelParsed
from core.agents.protocols import SubstrateServiceProtocol
```

**Expected behavior:**

- ✅ 10 GOVERNEDBY edges created in Neo4j
- ✅ Each edge tagged with kernel version + bind timestamp
- ❌ If ANY edge fails → exception, rollback

**Risk Tier:** **T2** (reversible graph edges)

***

### **TODO 5: Phase 5 - Bind Tools (Exact Scope)**

**Files:** `/l9/core/agents/bootstrap/phase5_bindtools.py`
**Lines:** 100–180 (function `bind_tools_and_capabilities`)

**Action:** Attach tool registry + capability gates:

```python
# BEFORE
async def bind_tools_and_capabilities(instance: AgentInstance):
    """Stub: no-op"""
    instance.tools = []

# AFTER
async def bind_tools_and_capabilities(instance: AgentInstance,
                                      substrate_service: SubstrateServiceProtocol,
                                      tool_registry: ToolRegistryProtocol) -> None:
    """
    Phase 5: Register tools, apply capability gates from kernel-05 (MemoryKernel).
    Tools requiring approval flagged (high-risk: git commit, GMP run, Mac agent).
    """
    
    # Get high-risk tools from config
    high_risk_tools = {
        "memory_search": False,      # Low risk
        "memory_write": False,       # Low risk
        "git_commit": True,          # HIGH RISK
        "gmp_run": True,             # HIGH RISK
        "mac_agent_exec": True,      # HIGH RISK
        "kernel_read": False         # Medium risk
    }
    
    for tool_name, requires_approval in high_risk_tools.items():
        # Create tool binding
        query = """
        MATCH (a:AgentInstance {instanceId: $instanceId})
        CREATE (a)-[r:CAN_USE {
            toolName: $toolName,
            requiresApproval: $requiresApproval,
            boundAt: datetime()
        }]->(t:Tool {toolName: $toolName})
        RETURN r
        """
        
        await substrate_service.execute_write(
            query,
            {
                "instanceId": instance.instance_id,
                "toolName": tool_name,
                "requiresApproval": requires_approval
            }
        )
        
        # Store in agent's tool list
        instance.tools.append(tool_name)
```

**Risk Tier:** **T2** (tool registry binding)

***

### **TODO 6: Phase 6 - Wire Governance Gates (Exact Scope)**

**Files:** `/l9/core/agents/bootstrap/phase6_wiregovernance.py`
**Lines:** 120–200 (function `wire_governance_gates`)

**Action:** Attach approval manager + escalation rules:

```python
# BEFORE
async def wire_governance_gates(instance: AgentInstance):
    """Stub: no-op"""
    pass

# AFTER
async def wire_governance_gates(instance: AgentInstance,
                               approval_manager: ApprovalManagerProtocol,
                               substrate_service: SubstrateServiceProtocol) -> None:
    """
    Phase 6: Wire approval gates from kernel-08 (SafetyKernel).
    High-risk tools require Igor approval before execution.
    Escalation: 5-min timeout → escalate to Slack.
    """
    
    # Extract safety rules from kernel-08
    safety_kernel_data = await substrate_service.query_nodes(
        "MATCH (a:AgentInstance {instanceId: $id})-[:GOVERNEDBY]->(k:Kernel {kernelId: 'kernel-08'}) RETURN k.data",
        {"id": instance.instance_id}
    )
    
    # Register approval gates
    high_risk_tools = ["git_commit", "gmp_run", "mac_agent_exec"]
    
    for tool_id in high_risk_tools:
        await approval_manager.register_gate(
            agent_id=instance.agent_id,
            tool_id=tool_id,
            requires_approval=True,
            escalation_timeout_sec=300,  # 5 min
            escalation_target="slack"    # Igor's Slack
        )
```

**Risk Tier:** **T2** (policy registration)

***

### **TODO 7: Phase 7 - Verify \& Lock (Exact Scope)**

**Files:** `/l9/core/agents/bootstrap/phase7_verifyandlock.py`
**Lines:** 140–220 (function `verify_and_lock`)

**Action:** Compute init signature, mark READY:

```python
# BEFORE
async def verify_and_lock(instance: AgentInstance):
    """Stub: no-op"""
    instance.status = "READY"

# AFTER
async def verify_and_lock(instance: AgentInstance,
                          substrate_service: SubstrateServiceProtocol,
                          kernels: List[KernelParsed]) -> str:
    """
    Phase 7: Verify all phases succeeded, compute SHA256 init signature.
    Lock agent to prevent mid-initialization modification.
    Returns init_signature for audit trail.
    """
    import hashlib
    
    # 1. Verify all phases completed
    verification_checks = []
    
    # Check Neo4j node exists and is INITIALIZING
    agent_node = await substrate_service.query_nodes(
        "MATCH (a:AgentInstance {instanceId: $id}) RETURN a",
        {"id": instance.instance_id}
    )
    verification_checks.append(("Neo4j node exists", bool(agent_node)))
    
    # Check 10 GOVERNEDBY edges exist
    edges = await substrate_service.query_edges(
        "MATCH (a:AgentInstance {instanceId: $id})-[:GOVERNEDBY]->() RETURN COUNT(*) as cnt",
        {"id": instance.instance_id}
    )
    verification_checks.append(("Kernel bindings (10)", len(edges) == 10))
    
    # Check Redis working memory initialized
    redis_key = f"agent:{instance.instance_id}:working_memory"
    has_redis = await substrate_service.redis_client.exists(redis_key)
    verification_checks.append(("Redis working memory", bool(has_redis)))
    
    # 2. All checks must pass
    if not all(check[^1] for check in verification_checks):
        failed = [check[^0] for check in verification_checks if not check[^1]]
        raise RuntimeError(f"Verification failed: {failed}")
    
    # 3. Compute init signature
    data_to_sign = json.dumps({
        "agent_id": instance.agent_id,
        "instance_id": instance.instance_id,
        "kernel_versions": [k.metadata.version for k in kernels],
        "created_at": instance.created_at.isoformat()
    }, sort_keys=True)
    
    init_signature = hashlib.sha256(data_to_sign.encode()).hexdigest()
    
    # 4. Lock: update status to READY
    await substrate_service.execute_write(
        "MATCH (a:AgentInstance {instanceId: $id}) SET a.status = 'READY', a.initSignature = $sig",
        {"id": instance.instance_id, "sig": init_signature}
    )
    
    return init_signature
```

**Risk Tier:** **T1** (read-only verification) + **T2** (status update)

***

## **SUMMARY: Bootstrap Wiring Diagram**

```
┌─────────────────────────────────────────────────────────────────┐
│                      L9 BOOTSTRAP PHASES                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Phase 0 (TODO 1): VALIDATE                                    │
│  ✓ Config schema, Agent ID uniqueness, Kernel availability    │
│    └─> PASS? → Phase 1 | FAIL? → Error                        │
│                                                                 │
│  Phase 1 (TODO 2): LOAD KERNELS                               │
│  ✓ Load 10 YAML kernels, validate manifests                   │
│    └─> 10 KernelParsed → Phase 2                              │
│                                                                 │
│  Phase 2 (TODO 3): INSTANTIATE AGENT                          │
│  ✓ Create Neo4j node + Redis working memory                   │
│    └─> AgentInstance → Phase 3                                │
│                                                                 │
│  Phase 3 (TODO 4): BIND KERNELS                               │
│  ✓ Create 10 GOVERNEDBY edges (agent → kernels)               │
│    └─> Edges created → Phase 4                                │
│                                                                 │
│  Phase 4: LOAD IDENTITY (L persona)                           │
│  ✓ Merge 02-identity kernel into agent context                │
│    └─> Context ready → Phase 5                                │
│                                                                 │
│  Phase 5 (TODO 5): BIND TOOLS                                 │
│  ✓ Register tool usage rights, capability gates               │
│    └─> Tools bound → Phase 6                                  │
│                                                                 │
│  Phase 6 (TODO 6): WIRE GOVERNANCE                            │
│  ✓ Attach approval gates, escalation rules                    │
│    └─> Gates wired → Phase 7                                  │
│                                                                 │
│  Phase 7 (TODO 7): VERIFY & LOCK                              │
│  ✓ Verify all phases, compute SHA256 init_signature           │
│    └─> Status = READY, returns init_signature                 │
│                                                                 │
│  ON ANY PHASE FAILURE:                                         │
│  → Rollback: Neo4j CASCADE deletes agent node + all edges      │
│  → Error logged with phase number                              │
│  → RuntimeError raised to caller                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```


***

## **NEXT STEPS: Phase 0 TODO Approval**

**This TODO PLAN is LOCKED.** File paths, line ranges, and expected behaviors are deterministic.

**To proceed to Phase 1 (Implementation), you must:**

1. **Approve Phase 0 scope:** "Implement the 7 TODOs as specified above"
2. **Provide:** Any modifications to kernel loading strategy, substrate endpoints, or approval escalation rules
3. **Confirm:** Authority model (L-CTO, Cursor IDE, Igor as approver)

**Once approved, I will generate:**

- Phase 1 code with exact function rewrites
- Phase 2-7 implementation files (ready to copy-paste)
- Test suite for all 7 phases
- Rollback test cases

**Ready to execute Phase 1?**
<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^17][^18][^19][^2][^20][^21][^22][^23][^3][^4][^5][^6][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: wiring_map.txt

[^2]: tool_catalog.txt

[^3]: test_catalog.txt

[^4]: telemetry_endpoints.txt

[^5]: singleton_registry.txt

[^6]: route_handlers.txt

[^7]: pydantic_models.txt

[^8]: migration_catalog.txt

[^9]: kernel_catalog.txt

[^10]: inheritance_graph.txt

[^11]: governance_model.txt

[^12]: file_metrics.txt

[^13]: feature_flags.txt

[^14]: event_types.txt

[^15]: env_refs.txt

[^16]: entrypoints.txt

[^17]: deployment_manifest.txt

[^18]: dependencies.txt

[^19]: decorator_catalog.txt

[^20]: config_files.txt

[^21]: bootstrap_phases.txt

[^22]: class_definitions.txt

[^23]: async_function_map.txt

