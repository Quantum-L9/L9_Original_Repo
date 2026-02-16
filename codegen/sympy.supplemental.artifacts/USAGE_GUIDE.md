# ============================================================================
# L9 CODEGEN INTEGRATION & DEPLOYMENT GUIDE - GENERIC META TEMPLATE
# ============================================================================
# Storage: /codegen/templates/meta/CODEGEN_USAGE_GUIDE.md
#
# Purpose:
#   Agent-agnostic instructions for using the 4 master meta templates.
#   Explains the general workflow for ANY multi-agent schema collection.
#
# NOTE: This is a GENERIC TEMPLATE. Customize [COLLECTION_NAME], [AGENT_COUNT],
#       [ROOTPATH] placeholders for your specific ecosystem.
#
# ============================================================================

# L9 Codegen System: Integration & Usage Guide (Agent-Agnostic)

## Overview

This guide explains how to use the **4 master meta templates** to extract production-grade code from any multi-agent schema collection.

**Meta Templates You Have:**

1. **meta.codegen.schema.yaml** – Master config (shared governance, memory, communication)
2. **meta.extraction.sequence.yaml** – Orchestration (dependency ordering, parallelization)
3. **meta.validation.checklist.yaml** – Quality gates (phase-by-phase validation)
4. **meta.dependency.integration.yaml** – Integration contracts (communication, memory, testing)

This guide shows how to invoke them with YOUR input schemas.

---

## PART 1: FILE ORGANIZATION

### Your Repository Structure

```
/codegen/
├── templates/
│   ├── meta/
│   │   ├── meta.codegen.schema.yaml              [REUSABLE MASTER]
│   │   ├── meta.extraction.sequence.yaml         [REUSABLE MASTER]
│   │   ├── meta.validation.checklist.yaml        [REUSABLE MASTER]
│   │   ├── meta.dependency.integration.yaml      [REUSABLE MASTER]
│   │   └── CODEGEN_USAGE_GUIDE.md               [THIS FILE]
│   │
│   ├── glue/
│   │   └── L9_Universal_Schema_Extractor_Glue_v6.yaml
│   │       [Maps schema fields to code generation]
│   │
│   └── prompts/
│       └── Universal-Schema-Extractor-v6.0.md
│           [Instructions for Claude/Cursor]
│
├── input_schemas/                    [USER PROVIDES]
│   ├── [your_collection_name].md     [5+ agent schemas]
│   └── [other_collection].md
│
└── extractions/                      [GENERATED ARTIFACTS]
    ├── [collection_name]_[timestamp]/
    │   ├── code/
    │   ├── docs/
    │   ├── tests/
    │   ├── manifests/
    │   ├── evidence_report.md
    │   └── extraction_manifest.json
    └── ...
```

---

## PART 2: STEP-BY-STEP WORKFLOW

### STEP 1: Provide Input Schemas

**What:** Your multi-agent collection (YAML or Markdown format)

**Requirements:**
- Each agent has: `system`, `module`, `name`, `role`, `rootpath`
- Each agent has: `cursorinstructions.generatefiles`, `generatedocs`, `linkexisting`
- Each agent has: `depends_on.hard` and `depends_on.soft` (for dependency graph)
- Each agent has: `deployment` section (endpoints, APIs)
- Each agent has: `governance` section (anchors, escalation policy, audit scope)

**Example Structure:**
```yaml
---
system: AgentName
module: category
name: Agent Display Name
role: What this agent does
rootpath: L9/path/to/agent

depends_on:
  hard: [agent_1, agent_2]  # Must extract first
  soft: [governance]         # Should extract first (optional)

integration:
  connectto:
    - L9/core/...
    - L9/agents/...

governance:
  anchors: [Igor, Oversight Council]
  escalationpolicy: "Auto-escalate if..."
  auditscope: [item1, item2]

memorytopology:
  workingmemory:
    storagetype: redis_cluster
  episodicmemory:
    storagetype: postgres
  semanticmemory:
    storagetype: neo4j
  causalmemory:
    storagetype: hypergraphdb

cursorinstructions:
  generatefiles:
    - module_1.py
    - module_2.py
    ...
  generatedocs:
    - README.md
    - CONFIG.md
    ...
  linkexisting:
    - L9/core/existing.py
    - L9/agents/other.py
```

