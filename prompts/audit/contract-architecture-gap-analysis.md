# L9 Contract Architecture Gap Analysis — Deep Audit Prompt

## Objective

Conduct a systematic audit of L9's contract-based architecture to identify **communication pathways, state mutations, and trust boundaries that lack formal contracts**.

A "contract" in L9 is a **machine-enforceable specification** that defines:
- **Pre-conditions**: What must be true before an action
- **Post-conditions**: What must be true after an action
- **Invariants**: What must remain true throughout
- **Authority**: Who can approve/execute
- **Evidence**: What proof is required
- **Rollback**: How to undo if failed

---

## Reference Architecture

### Existing Contract Infrastructure

| Component | Location | Purpose |
|-----------|----------|---------|
| **Accountability Hypergraph** | `core/governance/contract_hypergraph/accountability_hypergraph.yaml` | Central schema for permissions, causality, liability |
| **GMP Contract** | `agents/cursor/gmp_protocol/gmp-contract.yaml` | Process contract for governed changes |
| **Tool Risk Policy** | `config/policies/high_risk_tools.yaml` | Risk classification for tools |
| **Protected Files Policy** | `config/policies/protected_files.yaml` | Files requiring approval |

### Contract Hyperedge Types (from accountability_hypergraph.yaml)

```
REQUIRES    → action requires [capability, authority, evidence, ledger_entry]
VIOLATES    → action breaks [rule, invariant, prohibition]
ISSUED_BY   → verdict came from [authority, quorum]
SUPPORTS    → evidence backs [verdict, contract]
CAUSES      → action led to [state_transition]
GOVERNS     → contract applies to [agent, capability, action]
ATTESTS     → ledger proves [action, verdict]
IMPACTS     → change affects [tests, services, schemas, downstream_modules]
DELEGATES_TO → authority delegation chain
```

---

## Audit Scope

### 1. Agent-to-Agent Communication

**Question**: When Agent A asks Agent B to do something, is there a contract?

**Examine**:
- `orchestration/*.py` — Task routing between agents
- `orchestrators/**/*.py` — Swarm coordination
- `collaborative_cells/*.py` — Cell-to-cell messaging
- `runtime/websocket_orchestrator.py` — Real-time agent comms

**Contract Requirements**:
- [ ] Request schema validation
- [ ] Response schema validation
- [ ] Timeout/retry semantics
- [ ] Authority verification (can A ask B?)
- [ ] Audit trail (logged to PacketStore)

**Gap Detection Pattern**:
```python
# RED FLAG: Direct function call without contract
await other_agent.do_something(payload)  # No contract!

# GREEN: Contract-mediated communication
await contract_broker.request(
    from_agent="A",
    to_agent="B", 
    action="do_something",
    payload=payload,
    authority_proof=proof
)
```

---

### 2. Tool Invocations

**Question**: When an agent invokes a tool, is there a contract defining permissions and audit?

**Examine**:
- `core/tools/base_registry.py` — Tool definitions
- `core/tools/registry_adapter.py` — Tool dispatch
- `runtime/tool_registry.py` — Runtime tool access
- `core/governance/tool_risk_policy.py` — Risk classification

**Contract Requirements**:
- [ ] Tool has risk classification
- [ ] High-risk tools require authority proof
- [ ] Tool inputs are validated against schema
- [ ] Tool outputs are validated against schema
- [ ] Execution is logged to PacketStore
- [ ] Failure has defined rollback

**Gap Detection Pattern**:
```python
# RED FLAG: Tool without risk classification
@register_tool(category="unknown")  # No risk class!
async def dangerous_operation(): ...

# GREEN: Fully contracted tool
@register_tool(
    category="infrastructure",
    risk_class="high",
    requires_approval=True,
    rollback_handler=rollback_fn
)
async def dangerous_operation(): ...
```

---

### 3. Memory Operations

**Question**: When data is written to/read from memory substrate, is there a contract?

**Examine**:
- `memory/substrate_service.py` — Core memory operations
- `memory/substrate_repository.py` — Data access layer
- `memory/ingestion.py` — Packet ingestion
- `memory/graph_memory.py` — Neo4j operations

**Contract Requirements**:
- [ ] Write operations have schema validation
- [ ] Write operations have deduplication
- [ ] Write operations have audit trail
- [ ] Read operations have access control
- [ ] Deletions require authority proof
- [ ] Mutations are idempotent

**Gap Detection Pattern**:
```python
# RED FLAG: Direct DB write without contract
await db.execute("INSERT INTO packets ...")  # No contract!

# GREEN: Contract-mediated write
await memory_contract.ingest_packet(
    envelope=validated_envelope,
    authority=agent_authority,
    dedup_key=content_hash
)
```

---

### 4. External API Calls

**Question**: When L9 calls external services, is there a contract defining failure modes?

**Examine**:
- `services/research/*.py` — Research API calls
- `api/slack_client.py` — Slack integration
- `runtime/mcp_tool.py` — MCP server calls
- `clients/*.py` — External clients

**Contract Requirements**:
- [ ] Timeout defined
- [ ] Retry policy defined
- [ ] Circuit breaker for repeated failures
- [ ] Fallback behavior defined
- [ ] Response validation
- [ ] Rate limiting

**Gap Detection Pattern**:
```python
# RED FLAG: External call without contract
response = await httpx.get(url)  # No timeout, no retry, no validation!

# GREEN: Contracted external call
response = await external_contract.call(
    url=url,
    timeout_ms=5000,
    retry_policy=RetryPolicy(max_attempts=3),
    circuit_breaker=breaker,
    response_schema=ResponseSchema
)
```

---

### 5. State Mutations

**Question**: When system state changes, is there a contract ensuring consistency?

