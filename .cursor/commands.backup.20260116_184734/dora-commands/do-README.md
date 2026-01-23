# DORA Workflow Commands (`do-*`)

> DORA-aligned project management commands for Cursor

## Quick Reference

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `/do-init` | Initialize project structure | Once, at project start |
| `/do-status` | Show current state & context | Every session start |
| `/do-next` | Get next task from DORA Checklist | When unsure what to do |
| `/do-deploy` | Execute deployment workflow | When shipping changes |
| `/do-metrics` | View DORA metrics dashboard | Weekly review |
| `/do-end` | Log session & prepare handoff | End of every session |

## Typical Session Flow

```
┌─────────────────────────────────────────────────────┐
│  START SESSION                                      │
│  └─▶ /do-status (recover context)                   │
│       └─▶ /do-next (get task)                       │
│            └─▶ [do the work]                        │
│                 └─▶ "done" (mark complete)          │
│                      └─▶ /do-next (repeat)          │
│                           └─▶ /do-deploy (if ready) │
│                                └─▶ /do-end          │
│  END SESSION                                        │
└─────────────────────────────────────────────────────┘
```

## File Structure Created by `/do-init`

```
project/
├── .dora/
│   ├── state.yaml      ← Auto-tracked project state
│   ├── metrics.yaml    ← Auto-tracked DORA metrics
│   └── session-log.md  ← Auto-appended session history
├── .github/workflows/
│   └── ci-cd.yaml      ← GitHub Actions pipeline
├── src/
│   ├── __init__.py
│   └── main.py
├── tests/
│   └── test_example.py
├── docker-compose.yaml
├── Dockerfile
├── pyproject.toml
├── .pre-commit-config.yaml
└── README.md
```

## DORA Metrics Tracked

| Metric | What It Measures | Elite Target |
|--------|------------------|--------------|
| **Deployment Frequency** | How often you deploy | Multiple/day |
| **Lead Time** | Commit → Production | <1 hour |
| **Change Failure Rate** | % deployments causing failures | <5% |
| **MTTR** | Time to recover from failure | <1 hour |

## Templates Location

All templates are in `.cursor/commands/do-templates/`

These are copied to your project when you run `/do-init`.

## Version

- **Version:** 1.0.0
- **Created:** 2025-12-07
- **Prefix:** `do-`