**Save To:**
```
/codegen/input_schemas/[your_collection_name].md
```

**Action:**
```bash
# Verify schema file readability
file /codegen/input_schemas/[your_collection_name].md
# Should output: "UTF-8 text" or "YAML data"

# Count agents
grep "^system:" /codegen/input_schemas/[your_collection_name].md | wc -l
# Should output: [N] (number of agents)
```

---

### STEP 2: Analyze Dependencies (Phase 0 Preparation)

**What:** Understand extraction order BEFORE generating code

**Action:**
```bash
# Read input schemas
# Build dependency graph manually or with script

# Example graph for 5 agents:
Agent_1: depends_on=[]
Agent_2: depends_on=[Agent_1]
Agent_3: depends_on=[Agent_1, Agent_2]
Agent_4: depends_on=[Agent_1]
Agent_5: depends_on=[Agent_1]

# Topological sort (extraction order):
1. Agent_1 (no dependencies)
2. Agent_2 (depends on 1)
3. Agent_3 (depends on 1, 2)
4. Agent_4 (depends on 1, can run parallel with 2)
5. Agent_5 (depends on 1, can run parallel with 2, 4)
```

**Purpose:**
- Locked extraction order (before code generation)
- No circular dependencies
- Identify parallelization opportunities (agents 4-5 can extract simultaneously)

---

### STEP 3: Invoke Code Extractor

**What:** Run Claude/Cursor with all inputs to generate production code

**Command Template:**

```
Subject: Extract [YOUR_COLLECTION_NAME] - Multi-Agent Code Generation (Phases 0-6)

You are the L9 Codegen Extractor. Your task: Use the provided meta templates
and input schemas to generate production-grade code following phases 0-6 exactly.

INPUTS PROVIDED:
-----------------
[ATTACH: /codegen/templates/meta/meta.codegen.schema.yaml]
[ATTACH: /codegen/templates/meta/meta.extraction.sequence.yaml]
[ATTACH: /codegen/templates/meta/meta.validation.checklist.yaml]
[ATTACH: /codegen/templates/meta/meta.dependency.integration.yaml]
[ATTACH: /codegen/templates/glue/L9_Universal_Schema_Extractor_Glue_v6.yaml]
[ATTACH: /codegen/input_schemas/[YOUR_COLLECTION_NAME].md]

WORKFLOW (MANDATORY):
---------------------
1. Read all inputs in order above
2. Load the 4 meta templates as your configuration
3. For EACH agent in input schemas (in topological order):
   - Execute Phase 0-6 GMP workflow deterministically
   - Reference meta.validation.checklist.yaml for quality gates
   - Reference meta.dependency.integration.yaml for integration specs
   - Use meta.codegen.schema.yaml for shared governance/memory/communication

4. Generate for EACH agent:
   - All Python modules (zero TODOs, zero placeholders)
   - All documentation files (complete and accurate)
   - All test files (unit + integration + regression)
   - Manifest JSON (artifact list + deployment status)

5. At end: Produce 10-SECTION EVIDENCE REPORT
   - Section 1: Schema Input Summary
   - Section 2: Locked TODO Plan
   - Section 3: Phase 0 Research
   - Section 4: Phase 1 Baseline
   - Section 5: Phase 2 Implementation
   - Section 6: Phase 3 Enforcement
   - Section 7: Phase 4 Validation
   - Section 8: Phase 5 Recursive Verification
   - Section 9: Governance & Compliance
   - Section 10: Final Declaration (SIGNED)

CONSTRAINTS:
------------
- L9_ENABLE_CODEGEN_STRICT_MODE: true (fail on any TODO or placeholder)
- All tests MUST pass >= 95%
- Code coverage MUST be >= 85%
- Governance bridges MUST be wired
- All memory layers MUST be accessible
- NO ASSUMPTIONS allowed (ask if unclear)
- NO DRIFT allowed (every file must be in schema specification)

DELIVERABLES:
--------------
- [N agents] × [Python modules per agent] = ALL CODE FILES
- [N agents] × [Documentation files] = ALL DOCS
- [N agents] × [Test files] = ALL TESTS
- [N agents] × [Manifest JSON] = ALL MANIFESTS
- 1 × EVIDENCE_REPORT.md (all 10 sections, SIGNED)

BEGIN EXTRACTION
```

