# === DORA WORKFLOW COMMAND ===
# command: do-deploy
# version: 1.0.0
# purpose: Execute deployment workflow with DORA metrics tracking
# prefix: do-
# created: 2025-12-07

name: do-deploy
description: Walk through deployment process, track metrics, and verify success

# `/do-deploy` - Deploy Changes

**Structured deployment workflow with automatic DORA metrics tracking.**

---

## What This Command Does

1. Pre-deployment checks
2. Build verification
3. Deployment execution
4. Post-deployment validation
5. Metrics update

---

## Execution Instructions

When user runs `/do-deploy`:

### 1. Pre-Deployment Checklist

```markdown
# 🚀 Deployment Checklist

## Pre-Deploy Verification
- [ ] All tests passing? (run `pytest tests/`)
- [ ] Linting clean? (run `ruff check .`)
- [ ] Docker builds? (run `docker build -t app:test .`)
- [ ] Changes committed? (run `git status`)

Confirm ready to deploy? (yes/no)
```

### 2. Record Start Time

Store deployment start timestamp for lead time calculation.

### 3. Deployment Steps

Guide through deployment:

```markdown
## Deployment Steps

### Step 1: Build
```bash
docker build -t app:$(git rev-parse --short HEAD) .
```

### Step 2: Tag
```bash
docker tag app:$(git rev-parse --short HEAD) app:latest
```

### Step 3: Push (if using registry)
```bash
# docker push your-registry/app:latest
```

### Step 4: Deploy
```bash
docker-compose up -d
```

### Step 5: Verify
```bash
# Health check
curl http://localhost:8000/health || echo "Check your health endpoint"
```
```

### 4. Post-Deployment Validation

```markdown
## Post-Deploy Verification

- [ ] Application responding?
- [ ] Logs showing normal startup?
- [ ] No error spikes in monitoring?

**Deployment status:** (success/failed/rollback)
```

### 5. Update Metrics

Based on response, update `.dora/metrics.yaml`:

**On success:**
```yaml
deployments:
  total: +1
  successful: +1
  timestamps:
    - datetime: {ISO timestamp}
      status: success
      commit: {git SHA}

lead_time:
  samples:
    - {minutes from last commit to deploy complete}
```

**On failed:**
```yaml
deployments:
  total: +1
  failed: +1
  timestamps:
    - datetime: {ISO timestamp}
      status: failed
      commit: {git SHA}
      reason: {user-provided reason}
```

**On rollback:**
```yaml
mttr:
  incidents:
    - started: {failure timestamp}
      resolved: {rollback complete timestamp}
      duration_minutes: {calculated}
```

### 6. Output Summary

```markdown
## 📊 Deployment Complete

| Metric | Value |
|--------|-------|
| Status | {success/failed/rollback} |
| Commit | {git SHA} |
| Duration | {X minutes} |
| Total Deployments | {deployments.total} |

**Change Failure Rate:** {failed/total * 100}%

Next: `/do-metrics` for full DORA dashboard
```

---

## Quick Deploy (Skip Checklist)

For experienced users:
```
/do-deploy --quick
```

Skips interactive checklist, assumes pre-checks passed.

---

## Usage

```
/do-deploy
/do-deploy --quick
```

