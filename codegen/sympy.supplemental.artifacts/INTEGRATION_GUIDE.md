# ============================================================================
# L9 CODEGEN SYSTEM - INTEGRATION & DEPLOYMENT INSTRUCTIONS
# ============================================================================
# Document: CODEGEN_INTEGRATION_AND_DEPLOYMENT_GUIDE_v6.0.md
# 
# Purpose:
#   Complete workflow from schema input to production deployment.
#   Every step, every tool, every file location specified.
#
# ============================================================================

# L9 Codegen System: Complete Integration & Deployment Guide v6.0

## OVERVIEW

This guide walks through the **complete L9 codegen workflow** for extracting multi-agent systems at scale. From schema input to production deployment, every step is deterministic, validated, and auditable.

**Key Assets Provided:**
1. **meta.codegen.schema.yaml** – Master template with all shared config + validation gates
2. **meta.extraction.sequence.yaml** – Extraction orchestration (ordering, parallelization)
3. **meta.validation.checklist.yaml** – Production-grade quality gates (per agent)
4. **meta.dependency.integration.yaml** – Dependency graph + integration test specs
5. **This guide** – Step-by-step instructions for maximum leverage

---

## PART 1: FILE ORGANIZATION

### Folder Structure

```
/codegen/
├── templates/
│   ├── meta/                           # Master meta templates
│   │   ├── meta.codegen.schema.yaml              [MASTER CONFIG]
│   │   ├── meta.extraction.sequence.yaml         [ORCHESTRATION]
│   │   ├── meta.validation.checklist.yaml        [QUALITY GATES]
│   │   └── meta.dependency.integration.yaml      [DEPENDENCY GRAPH]
│   │
│   ├── glue/
│   │   └── L9_Universal_Schema_Extractor_Glue_v6.yaml
│   │       [Maps schema YAML to code generation patterns]
│   │
│   ├── prompts/
│   │   └── Universal-Schema-Extractor-v6.0.md
│   │       [Instructions for Claude/Cursor to generate code]
│   │
│   └── examples/
│       ├── Example-L9_Tensor-AIOS_Layer_Schemas_v6.md
│       └── example-L9_Tensor_MainAgent_Schema_v6.yaml
│
├── input_schemas/                      # User-provided schema collections
│   ├── tensoraios_ecosystem_v6.0.md    [USER PROVIDES]
│   └── [other_collection].md
│
├── extractions/                        # Generated artifacts (timestamped)
│   ├── tensoraios_ecosystem_20251212_120000/
│   │   ├── code/                       [Generated Python modules]
│   │   ├── docs/                       [Generated .md documentation]
│   │   ├── tests/                      [Generated test files]
│   │   ├── manifests/                  [Generated .json manifests]
│   │   ├── logs/                       [Extraction logs]
│   │   ├── evidence_report.md          [Full 10-section report]
│   │   └── extraction_manifest.json    [High-level artifact list]
│   │
│   └── [other_collection]_[timestamp]/
│
└── README.md                           # Codegen system overview

```

### Storage Locations (Long-term)

```
After extraction, generated code moves to L9 repo:

L9/
├── core/tensoraios/              [From: Extraction 1]
│   ├── tensor_scorer.py
│   ├── embedding_generator.py
│   ├── ...
│   └── __init__.py
│
├── agents/main/                  [From: Extraction 2]
│   ├── agent_controller.py
│   ├── reasoning_engine.py
│   ├── packet_router.py
│   └── ...
│
├── agents/adapters/plastos/      [From: Extraction 3]
│   ├── adapter_controller.py
│   ├── plastos_data_translator.py
│   └── ...
│
├── orchestration/tensor_trainer/ [From: Extraction 4]
│   ├── trainer_controller.py
│   ├── data_ingestion_agent.py
│   └── ...
│
├── governance/tensor_auditor/    [From: Extraction 5]
│   ├── auditor_controller.py
│   ├── compliance_checker.py
│   └── ...
│
├── logs/
│   └── codegen_extractions/
│       ├── tensoraios_ecosystem_20251212_120000/
│       │   ├── tensoraios/
│       │   ├── mainagent/
│       │   ├── plastos_adapter/
│       │   ├── tensor_trainer/
│       │   └── tensor_auditor/
│       └── ...
│
└── manifests/
    └── codegen_extractions/
        ├── tensoraios_ecosystem_20251212_120000/
        │   ├── tensoraios_manifest.json
        │   ├── mainagent_manifest.json
        │   ├── ...
        │   └── ecosystem_manifest.json
        └── ...
```