**Examine**:
- `runtime/task_queue.py` — Task state transitions
- `core/agents/executor.py` — Agent execution state
- `orchestration/*.py` — Orchestration state
- `world_model/*.py` — World model state

**Contract Requirements**:
- [ ] State machine defined (valid transitions)
- [ ] Transition logged to audit trail
- [ ] Invalid transitions rejected
- [ ] Concurrent mutation handled
- [ ] Recovery from inconsistent state

**Gap Detection Pattern**:
```python
# RED FLAG: State mutation without contract
self.state = "running"  # No validation, no audit!

# GREEN: Contracted state transition
await state_contract.transition(
    from_state="pending",
    to_state="running",
    actor=agent_id,
    evidence=start_evidence
)
```

---

### 6. Authority Delegation

**Question**: When authority is delegated, is there a contract defining scope and revocation?

**Examine**:
- `core/governance/approvals.py` — Approval system
- `core/governance/approval_gate.py` — Gate enforcement
- `config/policies/*.yaml` — Policy definitions

**Contract Requirements**:
- [ ] Delegation has scope limits
- [ ] Delegation has expiration
- [ ] Delegation chain is auditable
- [ ] Revocation is immediate
- [ ] Authority cannot exceed delegator's authority

**Gap Detection Pattern**:
```python
# RED FLAG: Unbounded delegation
agent.grant_capability("*")  # No scope limit!

# GREEN: Contracted delegation
await authority_contract.delegate(
    from_authority=igor,
    to_agent=l_agent,
    capability="tool:perplexity_search",
    scope={"max_calls_per_hour": 100},
    expires_at=datetime.now() + timedelta(hours=24)
)
```

---

### 7. Deployment & Infrastructure

**Question**: When infrastructure changes, is there a contract ensuring safety?

**Examine**:
- `deploy/k8s/**/*.yaml` — K8s manifests
- `docker-compose.yml` — Docker configuration
- `config/subsystems/*.yaml` — Subsystem configs

**Contract Requirements**:
- [ ] Changes require GMP process
- [ ] Rollback plan defined
- [ ] Health checks defined
- [ ] Blast radius assessed
- [ ] Approval required for production

---

## Audit Execution Steps

### Phase 1: Inventory (Read-Only)

1. **Map all communication pathways**
   ```bash
   grep -r "await.*\." orchestration/ orchestrators/ collaborative_cells/ | grep -v "test"
   ```

2. **Map all tool invocations**
   ```bash
   grep -r "@register_tool" core/tools/ runtime/
   ```

3. **Map all memory operations**
   ```bash
   grep -r "ingest_packet\|execute\|INSERT\|UPDATE\|DELETE" memory/
   ```

4. **Map all external calls**
   ```bash
   grep -r "httpx\|aiohttp\|requests\|fetch" services/ clients/ api/
   ```

### Phase 2: Gap Identification

For each communication/operation found:

| Pathway | Has Contract? | Contract Location | Gap Type |
|---------|---------------|-------------------|----------|
| `orchestrator_A → orchestrator_B` | ❌ | N/A | Missing inter-orchestrator contract |
| `agent.invoke_tool("X")` | ✅ | `tool_risk_policy.yaml` | None |
| ... | ... | ... | ... |

### Phase 3: Priority Classification

Classify gaps by risk:

| Priority | Criteria | Action |
|----------|----------|--------|
| **P0 - Critical** | Security boundary, data mutation, external API | Immediate contract needed |
| **P1 - High** | Agent coordination, state machine | Contract in next sprint |
| **P2 - Medium** | Internal helper functions | Contract when touched |
| **P3 - Low** | Read-only, idempotent | Document but defer |

### Phase 4: Contract Design

For each P0/P1 gap, design contract:

```yaml
contract:
  name: "<operation>_contract"
  version: "1.0.0"
  
  parties:
    - caller: <who initiates>
    - callee: <who executes>
    - authority: <who approves>
  
  preconditions:
    - <condition 1>
    - <condition 2>
  
  postconditions:
    - <outcome 1>
    - <outcome 2>
  
  invariants:
    - <must always be true>
  
  failure_modes:
    - condition: <when>
      response: <what happens>
      rollback: <how to undo>
  
  audit:
    log_to: "PacketStore"
    retention: "7 years"
```

---

## Output Format

### Gap Report Structure

```markdown
# L9 Contract Gap Analysis Report

**Date**: YYYY-MM-DD
**Auditor**: <name>
**Scope**: <modules audited>

## Executive Summary

- Total pathways examined: N
- Pathways with contracts: M
- **Coverage**: M/N (X%)
- **Critical gaps**: K

## Critical Gaps (P0)

### Gap 1: <name>

- **Location**: `path/to/file.py:line`
- **Description**: <what's missing>
- **Risk**: <what could go wrong>
- **Recommended Contract**: <link to design>

### Gap 2: ...

## High Priority Gaps (P1)

...

## Recommendations

1. <action item 1>
2. <action item 2>
...
```

---

## Validation Queries

After implementing contracts, validate with:

```cypher
// Neo4j: Find actions without contracts
MATCH (a:Action)
WHERE NOT (a)-[:GOVERNED_BY]->(:Contract)
RETURN a.name, a.location

// Neo4j: Find delegations without expiration
MATCH (d:Delegation)
WHERE d.expires_at IS NULL
RETURN d
```

---

## References

- `core/governance/contract_hypergraph/accountability_hypergraph.yaml` — Master schema
- `agents/cursor/gmp_protocol/gmp-contract.yaml` — Process contract example
- `config/policies/high_risk_tools.yaml` — Tool risk classification
- `readme/adr/0022-registry-pattern.md` — Registry architecture
