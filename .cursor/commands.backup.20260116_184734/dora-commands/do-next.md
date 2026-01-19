# === DORA WORKFLOW COMMAND ===
# command: do-next
# version: 1.0.0
# purpose: Get the next task based on DORA Checklist and current state
# prefix: do-
# created: 2025-12-07

name: do-next
description: Determine and present the next task from DORA Checklist based on current phase and progress

# `/do-next` - What's Next?

**Picks the right next task from your DORA Checklist. No guessing.**

---

## What This Command Does

1. Reads current phase from `.dora/state.yaml`
2. Checks completed items
3. Selects next uncompleted task from DORA Checklist
4. Presents task with context and guidance
5. On completion, updates state

---

## DORA Checklist Reference

The command uses the DORA Checklist phases:

| Phase | Name | Weeks |
|-------|------|-------|
| 1 | Foundation and Planning | 1-4 |
| 2 | Infrastructure and Tooling Setup | 5-8 |
| 3 | Data Management and Quality | 9-12 |
| 4 | Model Development and Training | 13-16 |
| 5 | Model Deployment and Serving | 17-20 |
| 6 | AI Agent Development | 21-24 |
| 7 | Security and Compliance | 25-28 |
| 8 | Production Operations | 29-32 |
| 9 | DORA Metrics Tracking and Optimization | 33-36 |
| 10 | Advanced Capabilities and Scaling | 37-52 |

---

## Execution Instructions

When user runs `/do-next`:

### 1. Load State

Read `.dora/state.yaml`:
- Current phase
- Completed items list
- Current task (if any)
- Blockers

### 2. Determine Next Task

Logic:
```
IF current_task is not null AND not in completed_items:
    → Return current_task (resume)
ELSE:
    → Find first uncompleted item in current phase
    → If phase complete, advance to next phase
    → Set as current_task
```

### 3. Present Task

```markdown
# 🎯 Next Task

## Phase {phase.current}: {phase.name}

### Task
{task_description}

### Why This Matters
{brief explanation of DORA alignment}

### Suggested Actions
1. {action_1}
2. {action_2}
3. {action_3}

### Completion Criteria
- [ ] {criterion_1}
- [ ] {criterion_2}

---

When done, say "done" or "complete" and I'll mark it and get your next task.
To skip: say "skip" with reason.
To block: say "blocked" with blocker description.
```

### 4. Handle Responses

**On "done" / "complete":**
- Add task to `progress.completed_items`
- Set `progress.current_task` to null
- Update `session.last_active`
- Automatically run `/do-next` again

**On "skip [reason]":**
- Log skip in session-log.md
- Move to next task
- Do NOT add to completed_items

**On "blocked [description]":**
- Add to `progress.blockers`
- Move to next task
- Flag for review in `/do-status`

---

## Phase 1 Task Examples

For initial setup, Phase 1 tasks include:

1. Establish project objectives and success criteria
2. Define team roles (you + AI agent + assistant)
3. Document baseline metrics approach
4. Set up version control (Git initialized)
5. Create initial project structure
6. Define coding standards
7. Set up communication protocols

---

## Usage

```
/do-next
```

After completing task:
```
done
```
or
```
complete - finished setting up CI/CD pipeline
```

