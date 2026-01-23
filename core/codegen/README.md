# Unified CodeGen System v1.0.0

**The Complete L9 Code Generation Operating System**

Transform high-level contracts/specs into production-ready Python code through deterministic compilation, symbolic mathematics, LLM-enhanced gap filling, and live research access.

---

## 🎯 Quick Start

### Installation

```bash
cd /home/ubuntu/L9
pip install -r core/codegen/requirements.txt
```

### Environment Setup

```bash
# Required
export PERPLEXITY_API_KEY=pplx-xxx
export L9_REPO_ROOT=/home/ubuntu/L9

# Optional
export L9_ENABLE_CODEGEN=true
export L9_ENABLE_PERPLEXITY_RESEARCH=true
export CODEGEN_MIN_CONFIDENCE=85
```

### Generate Code from Agent YAML

```bash
python -m l9.core.codegen.cli generate \
  --input agent_spec.yaml \
  --type agent_yaml \
  --output ./agents/new_agent \
  --research
```

### Generate Code from Module Block

```bash
python -m l9.core.codegen.cli generate \
  --input module_block.yaml \
  --type module_block \
  --output ./modules/twilio_adapter
```

### Validate Generated Code

```bash
python -m l9.core.codegen.cli validate \
  --files ./agents/new_agent
```

### Research a Topic

```bash
python -m l9.core.codegen.cli research \
  --query "What are best practices for async Python error handling?"
```

---

## 📚 Python API Usage

### Basic Usage

```python
import asyncio
from l9.core.codegen import CodeGenGatekeeperAgent, ContractType

async def main():
    # Initialize gatekeeper
    gatekeeper = CodeGenGatekeeperAgent(
        perplexity_api_key="pplx-xxx",
        research_enabled=True,
        min_confidence=85.0
    )
    
    # Read agent spec
    with open("agent_spec.yaml") as f:
        contract = f.read()
    
    # Generate code
    result = await gatekeeper.run(
        task={
            "contract": contract,
            "contract_type": "agent_yaml",
            "output_dir": "./agents/new_agent",
            "research_enabled": True
        }
    )
    
    if result.success:
        print(f"✅ Generated {len(result.data['files_generated'])} files")
        print(f"📊 Coverage: {result.data['coverage']}%")
        print(f"🌿 Git branch: {result.data['git_branch']}")
    else:
        print(f"❌ Generation failed: {result.data.get('reason')}")
        for gap in result.metadata.get("gaps", []):
            print(f"  - {gap['category']}: {gap['description']}")

asyncio.run(main())
```

### Advanced Usage - Custom Validation

```python
from l9.core.codegen.utilities import CodeValidator
from pathlib import Path

async def validate_code():
    validator = CodeValidator()
    
    files = list(Path("./agents/new_agent").rglob("*.py"))
    report = await validator.validate_all(files, {})
    
    print(f"Overall Score: {report['overall_score']:.1f}%")
    print(f"Passed: {report['passed']}")
    
    for gate in report['gates']:
        print(f"Gate {gate['gate_id']}: {gate['name']} - {gate['score']:.1f}%")
```

### Advanced Usage - DORA Blocks

```python
from l9.core.codegen.utilities import DORABlockGenerator
from pathlib import Path

async def add_dora_blocks():
    generator = DORABlockGenerator()
    
    for file_path in Path("./agents/new_agent").rglob("*.py"):
        dora_block = await generator.add_dora_block(
            file_path=file_path,
            spec_id="agent-spec-001",
            metadata={"tier": 2}
        )
        print(f"✅ Added DORA block to {file_path.name}")
```

### Advanced Usage - Git Safety

```python
from l9.core.codegen.utilities import GitSafetyManager
from pathlib import Path

async def safe_generation():
    git_manager = GitSafetyManager(repo_root=Path("/home/ubuntu/L9"))
    
    # Create feature branch
    branch = await git_manager.create_feature_branch("new_agent")
    print(f"🌿 Created branch: {branch}")
    
    # Generate files...
    # (generation code here)
    
    # Commit each file
    for file_path in generated_files:
        commit_sha = await git_manager.commit_file(
            file_path=file_path,
            message=f"Generated {file_path.name}"
        )
        print(f"✅ Committed: {commit_sha[:8]}")
    
    # If validation fails, rollback
    if not validation_passed:
        await git_manager.rollback_to_baseline()
        print(f"🔄 Rolled back to baseline")
```