---

## PART 2: STEP-BY-STEP WORKFLOW

### STEP 1: GATHER INPUT SCHEMAS

**What:** Collect multi-agent schema collection from user.

**Input Files:**
- Example-L9_Tensor-AIOS_Layer_Schemas_v6.md (5 agent schemas: TensorAIOS, Main, PlastOS, Trainer, Auditor)
- example-L9_Tensor_MainAgent_Schema_v6.yaml (alternative format if separate)

**Action:**
```bash
# Save to /codegen/input_schemas/
cp Example-L9_Tensor-AIOS_Layer_Schemas_v6.md \
   /codegen/input_schemas/tensoraios_ecosystem_v6.0.md

# Verify file readability
file /codegen/input_schemas/tensoraios_ecosystem_v6.0.md
# Expected: "YAML data" or "UTF-8 text"
```

**Validation:**
- [ ] File readable and non-empty
- [ ] Contains all 5 agent schema definitions
- [ ] Each schema has: system, module, name, role, rootpath, cursorinstructions
- [ ] No syntax errors (try to parse as YAML/JSON)

---

### STEP 2: LOAD META TEMPLATES

**What:** Load the four master meta templates into memory/environment.

**Files:**
1. meta.codegen.schema.yaml (master config)
2. meta.extraction.sequence.yaml (orchestration)
3. meta.validation.checklist.yaml (quality gates)
4. meta.dependency.integration.yaml (dependency graph)

**Action:**
```bash
# Verify all 4 meta templates in /codegen/templates/meta/
ls -la /codegen/master_meta_templates/*.yaml

# Expected output:
# -rw-r--r-- meta.codegen.schema.yaml
# -rw-r--r-- meta.extraction.sequence.yaml
# -rw-r--r-- meta.validation.checklist.yaml
# -rw-r--r-- meta.dependency.integration.yaml
```

**Validation:**
- [ ] All 4 files exist
- [ ] All readable
- [ ] No YAML syntax errors (try `yaml.safe_load()`)

---

### STEP 3: INSTANTIATE EXTRACTION SEQUENCE

**What:** Build the extraction order by analyzing input schemas.

**Process:**
```yaml
# Read input schemas
schemas:
  - system: TensorAIOS
    rootpath: L9/core/tensoraios
    depends_on:
      hard: []
      soft: [governance, memory]
  
  - system: Main Agent
    rootpath: L9/agents/main
    depends_on:
      hard: [tensoraios]
      soft: [governance]
  
  - system: PlastOS Adapter
    rootpath: L9/agents/adapters/plastos
    depends_on:
      hard: [main_agent, tensoraios]
      soft: []
  
  - system: Tensor Trainer
    rootpath: L9/orchestration/tensor_trainer
    depends_on:
      hard: [tensoraios]
      soft: [orchestration]
  
  - system: Tensor Auditor
    rootpath: L9/governance/tensor_auditor
    depends_on:
      hard: [tensoraios]
      soft: [governance]

# Build dependency DAG
dag = {
  tensoraios: depends_on=[],
  main_agent: depends_on=[tensoraios],
  plastos_adapter: depends_on=[main_agent, tensoraios],
  tensor_trainer: depends_on=[tensoraios],
  tensor_auditor: depends_on=[tensoraios]
}

# Topological sort
extraction_order = topological_sort(dag)
# Result: [tensoraios, main_agent, plastos_adapter, tensor_trainer, tensor_auditor]

# Assign sequence numbers
1. TensorAIOS Core Service
2. Main Agent
3. PlastOS Tensor Adapter
4. Tensor Training Orchestrator
5. Tensor Governance Auditor
```

**Output:**
- File: `/codegen/extractions/[timestamp]/extraction_sequence.yaml`
- Contains: All 5 agents with sequence numbers, dependencies, criticality levels
- Purpose: Locked extraction order (no changes without re-plan)

**Validation:**
- [ ] All agents present in sequence
- [ ] No circular dependencies
- [ ] Hard dependencies satisfied (Agent N depends only on Agents 1..N-1)
- [ ] Sequence numbers sequential (1, 2, 3, 4, 5)

---

### STEP 4: CREATE LOCKED TODO PLAN (Phase 0)

