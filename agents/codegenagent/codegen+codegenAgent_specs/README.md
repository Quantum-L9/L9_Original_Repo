# CodeGenAgent (CGA) — L9 Autonomous Code Generation System

## 🎯 Vision

**CodeGenAgent (CGA)** is the autonomous "Head of Code Generation" for L9 and all company projects. It receives contracts and specifications from L-CTO, generates comprehensive agent/module YAML definitions, and deterministically converts them into production code that is automatically wired into the L9 repository.

```
┌─────────────┐     Contract + Spec     ┌─────────────┐     Agent YAML     ┌─────────────┐
│   L-CTO     │ ──────────────────────▶ │     CGA     │ ─────────────────▶ │  Code Gen   │
│  (Human/AI) │                         │ CodeGenAgent│                    │  Pipeline   │
└─────────────┘                         └─────────────┘                    └──────┬──────┘
                                                                                  │
                                                                                  ▼
                                        ┌─────────────────────────────────────────────────┐
                                        │                  L9 Repository                  │
                                        │  • Python modules    • API routes               │
                                        │  • Tests             • Orchestration DAGs       │
                                        │  • Governance hooks  • Tool registrations       │
                                        └─────────────────────────────────────────────────┘
```

---

## 🏛️ Hierarchy

| Role | Responsibility | Authority |
|------|----------------|-----------|
| **Igor (Human)** | Strategic direction, final approval on critical systems | Absolute |
| **L-CTO** | Technical architecture, contract creation, CGA oversight | High |
| **CGA (CodeGenAgent)** | Code generation, YAML→Code pipeline, module emission | Medium |
| **Generated Agents** | Execute specific tasks as defined by their contracts | Low |

---

## 📋 The Contract System

### What is a Contract?

A **contract** is a formal specification sent to CGA that defines:
- **What** to build (agent, module, tool, API, etc.)
- **Why** it exists (purpose, responsibilities)
- **How** it integrates (wiring, dependencies, triggers)
- **Constraints** (governance, safety, permissions)

### Contract → YAML → Code Flow

```
1. CONTRACT RECEIVED
   └─▶ L-CTO sends spec/request to CGA
   
2. CGA PROCESSING
   └─▶ Analyzes contract
   └─▶ Validates against governance policies
   └─▶ Generates comprehensive Agent YAML

3. YAML VALIDATION
   └─▶ Schema validation
   └─▶ Dependency resolution
   └─▶ Governance approval (if required)

4. CODE GENERATION
   └─▶ Deterministic YAML → Python conversion
   └─▶ Linting + type checking
   └─▶ Test scaffold generation

5. WIRING
   └─▶ Register in AgentRegistry
   └─▶ Bind to ToolGraph
   └─▶ Add to orchestration DAGs
   └─▶ Emit telemetry hooks

6. DEPLOYMENT
   └─▶ Files written to L9 repo
   └─▶ Rollback hooks registered
   └─▶ Audit trail logged
```

---

## 📁 Directory Structure

```
agents/codegenagent/
├── README.md                    # This file
├── specs/                       # 81 YAML specifications (the blueprint library)
│   ├── agents_codegen_agent_*.yaml    # CGA core modules
│   ├── agents_mainagent_v6_*.yaml     # MainAgent modules
│   ├── runtime_*.yaml                 # Runtime tools
│   ├── orchestration_*.yaml           # Orchestrators, DAGs
│   ├── governance_*.yaml              # Policy enforcement
│   └── ...                            # Other domain specs
├── patches/
│   └── patches-done/            # Applied patches (archived)
└── extract_yaml_specs.py        # Extraction utility
```

---

## 🔧 The Spec Pack (81 YAML Files)

The `specs/` directory contains the complete blueprint for the CGA system:

### Core CGA Modules (5 files)
| File | Purpose |
|------|---------|
| `agents_codegen_agent_codegen_agent.yaml` | Main CGA agent definition |
| `agents_codegen_agent_meta.yaml` | CGA meta-contract (interface definition) |
| `agents_codegen_agent_meta_loader.yaml` | Loads and parses meta.yaml files |
| `agents_codegen_agent_c_gmp_engine.yaml` | GMP (God Mode Prompt) expansion engine |
| `agents_codegen_agent_file_emitter.yaml` | Writes generated code to files |

### Pipeline Components
| File | Purpose |
|------|---------|
| `ir_engine_meta_ir.yaml` | Intermediate Representation schema |
| `ir_engine_compile_meta_to_ir.yaml` | Compiles meta.yaml to IR |
| `agents_codegen_agent_pipeline_validator.yaml` | Validates generation pipeline |
| `agents_codegen_agent_ap_generator.yaml` | Generates action plans |

