# === DORA WORKFLOW COMMAND ===
# command: do-status
# version: 1.0.0
# purpose: Show current project state and context
# prefix: do-
# created: 2025-12-07

name: do-status
description: Display current project state, phase, progress, and session context

# `/do-status` - Where Am I?

**Run at session start or anytime to recover context instantly.**

---

## What This Command Does

1. Reads `.dora/state.yaml`
2. Reads `.dora/metrics.yaml`
3. Shows recent entries from `.dora/session-log.md`
4. Outputs formatted status report

---

## Execution Instructions

When user runs `/do-status`:

### 1. Read State Files

Load and parse:
- `.dora/state.yaml`
- `.dora/metrics.yaml`
- Last 3 entries from `.dora/session-log.md`

### 2. Output Status Report

```markdown
# 📊 DORA Project Status

## Project
- **Name:** {project.name}
- **Created:** {project.created}
- **Total Sessions:** {session.total_sessions}

## Current Phase
- **Phase {phase.current}/10:** {phase.name}
- **Current Task:** {progress.current_task or "None assigned"}

## Progress
- **Completed Items:** {len(progress.completed_items)}
- **Blockers:** {progress.blockers or "None"}

## DORA Metrics
| Metric | Value |
|--------|-------|
| Deployments | {deployments.total} ({deployments.successful} ✓ / {deployments.failed} ✗) |
| Avg Lead Time | {lead_time.average or "No data"} |
| Change Failure Rate | {change_failure_rate.calculated or "No data"} |
| Avg MTTR | {mttr.average or "No data"} |

## Recent Sessions
{last 3 session log entries}

## Quick Actions
- `/do-next` → Get next task
- `/do-deploy` → Deploy changes
- `/do-metrics` → Detailed metrics
- `/do-end` → End session
```

### 3. Update State

Update `.dora/state.yaml`:
- `session.last_active`: Current ISO timestamp

---

## Error Handling

If `.dora/` directory doesn't exist:
```
⚠️ DORA not initialized

Run /do-init first to set up project structure.
```

---

## Usage

```
/do-status
```

**Tip:** Run this at the start of every session to recover context.