**What:** Build deterministic TODO list per agent (files to create, imports to add, etc.)

**For each agent, specify:**
```
Agent 1: TensorAIOS Core Service
  TODO-1: Create L9/core/tensoraios/__init__.py (empty file)
  TODO-2: Create L9/core/tensoraios/tensor_scorer.py (19 functions)
  TODO-3: Create L9/core/tensoraios/embedding_generator.py (7 functions)
  TODO-4: Create L9/core/tensoraios/model_loader.py (import PyTorch)
  ...
  TODO-19: Create L9/core/tensoraios/README.md (documentation)
  ...
  TODO-32: Create test files (5 test modules)
  TODO-33: Create manifest L9/manifests/tensoraios/tensoraios_manifest.json

Agent 2: Main Agent
  DEPENDS_ON: Agent 1 (TensorAIOS must be extracted first)
  TODO-34: Create L9/agents/main/__init__.py (empty file)
  TODO-35: Create L9/agents/main/agent_controller.py
            (imports: from L9.core.tensoraios import tensor_scorer)
  TODO-36: Create L9/agents/main/reasoning_engine.py
  ...
```

**Output:**
- File: `/codegen/extractions/[timestamp]/locked_todo_plan.txt`
- Contains: Every TODO with file path, line count, action, imports
- Purpose: Proof that extraction is deterministic (TODOs locked before generation)

**Validation:**
- [ ] Every generatefile in schema has corresponding TODO
- [ ] Every generatedoc has corresponding TODO
- [ ] Every linkexisting has corresponding import statement
- [ ] No TODOs for files outside schema specification
- [ ] Total file count matches schema expectation

---

### STEP 5: INVOKE EXTRACTOR (Phases 1-6)

**What:** Run Claude/Cursor with all inputs + instructions.

**Invoke Command:**

```
Subject: Extract TensorAIOS Ecosystem - Phase 0-6 GMP Workflow

You are the L9 Codegen Extractor. Your task: Use the provided
meta templates + input schemas to generate production-grade code
with ZERO TODOs, ZERO placeholders, following phases 0-6 exactly.

INPUTS:
--------
[ATTACH: /codegen/templates/meta/meta.codegen.schema.yaml]
[ATTACH: /codegen/templates/meta/meta.extraction.sequence.yaml]
[ATTACH: /codegen/templates/meta/meta.validation.checklist.yaml]
[ATTACH: /codegen/templates/meta/meta.dependency.integration.yaml]
[ATTACH: /codegen/templates/glue/L9_Universal_Schema_Extractor_Glue_v6.yaml]
[ATTACH: /codegen/templates/prompts/Universal-Schema-Extractor-v6.0.md]
[ATTACH: /codegen/input_schemas/tensoraios_ecosystem_v6.0.md]
[ATTACH: /codegen/extractions/[timestamp]/locked_todo_plan.txt]

WORKFLOW:
---------
1. Read all inputs in order above.
2. For each agent (TensorAIOS, Main, PlastOS, Trainer, Auditor):
   - Follow Phase 0-6 GMP workflow deterministically
   - DO NOT skip phases. Execute ALL 6 phases.
   - Reference locked_todo_plan.txt for every file to create.
   - Use meta templates for shared config, governance, memory, communication
   - Use Glue file to map schema YAML -> code patterns
3. Produce for EACH agent:
   - All Python modules (zero TODOs, zero placeholders)
   - All documentation files (complete and accurate)
   - All test files (positive/negative/regression cases)
   - Manifest JSON (artifact list + deployment status)
4. At end, produce EVIDENCE REPORT with all 10 sections.

CONSTRAINTS:
------------
- L9_ENABLE_CODEGEN_STRICT_MODE: true (fail on any TODO)
- No assumptions allowed (ask if unclear)
- No drift allowed (every file must be in locked TODO list)
- All tests >= 95% pass rate
- All governance links must be wired
- Evidence report is mandatory (10 sections required)

DELIVERABLES:
--------------
[Extracted Python code for all 5 agents]
[Generated documentation]
[Generated test files]
[Generated manifests]
[EVIDENCE REPORT (all 10 sections)]

BEGIN EXTRACTION
```

**Duration:** 4-6 hours (depends on parallelization)

**Expected Output:**