### Governance & Safety
| File | Purpose |
|------|---------|
| `agents_codegen_agent_compliance_auditor.yaml` | Policy compliance checking |
| `governance_kernel_integrity_monitor.yaml` | Kernel file integrity monitoring |
| `governance_eval_patch.yaml` | Patch compliance evaluation |

### Wiring & Integration
| File | Purpose |
|------|---------|
| `orchestration_langgraph_builder.yaml` | Builds LangGraph DAGs |
| `core_agent_registry_patch.yaml` | Agent self-registration |
| `api_routes_codegen.yaml` | FastAPI endpoints for CGA |

### Roadmap
| File | Purpose |
|------|---------|
| `sandbox_session_roadmap_l9.yaml` | Master status tracker (completed/in-progress/blocked) |

---

## 🚀 Weaponization Strategy

### Phase 1: FOUNDATION (Current)
- [x] Extract all YAML specs from chat transcript
- [x] Organize into specs/ and patches/
- [x] Apply patches to specs (merge wiring)
- [ ] Add governance headers to all specs
- [ ] Create extraction pipeline

### Phase 2: CGA CORE
- [ ] Implement `codegen_agent.py` (main agent)
- [ ] Implement `meta_loader.py` (YAML parsing)
- [ ] Implement `c_gmp_engine.py` (code expansion)
- [ ] Implement `file_emitter.py` (code writing)
- [ ] Implement `pipeline_validator.py` (validation)

### Phase 3: PIPELINE
- [ ] Build IR compiler (meta.yaml → IR)
- [ ] Build code generator (IR → Python)
- [ ] Build wiring system (auto-registration)
- [ ] Build test scaffold generator

### Phase 4: GOVERNANCE
- [ ] Implement approval workflows
- [ ] Add rollback system
- [ ] Add audit trails
- [ ] Integrate with L-CTO approval gates

### Phase 5: AUTONOMY
- [ ] Self-evolution loop (CGA upgrades itself)
- [ ] Perplexity integration (external knowledge)
- [ ] Multi-agent swarm generation

---

## 📜 Contract Template

When L-CTO sends a contract to CGA, it should follow this structure:

```yaml
contract:
  id: CONTRACT-2024-001
  from: L-CTO
  to: CodeGenAgent
  priority: high
  
request:
  type: agent | module | tool | api | test
  name: MyNewAgent
  domain: orchestration | governance | memory | runtime
  
spec:
  description: |
    What this agent/module does and why it exists.
    
  responsibilities:
    - First responsibility
    - Second responsibility
    
  inputs:
    - PacketEnvelope
    - ConfigData
    
  outputs:
    - Result
    - AuditLog
    
  wiring:
    dependencies:
      - MemorySubstrate
      - ToolGraph
    triggers:
      - on_packet_received
    emits:
      - telemetry_event
      
  governance:
    approval_required: false
    risk_level: low | medium | high | critical
    
  constraints:
    - Must be idempotent
    - Must log all actions
```

---

## 🔄 How CGA Processes a Contract

1. **Receive** contract from L-CTO (via API, Slack, or direct call)
2. **Parse** and validate contract structure
3. **Check** governance requirements (approval needed?)
4. **Generate** comprehensive Agent YAML with:
   - Full code implementation
   - Wiring configuration
   - Test scaffolds
   - Documentation
5. **Validate** generated YAML against schemas
6. **Extract** code blocks from YAML
7. **Emit** files to correct locations
8. **Wire** into L9 systems (registry, tools, DAGs)
9. **Log** audit trail to memory substrate
10. **Report** completion to L-CTO

---

## 🎯 Success Criteria

CGA is successful when:
- ✅ Any agent/module can be generated from a contract
- ✅ Generated code is production-ready (linted, typed, tested)
- ✅ Wiring is automatic (no manual registration)
- ✅ Governance is enforced (approval gates respected)
- ✅ Full audit trail exists (who requested, what generated, when)
- ✅ Rollback is possible (revert any generation)
- ✅ Self-evolution works (CGA can upgrade itself)

---

## 📚 Related Documentation

- `docs/codegen_agent_evolution_plan.yaml` — Long-term evolution roadmap
- `sandbox_session_roadmap_l9.yaml` — Current status tracker
- `templates/Canonical-Schema-Template-v6.0.yaml` — Schema standards
- `templates/GMP-Prompt-Schema.yaml` — Prompt generation templates

---

*Created: 2024-12-31*
*Owner: CodeGenAgent System*
*Authority: L-CTO*


