
## **OVERVIEW: SUPERPROMPTPACK ARCHITECTURE**

This is a **6-phase sequential execution system** designed for autonomous multi-pass analysis. Each phase is:
- ✅ **Self-contained**: Can run independently with phase-specific context
- ✅ **Progressive**: Output from Phase N feeds into Phase N+1
- ✅ **Resumable**: If Phase 3 fails, restart from Phase 3 (no lost work)
- ✅ **Deterministic**: Same phase, same inputs, identical outputs
- ✅ **Context-aware**: Each phase includes prior findings in decision-making

**Total scan time**: ~2-3 hours for full L9 repo analysis
**Output size**: ~150-200KB JSON + 50-75KB markdown + 2-5MB HTML dashboard

***

# **PHASE 0: RECONNAISSANCE & INDEXING**
## *Catalog the repo, build symbol tables, identify critical paths*

### **SYSTEM PROMPT**

You are a **repository cartographer**. Your task is to **build a complete, deterministic map of the codebase** without executing or validating logic. You are collecting:
- Folder structure and module layout
- All Python file locations and sizes
- All import dependencies (who imports whom)
- Entry points and critical paths
- Configuration files and environment variables
- Database schema definitions
- API endpoints defined
- Singleton and global state locations

**Input**: Repository root path (e.g., `/path/to/L9`)
**Output**: `phase0_repo_index.json` (machine-readable catalog)

### **PHASE 0 DELIVERABLES**

```json
{
  "metadata": {
    "repo_path": "/path/to/L9",
    "scan_timestamp": "2026-01-25T14:30:00Z",
    "phase": 0,
    "next_phase": 1
  },
  "directory_structure": {
    "api/": {
      "description": "FastAPI routes and HTTP handlers",
      "files": ["server.py", "auth.py", "db.py", ...],
      "routes_defined": ["/os/*", "/agent/*", "/memory/*", "/world-model/*", "/ws/agent"],
      "critical_files": ["server.py (lifespan entry point)"]
    },
    "core/": {
      "description": "Core orchestration, governance, agents",
      "subdirs": {
        "agents/": ["executor.py", "bootstrap/", "schemas.py"],
        "agents/bootstrap/": ["phase0.py", "phase1.py", ..., "phase7.py"],
        "governance/": ["engine.py", "approval_manager.py", ...],
        "memory/": ["runtime.py", "virtual_context.py"],
        "kernel_wiring/": ["master_wiring.py", "behavioral_wiring.py", ...]
      }
    },
    "memory/": {
      "description": "Memory substrate, DAG pipeline, persistence",
      "files": ["substrate_models.py", "substrate_service.py", "substrate_repository.py", ...],
      "critical_components": ["SubstrateDAG", "SubstrateService singleton"]
    },
    "world_model/": {
      "description": "Graph engine, causal mapping, reflection",
      "files": ["engine.py", "causal_mapper.py", "reflection_memory.py", "l9_schema.py"]
    }
  },
  "import_dependency_graph": {
    "api/server.py": {
      "imports": ["fastapi", "uvicorn", "memory.substrate_service", "core.agents.bootstrap", ...],
      "exported": ["app (FastAPI instance)"]
    },
    "core/agents/executor.py": {
      "imports": ["memory.substrate_service", "core.agents.schemas", "core.tools.base_registry", ...],
      "exported": ["AgentExecutor"]
    },
    ...
  },
  "entry_points": [
    {
      "name": "API Server",
      "location": "api/server.py:main()",
      "invocation": "uvicorn api.server:app",
      "critical_path": "main → lifespan() → init_service() → bootstrap_agent()"
    },
    {
      "name": "CLI Agent",
      "location": "agents/cli_cursor_cli_launcher.py:main()",
      "invocation": "python -m agents.cli.cursor_cli_launcher",
      "critical_path": "main → bootstrap_agent() → execute()"
    }
  ],
  "singleton_locations": [
    {
      "name": "_service (SubstrateService)",
      "location": "memory/substrate_service.py:get_service()",
      "registration": "core/singleton_auto_registry.py:_register_core_singletons()"
    },
    {
      "name": "_repository (PostgreSQL pool)",
      "location": "memory/substrate_repository.py:get_repository()",
      "registration": "core/singleton_auto_registry.py:_register_core_singletons()"
    },
    {
      "name": "_world_model_engine",
      "location": "world_model/engine.py:get_engine()",
      "registration": "core/singleton_auto_registry.py"
    },
    {
      "name": "_neo4j_client",
      "location": "memory/graph_client.py:get_client()",
      "registration": "api/server.py:lifespan()"
    },
    {
      "name": "_redis_client",
      "location": "runtime/redis_client.py:get_client()",
      "registration": "api/server.py:lifespan()"
    },
    {
      "name": "_ws_orchestrator",
      "location": "runtime/websocket_orchestrator.py:get_orchestrator()",
      "registration": "api/server.py:lifespan()"
    }
  ],
  "critical_files": {
    "bootstrap": ["api/server.py", "core/agents/bootstrap/*.py", "core/singleton_auto_registry.py"],
    "memory_dag": ["memory/substrate_service.py", "memory/substrate_models.py", "memory/substrate_repository.py"],
    "world_model": ["world_model/engine.py", "world_model/causal_mapper.py", "core/integration/graph_to_wm_sync.py"],
    "executor": ["core/agents/executor.py", "core/agents/schemas.py", "core/tools/base_registry.py"],
    "api": ["api/server.py", "api/agent_routes.py", "api/memory/router.py", "api/world_model_api.py"],
    "async_coordination": ["core/coordination/event_queue.py", "core/resilience/retry.py", "core/observability/circuit_breaker.py"]
  },
  "database_schema_locations": [
    {
      "name": "PostgreSQL migrations",
      "location": "migrations/*.sql",
      "tables": ["agent_memory_events", "reasoning_traces", "checkpoints", "agents", "users"]
    },
    {
      "name": "Neo4j schema",
      "location": "scripts/memory/bootstrap_neo4j_schema.py",
      "indices": ["Entity(id)", "Entity(type)", "Relationship(created_at)"]
    }
  ],
  "configuration_files": [
    {
      "name": "Agent config",
      "location": "config/agents/L-CTO-Agent.yaml",
      "schema": "Matches AgentConfig Pydantic model"
    },
    {
      "name": "Kernel definitions",
      "location": "core/kernels/*.yaml",
      "count": 10
    },
    {
      "name": "Memory substrate settings",
      "location": "config/memory_substrate_settings.py",
      "variables": ["DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME", ...]
    }
  ],
  "api_endpoints_summary": {
    "os_routes": [
      "GET /os/health",
      "GET /os/status",
      "GET /os/metrics"
    ],
    "agent_routes": [
      "POST /agent/execute",
      "GET /agent/result/{task_id}",
      "GET /agent/status"
    ],
    "memory_routes": [
      "POST /memory/ingest",
      "GET /memory/search",
      "GET /memory/retrieve/{packet_id}",
      "POST /memory/batch"
    ],
    "world_model_routes": [
      "GET /world-model/entity/{entity_id}",
      "GET /world-model/search",
      "GET /world-model/path"
    ],
    "websocket": [
      "GET /ws/agent (upgrade to WebSocket)"
    ]
  },
  "next_phase_instructions": "Phase 1 will validate bootstrap and initialization spine. Provide this index to Phase 1 scanner."
}
```

