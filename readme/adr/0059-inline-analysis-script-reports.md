# ADR-0059: Inline Analysis with Script-Generated Reports

**Status:** Accepted  
**Date:** 2026-01-24  
**Decision Makers:** Igor  

## Context

The `/pr` command was generating GMP reports manually during analysis, which:
- Consumes tokens writing to files mid-conversation
- Creates reports before analysis is complete
- Duplicates information (inline chat + report file)
- Slows down the analysis workflow

## Decision

**Inline analysis, script-generated reports.**

### Principles

1. **Analysis is inline** — Present findings directly in chat/workspace during analysis
2. **Reports are on-demand** — Generate formatted reports only when explicitly requested
3. **Scripts handle formatting** — Use `scripts/workflow/generate_gmp_report.py` for consistent output
4. **Tokens are precious** — Don't write files when presenting inline suffices

### Workflow Change

**Before (Anti-Pattern):**
```
/pr #51 → Analyze → Write report file → Present in chat → User confirms → Done
```

**After (Correct):**
```
/pr #51 → Analyze → Present INLINE → User confirms → [Optional] Generate report via script
```

### When to Generate Reports

| Scenario | Generate Report? |
|----------|------------------|
| Quick PR analysis | ❌ No — inline summary sufficient |
| Complex multi-file PR | ⚠️ Optional — if user requests |
| Audit/compliance required | ✅ Yes — via script after completion |
| Historical record needed | ✅ Yes — via script after completion |

### Report Generation Command

```bash
# Generate GMP report for completed PR analysis
python3 scripts/workflow/generate_gmp_report.py \
  --pr 51 \
  --title "Spring Cleaning TODO Tracking" \
  --adopted 11 \
  --skipped 0 \
  --realigned 0 \
  --notes "23 TODOs tagged with GMP-100-122"
```

## Consequences

### Positive
- Faster PR analysis (no mid-analysis file writes)
- Lower token usage
- Reports only created when needed
- Consistent report formatting via script

### Negative
- Must run script separately if report needed
- Historical record requires explicit action

## Related

- `/pr` command: `.cursor-commands/commands/pr.md`
- Report generator: `scripts/workflow/generate_gmp_report.py`
- Workflow state: `scripts/workflow/update_workflow_state.py`
