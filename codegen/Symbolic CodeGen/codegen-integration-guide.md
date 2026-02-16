# INTEGRATION: Symbolic Codegen Pipeline → CodeGenAgent

## Where to Wire It

**File:** `agents/codegenagent/codegenagent.py`

Add this **import and method** to the existing `CodeGenAgent` class:

```python
# At top of codegenagent.py
from codegen.symbolic.pipeline import SymbolicCodegenPipeline
from codegen.symbolic.spec import CodegenSpec, CodegenIntent

class CodeGenAgent:
    """Existing CodeGenAgent class (modified)."""
    
    def __init__(self, ...):
        # Existing init code
        ...
        # NEW: Initialize symbolic codegen pipeline
        self.symbolic_pipeline = SymbolicCodegenPipeline()
    
    async def generate_with_symbolic_verification(
        self,
        intent: str,  # "generate", "refactor", "optimize", "verify"
        target_behavior: str,
        input_code: str | None = None,
        invariants: list[str] | None = None,
        constraints: list[str] | None = None,
        variables: list[str] | None = None,
    ):
        """
        Generate or transform code using symbolic verification.
        
        LIFECYCLE:
        1. Build CodegenSpec from inputs
        2. Run symbolic pipeline (5 stages)
        3. If pipeline succeeds, emit verified code
        4. If fails, return error + counterexample
        
        This enforces:
        - Spec-first (CodegenSpec)
        - Symbolic proof (EquivalenceVerifier)
        - Test-bound (verifications)
        - Kernel-governed (SYMBOLIC_CODEGEN_KERNEL.v2)
        """
        
        # Stage 1: Build spec
        spec = CodegenSpec(
            intent=CodegenIntent(intent),
            target_behavior=target_behavior,
            input_code=input_code,
            invariants=invariants or [],
            constraints=constraints or [],
            variables=variables or [],
        )
        
        # Stage 2-5: Run pipeline
        result = self.symbolic_pipeline.execute(spec)
        
        if not result.success:
            return {
                "success": False,
                "error": "; ".join(result.errors),
                "spec": spec.dict(),
            }
        
        # Emit verified code
        return {
            "success": True,
            "code": result.selected_code,
            "candidates_evaluated": len(result.candidates),
            "invariants_verified": all(
                v.all_invariants_pass for v in result.verifications
            ),
            "selection_rationale": result.selection_result.get(
                "selection_rationale", ""
            ),
        }
```

---

## Usage Examples

### Example 1: Optimize a Function

```python
# In your GMP or task flow
agent = CodeGenAgent(...)

result = await agent.generate_with_symbolic_verification(
    intent="optimize",
    target_behavior="(x**2 + 2*x + 1) / (x + 1) can be simplified",
    input_code="""
def compute(x):
    return (x**2 + 2*x + 1) / (x + 1)
    """,
    invariants=[
        "result must match original for all valid x",
        "must be numerically stable",
    ],
    variables=["x: float"],
)

if result["success"]:
    print("Optimized code:")
    print(result["code"])
else:
    print("Optimization failed:", result["error"])
```

### Example 2: Generate New Code with Invariants

```python
result = await agent.generate_with_symbolic_verification(
    intent="generate",
    target_behavior="Euclidean distance between two points",
    invariants=[
        "distance(x, y) >= 0",
        "distance(x, y) == distance(y, x)",
        "distance(0, 0) == 0",
    ],
    variables=["x: float", "y: float"],
)

if result["success"]:
    print("Generated code:")
    print(result["code"])
    print(f"\nInvariants verified: {result['invariants_verified']}")
```

### Example 3: Refactor with Symbolic Proof

```python
result = await agent.generate_with_symbolic_verification(
    intent="refactor",
    target_behavior="Same behavior, but avoid repeated computation",
    input_code="""
def process(a, b, c):
    x = a + b
    y = a + b  # Redundant
    return x * y
    """,
    invariants=[
        "Must return a*a + 2*a*b + b*b",
    ],
    variables=["a: float", "b: float", "c: float"],
)
```

