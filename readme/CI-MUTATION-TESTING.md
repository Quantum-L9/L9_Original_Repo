# Mutation Testing in L9 CI

## Overview

L9 uses **mutation testing** to detect weak tests that pass even when code logic is broken. This catches bugs that traditional coverage metrics miss.

**Tool:** [mutmut](https://mutmut.readthedocs.io/) - Python mutation testing framework

## How It Works

1. **Mutation:** mutmut creates small changes ("mutants") in your code:

   - `x > 0` → `x >= 0`
   - `return True` → `return False`
   - `x + 1` → `x - 1`

2. **Testing:** Each mutant is tested against your test suite

3. **Scoring:**
   - **Killed:** Test suite caught the mutation (good!)
   - **Survived:** Tests passed despite broken code (bad - weak tests!)
   - **Score:** `killed / total × 100%`

## CI Integration

### When It Runs

- **PRs only** - Mutation testing is slow (~30s per mutant)
- **After tests pass** - No point mutating if tests already fail
- **On critical paths only** - Full codebase would take hours

### Threshold

**85% minimum mutation score required to merge PRs**

If score < 85%, the PR is blocked until tests are strengthened.

### Critical Paths Tested

```yaml
paths_to_mutate:
  - core/agents/executor.py # Agent execution loop
  - memory/substrate_service.py # Memory operations
  - core/governance/ # Governance enforcement
  - memory/ingestion.py # Packet ingestion
```

## Local Usage

### Quick Test (single file)

```bash
./scripts/refactoring/run_mutation_tests.sh --quick
```

### Full Test (all critical paths)

```bash
./scripts/refactoring/run_mutation_tests.sh
```

### Custom Threshold

```bash
./scripts/refactoring/run_mutation_tests.sh --threshold 90
```

### Manual mutmut Commands

```bash
# Run mutations
mutmut run --paths-to-mutate core/agents/executor.py --tests-dir tests/

# View results
mutmut results

# Show specific surviving mutant
mutmut show 42

# Apply mutant to inspect (then revert)
mutmut apply 42
git checkout -- core/agents/executor.py
```

## Fixing Surviving Mutants

When mutation score is below threshold:

1. **List survivors:**

   ```bash
   mutmut results
   ```

2. **Inspect a survivor:**

   ```bash
   mutmut show <id>
   ```

   This shows the mutation that wasn't caught.

3. **Add a test that catches it:**

   - If `x > 0` → `x >= 0` survived, add test for `x = 0` boundary
   - If `return True` → `return False` survived, assert the return value

4. **Re-run to verify:**
   ```bash
   mutmut run --paths-to-mutate <file>
   ```

## Configuration

See `config/refactoring/mutation-config.yaml` for full configuration.

### Key Settings

| Setting              | Value          | Description              |
| -------------------- | -------------- | ------------------------ |
| `minimum_score`      | 85             | PR blocking threshold    |
| `warning_score`      | 90             | Warning threshold        |
| `timeout_per_mutant` | 30s            | Max time per mutant test |
| `run_on`             | `pull_request` | Only run on PRs          |

## Why 85%?

- **Industry standard** - 80-85% is considered good coverage
- **Pragmatic** - Some mutations are false positives (e.g., logging changes)
- **Achievable** - Higher thresholds cause too many false blocks
- **Meaningful** - Below 85% indicates real test gaps

## Skip Mutation Tests

Add the `skip-mutation` label to a PR to bypass mutation testing (use sparingly).

## Related Files

- `scripts/refactoring/run_mutation_tests.sh` - Local runner script
- `config/refactoring/mutation-config.yaml` - Configuration
- `.github/workflows/ci.yml` - CI job definition
- `requirements.txt` - mutmut dependency

## References

- [mutmut Documentation](https://mutmut.readthedocs.io/)
- [Mutation Testing Wikipedia](https://en.wikipedia.org/wiki/Mutation_testing)
- [L9 Refactoring Suite](../current_work/01-20-2026/Refactoring%20Suite/)