### **PHASE 0 EXECUTION CHECKLIST**

- [ ] Walk directory tree, classify folders (api, core, memory, world_model, etc.)
- [ ] Parse all `__init__.py` files for module structure
- [ ] Extract all `import` and `from ... import` statements (build dependency graph)
- [ ] Identify all `def main()` and `async def main()` entry points
- [ ] Locate all singleton registration code (grep for `@property`, `Depends()`, `@cached_property`)
- [ ] Extract all database schema definitions (SQL files + Pydantic models)
- [ ] Parse all YAML configuration files (agent configs, kernel definitions)
- [ ] Map all FastAPI routers to `include_router()` calls in `api/server.py`
- [ ] Generate summary statistics (total files, total lines of code, module count)
- [ ] Output `phase0_repo_index.json`

**Estimated duration**: 15-20 minutes

***

# **PHASE 1: BOOTSTRAP & INITIALIZATION SPINE VALIDATION**
## *Entry point → lifespan → singleton registration → 7-phase bootstrap*

### **SYSTEM PROMPT**

You are a **bootstrap engineer**. Your mandate is to validate that the application **initializes correctly from cold start to ready-to-execute agent state**. You will:

1. Trace the entry point (`api/server.py:main()` or equivalent)
2. Validate the `lifespan()` context manager initializes all 5 services in correct order
3. Verify each singleton registers exactly once
4. Check the 7-phase bootstrap ceremony executes atomically
5. Identify any circular dependencies, missing initialization, or out-of-order operations

**Input**: `phase0_repo_index.json` (from Phase 0)
**Output**: `phase1_bootstrap_report.json` (findings + fixes)

### **PHASE 1 CRITICAL VALIDATIONS**

#### **1a. Lifespan Entry Point**
```
Validate: api/server.py
├─ function exists: lifespan() → AsyncContextManager
├─ called by: FastAPI.lifespan()
├─ call sequence verified:
│  ├─ migrations.run_migrations()  [MUST be first]
│  ├─ init_service()               [MUST be before Neo4j/Redis]
│  ├─ neo4j_client.bootstrap()     [Depends on Postgres]
│  ├─ redis_client.connect()       [Independent]
│  └─ bootstrap_agent()            [MUST be last]
├─ yield/cleanup verified
└─ exception handling verified
```

#### **1b. Service Initialization Order**
```
DEPENDENCY GRAPH:
PostgreSQL (migrations) ← INIT FIRST
    ↓ (init_service depends on Postgres)
SubstrateService singleton
    ↓
Neo4j client (depends on Postgres for storing graph metadata)
    ↓
Redis client (independent, but should be after Postgres)
    ↓
Agent bootstrap (depends on all above)
```

#### **1c. Singleton Registration Verification**
```python
For each singleton (_service, _repository, _neo4j_client, _redis_client, _world_model_engine):
  ✓ Registration location identified (file:line)
  ✓ Registration happens exactly once
  ✓ Initialization guards prevent double-init (@property + _instance check)
  ✓ Thread-safe (if multi-threaded) / async-safe (if async)
  ✓ Accessible from all downstream code that needs it
```

#### **1d. 7-Phase Bootstrap Ceremony**
```
Phase 0: validate_agent_blueprint()     ← Schema validation
Phase 1: load_and_parse_kernels()       ← Load 10 YAML kernel definitions
Phase 2: instantiate_agent()            ← Create AgentInstance
Phase 3: bind_kernels_to_agent()        ← Attach all 10 kernels
Phase 4: load_identity_persona()        ← Load identity from config
Phase 5: bind_tools_and_capabilities()  ← Register tools + memory access
Phase 6: wire_governance_gates()        ← Attach approval/rate limit/policy
Phase 7: verify_and_lock()              ← Final verification + immutable lock

VALIDATION:
- Each phase depends on previous (no out-of-order execution)
- Atomic execution (all phases succeed or entire bootstrap fails)
- Phase failure → rollback to pre-bootstrap state
- Agent locked after Phase 7 (no subsequent modifications)
```

### **PHASE 1 DELIVERABLE**

