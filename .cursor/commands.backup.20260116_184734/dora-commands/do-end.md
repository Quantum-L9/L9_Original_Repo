# === DORA WORKFLOW COMMAND ===
# command: do-end
# version: 1.0.0
# purpose: End session with progress logging and state update
# prefix: do-
# created: 2025-12-07

name: do-end
description: Log session accomplishments, update state, and prepare for next session

# `/do-end` - End Session

**Log what you accomplished and prepare handoff for next session.**

---

## What This Command Does

1. Prompts for session summary
2. Appends to session log
3. Updates state file
4. Shows handoff summary

---

## Execution Instructions

When user runs `/do-end`:

### 1. Gather Session Summary

```markdown
# 📝 End of Session

## What did you accomplish this session?
(Brief summary - 1-3 sentences)

> 
```

Wait for user input.

### 2. Check for Blockers

```markdown
## Any blockers or issues to flag?
(Enter blockers or "none")

> 
```

### 3. Note Next Priority

```markdown
## What should be tackled next session?
(Optional - leave blank to auto-determine via /do-next)

> 
```

### 4. Update Session Log

Append to `.dora/session-log.md`:

```markdown
---

## Session: {date} {time}

**Duration:** {session_duration or "Not tracked"}
**Phase:** {phase.current} - {phase.name}

### Accomplished
{user_summary}

### Tasks Completed
{list from progress.completed_items added this session}

### Blockers
{blockers or "None"}

### Next Priority
{next_priority or "To be determined"}

---
```

### 5. Update State

Update `.dora/state.yaml`:
- `session.last_active`: Current ISO timestamp
- `session.total_sessions`: +1
- `progress.blockers`: Add any new blockers

### 6. Output Handoff Summary

```markdown
# ✅ Session Logged

## Summary
- **Session #{session.total_sessions}**
- **Phase:** {phase.current}/10 - {phase.name}
- **Tasks Completed This Session:** {count}
- **Total Progress:** {total_completed}/{total_tasks} items

## State Saved
Your progress has been saved to `.dora/state.yaml`

## Next Session
Run `/do-status` to recover context instantly.

---

**See you next time! 👋**
```

---

## Quick End (No Prompts)

For quick session close:
```
/do-end "Completed CI/CD setup and first deployment"
```

Skips interactive prompts, uses provided summary.

---

## Usage

```
/do-end
/do-end "Brief summary of what was done"
```

