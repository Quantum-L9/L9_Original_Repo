# Unified CodeGen System - QUICKSTART Guide

**Get started in 5 minutes!**

---

## 🚀 Installation

```bash
# 1. Navigate to L9 repo
cd /home/ubuntu/L9

# 2. Install dependencies
pip install -r core/codegen/requirements.txt

# 3. Set environment variables
export PERPLEXITY_API_KEY=pplx-your-key-here
export L9_REPO_ROOT=/home/ubuntu/L9
export L9_ENABLE_CODEGEN=true
```

---

## 📝 Your First Code Generation

### Step 1: Create an Agent Spec

Create `my_agent.yaml`:

```yaml
system:
  name: "My First Agent"
  role: "Test agent for learning CodeGen"

integration:
  depends_on: ["memory.service"]

governance:
  escalation_path: "Igor"
  tier: 3

memorytopology:
  working_memory: "redis"

communicationstack:
  input_channels: ["http"]

reasoningengine:
  framework: "langgraph"
```

### Step 2: Generate Code

```bash
python -m l9.core.codegen.cli generate \
  --input my_agent.yaml \
  --type agent_yaml \
  --output ./agents/my_first_agent \
  --research
```

**Output**:
```
🚀 Unified CodeGen System v1.0.0
📄 Input: my_agent.yaml
📦 Type: agent_yaml
📂 Output: ./agents/my_first_agent
🔬 Research: enabled
🎯 Min Confidence: 85.0%

✅ Code generation successful!
📊 Confidence: 92.5%
📁 Files generated: 13
🌿 Git branch: codegen-my_first_agent-20251231-120000
📈 Coverage: 85.0%
⏱️  Time: 42.3s
```

### Step 3: Explore Generated Code

```bash
cd ./agents/my_first_agent
ls -la
```

**Generated files**:
```
module_my_first_agent/
├── __init__.py           # Module exports
├── config.py             # Pydantic settings
├── models.py             # Request/Response schemas
├── core.py               # Main orchestrator (async)
├── tools.py              # Tool registry integration
├── exceptions.py         # Custom exceptions
├── logger.py             # Structured logging
├── health_check.py       # Health endpoint
├── tests/
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_core.py
│   └── test_integration.py
├── README.md
├── requirements.txt
└── .env.example
```

### Step 4: Run Tests

```bash
cd module_my_first_agent
pytest tests/ -v --cov=.
```

**Output**:
```
============================= test session starts ==============================
collected 5 items

tests/test_models.py::test_request_model_creation PASSED                 [ 20%]
tests/test_models.py::test_response_model_creation PASSED                [ 40%]
tests/test_core.py::test_orchestrator_initialization PASSED              [ 60%]
tests/test_core.py::test_process_request PASSED                          [ 80%]
tests/test_core.py::test_health_check PASSED                             [100%]

---------- coverage: platform linux, python 3.11.0 -----------
Name                     Stmts   Miss  Cover
--------------------------------------------
__init__.py                  5      0   100%
config.py                   12      0   100%
core.py                     45      3    93%
exceptions.py                8      0   100%
health_check.py              6      0   100%
logger.py                   15      2    87%
models.py                   22      0   100%
tools.py                    12      2    83%
--------------------------------------------
TOTAL                      125     7    94%

============================== 5 passed in 2.34s ===============================
```

### Step 5: Use the Generated Code

```python
import asyncio
from module_my_first_agent import MyFirstAgentOrchestrator, MyFirstAgentRequest

async def main():
    # Initialize orchestrator
    orchestrator = MyFirstAgentOrchestrator()

    # Create request
    request = MyFirstAgentRequest(data={"message": "Hello, CodeGen!"})

    # Process
    response = await orchestrator.process(request)

    print(f"Success: {response.success}")
    print(f"Data: {response.data}")

asyncio.run(main())
```

---

## 🎯 Common Use Cases

### Use Case 1: Generate Module from Block

```bash
# Create module_block.yaml
cat > email_processor.yaml << 'EOF'
schema_version: "2.6"
metadata:
  module_id: "email_processor"
  name: "Email Processor"
  tier: 2
runtime_wiring:
  service: "api"
external_surface:
  exposes_tool: true
EOF

# Generate
python -m l9.core.codegen.cli generate \
  -i email_processor.yaml \
  -t module_block \
  -o ./modules/email_processor
```

### Use Case 2: Validate Existing Code

```bash
python -m l9.core.codegen.cli validate \
  --files ./agents/my_first_agent
```

### Use Case 3: Research Best Practices

```bash
python -m l9.core.codegen.cli research \
  --query "What are async Python best practices for error handling?"
```

---

## 📊 Understanding the Output

### Confidence Score

- **90-100%**: Excellent - All fields complete, no gaps
- **85-89%**: Good - Minor gaps filled by research
- **70-84%**: Fair - Some gaps, may need manual review
- **<70%**: Poor - Major gaps, generation blocked

### Validation Gates

All generated code passes through 14 validation gates:

1. ✅ **Syntax** (MANDATORY) - No syntax errors
2. ✅ **Type Safety** - All functions type-hinted
3. ✅ **Imports** - All imports resolve
4. ✅ **L9 Patterns** - Follows L9 conventions
5. ✅ **Feature Flags** - Respects L9_ENABLE_*
6. ✅ **Kernel Deps** - Valid kernel references
7. ✅ **Memory Substrate** - Valid DB schema
8. ✅ **Tool Registry** - Correct tool bindings
9. ✅ **Packet Contract** - Valid packet types
10. ✅ **Error Handling** - Explicit exceptions
11. ✅ **Async Patterns** - Proper async/await
12. ✅ **Test Coverage** - >80% coverage
13. ✅ **Security** - No hardcoded secrets
14. ✅ **Performance** - No N+1 queries

### Git Safety

Every generation creates a Git branch:

```bash
# View branch
git branch | grep codegen

# Review changes
git diff main..codegen-my_first_agent-20251231-120000

# Merge when ready
git checkout main
git merge codegen-my_first_agent-20251231-120000
```

---

## 🔧 Troubleshooting

### Issue: "Perplexity API key not set"

**Solution**:
```bash
export PERPLEXITY_API_KEY=pplx-your-key-here
```

### Issue: "Confidence below threshold"

**Solution**: Enable research or lower threshold:
```bash
python -m l9.core.codegen.cli generate \
  -i spec.yaml \
  -t agent_yaml \
  -o ./output \
  --research \
  --min-confidence 70
```

### Issue: "Validation failed"

**Solution**: Check validation report:
```bash
python -m l9.core.codegen.cli validate --files ./output
```

Fix errors and re-run generation.

### Issue: "Import errors in generated code"

**Solution**: Install dependencies:
```bash
cd ./output/module_*
pip install -r requirements.txt
```

---

## 📚 Next Steps

1. **Read the full documentation**: `core/codegen/README.md`
2. **Explore examples**: `core/codegen/examples/`
3. **Try different input formats**: Agent YAML, Module Block, SymCode, Concept
4. **Customize templates**: `core/codegen/templates/`
5. **Integrate with CI/CD**: Add to your deployment pipeline

---

## 🤝 Need Help?

- **Documentation**: `/home/ubuntu/L9/core/codegen/README.md`
- **Architecture**: `/home/ubuntu/L9/docs/CodeGen/UNIFIED_CODEGEN_SYSTEM_v1.0.md`
- **Examples**: `/home/ubuntu/L9/core/codegen/examples/`

---

**Unified CodeGen System v1.0.0** - From spec to production in minutes! 🚀