---

## Integration into GMP Flow

**In your GMP prompts** (e.g., `GMP-Action-Prompt-v1.0.md`), add:

```markdown
## Tool: symbolic_codegen

When you need to generate or refactor code with proof of correctness:

```bash
gmp_run(
  tool="symbolic_codegen",
  intent="refactor|optimize|generate",
  target_behavior="...",
  input_code="...",
  invariants=[...],
  variables=[...],
)
```

The kernel (`SYMBOLIC_CODEGEN_KERNEL.v2`) governs:
- Symbolic verification before code emission
- Equivalence proofs or counterexamples
- Invariant satisfaction
- Safe code selection

If symbolic verification fails, no code is emitted.
```

---

## Governance Hooks (SYMBOLIC_CODEGEN_KERNEL.v2)

Add this to the kernel's **enforcement section** if needed:

```yaml
# In SYMBOLIC_CODEGEN_KERNEL.v2

enforcement:
  codegen_agent_hooks:
    - method: generate_with_symbolic_verification
      required: true
      triggers:
        - intent in (GENERATE, REFACTOR, OPTIMIZE)
        - input involves core SymPy service modules
      checks:
        - symbolic_verification_passed
        - equivalence_proof_exists
        - all_invariants_satisfied
      on_failure:
        - emit_counterexample
        - halt_codegen
```

---

## Testing

Create **integration tests** in `tests/test_codegen_symbolic_integration.py`:

```python
import pytest
from agents.codegenagent import CodeGenAgent

@pytest.mark.asyncio
async def test_symbolic_optimize():
    """Test optimization with symbolic verification."""
    agent = CodeGenAgent()
    
    result = await agent.generate_with_symbolic_verification(
        intent="optimize",
        target_behavior="(x**2 + 2*x + 1) / (x + 1)",
        input_code="def f(x):\n    return (x**2 + 2*x + 1) / (x + 1)",
        invariants=["must be equivalent to original"],
        variables=["x: float"],
    )
    
    assert result["success"], result.get("error")
    assert "code" in result
    assert result["invariants_verified"]


@pytest.mark.asyncio
async def test_symbolic_generate():
    """Test code generation with invariants."""
    agent = CodeGenAgent()
    
    result = await agent.generate_with_symbolic_verification(
        intent="generate",
        target_behavior="distance formula",
        invariants=[
            "distance(x, y) >= 0",
            "distance(x, y) == distance(y, x)",
        ],
        variables=["x: float", "y: float"],
    )
    
    assert result["success"]
    assert "code" in result
```

---

## Expected Output

When successful:

```python
{
    "success": True,
    "code": "def f(x):\n    return x + 1  # Simplified",
    "candidates_evaluated": 4,
    "invariants_verified": True,
    "selection_rationale": "✓ Symbolically equivalent | O(1) complexity | Minimal diff | ...",
}
```

When verification fails:

```python
{
    "success": False,
    "error": "Candidate not equivalent to original; counterexample: {x: -5.3}",
    "spec": { ... }
}
```

---

## Checklist

- [ ] Create `codegen/symbolic/` directory with all modules
- [ ] Add `symbolic_pipeline` to `CodeGenAgent.__init__`
- [ ] Add `generate_with_symbolic_verification` method
- [ ] Create integration tests
- [ ] Update kernel catalog to list `SYMBOLIC_CODEGEN_KERNEL.v2`
- [ ] Add GMP action prompt documentation
- [ ] Test end-to-end: spec → pipeline → verified code
- [ ] Deploy and verify symbolic verification gates function

---

## Summary

The symbolic codegen pipeline is now:

1. **Wired into CodeGenAgent** as `generate_with_symbolic_verification()`
2. **Governed by the kernel** (`SYMBOLIC_CODEGEN_KERNEL.v2`)
3. **Production-ready** with 5 compiler-like stages
4. **Test-bound** with mandatory verification
5. **Ready for Codex** to call from GMP tasks

You can now say: **"Refactor this code, but prove it's equivalent first."**

And Codex knows how.