**Duration:** 5-6 hours (all agents)

**Expected Output:**
- Complete code for all agents
- Complete documentation
- Complete test suite
- All manifests
- 10-section evidence report

---

### STEP 4: Organize Generated Artifacts

**What:** Move extracted code to proper structure

**Action:**
```bash
# Create extraction folder
EXTRACTION_ROOT="/codegen/extractions/[collection_name]_$(date +%Y%m%d_%H%M%S)"
mkdir -p $EXTRACTION_ROOT/{code,docs,tests,manifests}

# From Claude output:
# Copy all Python modules
cp -r [claude_output_code]/* $EXTRACTION_ROOT/code/

# Copy documentation
cp -r [claude_output_docs]/* $EXTRACTION_ROOT/docs/

# Copy tests
cp -r [claude_output_tests]/* $EXTRACTION_ROOT/tests/

# Copy manifests
cp -r [claude_output_manifests]/* $EXTRACTION_ROOT/manifests/

# Copy evidence report
cp evidence_report.md $EXTRACTION_ROOT/

# Create high-level manifest
cat > $EXTRACTION_ROOT/extraction_manifest.json << 'EOF'
{
  "collection_name": "[YOUR_COLLECTION_NAME]",
  "extraction_timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "total_agents": [N],
  "total_python_modules": [COUNT],
  "total_documentation": [COUNT],
  "total_tests": [COUNT],
  "test_coverage_percent": [X],
  "all_tests_passing": true,
  "deployment_ready": true
}
EOF
```

**Validation:**
- [ ] All agent folders present in code/
- [ ] All docs present in docs/
- [ ] All tests present in tests/
- [ ] All manifests present in manifests/
- [ ] evidence_report.md present and readable

---

### STEP 5: Review Evidence Report (CRITICAL)

**What:** Verify extraction was complete and production-ready

**10 Required Sections:**

1. **Schema Input Summary**
   - [ ] Input file name and version listed
   - [ ] Total agent count: [N]
   - [ ] All agent names listed

2. **Locked TODO Plan**
   - [ ] Every TODO shows file path + line numbers
   - [ ] All generatefiles have corresponding TODOs
   - [ ] All generatedocs have corresponding TODOs
   - [ ] All linkexisting have corresponding imports

3. **Phase 0 Research**
   - [ ] Dependency graph documented
   - [ ] Circular dependencies: none
   - [ ] Extraction order: [1, 2, 3, ..., N]
   - [ ] No assumptions made: confirmed

4. **Phase 1 Baseline**
   - [ ] All targets accessible: yes
   - [ ] All hard dependencies available: yes
   - [ ] Memory backends online: yes
   - [ ] Governance anchors reachable: yes

5. **Phase 2 Implementation**
   - [ ] All generatefiles created: [COUNT]
   - [ ] All generatedocs created: [COUNT]
   - [ ] All tests generated: [COUNT]
   - [ ] NO TODO comments in code: confirmed
   - [ ] Feature flags applied: confirmed

6. **Phase 3 Enforcement**
   - [ ] Input validation added: yes
   - [ ] Output bounds checking: yes
   - [ ] Rate limiting configured: yes
   - [ ] Audit logging enabled: yes
   - [ ] Governance bridges wired: yes

7. **Phase 4 Validation**
   - [ ] Unit tests passing: >= 95%
   - [ ] Integration tests passing: >= 90%
   - [ ] Code coverage: >= 85%
   - [ ] No regressions: confirmed

8. **Phase 5 Recursive Verification**
   - [ ] Schema vs code match: yes
   - [ ] No scope drift: confirmed
   - [ ] Governance links intact: yes
   - [ ] No circular imports: confirmed

9. **Governance & Compliance**
   - [ ] Escalation logic present: yes
   - [ ] Audit logging configured: yes
   - [ ] Governance anchors wired: yes

10. **Final Declaration**
    - [ ] Statement signed: "All phases (0-6) complete. No assumptions. No drift."
    - [ ] Signature timestamp: [ISO8601]