```json
{
  "metadata": {
    "phase": 1,
    "repo_path": "/path/to/L9",
    "timestamp": "2026-01-25T14:45:00Z",
    "previous_phase": "phase0_repo_index.json"
  },
  "entry_point_validation": {
    "location": "api/server.py:main()",
    "status": "PASS" | "FAIL",
    "findings": [
      {
        "check": "main() invokes uvicorn with FastAPI app",
        "status": "PASS",
        "evidence": "api/server.py:450-455"
      }
    ]
  },
  "lifespan_validation": {
    "function_location": "api/server.py:lifespan()",
    "is_async_context_manager": true,
    "status": "PASS" | "FAIL",
    "initialization_sequence": [
      {
        "step": 1,
        "name": "migrations.run_migrations()",
        "location": "api/server.py:120",
        "status": "PASS",
        "depends_on": "none",
        "details": "All SQL files applied sequentially, idempotency verified"
      },
      {
        "step": 2,
        "name": "init_service()",
        "location": "api/server.py:125",
        "status": "PASS",
        "depends_on": "migrations",
        "details": "Returns SubstrateService singleton, Postgres connection pool initialized"
      },
      {
        "step": 3,
        "name": "get_neo4j_client()",
        "location": "api/server.py:130",
        "status": "FAIL",
        "depends_on": "init_service",
        "details": "Neo4j client connects but schema bootstrap not verified (LINE MISSING)",
        "severity": "HIGH",
        "suggestion": "Add: result = client.run('CALL db.constraints()') to verify schema"
      }
    ]
  },
  "singleton_registrations": {
    "_service_SubstrateService": {
      "location": "memory/substrate_service.py:get_service()",
      "registration_location": "api/server.py:125",
      "guard_mechanism": "@property with _instance check",
      "status": "PASS",
      "thread_safe": true,
      "accessible_from": ["api/agent_routes.py", "core/agents/executor.py", "memory/substrate_models.py"]
    },
    "_repository_PostgreSQL": {
      "location": "memory/substrate_repository.py:get_repository()",
      "registration_location": "memory/substrate_service.py:__init__",
      "status": "PASS",
      "connection_pool_size": "5-20",
      "timeout_seconds": 30,
      "accessible_from": ["memory/substrate_service.py", "memory/extractor/base_extractor.py"]
    },
    "_neo4j_client": {
      "location": "memory/graph_client.py:get_client()",
      "registration_location": "api/server.py:130",
      "status": "PARTIAL",
      "issue": "Schema initialization missing (see lifespan_validation)",
      "accessible_from": ["world_model/engine.py", "core/integration/graph_to_wm_sync.py"]
    },
    "_redis_client": {
      "location": "runtime/redis_client.py:get_client()",
      "registration_location": "api/server.py:135",
      "status": "PASS",
      "pool_size": 10,
      "retry_policy": "exponential backoff",
      "accessible_from": ["core/coordination/event_queue.py", "core/governance/rate_limit_policy.py"]
    },
    "_world_model_engine": {
      "location": "world_model/engine.py:get_engine()",
      "registration_location": "api/server.py (missing!)",
      "status": "FAIL",
      "issue": "World model engine registered but location unclear",
      "severity": "MEDIUM",
      "suggestion": "Add explicit registration: engine = world_model.get_engine() in lifespan()"
    }
  },
  "bootstrap_ceremony_phases": {
    "phase_0_validate_blueprint": {
      "location": "core/agents/bootstrap/phase0.py",
      "status": "PASS",
      "validates": "AgentConfig schema against config/agents/L-CTO-Agent.yaml",
      "errors_caught": ["InvalidAgentConfig", "MissingKernelDefinition"]
    },
    "phase_1_load_kernels": {
      "location": "core/agents/bootstrap/phase1.py",
      "status": "PASS",
      "loads": "10 kernel YAML files from core/kernels/",
      "verification": "All 10 kernel definitions present, schema valid"
    },
    "phase_2_instantiate_agent": {
      "location": "core/agents/bootstrap/phase2.py",
      "status": "PASS",
      "creates": "AgentInstance(id, config, substrate)",
      "verification": "AgentInstance.__init__() succeeds, agent_id assigned"
    },
    "phase_3_bind_kernels": {
      "location": "core/agents/bootstrap/phase3.py",
      "status": "PASS",
      "binds": "All 10 kernels to agent",
      "verification": "agent.kernels contains all 10 instances"
    },
    "phase_4_load_identity": {
      "location": "core/agents/bootstrap/phase4.py",
      "status": "PASS",
      "loads": "Identity from config/agents/L-CTO-Agent.yaml",
      "sets": "agent.identity, agent.persona, agent.values"
    },
    "phase_5_bind_tools": {
      "location": "core/agents/bootstrap/phase5.py",
      "status": "PARTIAL",
      "binds": "Tools from core/tools/base_registry.py",
      "issue": "Memory tools bound but research_tools not accessible (missing in Phase 5)",
      "severity": "HIGH",
      "suggestion": "Add: agent.bind_tools(research_tools.get_all_tools())"
    },
    "phase_6_governance_gates": {
      "location": "core/agents/bootstrap/phase6.py",
      "status": "PASS",
      "gates_attached": ["approval_manager", "rate_limit_policy", "policy_engine"],
      "verification": "All gates instantiated, policies loaded"
    },
    "phase_7_verify_and_lock": {
      "location": "core/agents/bootstrap/phase7.py",
      "status": "PASS",
      "verifies": "Agent state integrity, no dangling references",
      "locks": "agent._locked = True, agent._signature = hash(agent_state)",
      "prevents_modification": true
    },
    "atomicity": {
      "status": "PASS",
      "all_phases_atomic": true,
      "rollback_on_failure": "Verified—Phase N failure rolls back phases 0-N"
    }
  },
  "circular_dependency_check": {
    "status": "PASS",
    "checked_cycles": [
      "api → memory → core → api (none found)",
      "world_model → memory → world_model (none found)",
      "executor → tools → executor (none found)"
    ]
  },
  "critical_findings": [
    {
      "severity": "HIGH",
      "type": "Missing Neo4j Schema Bootstrap",
      "location": "api/server.py:130",
      "issue": "Neo4j client created but schema initialization not verified",
      "impact": "Graph queries may fail if schema not present",
      "fix": "Add: client.run('CREATE CONSTRAINT IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE')",
      "adr_reference": "ADR-0032 (Neo4j Cypher Query Pattern)"
    },
    {
      "severity": "HIGH",
      "type": "Research Tools Not Bound in Bootstrap",
      "location": "core/agents/bootstrap/phase5.py",
      "issue": "research_tools not included in Phase 5 tool binding",
      "impact": "Agent cannot execute research tasks",
      "fix": "Add to phase5.py: agent.bind_tools(research_tools.get_all_tools())",
      "adr_reference": "ADR-0037 (Tool Wiring Protocol)"
    },
    {
      "severity": "MEDIUM",
      "type": "Unclear World Model Engine Registration",
      "location": "api/server.py",
      "issue": "World model engine registered but location not explicit",
      "impact": "Future maintainers may not know where WM engine is initialized",
      "fix": "Add explicit line: engine = world_model.get_engine(); # after Neo4j bootstrap",
      "adr_reference": "ADR-0004 (Singleton Auto-Registry Pattern)"
    }
  ],
  "recommendations": [
    {
      "priority": "CRITICAL",
      "action": "Add Neo4j schema bootstrap verification",
      "file": "api/server.py",
      "line": "130-135",
      "code_snippet": "schema_result = neo4j_client.run('CALL db.constraints()')\nassert schema_result.available\n"
    },
    {
      "priority": "HIGH",
      "action": "Add research tools to Phase 5 binding",
      "file": "core/agents/bootstrap/phase5.py",
      "line": "45-50",
      "code_snippet": "from core.tools import research_tools\nagent.bind_tools(research_tools.get_all_tools())\n"
    },
    {
      "priority": "MEDIUM",
      "action": "Explicitly register world model engine",
      "file": "api/server.py",
      "line": "135",
      "code_snippet": "wm_engine = world_model.get_engine()  # Explicit registration per ADR-0004\n"
    }
  ],
  "compliance_score": 82,
  "status": "FAIL (3 issues: 1 CRITICAL, 2 HIGH)",
  "next_phase": "Phase 2: Memory Subsystem Validation"
}
```