Claude will provide:
1. Code for all 5 agents (~100 Python files)
2. Documentation for all agents (~30 .md files)
3. Test files for all agents (~50 test files)
4. Manifest files (5 x .json)
5. Full evidence report (markdown, all 10 sections)

---

### STEP 6: VALIDATE EXTRACTION (Evidence Report Review)

**What:** Review the evidence report from extraction. Verify all 10 sections present.

**Required 10 Sections:**

1. **Schema Input Summary**
   - [ ] Input schema name, version, purpose
   - [ ] Total agents: 5
   - [ ] All input files listed
   - Evidence: Copy input file names

2. **Locked TODO Plan**
   - [ ] Every TODO executed
   - [ ] File paths + line numbers
   - [ ] Actions (Create/Insert/Delete/Wrap)
   - Evidence: Before/after code snapshots

3. **Phase 0 Research**
   - [ ] Ground truth established
   - [ ] Dependencies mapped
   - [ ] No assumptions made
   - Evidence: Dependency DAG + explanations

4. **Phase 1 Baseline**
   - [ ] All targets accessible
   - [ ] Dependencies available
   - [ ] No blocking conditions
   - Evidence: Connection tests, file listings

5. **Phase 2 Implementation**
   - [ ] All files generated
   - [ ] No TODOs
   - [ ] Feature flags applied
   - Evidence: File listing + wc -l per module

6. **Phase 3 Enforcement**
   - [ ] Safety layers added
   - [ ] Input/output validation
   - [ ] Governance bridges wired
   - Evidence: Code snippets with line numbers

7. **Phase 4 Validation**
   - [ ] Tests running
   - [ ] Coverage >= 85%
   - [ ] All tests passing >= 95%
   - Evidence: pytest output, coverage report

8. **Phase 5 Recursive Verification**
   - [ ] Schema vs code comparison
   - [ ] No drift detected
   - [ ] Governance links intact
   - Evidence: Checklist with yes/no per item

9. **Governance & Compliance**
   - [ ] Escalation logic present
   - [ ] Audit logging enabled
   - [ ] Governance anchors wired
   - Evidence: Code snippets

10. **Final Declaration**
    - [ ] Statement: "All phases (0-6) complete. No assumptions. No drift."
    - [ ] Signed timestamp
    - Evidence: Signature

**Action:**
```bash
# Save evidence report
cp [claude_output_evidence_report].md \
   /codegen/extractions/tensoraios_ecosystem_[timestamp]/evidence_report.md

# Verify all 10 sections present
grep -E "^## SECTION [0-9]" evidence_report.md | wc -l
# Expected: 10 sections

# Spot-check a few sections
grep "All phases.*complete" evidence_report.md
# Should find final declaration
```

**Validation:**
- [ ] All 10 sections present
- [ ] Section 7 shows >= 95% tests passing
- [ ] Section 5 shows all generatefiles created
- [ ] Section 8 shows no drift detected
- [ ] Section 10 has signed final declaration

---

### STEP 7: ORGANIZE EXTRACTED ARTIFACTS

**What:** Move extracted code, docs, tests to proper folders.

**Action:**
```bash
# Create extraction folder with timestamp
EXTRACTION_ROOT="/codegen/extractions/tensoraios_ecosystem_$(date +%Y%m%d_%H%M%S)"
mkdir -p $EXTRACTION_ROOT/{code,docs,tests,manifests,logs}

# From Claude output:
# Copy Python code to code/
cp -r [extracted_tensoraios_code] $EXTRACTION_ROOT/code/tensoraios/
cp -r [extracted_main_code] $EXTRACTION_ROOT/code/main_agent/
cp -r [extracted_plastos_adapter_code] $EXTRACTION_ROOT/code/plastos_adapter/
cp -r [extracted_trainer_code] $EXTRACTION_ROOT/code/tensor_trainer/
cp -r [extracted_auditor_code] $EXTRACTION_ROOT/code/tensor_auditor/

# Copy documentation
cp -r [extracted_docs] $EXTRACTION_ROOT/docs/

# Copy tests
cp -r [extracted_tests] $EXTRACTION_ROOT/tests/

# Copy manifests
cp -r [extracted_manifests] $EXTRACTION_ROOT/manifests/

# Copy evidence report
cp [evidence_report.md] $EXTRACTION_ROOT/evidence_report.md

# Create extraction manifest (high-level summary)
cat > $EXTRACTION_ROOT/extraction_manifest.json << 'EOF'
{
  "collection": "tensoraios_ecosystem",
  "version": "6.0.0",
  "extraction_timestamp": "[timestamp]",
  "total_agents": 5,
  "agents": [
    {"agent_id": "tensoraios", "rootpath": "L9/core/tensoraios", "files": "19 modules + 6 docs + 25 tests"},
    {"agent_id": "mainagent", "rootpath": "L9/agents/main", "files": "23 modules + 9 docs + 30 tests"},
    {"agent_id": "plastos_adapter", "rootpath": "L9/agents/adapters/plastos", "files": "18 modules + 6 docs + 20 tests"},
    {"agent_id": "tensor_trainer", "rootpath": "L9/orchestration/tensor_trainer", "files": "18 modules + 5 docs + 18 tests"},
    {"agent_id": "tensor_auditor", "rootpath": "L9/governance/tensor_auditor", "files": "20 modules + 6 docs + 22 tests"}
  ],
  "total_python_modules": 98,
  "total_documentation": 32,
  "total_tests": 115,
  "test_coverage_percent": 87.5,
  "all_tests_passing": true,
  "deployment_ready": true,
  "evidence_report": "evidence_report.md"
}
EOF

# List final structure
tree $EXTRACTION_ROOT -L 2
```

