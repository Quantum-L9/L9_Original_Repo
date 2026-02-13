"""
Test Pipeline Session DAG
=========================

Systematic workflow for identifying missing tests and generating test coverage.

Flow:
1. Gap Analysis - Identify modules without tests
2. Spec Generation - Generate YAML test specs for gaps
3. Test Generation - Run test generator (tools/codegen/test_generator.py)
4. Validation - Verify generated tests compile and pass
5. Coverage Check - Verify coverage improved
6. Report - Summarize results

Version: 1.0.0
Based on: readme-pipeline-v1 pattern + tools/codegen/test_generator.py
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Test Pipeline Dag",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-31T20:27:26Z",
    "updated_at": "2026-01-31T22:27:11Z",
    "layer": "operations",
    "domain": "workflows",
    "module_name": "test_pipeline_dag",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["workflows.dags.__init__"],
    },
}
# ============================================================================

from workflows.session.interface import (
    GateType,
    NodeType,
    SessionDAG,
    SessionEdge,
    SessionNode,
)
from workflows.session.registry import register_session_dag

# =============================================================================
# KEY FILES
# =============================================================================
KEY_FILES = {
    "test_generator": "tools/codegen/test_generator.py",
    "spec_generator": "tools/codegen/spec_generator.py",
    "core_test_generator": "core/testing/test_generator.py",
    "spec_schema": "tools/codegen/fixtures/spec_schema_v1.0.json",
    "specs_dir": "private/specs/",
    "tests_dir": "tests/",
}

# =============================================================================
# TEST PIPELINE DAG DEFINITION
# =============================================================================

TEST_PIPELINE_DAG = SessionDAG(
    id="test-pipeline-v1",
    name="Test Generation Pipeline",
    version="1.0.0",
    description="""
Systematic workflow for identifying missing tests and generating test coverage.

This DAG guides through:
1. Gap Analysis - Compare test files vs source modules
2. Spec Generation - Generate YAML test specs for untested modules
3. Test Generation - Run tools/codegen/test_generator.py with specs
4. Validation - py_compile, pytest, ensure tests pass
5. Coverage Check - Verify coverage improved vs baseline
6. Report - Summarize coverage delta and files generated

Use when: Filling test gaps, increasing coverage, systematic test generation.

KEY FILES:
- Generator: tools/codegen/test_generator.py
- Specs: private/specs/*.yaml
- Output: tests/**/*.py

MODES:
- check: Validate specs (no writes)
- diff: Show what would change
- write: Generate and write tests
""",
    tags=["test", "coverage", "generation", "gap-analysis", "specs"],
    nodes=[
        # === ENTRY ===
        SessionNode(
            id="start",
            name="Start",
            node_type=NodeType.START,
            description="Entry point",
            action="Begin test pipeline workflow. Specify target module/tier or full coverage scan.",
        ),
        # === PHASE 1: GAP ANALYSIS ===
        SessionNode(
            id="gap_analysis",
            name="Gap Analysis",
            node_type=NodeType.ANALYZE,
            description="Identify modules without tests",
            action="""Analyze test coverage gaps:

1. **List all source modules:**
```bash
find . -path ./tests -prune -o -name "*.py" -print | \\
  grep -E "^\\./[a-z]" | \\
  grep -v -E "(__pycache__|venv|node_modules|\\.git)" | \\
  sort > /tmp/source_modules.txt
```

2. **List all test files:**
```bash
find tests -name "test_*.py" | \\
  sed 's|tests/||' | \\
  sed 's|test_||' | \\
  sort > /tmp/test_modules.txt
```

3. **Find modules without tests:**
```bash
# Map source to expected test path
# core/tools/registry.py → tests/core/tools/test_registry.py
```

4. **Check current coverage (if available):**
```bash
pytest --cov=. --cov-report=term-missing 2>/dev/null | \\
  grep -E "^[a-z].*MISS" | head -20
```

5. **Identify high-priority gaps:**
   - Critical tier modules without tests
   - Modules with 0% coverage
   - Recently modified modules without tests

Output format:
## GAP ANALYSIS RESULTS

| Module | Test Exists | Coverage | Priority |
|--------|-------------|----------|----------|
| core/tools/registry.py | ❌ | 0% | HIGH |
| memory/substrate.py | ✅ | 45% | MEDIUM |

### Gaps Found: {count}
### High Priority: {high_count}
""",
            outputs=["gaps", "high_priority_gaps", "baseline_coverage"],
        ),
        # === GATE: GAPS FOUND? ===
        SessionNode(
            id="gate_gaps",
            name="Gaps Found?",
            node_type=NodeType.GATE,
            description="Check if there are gaps to address",
            action="""## GAP ANALYSIS COMPLETE