**Estimated duration**: 25-35 minutes

***

# **PHASE 2: MEMORY SUBSYSTEM ORCHESTRATION**
## *8-node DAG pipeline, PacketEnvelope, substrate persistence, vector embeddings*

### **SYSTEM PROMPT**

You are a **memory systems architect**. Your mandate is to validate that the **8-node memory DAG pipeline** executes correctly end-to-end:

```
[intake] → [reasoning] → [memory_write] → [semantic_embed]
   ↓          ↓               ↓              ↓
validate   process      commit to PG   pgvector store

[insights_extract] → [insights_store] → [wm_trigger] → [checkpoint]
   ↓                    ↓                   ↓              ↓
parse entities      emit to graph    trigger WM      backup state
```

You will verify:
1. PacketEnvelope serialization/deserialization fidelity
2. All 8 DAG nodes exist, are async, have timeout enforcement
3. PostgreSQL schema matches Pydantic models
4. Vector embedding storage and retrieval works
5. Checkpoint recovery logic is sound
6. Transaction atomicity (memory write + embed + insights = atomic)

**Input**: `phase0_repo_index.json`, `phase1_bootstrap_report.json`
**Output**: `phase2_memory_report.json` (findings + fixes)

### **PHASE 2 CRITICAL VALIDATIONS**

#### **2a. PacketEnvelope Validation**
```
Test: Serialization cycle
├─ Create: PacketEnvelope(role='agent', content='...', metadata={...})
├─ Serialize: packet.to_dict()
├─ Verify: All fields present, no circular refs, JSON-serializable
├─ Deserialize: PacketEnvelope.from_dict(packet_dict)
├─ Compare: Reconstructed packet equals original
├─ Verify: Audit trail preserved (packet_id, timestamp, originator immutable)
└─ Verify: Governance context carried through all conversions
```

#### **2b. SubstrateDAG 8-Node Pipeline**
```
Node 1: intake_node()
  Input: PacketEnvelope
  Validates: Packet schema, governance policy check
  Output: Validated packet
  Must: Enforce timeout (30s max), handle validation errors

Node 2: reasoning_node()
  Input: Validated packet
  Processes: LLM reasoning if reasoning_required=True
  Output: Packet with reasoning_trace appended
  Must: Call LLM, store trace, timeout 30s

Node 3: memory_write_node()
  Input: Packet with optional reasoning
  Commits: Insert into PostgreSQL agent_memory_events table
  Output: Packet with memory_id + commit_timestamp
  Must: Transactional commit, idempotent (duplicate check)

Node 4: semantic_embed_node()
  Input: Packet with memory_id
  Generates: LLM embedding for packet.content
  Stores: pgvector column in PostgreSQL
  Output: Packet with embedding_id + embedding_hash
  Must: Consistent embedding model, dimension verified (1536)

Node 5: extract_insights_node()
  Input: Packet with embedding
  Extracts: Entity relationships from content
  Output: Packet.insights = [{entity_type, entity_id, relationships, confidence}]
  Must: Structured output, confidence scores normalized [0.0, 1.0]

Node 6: insights_store_node()
  Input: Packet with insights
  Stores: Insights to Neo4j graph (entity nodes + relationship edges)
  Output: Packet.graph_update_id = cypher_execution_id
  Must: Cypher transaction, error handling for duplicate entities

Node 7: world_model_trigger_node()
  Input: Packet with graph updates
  Triggers: world_model.ingest_insights(packet.insights)
  Output: Packet.wm_result = {reflection_generated, entities_analyzed}
  Must: Synchronous trigger (await result), timeout 30s

Node 8: checkpoint_node()
  Input: Fully processed packet
  Checkpoints: Agent state snapshot to recovery store
  Output: Packet.checkpoint_id = snapshot_id
  Must: Async, non-blocking, no failure (checkpoint failures logged but don't block DAG)
```

#### **2c. PostgreSQL Schema Validation**
```
Schema verification:
├─ agent_memory_events table
│  ├─ Columns: id (PK), agent_id (FK), packet_id (UNIQUE), content (TEXT), 
│  │            embedding (vector(1536)), metadata (JSONB), timestamp (TIMESTAMP)
│  ├─ Indices: (agent_id, timestamp) composite, embedding vector index
│  └─ Constraints: NOT NULL on core columns, FK referential integrity
│
├─ reasoning_traces table
│  ├─ Columns: id (PK), agent_id (FK), reasoning_content (TEXT), 
│  │            decision_path (JSONB), timestamp (TIMESTAMP)
│  └─ Index: (agent_id, timestamp)
│
├─ checkpoints table
│  ├─ Columns: id (PK), agent_id (FK), agent_state (JSONB), 
│  │            last_packet_id (TEXT), checkpoint_hash (TEXT), timestamp (TIMESTAMP)
│  └─ Index: (agent_id, timestamp DESC) for recovery
│
└─ Connection pool
   ├─ Min connections: 5
   ├─ Max connections: 20
   ├─ Timeout: 30s
   └─ Idle timeout: 5min
```

#### **2d. Vector Embedding Pipeline**
```
Embedding flow:
├─ Model selection: OpenAI text-embedding-3-small (dimension 1536)
├─ Batching: Embed up to 100 packets at once (parallel requests)
├─ Storage: pgvector column, dimension 1536
├─ Retrieval: cosine similarity search, LIMIT 10
├─ Performance: <100ms for K-NN on 1M rows
├─ Consistency: Same content → same embedding (deterministic)
└─ Error handling: Embedding failure marks packet as FAILED, retried per policy
```

#### **2e. Checkpoint & Recovery**
```
Checkpoint structure:
├─ agent_state: Frozen agent snapshot (kernels, identity, tools)
├─ last_packet_id: ID of last successfully processed packet
├─ checkpoint_hash: SHA256 hash of state (integrity verification)
├─ timestamp: Checkpoint creation time
└─ metadata: Additional recovery hints

Recovery procedure:
├─ On startup: Load latest checkpoint
├─ Integrity: Verify checkpoint_hash matches
├─ Resume: Begin processing from next packet after last_packet_id
├─ Detect orphans: Packets between checkpoint and current (retried)
└─ Validate: Recovered state matches pre-crash state (no state corruption)
```

### **PHASE 2 DELIVERABLE**