**Expected Structure:**
```
/codegen/extractions/tensoraios_ecosystem_20251212_120000/
├── code/
│   ├── tensoraios/             [19 modules]
│   ├── main_agent/             [23 modules]
│   ├── plastos_adapter/        [18 modules]
│   ├── tensor_trainer/         [18 modules]
│   └── tensor_auditor/         [20 modules]
├── docs/
│   ├── tensoraios/             [6 .md files]
│   ├── main_agent/             [9 .md files]
│   ├── plastos_adapter/        [6 .md files]
│   ├── tensor_trainer/         [5 .md files]
│   └── tensor_auditor/         [6 .md files]
├── tests/
│   ├── tensoraios/             [25 test files]
│   ├── main_agent/             [30 test files]
│   ├── plastos_adapter/        [20 test files]
│   ├── tensor_trainer/         [18 test files]
│   └── tensor_auditor/         [22 test files]
├── manifests/
│   ├── tensoraios_manifest.json
│   ├── mainagent_manifest.json
│   ├── plastos_adapter_manifest.json
│   ├── tensor_trainer_manifest.json
│   ├── tensor_auditor_manifest.json
│   └── ecosystem_manifest.json
├── logs/
│   ├── tensoraios/
│   ├── main_agent/
│   ├── plastos_adapter/
│   ├── tensor_trainer/
│   └── tensor_auditor/
├── evidence_report.md          [ALL 10 SECTIONS]
└── extraction_manifest.json    [HIGH-LEVEL SUMMARY]
```

---

### STEP 8: RUN INTEGRATION TESTS

**What:** Verify all agents work together (cross-agent communication).

**Action:**
```bash
# Copy extracted code to L9 for testing
cp -r $EXTRACTION_ROOT/code/* /path/to/L9/

# Run integration tests
cd /path/to/L9/
pytest tests/codegen_integration/ -v

# Expected: All integration tests pass
# Examples:
#   - TensorAIOS available, Main Agent can call it
#   - Main Agent can create PacketEnvelopes, PlastOS Adapter can receive them
#   - Trainer can update TensorAIOS models
#   - Auditor can subscribe to agent events
#   - Memory backends all accessible
#   - Governance escalations work end-to-end
```

**Validation:**
- [ ] All integration tests pass (>= 90% pass rate)
- [ ] No import errors between agents
- [ ] PacketEnvelope communication works
- [ ] Memory backend writes succeed
- [ ] Governance escalation path verified

---

### STEP 9: PREPARE DEPLOYMENT ARTIFACTS

**What:** Create deployment-ready package (code + config + secrets).