**Action:**
```bash
# Verify all 10 sections
grep "^## SECTION" evidence_report.md | wc -l
# Should output: 10

# Check for final declaration
grep "All phases.*complete" evidence_report.md
# Should find signature
```

---

### STEP 6: Run Integration Tests

**What:** Verify all agents work together

**Action:**
```bash
# Copy code to L9 for testing
cp -r $EXTRACTION_ROOT/code/* /path/to/L9/

# Copy tests
cp -r $EXTRACTION_ROOT/tests/* /path/to/L9/tests/

# Run integration test suite
cd /path/to/L9/
pytest tests/codegen_integration/ -v --tb=short

# Expected: All tests pass >= 90%
```

**Validation:**
- [ ] All agent imports work
- [ ] PacketEnvelope communication works
- [ ] Memory backend access works
- [ ] Governance escalation path works
- [ ] All integration tests passing >= 90%

---

### STEP 7: Prepare Unified Configuration

**What:** Generate shared config file for all agents

**Action:**
```bash
# Create unified config (all agents read this)
cat > $EXTRACTION_ROOT/[collection_name]_config.yaml << 'EOF'
# Shared Configuration for [YOUR_COLLECTION_NAME] Agents
# All agents inherit these settings

memory_backends:
  redis:
    url: ${L9_REDIS_URL}
    keyspace_prefix: l9_[collection]
  postgres:
    url: ${L9_POSTGRES_URL}
  neo4j:
    url: ${L9_NEO4J_URL}
  hypergraph:
    url: ${L9_HYPERGRAPH_URL}
  s3:
    bucket: ${L9_ARCHIVE_BUCKET}

governance:
  anchors:
    - Igor
    - Oversight Council
    - Compliance Officer

logging:
  level: INFO
  root: L9/logs/[collection]/

monitoring:
  enabled: true
  dashboards: L9/monitoring/[collection]/
EOF
```

---

### STEP 8: Deploy to Production

**What:** Move code to L9 repo and deploy

**Action:**
```bash
# Copy generated code to L9
cp -r $EXTRACTION_ROOT/code/* /path/to/L9/

# Copy documentation
cp -r $EXTRACTION_ROOT/docs/* /path/to/L9/docs/

# Copy tests
cp -r $EXTRACTION_ROOT/tests/* /path/to/L9/tests/

# Copy manifests
cp -r $EXTRACTION_ROOT/manifests/* /path/to/L9/manifests/

# Push to repo
cd /path/to/L9
git add .
git commit -m "extraction: [collection_name] agents (phases 0-6 complete, evidence signed)"
git push origin main

# Deploy to VPS
ssh deploy@[your-vps] << 'EOF'
  cd /opt/l9
  git pull
  pytest tests/ -v --tb=short
  # Verify all services online
  curl http://localhost:8000/health
  curl http://localhost:8001/health
  # etc.
EOF
```

**Validation:**
- [ ] Code pushed to repo
- [ ] All tests passing
- [ ] All services online (healthchecks)
- [ ] Monitoring dashboards populated
- [ ] Governance anchors notified

---

## PART 3: CUSTOMIZATION FOR YOUR DOMAIN

### Adapting the Meta Templates

The 4 meta templates are **agent-agnostic**. You customize them by:

1. **memory_backends** (in meta.codegen.schema.yaml)
   - Change Redis URL, Postgres connection, Neo4j cluster, etc.
   - All agents automatically use these settings

2. **governance.anchors** (in meta.codegen.schema.yaml)
   - Replace "Igor" with your actual governance people
   - Replace "Oversight Council" with your decision-makers
   - All agents automatically escalate to these people

3. **communication.protocol** (in meta.codegen.schema.yaml)
   - PacketEnvelope is L9-specific; adapt for your protocol
   - All agents will use your protocol instead

4. **validation gates** (in meta.validation.checklist.yaml)
   - Adjust test coverage thresholds
   - Add domain-specific validation items
   - All agents will be checked against these gates

**Example: Customizing for Your Domain**