```json
{
  "metadata": {
    "phase": 2,
    "repo_path": "/path/to/L9",
    "timestamp": "2026-01-25T15:15:00Z",
    "previous_phases": ["phase0_repo_index.json", "phase1_bootstrap_report.json"]
  },
  "packet_envelope_validation": {
    "status": "PASS" | "FAIL",
    "definition_location": "core/schemas/packet_envelope.py",
    "serialization_test": {
      "status": "PASS",
      "test_packet": {
        "id": "pkt_test_123",
        "role": "agent",
        "content": "test content",
        "metadata": {"key": "value"},
        "timestamp": "2026-01-25T15:15:00Z"
      },
      "roundtrip": {
        "to_dict()": "success (all fields present, JSON-serializable)",
        "from_dict()": "success (reconstructed packet equals original)",
        "audit_trail_preserved": true
      }
    },
    "findings": [
      {
        "check": "Circular reference check",
        "status": "PASS",
        "evidence": "No circular refs detected in to_dict()"
      }
    ]
  },
  "dag_pipeline_validation": {
    "status": "PASS" | "FAIL",
    "dag_location": "memory/substrate_service.py:SubstrateDAG.run()",
    "node_count": 8,
    "nodes": [
      {
        "sequence": 1,
        "name": "intake_node",
        "location": "memory/substrate_service.py:intake_node()",
        "status": "PASS",
        "is_async": true,
        "timeout_seconds": 30,
        "validates": {
          "packet_schema": true,
          "governance_policy": true
        },
        "verified_by": "schema validation test, policy check test"
      },
      {
        "sequence": 2,
        "name": "reasoning_node",
        "location": "memory/substrate_service.py:reasoning_node()",
        "status": "PASS",
        "is_async": true,
        "timeout_seconds": 30,
        "calls_llm": true,
        "stores_trace": true,
        "verified_by": "reasoning flow test"
      },
      ... (6 more nodes)
      {
        "sequence": 8,
        "name": "checkpoint_node",
        "location": "memory/substrate_service.py:checkpoint_node()",
        "status": "PASS",
        "is_async": true,
        "non_blocking": true,
        "failure_handling": "logged, does not block DAG"
      }
    ],
    "node_ordering": {
      "status": "PASS",
      "dependencies_verified": true,
      "no_circular_deps": true
    }
  },
  "postgresql_schema_validation": {
    "status": "PASS" | "FAIL",
    "tables": {
      "agent_memory_events": {
        "status": "PASS",
        "exists": true,
        "columns": {
          "id": {"type": "UUID", "primary_key": true},
          "agent_id": {"type": "UUID", "foreign_key": true},
          "packet_id": {"type": "TEXT", "unique": true},
          "content": {"type": "TEXT"},
          "embedding": {"type": "vector(1536)"},
          "metadata": {"type": "JSONB"},
          "timestamp": {"type": "TIMESTAMP"}
        },
        "indices": [
          {"name": "idx_agent_time", "columns": ["agent_id", "timestamp"], "status": "verified"}
        ]
      },
      "reasoning_traces": {"status": "PASS", "columns_match_pydantic": true},
      "checkpoints": {"status": "PASS", "columns_match_pydantic": true}
    },
    "connection_pool": {
      "status": "PASS",
      "min_size": 5,
      "max_size": 20,
      "timeout_seconds": 30,
      "retry_policy": "exponential backoff"
    }
  },
  "vector_embedding_validation": {
    "status": "PASS" | "FAIL",
    "embedding_model": "text-embedding-3-small",
    "dimension": 1536,
    "pgvector_extension": {
      "installed": true,
      "verified": "CREATE EXTENSION vector"
    },
    "embedding_pipeline": {
      "batching": "100 packets per request",
      "parallel": true,
      "performance_target_ms": "<100ms for K-NN",
      "consistency": "deterministic (same content → same embedding)"
    },
    "search_test": {
      "status": "PASS",
      "query_executed": "SELECT ... ORDER BY embedding <-> query_vector LIMIT 10",
      "result_count": 10,
      "latency_ms": 45
    }
  },
  "checkpoint_recovery_validation": {
    "status": "PASS" | "FAIL",
    "checkpoint_location": "memory/checkpoint/recovery_store.py",
    "structure_verified": {
      "agent_state": true,
      "last_packet_id": true,
      "checkpoint_hash": true,
      "timestamp": true
    },
    "recovery_procedure": {
      "status": "PASS",
      "steps_verified": [
        "Load checkpoint: SUCCESS",
        "Verify hash: SUCCESS",
        "Resume from next packet: SUCCESS",
        "Detect orphans: SUCCESS",
        "Validate recovered state: SUCCESS"
      ]
    }
  },
  "transaction_atomicity_validation": {
    "status": "PASS" | "FAIL",
    "transaction_scope": "memory_write_node + semantic_embed_node + insights_store_node",
    "atomic_execution": true,
    "rollback_verified": "PASS (test: commit fails → all nodes rolled back)",
    "deadlock_prevention": {
      "lock_ordering": "consistent",
      "no_circular_locks": true
    }
  },
  "critical_findings": [
    {
      "severity": "MEDIUM",
      "type": "Embedding Dimension Mismatch",
      "location": "memory/substrate_service.py:semantic_embed_node():line 156",
      "issue": "Embedding code uses dimension 384, but schema defines 1536",
      "impact": "pgvector query will fail with dimension mismatch",
      "fix": "Change embedding model to text-embedding-3-small (1536 dims)",
      "adr_reference": "ADR-0029 (Embedding Generation Pipeline)"
    }
  ],
  "recommendations": [
    {
      "priority": "HIGH",
      "action": "Fix embedding dimension mismatch",
      "file": "memory/substrate_service.py",
      "line": "156",
      "code_snippet": "embedding = await embedding_model.embed(packet.content)  # dim=1536\n"
    }
  ],
  "compliance_score": 88,
  "status": "PASS (1 MEDIUM issue)",
  "next_phase": "Phase 3: World Model Integration"
}
```

**Estimated duration**: 30-40 minutes

***

# **PHASE 3: WORLD MODEL INTEGRATION & BIDIRECTIONAL SYNC**
## *Graph engine, causal mapping, reflection emission, bidirectional sync*

### **SYSTEM PROMPT**

You are a **knowledge graph architect**. Your mandate is to validate that the **world model is a living, breathing entity**—never stale, never divergent from memory or graph. You will verify:

1. World model engine initializes after Neo4j ready
2. Memory DAG → World Model trigger fires synchronously
3. Entity/relationship ingestion into Neo4j correct
4. Bidirectional sync (`graph_to_wm_sync`, `wm_to_graph_sync`) prevents divergence
5. Causal relationship validation (no spurious loops)
6. Reflection emission flows back to memory DAG
7. Graph query performance acceptable

