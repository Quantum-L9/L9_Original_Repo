# === DORA WORKFLOW COMMAND ===
# command: do-metrics
# version: 1.0.0
# purpose: Display DORA metrics dashboard
# prefix: do-
# created: 2025-12-07

name: do-metrics
description: Show comprehensive DORA metrics with performance assessment

# `/do-metrics` - DORA Metrics Dashboard

**View your DORA performance metrics and identify improvement areas.**

---

## What This Command Does

1. Reads `.dora/metrics.yaml`
2. Calculates derived metrics
3. Assesses performance level
4. Provides improvement recommendations

---

## DORA Performance Levels

| Level | Deploy Freq | Lead Time | Change Fail Rate | MTTR |
|-------|-------------|-----------|------------------|------|
| Elite | Multiple/day | <1 hour | <5% | <1 hour |
| High | Weekly-daily | 1 day-1 week | 6-15% | <1 day |
| Medium | Monthly-weekly | 1 week-1 month | 16-30% | 1 day-1 week |
| Low | Monthly+ | 1 month+ | >30% | 1 week+ |

---

## Execution Instructions

When user runs `/do-metrics`:

### 1. Load Metrics

Read `.dora/metrics.yaml` and calculate:

```python
# Deployment Frequency
if deployments.total == 0:
    deploy_freq = "No deployments yet"
else:
    days_active = (now - project.created).days or 1
    deploys_per_day = deployments.total / days_active
    
    if deploys_per_day >= 1:
        deploy_freq = f"{deploys_per_day:.1f}/day"
    elif deploys_per_day >= 0.14:  # ~1/week
        deploy_freq = f"{deploys_per_day * 7:.1f}/week"
    else:
        deploy_freq = f"{deploys_per_day * 30:.1f}/month"

# Lead Time (average)
if lead_time.samples:
    avg_lead_time = sum(lead_time.samples) / len(lead_time.samples)
else:
    avg_lead_time = None

# Change Failure Rate
if deployments.total > 0:
    cfr = (deployments.failed / deployments.total) * 100
else:
    cfr = None

# MTTR
if mttr.incidents:
    avg_mttr = sum(i.duration_minutes for i in mttr.incidents) / len(mttr.incidents)
else:
    avg_mttr = None
```

### 2. Assess Performance Level

```python
def assess_level(metric, value):
    thresholds = {
        'deploy_freq': [(1, 'Elite'), (0.14, 'High'), (0.03, 'Medium')],
        'lead_time': [(60, 'Elite'), (1440, 'High'), (10080, 'Medium')],  # minutes
        'cfr': [(5, 'Elite'), (15, 'High'), (30, 'Medium')],
        'mttr': [(60, 'Elite'), (1440, 'High'), (10080, 'Medium')],  # minutes
    }
    # Return level based on thresholds
```

### 3. Output Dashboard

```markdown
# 📈 DORA Metrics Dashboard

## Current Performance

| Metric | Value | Level | Target |
|--------|-------|-------|--------|
| **Deployment Frequency** | {deploy_freq} | {level} | Daily+ |
| **Lead Time for Changes** | {avg_lead_time or "N/A"} | {level} | <1 hour |
| **Change Failure Rate** | {cfr or "N/A"}% | {level} | <5% |
| **Mean Time to Recovery** | {avg_mttr or "N/A"} | {level} | <1 hour |

## Overall Assessment

**Current Level: {overall_level}**

```
Elite  ████████░░  {if elite}
High   ████████░░  {if high}
Medium ████████░░  {if medium}
Low    ████████░░  {if low}
```

## Trend (Last 5 Deployments)

| Date | Status | Lead Time |
|------|--------|-----------|
{for each in last 5 deployments}
| {date} | {status} | {lead_time} |
{end for}

## Recommendations

{Based on weakest metric}

### To Improve {weakest_metric}:

1. {recommendation_1}
2. {recommendation_2}
3. {recommendation_3}

---

**Data Period:** {project.created} to {now}
**Last Updated:** {metrics.last_updated}
```

### 4. Improvement Recommendations

**Low Deployment Frequency:**
- Reduce batch sizes
- Automate deployment pipeline
- Implement trunk-based development

**High Lead Time:**
- Streamline code review process
- Parallelize CI/CD stages
- Reduce manual approval gates

**High Change Failure Rate:**
- Increase test coverage
- Implement canary deployments
- Add pre-deploy validation

**High MTTR:**
- Improve monitoring and alerting
- Create runbooks for common issues
- Implement automated rollback

---

## Usage

```
/do-metrics
/do-metrics --detail    # Show all historical data
/do-metrics --export    # Export to markdown file
```