---

## 🏗️ Architecture

### System Components

1. **CodeGenGatekeeperAgent** - Main entry point
   - Contract parsing & validation
   - Perplexity research integration
   - Spec normalization
   - Confidence scoring

2. **ModuleCompiler** - Deterministic code generator
   - Module-Spec v2.6 → Python
   - Async/await patterns
   - Type hints & Pydantic models
   - Test generation

3. **CodeValidator** - 14-gate validation
   - Syntax validation (MANDATORY)
   - Type safety
   - L9 pattern compliance
   - Security checks
   - Test coverage

4. **DORABlockGenerator** - Metadata blocks
   - File metadata
   - Automation rules
   - L9 integration
   - Quality metrics

5. **GitSafetyManager** - Git-based safety
   - Feature branch per execution
   - Commit per file
   - Instant rollback

### Pipeline Flow

```
Contract Input
    ↓
CodeGenGatekeeperAgent
    ├─ Parse & Validate
    ├─ Detect Blind Spots
    ├─ Research (Perplexity)
    ├─ Fill Gaps
    ├─ Normalize to Module-Spec v2.6
    └─ Calculate Confidence
    ↓
ModuleCompiler
    ├─ Generate Python files
    ├─ Generate tests
    └─ Generate documentation
    ↓
DORABlockGenerator
    └─ Add metadata blocks
    ↓
GitSafetyManager
    ├─ Create branch
    └─ Commit files
    ↓
CodeValidator
    ├─ Run 14 gates
    └─ Generate report
    ↓
Production-Ready Code
```

---

## 📋 Supported Input Formats

### 1. Agent YAML (QPF v6.0)

```yaml
system:
  name: "Research Agent"
  role: "Autonomous research and synthesis"

integration:
  depends_on: ["memory.service", "tool_registry"]

governance:
  escalation_path: "Igor"

memorytopology:
  working_memory: "redis"
  episodic_memory: "postgres"

communicationstack:
  input_channels: ["websocket", "http"]

reasoningengine:
  framework: "langgraph"
  modes: ["analytical", "creative"]
```

### 2. Module Block (Module-Spec v2.6)

```yaml
schema_version: "2.6"
metadata:
  module_id: "twilio_adapter"
  name: "Twilio SMS Adapter"
  tier: 2

runtime_wiring:
  service: "api"
  startup_phase: "normal"

external_surface:
  exposes_tool: true

packet_contract:
  emits: ["twilio.sms.sent", "twilio.sms.error"]
```

### 3. SymCode Spec

```yaml
symbols:
  - name: "m"
    domain: "positive"
    units: "kg"
  - name: "v"
    domain: "real"
    units: "m/s"

equations:
  - name: "kinetic_energy"
    expression: "0.5 * m * v**2"
    equation_type: "objective"

target_languages: ["python", "numpy", "c"]
```

### 4. Natural Language Concept

```yaml
CONCEPT_NAME: "Email Sentiment Analyzer"
ONE_SENTENCE: "Analyze email sentiment and route to appropriate agent"

ARCHITECTURE:
  components:
    - name: "Email Parser"
      role: "Extract text from email"
    - name: "Sentiment Scorer"
      role: "Score sentiment 0-100"

DECISION_POINTS:
  - "Route to urgent queue if sentiment < 30"
```

---

## 🎯 Generated File Structure

```
module_{name}/
├── __init__.py           # Module exports
├── config.py             # Pydantic settings
├── models.py             # Request/Response schemas
├── core.py               # Main orchestrator (async)
├── database.py           # DB layer (if needed)
├── tools.py              # Tool registry integration (if needed)
├── exceptions.py         # Custom exceptions
├── logger.py             # Structured logging
├── health_check.py       # Health endpoint
├── tests/
│   ├── conftest.py       # Pytest fixtures
│   ├── test_models.py    # Model tests
│   ├── test_core.py      # Core logic tests
│   └── test_integration.py  # Integration tests
├── README.md             # Documentation
├── requirements.txt      # Dependencies
└── .env.example          # Configuration template
```

---

## 🔧 Configuration

### Environment Variables