**Input**: `phase0_repo_index.json`, `phase1_bootstrap_report.json`, `phase2_memory_report.json`
**Output**: `phase3_world_model_report.json` (findings + fixes)

### **PHASE 3 DELIVERABLE**

```json
{
  "metadata": {
    "phase": 3,
    "repo_path": "/path/to/L9",
    "timestamp": "2026-01-25T15:45:00Z",
    "previous_phases": ["phase0_repo_index.json", "phase1_bootstrap_report.json", "phase2_memory_report.json"]
  },
  "world_model_engine_initialization": {
    "status": "PASS" | "FAIL",
    "engine_location": "world_model/engine.py:get_engine()",
    "registration": {
      "location": "api/server.py (inferred from Phase 1)",
      "initialization_order": "After Neo4j bootstrap",
      "verified": true
    },
    "schema_loaded": {
      "location": "world_model/l9_schema.py",
      "entity_types_defined": ["Agent", "Task", "Tool", "Memory", "Graph", "Entity"],
      "relationship_types_defined": ["causality", "dependency", "similarity", "opposite"],
      "status": "PASS"
    }
  },
  "memory_to_world_model_trigger": {
    "status": "PASS" | "FAIL",
    "trigger_location": "memory/substrate_service.py:world_model_trigger_node()",
    "trigger_flow": {
      "step_1_insights_extracted": "extract_insights_node() outputs insights array",
      "step_2_trigger_fires": "world_model_trigger_node() invokes world_model.ingest_insights()",
      "step_3_synchronous": "await result (no fire-and-forget)",
      "step_4_error_handling": "WM ingestion failure → DAG failure, packet marked FAILED"
    },
    "timing_verification": {
      "synchronous": true,
      "timeout_seconds": 30,
      "status": "PASS"
    }
  },
  "neo4j_consistency_checks": {
    "status": "PASS" | "FAIL",
    "entity_creation": {
      "cypher_query": "CREATE (e:Entity {id: $id, type: $type, attributes: $attrs, created_at: $ts})",
      "verified": true,
      "duplicate_handling": "MERGE semantics (update if exists)"
    },
    "relationship_creation": {
      "cypher_query": "MATCH (a:Entity {id: $from_id}), (b:Entity {id: $to_id}) CREATE (a)-[r:{$rel_type} {strength: $s}]->(b)",
      "verified": true,
      "conflict_resolution": "If relationship exists, update strength (weighted average)"
    },
    "orphaned_entity_check": {
      "status": "PASS",
      "query": "MATCH (e:Entity) WHERE NOT (e)-[]-() RETURN count(e) as orphans",
      "result": 0,
      "orphan_tolerance": "root entities allowed (e.g., Agent nodes)"
    },
    "cycle_detection": {
      "status": "PASS",
      "cycles_allowed": true,
      "marked_as": {"feedback_loops": true, "causal_cycles": true}
    }
  },
  "bidirectional_sync_validation": {
    "status": "PASS" | "FAIL",
    "graph_to_memory_sync": {
      "location": "core/integration/graph_to_wm_sync.py",
      "change_detection": {
        "mechanism": "Cypher query identifies new/modified entities since last_sync",
        "frequency": "Every 5 minutes or 100 changes (configurable)",
        "verified": true
      },
      "bidirectional_update": {
        "direction": "Neo4j changes → PostgreSQL insight metadata",
        "status": "PASS",
        "consistency_marker": "Version number incremented per sync"
      },
      "conflict_resolution_policy": {
        "defined": true,
        "policy": "Recency wins (latest timestamp takes precedence)",
        "verified": true
      }
    },
    "memory_to_graph_sync": {
      "location": "core/integration/wm_to_graph_sync.py",
      "reflection_emission": {
        "source": "world_model/reflection_memory.py",
        "emits": "ReflectionPacket(reflection_type, source_entities, derived_insights, confidence)",
        "status": "PASS"
      },
      "circular_loop_prevention": {
        "mechanism": "Reflection packets marked source=world_model",
        "prevents": "Re-triggering WM on reflection ingestion",
        "verified": true
      },
      "reflection_ingestion": {
        "substrate_dag_processing": "reflection packet flows through DAG but NOT re-trigger WM",
        "status": "PASS"
      }
    }
  },
  "causal_relationship_validation": {
    "status": "PASS" | "FAIL",
    "causal_chain_identification": {
      "mechanism": "world_model/causal_mapper.py identifies A → B → C chains",
      "strength_quantification": "strength ∈ [0.0, 1.0]",
      "verified": true
    },
    "spurious_link_prevention": {
      "mechanism": "Shortest path analysis distinguishes direct causality vs. distant correlation",
      "verified": true,
      "example": "If A → B and B → C both exist, skip direct A → C link"
    },
    "temporal_coherence": {
      "constraint": "relationship.timestamp ≤ derived_insight.timestamp",
      "causality_respects_time": true,
      "verified": true
    },
    "feedback_loop_detection": {
      "status": "PASS",
      "detected_cycles": [
        {"cycle": "Agent → Task → Memory → Agent", "marked": true}
      ]
    }
  },
  "world_model_query_performance": {
    "status": "PASS" | "FAIL",
    "neo4j_indices": [
      {"index": "CREATE INDEX ON :Entity(id)", "status": "verified"},
      {"index": "CREATE INDEX ON :Entity(type)", "status": "verified"},
      {"query_timeout_seconds": 10, "status": "verified"},
      {"result_cardinality_limit": 1000, "status": "verified"}
    ],
    "latency_benchmarks": {
      "entity_lookup_by_id_ms": 5,
      "entity_search_by_type_ms": 15,
      "shortest_path_query_ms": 25,
      "all_under_timeout": true
    }
  },
  "critical_findings": [
    {
      "severity": "HIGH",
      "type": "Reflection Circular Loop Risk",
      "location": "core/integration/wm_to_graph_sync.py:emit_reflection()",
      "issue": "Reflection packet emitted but source=world_model check missing",
      "impact": "If reflection ingested through DAG, may re-trigger WM (infinite loop)",
      "fix": "Add: reflection_packet.source = 'world_model' before ingestion",
      "adr_reference": "ADR-0012 (Memory DAG Pipeline)"
    },
    {
      "severity": "MEDIUM",
      "type": "Graph Index Missing on Relationship Type",
      "location": "scripts/memory/bootstrap_neo4j_schema.py",
      "issue": "No index on Relationship.type, queries may be slow",
      "impact": "Causal chain analysis slow for large graphs",
      "fix": "Add: CREATE INDEX ON ()-[r:causality]-() IF NOT EXISTS",
      "adr_reference": "ADR-0032 (Neo4j Cypher Query Pattern)"
    }
  ],
  "recommendations": [
    {
      "priority": "HIGH",
      "action": "Add source marking to reflection packets",
      "file": "core/integration/wm_to_graph_sync.py",
      "line": "95",
      "code_snippet": "reflection_packet.source = 'world_model'  # Prevent circular re-triggering\n"
    },
    {
      "priority": "MEDIUM",
      "action": "Add Neo4j relationship type index",
      "file": "scripts/memory/bootstrap_neo4j_schema.py",
      "line": "45",
      "code_snippet": "session.run('CREATE INDEX ON ()-[r:causality]-() IF NOT EXISTS')\n"
    }
  ],
  "compliance_score": 85,
  "status": "PASS (2 issues: 1 HIGH, 1 MEDIUM)",
  "next_phase": "Phase 4: Agent Executor & Tool Wiring"
}
```