### Summary
- **Modules scanned:** {scanned_count}
- **Gaps found:** {gap_count}
- **High priority:** {high_count}
- **Baseline coverage:** {baseline}%

### Top Gaps
{top_gaps_table}

Options:
- **CONTINUE:** Proceed to spec generation for gaps
- **SCOPE:** Limit to specific tier (core/runtime/api)
- **SKIP:** Jump directly to validation (existing tests only)
- **ABORT:** Exit workflow

⏸️ **AWAITING:** Response""",
            gate_type=GateType.USER_CONFIRM,
        ),
        # === PHASE 2: SPEC GENERATION ===
        SessionNode(
            id="spec_generation",
            name="Generate Test Specs",
            node_type=NodeType.TRANSFORM,
            description="Generate YAML test specifications for gaps",
            action="""Generate YAML test specs for identified gaps:

### For each gap module, create spec:

```yaml
# private/specs/{module_name}_tests.yaml
test_suites:
  - suite_id: "{module_name}_unit_tests"
    module: "{module_path}"
    strategy: "two_phase_loader"  # or: unit, integration, async
    priority: "p1"
    metadata:
      generated_by: "test-pipeline-v1"
      gap_analysis_date: "{date}"

    fixtures:
      - name: "mock_{dependency}"
        scope: "function"
        generator: "monkeypatch"

    unit_tests:
      - test_id: "test_{function}_happy_path"
        name: "Test {function} with valid inputs"
        type: "unit"
        scenarios:
          - scenario_id: "happy_path"
            condition: "Valid inputs provided"
            assertions:
              - type: "return_success"

      - test_id: "test_{function}_error_handling"
        name: "Test {function} error cases"
        type: "unit"
        scenarios:
          - scenario_id: "invalid_input"
            condition: "Invalid inputs provided"
            assertions:
              - type: "raises"
                exception: "ValueError"
```

### Spec generation commands:
```bash
# For each gap, analyze the source and generate spec
python3 -c "
from tools.codegen.test_generator import TestTemplateEngine
engine = TestTemplateEngine(Path('.'))
# Analyze {module} and suggest spec structure
"
```

### Manual spec enrichment:
- Add specific test scenarios based on code analysis
- Define mocks for external dependencies
- Set priority based on criticality

Output: private/specs/{module}_tests.yaml files""",
            outputs=["generated_specs", "spec_count"],
        ),
        SessionNode(
            id="validate_specs",
            name="Validate Specs",
            node_type=NodeType.VALIDATE,
            description="Validate spec files against schema",
            action="""Validate generated spec files:

```bash
# Validate spec syntax
python3 tools/codegen/test_generator.py \\
  --spec private/specs/{module}_tests.yaml \\
  --mode check

# Or validate all specs
python3 tools/codegen/test_generator.py \\
  --spec-glob "private/specs/*_tests.yaml" \\
  --mode check
```

Check for:
- YAML syntax errors
- Schema compliance (spec_schema_v1.0.json)
- Module paths exist
- Strategy is valid (two_phase_loader, unit, async, etc.)

Report validation errors:
| Spec File | Status | Errors |
|-----------|--------|--------|
| core_tools_tests.yaml | ✅ | None |
| memory_tests.yaml | ❌ | Invalid strategy |
""",
            validation="All specs pass schema validation",
        ),
        SessionNode(
            id="gate_specs",
            name="Specs Gate",
            node_type=NodeType.GATE,
            description="User confirms specs before test generation",
            action="""## SPECS GENERATED

### Summary
- **Specs created:** {spec_count}
- **Modules covered:** {module_count}
- **Estimated tests:** {test_count}

### Specs Ready
| Spec File | Module | Tests | Priority |
|-----------|--------|-------|----------|
{specs_table}

Options:
- **GENERATE:** Proceed to test generation
- **EDIT:** Modify specs before generation
- **DIFF:** Show what tests would be generated
- **ABORT:** Exit workflow

⏸️ **AWAITING:** Response""",
            gate_type=GateType.USER_CONFIRM,
        ),
        # === PHASE 3: TEST GENERATION ===
        SessionNode(
            id="generate_tests",
            name="Generate Tests",
            node_type=NodeType.TRANSFORM,
            description="Run test generator with specs",
            action="""Execute test generation:

