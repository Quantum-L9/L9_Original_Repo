# L9 Semgrep Rules

Custom static analysis rules enforcing L9 architectural patterns.

## Rules Overview

| Rule ID                           | Severity | ADR      | Status                                   |
| --------------------------------- | -------- | -------- | ---------------------------------------- |
| `l9-no-datetime-utcnow`           | ERROR    | ADR-0083 | ✅ Clean                                 |
| `l9-httpx-async-context-required` | ERROR    | ADR-0084 | ✅ Clean (6 nosemgrep)                   |
| `l9-singleton-requires-lock`      | WARNING  | ADR-0085 | ⚠️ ~37 warnings (low priority)           |
| `l9-float-requires-try-except`    | WARNING  | ADR-0086 | ⚠️ ~32 warnings (mostly false positives) |
| `l9-no-eval`                      | ERROR    | ADR-0041 | ✅ Clean                                 |
| `l9-no-sql-fstring`               | ERROR    | ADR-0087 | ✅ Clean                                 |
| `l9-no-pickle-loads`              | ERROR    | ADR-0088 | ✅ Clean                                 |

**Note:** Warnings are technical debt tracking, not CI blockers.

## Running Locally

```bash
# Full scan
semgrep --config .semgrep/l9-rules.yaml api/ core/ services/ runtime/

# Single rule
semgrep --config .semgrep/l9-rules.yaml --include-rule l9-httpx-async-context-required api/
```

## Handling False Positives

### Step 1: Add nosemgrep comment

```python
# nosemgrep: rule-id (explanation of why this is safe)
code_that_triggers_rule()
```

### Step 2: Document in ADR

Update the corresponding ADR with:

- Pattern being suppressed
- File and line number
- Why it's safe

### Step 3: Keep line numbers updated

Line numbers in ADR documentation are approximate (`~`) since code changes.

## CI Integration

Runs in `.github/workflows/ci.yml` as `l9-patterns` job:

- Errors fail the build
- Warnings are reported but don't fail

## Adding New Rules

1. Add rule to `l9-rules.yaml`
2. Create corresponding ADR in `readme/adr/`
3. Test locally before committing
4. Update this README

## References

- [Semgrep Rule Syntax](https://semgrep.dev/docs/writing-rules/rule-syntax/)
- [nosemgrep Comments](https://semgrep.dev/docs/ignoring-files-folders-code/#ignore-code-through-comments)