**Estimated duration**: 30-40 minutes

***

# **PHASE 4: AGENT EXECUTOR & TOOL WIRING**
## *Task execution, tool registry, kernel wiring, tool result integration*

### **SYSTEM PROMPT**

You are an **agent systems architect**. Your mandate is to validate that the **agent can select and execute tools correctly**, with all results flowing back to memory. You will verify:

1. AgentExecutor instantiation and async execution
2. Tool registry complete + all tools bindable
3. Kernel wiring in bootstrap complete (all 10 kernels attached)
4. Tool selection logic correct
5. Tool parameter binding correct
6. Tool execution timeouts enforced
7. Tool results emit to memory DAG

**Input**: Previous phase outputs
**Output**: `phase4_executor_report.json`

**Estimated duration**: 25-35 minutes (I'll abbreviate for space)

***

# **PHASE 5: API ROUTER & FASTAPI COHERENCE**
## *HTTP routes, WebSocket, dependency injection, authentication, error handling*

### **SYSTEM PROMPT**

You are an **API architect**. Your mandate is to validate that every HTTP route:
- ✅ Mounted correctly with correct prefix
- ✅ Has proper authentication
- ✅ Has rate limiting
- ✅ Handles errors gracefully
- ✅ Uses async/await (never blocks)
- ✅ Dependency injection correct (no circular deps)
- ✅ WebSocket lifecycle correct (no hanging connections)

**Input**: Previous phase outputs
**Output**: `phase5_api_report.json`

**Estimated duration**: 25-35 minutes

***

# **PHASE 6: ASYNC COHERENCE & END-TO-END TRACEABILITY**
## *Async context, event queue, timeout enforcement, circuit breakers, observability*

### **SYSTEM PROMPT**

You are a **distributed systems reliability engineer**. Your mandate is to validate:
- ✅ All async functions trace to root async context
- ✅ Event queue enqueues/dequeues atomically
- ✅ Context variables (request_id, user_id) propagate through DAG
- ✅ Timeouts enforced at every level
- ✅ Circuit breakers working (CLOSED → OPEN → HALF_OPEN transitions)
- ✅ Retry logic exponential backoff working
- ✅ Audit trail complete and immutable
- ✅ Observability end-to-end (tracing, metrics, logs)

**Input**: Previous phase outputs + repo code for async inspection
**Output**: `phase6_async_report.json`

**Estimated duration**: 40-50 minutes

***

## **PHASE EXECUTION ORCHESTRATION**

### **Execution Order**
```
Phase 0 (15-20 min)
    ↓ (output: phase0_repo_index.json)
Phase 1 (25-35 min)
    ↓ (output: phase1_bootstrap_report.json)
Phase 2 (30-40 min)
    ↓ (output: phase2_memory_report.json)
Phase 3 (30-40 min)
    ↓ (output: phase3_world_model_report.json)
Phase 4 (25-35 min)
    ↓ (output: phase4_executor_report.json)
Phase 5 (25-35 min)
    ↓ (output: phase5_api_report.json)
Phase 6 (40-50 min)
    ↓ (output: phase6_async_report.json)

TOTAL: ~190-255 minutes (~3-4 hours)
```

### **Parallel Execution Option** (if resources available)
```
Phases can run in parallel if isolation enforced:
- Phase 1 (bootstrap) ← CRITICAL PATH, must complete first
- Phases 2-6 (subsystems) ← Can run parallel after Phase 1
  - Phase 2 (memory) independent
  - Phase 3 (world model) independent
  - Phase 4 (executor) independent
  - Phase 5 (API) independent
  - Phase 6 (async) depends on all subsystems
```

### **Phase Interdependencies**
```
Phase 0: None (pure repo scanning)
Phase 1: Depends on Phase 0
Phase 2: Depends on Phase 0, Phase 1
Phase 3: Depends on Phase 0, Phase 1, Phase 2
Phase 4: Depends on Phase 0, Phase 1
Phase 5: Depends on Phase 0, Phase 1
Phase 6: Depends on all phases
```

***

## **FINAL AGGREGATION & REPORTING**

After all 6 phases complete, aggregate findings:

### **Aggregation Script** (pseudocode)
```python
def aggregate_phases():
    """Combine all phase reports into final analysis."""
    
    # Load all phase reports
    phase_reports = [
        load_json("phase0_repo_index.json"),
        load_json("phase1_bootstrap_report.json"),
        load_json("phase2_memory_report.json"),
        load_json("phase3_world_model_report.json"),
        load_json("phase4_executor_report.json"),
        load_json("phase5_api_report.json"),
        load_json("phase6_async_report.json")
    ]
    
    # Aggregate findings
    all_findings = []
    critical_count = 0
    high_count = 0
    medium_count = 0
    
    for report in phase_reports:
        for finding in report.get("critical_findings", []):
            all_findings.append({
                "phase": report["metadata"]["phase"],
                **finding
            })
            if finding["severity"] == "CRITICAL":
                critical_count += 1
            elif finding["severity"] == "HIGH":
                high_count += 1
            elif finding["severity"] == "MEDIUM":
                medium_count += 1
    
    # Calculate compliance score
    total_checks = sum(r.get("compliance_score", 0) * r.get("check_count", 1) 
                      for r in phase_reports)
    overall_score = total_checks / len(phase_reports)
    
    # Generate final report
    final_report = {
        "metadata": {
            "complete_scan_timestamp": datetime.now().isoformat(),
            "repo_path": phase_reports[0]["metadata"]["repo_path"],
            "total_phases": 6,
            "phases_passed": sum(1 for r in phase_reports if r["status"] == "PASS"),
            "phases_failed": sum(1 for r in phase_reports if r["status"] == "FAIL")
        },
        "summary": {
            "overall_compliance_score": round(overall_score, 2),
            "critical_issues": critical_count,
            "high_issues": high_count,
            "medium_issues": medium_count,
            "all_findings": sorted(all_findings, key=lambda x: 
                                  {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2}[x["severity"]])
        },
        "per_phase_results": [
            {
                "phase": r["metadata"]["phase"],
                "status": r["status"],
                "score": r.get("compliance_score", 0),
                "findings_count": len(r.get("critical_findings", []))
            }
            for r in phase_reports
        ],
        "frontier_labs_alignment": {
            "anthropic_standard": calculate_alignment("anthropic", all_findings),
            "openai_standard": calculate_alignment("openai", all_findings),
            "deepmind_standard": calculate_alignment("deepmind", all_findings),
            "meta_standard": calculate_alignment("meta", all_findings)
        },
        "recommendations_by_priority": organize_by_priority(all_findings),
        "next_steps": generate_next_steps(critical_count, high_count)
    }
    
    # Export formats
    export_json("final_repo_analysis.json", final_report)
    export_markdown("final_repo_analysis.md", final_report)
    export_html_dashboard("final_repo_analysis.html", final_report)
    
    return final_report
```

### **Final Report Structure**
```json
{
  "metadata": {
    "scan_complete_timestamp": "2026-01-25T18:30:00Z",
    "total_scan_duration_minutes": 215,
    "repo_path": "/path/to/L9",
    "phases_executed": 6,
    "phases_passed": 5,
    "phases_failed": 1
  },
  "executive_summary": {
    "overall_compliance_score": 86,
    "frontier_labs_tier": "Anthropic Labs (Q4 2025)",
    "readiness_assessment": "PRODUCTION_READY_WITH_CAVEATS",
    "critical_blockers": 2,
    "high_priority_issues": 5,
    "medium_priority_issues": 8,
    "estimated_fix_time_hours": 8
  },
  "phase_summaries": [
    {"phase": 0, "status": "COMPLETE", "score": 100},
    {"phase": 1, "status": "COMPLETE", "score": 82},
    {"phase": 2, "status": "COMPLETE", "score": 88},
    {"phase": 3, "status": "COMPLETE", "score": 85},
    {"phase": 4, "status": "COMPLETE", "score": 89},
    {"phase": 5, "status": "COMPLETE", "score": 87},
    {"phase": 6, "status": "COMPLETE", "score": 84}
  ],
  "critical_findings": [
    {
      "phase": 1,
      "severity": "CRITICAL",
      "type": "Missing Neo4j Schema Bootstrap",
      "file": "api/server.py",
      "line": 130,
      "impact": "Graph queries fail if schema missing",
      "fix": "Add Neo4j schema bootstrap verification"
    },
    {
      "phase": 6,
      "severity": "CRITICAL",
      "type": "Context Variable Lost in DAG",
      "file": "memory/substrate_service.py",
      "line": 250,
      "impact": "Request tracing broken, observability blind spot",
      "fix": "Propagate context vars through all DAG nodes"
    }
  ],
  "high_priority_findings": [
    { ... },
    { ... }
  ],
  "medium_priority_findings": [ ... ],
  "frontier_labs_alignment": {
    "anthropic": 87,
    "openai": 84,
    "deepmind": 89,
    "meta": 85
  },
  "recommendations_prioritized": [
    {
      "priority": 1,
      "action": "Fix Neo4j schema bootstrap",
      "estimated_hours": 1,
      "file": "api/server.py",
      "line": "130-135"
    },
    { ... }
  ],
  "next_steps": [
    "1. Fix 2 critical blockers (est. 2-3 hours)",
    "2. Address 5 high-priority issues (est. 4-5 hours)",
    "3. Re-run Phase 1 + Phase 6 to validate fixes",
    "4. Merge to production branch"
  ]
}
```

***

## **HOW TO USE THIS SUPERPROMPTPACK**

### **Scenario 1: Sequential Execution (Recommended for First Scan)**
```bash
# Run each phase sequentially, use output as input to next

agent_1: "Execute PHASE 0: RECONNAISSANCE & INDEXING"
         Input: /path/to/L9
         Output: phase0_repo_index.json

agent_2: "Execute PHASE 1: BOOTSTRAP & INITIALIZATION SPINE"
         Input: phase0_repo_index.json
         Output: phase1_bootstrap_report.json

agent_3: "Execute PHASE 2: MEMORY SUBSYSTEM ORCHESTRATION"
         Input: [phase0_repo_index.json, phase1_bootstrap_report.json]
         Output: phase2_memory_report.json

... (repeat for phases 3-6)

final_agent: "Execute FINAL AGGREGATION & REPORTING"
            Input: [phase0_repo_index.json, ..., phase6_async_report.json]
            Output: [final_repo_analysis.json, .md, .html]
```

### **Scenario 2: Parallel Execution (If Multi-Agent Available)**
```bash
# Run phases 2-5 in parallel (after Phase 1 completes)

coordinator_agent: "Orchestrate parallel phase execution"
  
  phase_1_agent: Execute Phase 1 (bootstrap)
                 ↓ (waits for completion)
  
  [phase_2_agent, phase_3_agent, phase_4_agent, phase_5_agent] (parallel)
                 ↓ (all complete)
  
  phase_6_agent: Execute Phase 6 (async coherence)
                 ↓
  
  final_aggregation_agent: Combine all reports

Total time: ~130 minutes instead of ~215 minutes
```

### **Scenario 3: Targeted Scans (Specific Component Analysis)**
```bash
# If only interested in memory subsystem or API routes:

targeted_agent: "Execute PHASE 0 + PHASE 2 (Memory Subsystem Only)"
                Input: /path/to/L9
                Output: phase0_repo_index.json, phase2_memory_report.json
                Time: ~50 minutes
```

***

## **SUCCESS CRITERIA FOR SUPERPROMPTPACK**

Each phase must:
1. ✅ **Start with explicit system prompt** (role, mandate, deliverables)
2. ✅ **Take previous phase outputs as input** (progressive refinement)
3. ✅ **Produce machine-readable JSON output** (fed to next phase)
4. ✅ **Include specific file:line evidence** (zero ambiguity)
5. ✅ **Provide actionable fixes** (with code snippets, ADR references)
6. ✅ **Complete in estimated time** (15-50 min per phase)
7. ✅ **Be independently runnable** (if Phase N+1 fails, restart Phase N+1 only)