### Mode: write (generates and writes tests)
```bash
python3 tools/codegen/test_generator.py \\
  --spec-glob "private/specs/*_tests.yaml" \\
  --output-dir tests/ \\
  --mode write \\
  --force-write
```

### Mode: diff (show changes without writing)
```bash
python3 tools/codegen/test_generator.py \\
  --spec-glob "private/specs/*_tests.yaml" \\
  --output-dir tests/ \\
  --mode diff
```

### Alternative: Use core/testing/test_generator.py
```python
from core.testing.test_generator import TestGenerator

generator = TestGenerator()
tests = generator.generate_unit_tests(
    code_proposal=source_code,
    module_name="{module_name}"
)
```

Expected output:
- Generated test files in tests/
- Test count per module
- Warnings/errors logged

Log format:
✓ Generated tests/core/tools/test_registry.py (8 tests)
✓ Generated tests/memory/test_substrate.py (12 tests)
""",
            outputs=["generated_files", "test_count", "generation_errors"],
        ),
        # === PHASE 4: VALIDATION ===
        SessionNode(
            id="validate_tests",
            name="Validate Generated Tests",
            node_type=NodeType.VALIDATE,
            description="Verify generated tests compile and pass",
            action="""Validate generated test files:

### 1. Syntax check (py_compile)
```bash
python3 -m py_compile {generated_test_files}
```

### 2. Import check
```bash
for f in {generated_test_files}; do
  python3 -c "import $(echo $f | sed 's|/|.|g' | sed 's|.py||')"
done
```

### 3. Run generated tests
```bash
pytest {generated_test_files} -v --tb=short
```

### 4. Check for common issues:
- Missing fixtures
- Import errors
- Undefined mocks
- Async/await issues

### Validation results:
| Test File | Syntax | Imports | Runs | Status |
|-----------|--------|---------|------|--------|
| test_registry.py | ✅ | ✅ | ✅ | PASS |
| test_substrate.py | ✅ | ❌ | - | FAIL |

⚠️ If tests fail, fix before proceeding""",
            validation="py_compile ✅, imports ✅, pytest ✅",
        ),
        SessionNode(
            id="gate_validation",
            name="Validation Gate",
            node_type=NodeType.GATE,
            description="Check if validation succeeded",
            action="""## VALIDATION RESULTS

### Syntax Check
{syntax_results}

### Import Check
{import_results}

### Test Execution
{pytest_results}

**Overall Status:** {PASS/FAIL}

If FAIL:
- Fix issues before coverage check
- Common fixes: add missing imports, fix fixtures

If PASS:
- Proceed to coverage check

⏸️ **AWAITING:** "CONTINUE" or "FIX" """,
            gate_type=GateType.USER_CONFIRM,
        ),
        # === PHASE 5: COVERAGE CHECK ===
        SessionNode(
            id="coverage_check",
            name="Coverage Check",
            node_type=NodeType.VALIDATE,
            description="Verify coverage improved vs baseline",
            action="""Check coverage improvement:

### Run coverage report
```bash
pytest tests/ --cov=. --cov-report=term-missing --cov-report=html
```

### Compare with baseline
| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Total Coverage | {baseline}% | {new}% | +{delta}% |
| core/ | {core_before}% | {core_after}% | +{core_delta}% |
| memory/ | {mem_before}% | {mem_after}% | +{mem_delta}% |

### Coverage by generated file:
| Module | Before | After | Tests Added |
|--------|--------|-------|-------------|
| core/tools/registry.py | 0% | 85% | 8 |
| memory/substrate.py | 45% | 78% | 12 |

### Target:
- Minimum improvement: +5%
- Target per module: 80%+

### If coverage didn't improve:
- Tests may not be hitting target code
- Review generated test scenarios
- Add more specific test cases
""",
            validation="Coverage improved by at least 5%",
            outputs=["new_coverage", "coverage_delta", "coverage_report"],
        ),
        # === PHASE 6: REPORT ===
        SessionNode(
            id="generate_report",
            name="Generate Report",
            node_type=NodeType.ANALYZE,
            description="Summarize pipeline results",
            action="""Generate summary report:

## TEST PIPELINE REPORT

### Overview
| Metric | Value |
|--------|-------|
| Workflow ID | test-pipeline-v1 |
| Started | {started_at} |
| Completed | {completed_at} |

### Gap Analysis
- Modules scanned: {scanned_count}
- Gaps found: {gap_count}
- High priority filled: {filled_count}

### Test Generation
- Specs created: {spec_count}
- Test files generated: {file_count}
- Total tests generated: {test_count}

