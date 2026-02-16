# Dev Layer Standard Operating Procedures (SOP)

**Authority**: L (CTO)  
**Version**: 1.0.0  
**Last Updated**: 2026-01-08

---

## Table of Contents

1. [Overview](#overview)
2. [Daily Operations](#daily-operations)
3. [Artifact Compilation](#artifact-compilation)
4. [Verification & Testing](#verification--testing)
5. [Change Promotion](#change-promotion)
6. [Incident Response](#incident-response)
7. [Secret Rotation](#secret-rotation)
8. [Rollback Procedures](#rollback-procedures)

---

## Overview

The Dev Layer is L9's code engineering governance system. It enforces reproducibility, auditability, and control through:

- **AM Engine**: Compiles human knowledge (docs) into machine-enforceable law (YAML)
- **Enforcement Engine**: Applies law at runtime, blocks violations, escalates to L
- **Code Planning**: Generates deterministic plans for code changes
- **Verification**: Tests plans against governance constraints

**Key Principle**: Same inputs → identical outputs. Always auditable. Never implicit.

---

## Daily Operations

### Startup

On bootstrap, the Dev Layer loads governance law:

```bash
# Manual (for testing)
python -m dev_layer.am_engine.compile \
  --input l9/dev_layer/artifacts/raw \
  --output l9/dev_layer/artifacts/compiled

# CI (automatic on every PR)
# See .github/workflows/dev-layer-gmp.yml
```


### Health Check

```bash
# Verify governance law is loaded
python -c "from dev_layer.am_engine.compile import load_canonical_yaml; \
from pathlib import Path; \
law = load_canonical_yaml(Path('l9/dev_layer/governance')); \
print('Constraints:', len(law))"

# Check enforcement engine
pytest l9/dev_layer/tests/test_determinism.py -v
```


### Log Inspection

All decisions are logged to stderr at runtime:

```bash
# View audit trail
python -m dev_layer.runtime.enforcement 2>&1 | grep "Audit:"
```


---

## Artifact Compilation

### Adding a New Governance Artifact

1. **Author the artifact** (Markdown):
```markdown
# DevLayer Enhancement

## H-LOGGING-001

Rule: All asynchronous operations must emit structured logs.

Severity: high
Violation Signals:
  - empty_logging_block
  - generic_exception_with_no_trace
```

2. **Place in raw artifacts directory**:
```bash
cp my_heuristic.md l9/dev_layer/artifacts/raw/
```

3. **Compile**:
```bash
./scripts/dev_layer_compile.sh
# or
python -m dev_layer.am_engine.compile \
  --input l9/dev_layer/artifacts/raw \
  --output l9/dev_layer/artifacts/compiled
```

4. **Verify output**:
```bash
ls -la l9/dev_layer/artifacts/compiled/heuristics/
# Should see: my_heuristic_abc123ef.yaml
```

5. **Inspect compiled YAML**:
```bash
cat l9/dev_layer/artifacts/compiled/heuristics/my_heuristic_abc123ef.yaml
```

6. **Commit**:
```bash
git add l9/dev_layer/artifacts/raw/my_heuristic.md
git add l9/dev_layer/artifacts/compiled/heuristics/my_heuristic_abc123ef.yaml
git commit -m "feat: add H-LOGGING-001 heuristic"
```


### Compilation Properties

- **Idempotent**: Running twice on same input produces same output path
- **Conservative**: Unknown fields preserved, never hallucinated
- **Deterministic**: Source hash in filename, immutable once created
- **Auditable**: Every YAML includes source_document, source_hash, confidence

---

## Verification \& Testing

### Run Full Test Suite

```bash
# Unit tests
pytest l9/dev_layer/tests/test_determinism.py -v

# E2E tests
pytest l9/dev_layer/tests/test_e2e_diff_generation.py -v

# All dev_layer tests
pytest l9/dev_layer/tests/ -v
```


### Test Determinism Specifically

```bash
# Verify same inputs → same hashes
pytest l9/dev_layer/tests/test_determinism.py::TestCodePlanDeterminism -v
```


### Generate Coverage Report

```bash
pytest l9/dev_layer/tests/ --cov=dev_layer --cov-report=html
open htmlcov/index.html
```


---

## Change Promotion

### Staging → Production Flow

1. **Develop on feature branch**:
```bash
git checkout -b feature/new-constraint
# Add artifact to l9/dev_layer/artifacts/raw/
# Compile locally
./scripts/dev_layer_compile.sh
# Run tests
pytest l9/dev_layer/tests/ -v
```

2. **Create PR**:
```bash
git push origin feature/new-constraint
# Opens PR; CI runs:
#   - AM compile
#   - Determinism tests
#   - E2E verification
```

3. **L Review**:

- L reviews diff of compiled YAML
- L verifies no unauthorized rules added
- L approves PR (merge to main)

4. **Merge to main**:
```bash
# GitHub: "Squash and merge"
# This triggers prod CI
```

5. **Production CI** (automatic):
```yaml
# .github/workflows/dev-layer-gmp.yml runs:
- Load governance law
- Run all tests
- Verify compilation is idempotent
- Store evidence in audit log
```

6. **Verify in production**:
```bash
# SSH to prod
ssh prod-server

# Reload law (service will do this on next start)
curl http://localhost:8000/health/dev-layer

# Check audit log
tail -f /var/log/l9/dev_layer_audit.log
```


---

## Incident Response

### Constraint Violation in Production

**Symptoms**: Operation blocked with `ConstraintViolation`

**Response**:

1. **Check audit log**:
```bash
grep "ConstraintViolation" /var/log/l9/dev_layer_audit.log
# Look for: which constraint, which operation, timestamp
```

2. **Identify the constraint**:
```bash
cat l9/dev_layer/governance/core.yaml | grep -A 5 "C-FILES-001"
# Understand why it blocked
```

3. **Options**:

**Option A: Operation was illegal** (constraint is correct)

- Modify operation to comply
- Resubmit with compliant approach
- No code change needed

**Option B: Constraint needs clarification**

- L reviews constraint
- L may adjust severity or scope
- Submit PR to update governance
- Process: Review → Approval → Merge → Reload

**Option C: Emergency override** (rare, L only)

- Only L can override
- Must log reason in decision record
- Requires incident post-mortem
- Change governance after incident resolved


### Escalation to L

**Symptoms**: Operation raises `EscalationRequired`

**Cause**: Confidence < 0.85 OR critical risk detected OR pattern ambiguity

**Response**:

1. **Check decision log**:
```bash
python -c "from dev_layer.runtime.enforcement import get_decision_log; \
logs = get_decision_log(); \
print('\\n'.join(str(l) for l in logs))"
```

2. **Inform L**:
```bash
echo "Plan abc123 requires L approval: confidence 0.80, pattern ambiguity in CQRS"
# Escalate via governance approval queue
```

3. **L Action**:

- Reviews plan, report, rationale
- Approves (allow) or rejects (block)
- Decision logged in audit trail

---

## Secret Rotation

### Governance API Keys (if used)

Currently: None. All operations are local to repo.

**Future**: If Dev Layer connects to external services (e.g., artifact storage, approval queue):

```bash
# Rotate API key
export DEV_LAYER_API_KEY="new_key_xyz"

# Restart enforcement engine
systemctl restart l9-dev-layer

# Verify new key is active
curl http://localhost:8000/health/dev-layer -H "Authorization: Bearer $DEV_LAYER_API_KEY"
```


---

## Rollback Procedures

### Rollback a Governance Change

**Scenario**: You merged a constraint that breaks CI.

**Recovery**:

1. **Identify the bad YAML**:
```bash
# Check compilation index
cat l9/dev_layer/artifacts/compiled/compilation_index.json | jq '.[] | select(.category == "constraints")'
```

2. **Find the commit that added it**:
```bash
git log --oneline l9/dev_layer/governance/
# Find commit hash
```

3. **Revert the commit**:
```bash
git revert abc123def456
git push origin main
```

4. **Prod CI automatically reloads law** (no manual action needed):
```bash
# Law is reloaded from compiled/ directory
# Constraint removed
```

5. **Verify**:
```bash
curl http://localhost:8000/health/dev-layer
# Check that constraint is no longer in loaded law
```


### Rollback a Code Change

**Scenario**: CA generated a bad diff that broke tests.

**Recovery**:

1. **Revert the merge commit**:
```bash
git revert main~1  # or specific commit hash
git push origin main
```

2. **Re-run CI**:
```bash
# GitHub CI automatically re-runs
# Verify all tests pass
```

3. **Post-mortem**:

- Why was the diff bad?
- Was governance law insufficient?
- Does CA need instruction adjustment?
- Update heuristics if needed

---

## Troubleshooting

### Compilation Hangs

**Symptom**: `./scripts/dev_layer_compile.sh` doesn't finish

**Cause**: Large artifact or malformed YAML

**Fix**:

```bash
# Run with debug logging
python -m dev_layer.am_engine.compile \
  --input l9/dev_layer/artifacts/raw \
  --output l9/dev_layer/artifacts/compiled \
  --log-level DEBUG

# Look for file causing hang
```


### Tests Fail Locally but Pass in CI

**Symptom**: `pytest l9/dev_layer/tests/ -v` fails locally

**Cause**: Environment differences, missing imports, or ordering issues

**Fix**:

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run in isolated venv
python -m venv test_env
source test_env/bin/activate
pip install -e ".
pytest l9/dev_layer/tests/ -v
```


### Governance Law Won't Load

**Symptom**: `initialize_with_law()` fails

**Cause**: Malformed YAML, missing file, or broken import

**Fix**:

```bash
# Verify YAML syntax
python -c "import yaml; yaml.safe_load(open('l9/dev_layer/governance/core.yaml'))"

# Check file exists
ls -la l9/dev_layer/governance/core.yaml

# Verify imports
python -c "from dev_layer.runtime.enforcement import initialize_with_law; print('OK')"
```


---

## Contact \& Escalation

**L (CTO)**: Final authority on governance changes, escalations, overrides
**CA (Coding Agent)**: Executes plans within governance constraints
**Igor (Human Authority)**: Overall system authority, governance charter

For issues:

1. Check this SOP
2. Review audit logs
3. Escalate to L
4. If governance is questioned, escalate to Igor