**Action:**
```bash
# Create unified configuration (all agents read from this file)
cat > L9/tensoraios_ecosystem_config.yaml << 'EOF'
# Shared configuration for all TensorAIOS ecosystem agents

memory_backends:
  redis:
    url: ${L9_REDIS_URL}
    keyspace_prefix: l9_tensoraios
  postgres:
    url: ${L9_POSTGRES_URL}
    extensions: [pgvector]
  neo4j:
    url: ${L9_NEO4J_URL}
  hypergraph:
    url: ${L9_HYPERGRAPH_URL}
  s3:
    bucket: ${L9_ARCHIVE_BUCKET}
    prefix: tensoraios_ecosystem/

governance:
  anchors:
    - name: Igor
      email: ${IGOR_EMAIL}
      slack: ${IGOR_SLACK}
    - name: Domain Oversight Council
      members: [domain_lead_1, domain_lead_2]
    - name: Compliance Officer
      email: ${COMPLIANCE_EMAIL}

logging:
  level: INFO
  root: L9/logs/tensoraios_ecosystem/
  
monitoring:
  dashboards: L9/monitoring/tensoraios_ecosystem/
  metrics_enabled: true
EOF

# Create deployment script
cat > L9/deployment/deploy_tensoraios_ecosystem.sh << 'EOF'
#!/bin/bash
set -e

echo "Deploying TensorAIOS Ecosystem Agents..."

# 1. Verify environment
env_vars=(L9_REDIS_URL L9_POSTGRES_URL L9_NEO4J_URL L9_HYPERGRAPH_URL L9_ARCHIVE_BUCKET)
for var in "${env_vars[@]}"; do
  if [ -z "${!var}" ]; then
    echo "ERROR: $var not set"
    exit 1
  fi
done

# 2. Start agents (example with Docker)
docker-compose -f docker-compose.tensoraios.yml up -d

# 3. Wait for services online
for i in {1..30}; do
  if curl -f http://localhost:8000/tensoraios/v6/status; then
    echo "TensorAIOS online"
    break
  fi
  sleep 2
done

# 4. Run smoke tests
pytest tests/tensoraios_ecosystem_smoke/ -v

# 5. Enable alerting
# (Integration with your monitoring system)

# 6. Notify governance
echo "Deployment complete. Notifying governance anchors..."
# (Send notifications)

echo "TensorAIOS Ecosystem deployed successfully!"
EOF

chmod +x L9/deployment/deploy_tensoraios_ecosystem.sh
```

**Validation:**
- [ ] Unified config file created
- [ ] All environment variables referenced
- [ ] Deployment script is executable
- [ ] README with deployment instructions exists

---

### STEP 10: DEPLOYMENT TO VPS

**What:** Run extraction on actual VPS infrastructure.

**Action:**
```bash
# Push code to repo
cd /path/to/L9
git add .
git commit -m "chore: extraction of TensorAIOS ecosystem agents (phases 0-6 complete)"
git push origin main

# Deploy to VPS
ssh deploy@l9-vps << 'EOF'
  cd /opt/l9
  git pull
  ./deployment/deploy_tensoraios_ecosystem.sh
  
  # Verify services online
  curl http://localhost:8000/tensoraios/v6/status
  curl http://localhost:8001/mainagent/v6/status
  curl http://localhost:8002/plastos_adapter/v6/status
  
  # Run full test suite
  pytest tests/ -v --tb=short
EOF
```

**Validation:**
- [ ] Code pushed to repo
- [ ] All services online (healthchecks)
- [ ] All tests passing (>= 95%)
- [ ] Monitoring dashboards populated
- [ ] Alerting rules active
- [ ] Governance anchors notified

---

## PART 3: MAXIMUM LEVERAGE & SCALE

### How This System Scales

**One-time Setup (4-6 hours):**
1. Load meta templates
2. Provide input schemas
3. Run extraction (phases 0-6)
4. Integration test
5. Deploy

**Future Extractions (Parallel):**
- Add new schemas to input collection
- Run extraction again using same meta templates
- All shared config, governance, memory already integrated
- **Time per new agent:** 20-30 minutes (parallel extraction reduces further)

**Example: Adding MortgageOS Adapter**
```yaml
# Just add to input schemas:
  - system: MortgageOS Tensor Adapter
    rootpath: L9/agents/adapters/mortgageos
    depends_on:
      hard: [main_agent, tensoraios]

# Re-run extraction with same meta templates
# All governance, memory, communication inherited
# Seamlessly wires to existing TensorAIOS ecosystem
```

### Key Leverage Points

**1. Meta Templates are Reusable**
- Same governance structure for ALL agents
- Same memory topology for ALL agents
- Same communication protocol for ALL agents
- New agents automatically inherit all shared infrastructure

**2. Dependency Graph is Deterministic**
- Topological sort locks extraction order
- No circular dependencies possible
- Dependencies pre-declared in schema
- Extraction guaranteed to succeed or fail early (phase 1)