### Coverage Impact
| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Overall | {before}% | {after}% | +{delta}% |

### Files Created
| File | Tests | Coverage |
|------|-------|----------|
{files_table}

### Next Steps
- [ ] Review generated tests for accuracy
- [ ] Add custom test scenarios where needed
- [ ] Commit: `git add tests/ && git commit -m "test: add generated tests for {modules}"`
- [ ] Run full test suite: `pytest tests/ -v`

### Commit?
⏸️ **AWAITING:** "COMMIT" or "EXIT" """,
            outputs=["report"],
        ),
        SessionNode(
            id="gate_commit",
            name="Commit Gate",
            node_type=NodeType.GATE,
            description="User decides whether to commit",
            action="""## Ready to Commit?

**New test files:** {file_count}
**Tests added:** {test_count}
**Coverage delta:** +{delta}%

Options:
- **YES:** Commit changes
- **NO:** Exit without committing
- **DIFF:** Show git diff first

⏸️ **AWAITING:** Response""",
            gate_type=GateType.USER_CONFIRM,
        ),
        SessionNode(
            id="commit",
            name="Commit Changes",
            node_type=NodeType.COMMIT,
            description="Git commit if user approves",
            action="""git add tests/ private/specs/

git commit -m "$(cat <<'EOF'
test: add generated tests for test coverage

## Test Pipeline Summary
- Gaps filled: {gap_count}
- Test files added: {file_count}
- Coverage delta: +{delta}%

## Files Added
{files_list}

Generated via test-pipeline-v1 workflow.
EOF
)"

git log -1 --oneline""",
            outputs=["commit_hash"],
        ),
        # === EXIT ===
        SessionNode(
            id="end",
            name="End",
            node_type=NodeType.END,
            description="Workflow complete",
            action="Test pipeline complete. Review coverage report at htmlcov/index.html",
        ),
    ],
    edges=[
        # Start -> Gap Analysis
        SessionEdge("start", "gap_analysis"),
        SessionEdge("gap_analysis", "gate_gaps"),
        # Gap gate decisions
        SessionEdge(
            "gate_gaps", "spec_generation", condition="continue", label="Generate specs"
        ),
        SessionEdge(
            "gate_gaps", "validate_tests", condition="skip", label="Skip to validation"
        ),
        SessionEdge("gate_gaps", "end", condition="abort", label="Abort"),
        # Spec generation -> Validation
        SessionEdge("spec_generation", "validate_specs"),
        SessionEdge("validate_specs", "gate_specs"),
        # Spec gate decisions
        SessionEdge(
            "gate_specs", "generate_tests", condition="generate", label="Generate"
        ),
        SessionEdge(
            "gate_specs", "spec_generation", condition="edit", label="Edit specs"
        ),
        SessionEdge("gate_specs", "end", condition="abort", label="Abort"),
        # Test generation -> Validation
        SessionEdge("generate_tests", "validate_tests"),
        SessionEdge("validate_tests", "gate_validation"),
        # Validation gate decisions
        SessionEdge(
            "gate_validation", "coverage_check", condition="continue", label="Continue"
        ),
        SessionEdge(
            "gate_validation", "generate_tests", condition="fix", label="Fix issues"
        ),
        SessionEdge("gate_validation", "end", condition="abort", label="Abort"),
        # Coverage -> Report
        SessionEdge("coverage_check", "generate_report"),
        SessionEdge("generate_report", "gate_commit"),
        # Commit gate decisions
        SessionEdge("gate_commit", "commit", condition="yes", label="Commit"),
        SessionEdge("gate_commit", "end", condition="no", label="Skip Commit"),
        # End
        SessionEdge("commit", "end"),
    ],
    entry_node="start",
)


# Register on module import
register_session_dag(TEST_PIPELINE_DAG)


def get_test_pipeline_dag() -> SessionDAG:
    """Get the test pipeline DAG."""
    return TEST_PIPELINE_DAG


# Generate Mermaid diagram for documentation
if __name__ == "__main__":
    print(TEST_PIPELINE_DAG.to_markdown())  # noqa: ADR-0019
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-OPER-028",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "caching",
        "cli",
        "metrics",
        "mocking",
        "operations",
        "security",
        "testing",
        "workflows",
    ],
    "keywords": [
        "analysis",
        "codegen",
        "coverage",
        "dag",
        "generation",
        "pattern",
        "pipeline",
        "test",
    ],
    "business_value": "Utility module for test pipeline dag",
    "last_modified": "2026-01-31T22:27:11Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