```bash
# Perplexity Labs API
PERPLEXITY_API_KEY=pplx-xxx

# L9 Repository
L9_REPO_ROOT=/home/ubuntu/L9
L9_CODEGEN_OUTPUT_DIR=${L9_REPO_ROOT}/generated

# Feature Flags
L9_ENABLE_CODEGEN=true
L9_ENABLE_PERPLEXITY_RESEARCH=true
L9_ENABLE_SYMCODE=true

# Code Generation
CODEGEN_DEFAULT_TIER=2
CODEGEN_MIN_CONFIDENCE=85
CODEGEN_MAX_RESEARCH_QUERIES=10

# Git Safety
CODEGEN_GIT_BRANCH_PREFIX=codegen
CODEGEN_AUTO_COMMIT=true
CODEGEN_AUTO_ROLLBACK_ON_FAIL=true

# Validation
CODEGEN_MIN_COVERAGE=80
CODEGEN_STRICT_TYPE_CHECKING=true
CODEGEN_SECURITY_SCAN=true
```

---

## 📊 Validation Gates

The CodeValidator runs 14 gates:

1. **Syntax Validation** (MANDATORY) - 0 syntax errors
2. **Type Safety** - All functions type-hinted
3. **Import Resolution** - All imports resolve
4. **L9 Pattern Compliance** - Follows naming conventions
5. **Feature Flag Awareness** - Respects L9_ENABLE_*
6. **Kernel Dependencies** - Valid kernel YAML references
7. **Memory Substrate** - Valid PostgreSQL schema
8. **Tool Registry** - Correct tool bindings
9. **Packet Contract** - Valid packet types
10. **Error Handling** - Explicit exception types
11. **Async Patterns** - Proper async/await usage
12. **Test Coverage** - >80% coverage
13. **Security** - No hardcoded secrets, input validation
14. **Performance** - No N+1 queries, proper indexing

**Confidence Formula**:
```
BASE: 100%
PENALTIES:
- Syntax error: -25% (FAIL if >1)
- Logic error: IMMEDIATE FAIL (0%)
- Missing type hint: -2% per function
- Missing test: -5% per module
- Feature flag violation: -30%
- Security issue: -50%
```

---

## 🚀 Examples

### Example 1: Generate Agent from YAML

```bash
# Create agent spec
cat > research_agent.yaml << 'EOF'
system:
  name: "Research Agent"
  role: "Autonomous research and synthesis"
integration:
  depends_on: ["memory.service"]
governance:
  escalation_path: "Igor"
memorytopology:
  working_memory: "redis"
communicationstack:
  input_channels: ["websocket"]
reasoningengine:
  framework: "langgraph"
EOF

# Generate code
python -m l9.core.codegen.cli generate \
  -i research_agent.yaml \
  -t agent_yaml \
  -o ./agents/research_agent \
  --research

# Validate
python -m l9.core.codegen.cli validate \
  -f ./agents/research_agent

# Run tests
cd ./agents/research_agent
pytest tests/ -v --cov=.
```

### Example 2: Generate Module from Block

```bash
# Create module block
cat > twilio_adapter.yaml << 'EOF'
schema_version: "2.6"
metadata:
  module_id: "twilio_adapter"
  name: "Twilio SMS Adapter"
  tier: 2
runtime_wiring:
  service: "api"
external_surface:
  exposes_tool: true
EOF

# Generate code
python -m l9.core.codegen.cli generate \
  -i twilio_adapter.yaml \
  -t module_block \
  -o ./modules/twilio_adapter
```

---

## 📈 Performance

| Metric | Value |
|--------|-------|
| Agent YAML → Code | ~45 seconds |
| Module Block → Code | ~30 seconds |
| SymCode → Multi-language | ~60 seconds |
| Concept → Module | ~90 seconds |
| Perplexity Research Queries | 3-10 per spec |
| Code Coverage Target | >80% |
| Validation Gates | 14 |
| Confidence Threshold | 85% |

---

## 🤝 Contributing

See `/docs/CodeGen/CONTRIBUTING.md`

---

## 📄 License

Apache 2.0

---

## 🔗 Links

- **Architecture**: `/docs/CodeGen/UNIFIED_CODEGEN_SYSTEM_v1.0.md`
- **API Reference**: `/docs/CodeGen/API_REFERENCE.md`
- **Examples**: `/docs/CodeGen/examples/`
- **Troubleshooting**: `/docs/CodeGen/TROUBLESHOOTING.md`

---

**Unified CodeGen System v1.0.0** - Making code generation deterministic, researched, and production-ready for L9 AIOS.