**3. Quality Gates are Automated**
- 10-section evidence report proves completeness
- Zero TODOs = production-ready code
- >= 95% test pass rate = verified correctness
- No manual code review needed (structure guaranteed)

**4. Integration is Formulaic**
- All agents use same PacketEnvelope protocol
- All agents use same memory layers (Redis, Postgres, Neo4j, HyperGraphDB)
- All agents have same governance escalation path
- New agents work with old agents immediately

**5. Deployment is Scriptable**
- Unified config file (all agents read same settings)
- Single deployment script for entire ecosystem
- Same healthchecks, monitoring, alerting for all agents
- Scale from 1 agent to 100 agents without code change

### Cost Analysis

**Manual Code Writing (Traditional):**
- Per agent: 40-80 hours
- 5 agents: 200-400 hours
- Coordination overhead: +20%
- **Total: 240-480 hours**

**Codegen System (This Approach):**
- Setup meta templates: 8 hours (one-time)
- Per extraction: 5-6 hours (all 5 agents in parallel)
- Integration testing: 2 hours
- Deployment: 1 hour
- **Total: 16-17 hours for first extraction**
- **Subsequent extractions: 5-6 hours each**

**Savings Example:**
- Traditional (5 agents): 300 hours
- Codegen (5 agents + meta setup): 17 hours
- **Savings: 283 hours (~94% faster)**

### Scaling to 100 Agents

**Timeline:**
- Meta templates: 8 hours (one-time, already done)
- Extract 5 agents at a time (parallel batches)
- Each batch: 5-6 hours
- 100 agents = 20 batches = 100-120 hours
- **Total: ~110 hours to extract 100 production agents**
- **Per-agent cost: ~1.1 hours (code + tests + docs + deployment)**

**With Traditional Approach:**
- 100 agents x 60 hours = 6,000 hours
- **Codegen saves: 5,890 hours (98% faster)**

---

## PART 4: TROUBLESHOOTING & FAQ

### FAQ

**Q: What if extraction fails in phase 2?**
A: Phase 1 baseline would have caught blocking dependencies. If phase 2 fails, evidence report section 5 will list exact files/imports missing. Resolve those and re-run from phase 2.

**Q: Can I extract agents 4 & 5 in parallel?**
A: Yes! Both depend only on agent 1 (TensorAIOS). Set `orchestration.parallel_after_phase: 3`. Reduces time by ~30%.

**Q: What if a test fails?**
A: Evidence report section 7 will show which tests failed. Re-run extraction, provide Claude with error details. Extractor will fix code + tests.

**Q: How do I add a new agent mid-extraction?**
A: Don't. Complete current extraction (all phases), then add new agent schema and re-run from phase 0. New agent will integrate with existing agents automatically via meta templates.

**Q: What if governance anchors are unavailable?**
A: Phase 1 baseline will fail (governance_anchors_reachable check). Either make anchors available or skip that validation (not recommended for production).

**Q: Can I use this for non-L9 systems?**
A: Partially. Meta templates are generic (shared config, memory, communication). But L9 patterns (PacketEnvelope, feature flags, kernels) are L9-specific. Adapt the Glue file for your patterns.

---

## PART 5: CHECKLIST FOR PRODUCTION

Before deploying to VPS, verify:

- [ ] Extraction evidence report has all 10 sections
- [ ] Section 7 shows >= 95% tests passing
- [ ] Section 8 shows no scope drift
- [ ] Section 10 signed final declaration
- [ ] Integration tests pass (all agent pairs)
- [ ] Unified config file created
- [ ] All environment variables set
- [ ] Deployment script executable and tested (dry-run)
- [ ] Monitoring dashboards accessible
- [ ] Alerting rules configured
- [ ] Governance anchors notified + agreed
- [ ] Code pushed to repo
- [ ] Rollback plan documented (if needed)

---

## CONCLUSION

The L9 Codegen System + meta templates + this integration guide provide a **production-grade pipeline** for extracting multi-agent systems at scale.

**From schema input to deployment: Deterministic, validated, auditable.**

**For questions or issues:** Refer to evidence reports (sections 1-10) or meta templates (configuration reference).

**Next extraction:** Load meta templates, provide new schema collection, run phases 0-6, deploy.

---

END OF INTEGRATION GUIDE