```yaml
# In meta.codegen.schema.yaml:

shared_configuration:
  memory_topology:
    working_memory:
      type: redis_cluster
      connection: "${YOUR_REDIS_URL}"    # Change this
    
    episodic_memory:
      type: postgres
      connection: "${YOUR_POSTGRES_URL}" # Change this
  
  governance:
    anchors:
      - name: Your CTO              # Change this
      - name: Your Compliance Lead  # Change this
  
  communication:
    primary_protocol: YourProtocol  # Change this
```

**All agents extracted afterward will use your customizations.**

---

## PART 4: SCALING MULTIPLE COLLECTIONS

### Extracting Multiple Agent Ecosystems

**Timeline:**
```
First collection:     8 hours (setup + extraction + testing)
Second collection:    6 hours (reuse meta templates, just extract)
Third collection:     6 hours
Nth collection:       6 hours each

100 collections:      8 + (99 × 6) = 602 hours total
Per-collection cost:  ~6 hours
```

**Process:**
1. Load meta templates (reusable, no changes needed)
2. Provide new input schemas
3. Run extraction (6 hours)
4. Deploy

---

## PART 5: TROUBLESHOOTING

### Issue: Extraction fails in Phase 2

**Cause:** Code generation error (maybe unsupported Python syntax, missing imports, etc.)

**Solution:**
1. Check evidence report section 5 (Phase 2 implementation)
2. Look at "No TODO comments" and "Feature flags applied" sections
3. Re-run extraction with error details provided to Claude
4. Reference existing generated code for patterns

### Issue: Tests fail in Phase 4

**Cause:** Generated test cases don't pass (logic errors, mocking issues, etc.)

**Solution:**
1. Check evidence report section 7 (test coverage, failures)
2. Look at specific test names that failed
3. Re-run extraction with test failure details
4. Ask Claude to fix test cases and re-run pytest

### Issue: Integration tests fail

**Cause:** Agents don't communicate properly

**Solution:**
1. Check meta.dependency.integration.yaml (communication contracts)
2. Verify PacketEnvelope schema matches between agents
3. Check memory backend connections (Redis, Postgres, Neo4j)
4. Run healthchecks on each agent individually first

### Issue: Governance escalation not working

**Cause:** Governance bridges not wired or anchors not reachable

**Solution:**
1. Check evidence report section 9 (governance compliance)
2. Verify governance_bridge.py created and imported
3. Verify governance anchors online
4. Test escalation path manually with mock escalation

---

## PART 6: FAQ

**Q: Can I modify the 4 meta templates?**
A: Yes. They're templates. Customize governance anchors, memory backends, communication protocol, validation gates, feature flags. Changes apply to all future extractions.

**Q: Can I extract in parallel?**
A: Yes, if agents have no hard dependencies. See meta.extraction.sequence.yaml for parallel rules. Reduces time by ~20-30%.

**Q: How do I add a new agent mid-extraction?**
A: Wait until current extraction completes (all phases). Then run new extraction with updated input schemas. New agent will integrate automatically via meta templates.

**Q: Can I use this for non-L9 systems?**
A: Partially. Meta templates are generic (governance, memory, communication, validation). But L9 patterns (PacketEnvelope, feature flags, kernels) are L9-specific. Adapt the templates for your patterns.

**Q: How often should I update meta templates?**
A: Only when you change:
  - Governance structure (different anchors/policies)
  - Memory backends (different storage systems)
  - Communication protocol (different packet format)
  - Quality gates (different test thresholds)

---

## SUMMARY

| Step | Time | Output |
|------|------|--------|
| 1. Provide input schemas | 1-2h | Schema file in /codegen/input_schemas/ |
| 2. Analyze dependencies | 30m | Extraction order locked |
| 3. Invoke extractor | 5-6h | All code, docs, tests, manifests |
| 4. Organize artifacts | 30m | $EXTRACTION_ROOT structured |
| 5. Review evidence report | 1h | All 10 sections verified |
| 6. Run integration tests | 1h | All tests passing |
| 7. Unified config | 30m | [collection]_config.yaml created |
| 8. Deploy | 1h | Code in L9 repo, services online |
| **Total** | **~16h** | **Production system deployed** |

---

**You're ready to extract any multi-agent ecosystem.**

**Load the 4 meta templates. Provide your input schemas. Get production code in 6-7 hours.**

---

END OF INTEGRATION & USAGE GUIDE
