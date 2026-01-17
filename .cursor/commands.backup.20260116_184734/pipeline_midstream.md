---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "7.0.0"
component_id: "CMD-PIPELINEMID-001"
component_name: "Pipeline-Midstream - Recalibration"
layer: "commands"
domain: "pipeline"
type: "slash_command"
status: "active"
created: "2025-12-01T00:00:00Z"
updated: "2026-01-01T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "operational"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === COMMAND METADATA ===
name: pipeline-midstream
description: "L9 midstream recalibration — realign, clean, accelerate when context grows too large"
memory_inject: true            # INJECT: Search VPS memory for preferences/lessons before execution
before_chain: extract-chat   # EXTRACT: Write learnings to VPS memory
auto_chain: ynp
---

# === L9 PIPELINE-MIDSTREAM: Project Recalibration ===
# Cursor Slash Command: /pipeline-midstream
# Version: 7.0.0 (L9-native)
# Updated: 2026-01-01

---

## ⛓️ AUTO-CHAINS TO /ynp

After recalibration, **automatically runs /ynp** to recommend next highest-leverage action.

---

## WHAT IT DOES

**Three-stage project recalibration pipeline:**

1. **Stage 1: `/analyze+evaluate`** — Current state analysis + health scoring
2. **Stage 2: `/clean+compress`** — Remove noise, extract core insights
3. **Stage 3: `/ynp`** — Single highest-leverage next move

**Key principle:** Prevent drift and complexity buildup mid-flight. Recalibrate often.

---

## WHEN TO USE

### ✅ USE /pipeline-midstream WHEN:

| Trigger | Signs | Why It Helps |
|---------|-------|--------------|
| **Time-based** | 2-3 days since last recalibration | Prevents accumulated drift |
| **Context overload** | workflow_state.md > 300 lines | Compresses to essentials |
| **Feeling lost** | "What was I working on?" | Re-establishes clarity |
| **Too many TODOs** | 10+ active items, unclear priority | Reprioritizes ruthlessly |
| **Return from break** | 24+ hours since last session | Restores working memory |
| **Before big change** | About to start major feature | Clean slate, clear focus |
| **Post-GMP chain** | Just finished 3+ GMPs | Consolidate gains, plan next |
| **Energy dip** | Productive but scattered | Refocuses on highest leverage |

### ❌ DON'T USE WHEN:

| Situation | Use Instead |
|-----------|-------------|
| About to commit | `/pipeline-precommit` |
| New to code | `/analyze` |
| Need deep audit | `/evaluate` |
| Ready to build | `/forge` |
| Just need next step | `/ynp` |

### 📊 Recalibration Frequency Guide

| Work Intensity | Recalibrate Every |
|----------------|-------------------|
| Full-time focused (8+ hrs/day) | Every 2 days |
| Part-time work (4 hrs/day) | Every 3-4 days |
| Intermittent (1-2 hrs/day) | Weekly |
| After any break > 24 hours | Immediately on return |

---

## EXECUTION PROTOCOL

### Stage 1: ANALYZE + EVALUATE

```
1. Read workflow_state.md
2. Analyze current project state
3. Evaluate health across tiers
4. Identify bottlenecks and blockers
5. Calculate progress metrics
```

**Output:**
- Current phase and priority
- Health scores by tier
- Bottlenecks identified
- Progress vs goals

### Stage 2: CLEAN + COMPRESS

```
1. Identify noise in context:
   - Stale TODOs
   - Completed but not closed items
   - Orphan artifacts
   - Redundant notes
   
2. Compress insights:
   - Extract key decisions
   - Summarize completed work
   - Clarify remaining work
   
3. Update workflow_state.md:
   - Clean recent changes
   - Update next steps
   - Refresh priority queue
```

**Output:**
- Cleaned workflow_state.md
- Compressed context pack
- Clear priority queue

### Stage 3: YNP (Your Next Play)

```
Based on recalibrated state:
1. Identify single highest-leverage action
2. Consider batch opportunities
3. Recommend concrete next step
4. Suggest timeline
```

---

## OUTPUT FORMAT

```markdown
## 🔄 MIDSTREAM RECALIBRATION

### 📍 Stage 1: Current State Analysis

**Phase:** [current phase]
**Priority Tier:** [🔴/🟠/🟡/🔵]
**Days Since Last Recalibration:** [N]

| Area | Health | Trend |
|------|--------|-------|
| Core Runtime | 85% | ↗️ Improving |
| API Layer | 78% | → Stable |
| Memory Substrate | 92% | ↗️ Improving |
| Orchestration | 65% | ↘️ Needs attention |
| Tests | 55% | → Stable |

**Bottlenecks Identified:**
1. 🔴 Orchestration wiring incomplete (blocking 3 downstream tasks)
2. 🟡 Test coverage below target (not blocking but accumulating)

**Progress:**
- GMPs Completed: 11/16
- Files Modified: 45
- TODOs Resolved: 23

---

### 🧹 Stage 2: Clean + Compress

**Noise Removed:**
- Closed 5 stale TODOs
- Archived 3 completed GMP reports
- Removed 2 duplicate notes

**Context Compressed:**
```yaml
current_focus: "Wire orchestrators to executor"
completed_recently:
  - GMP-11: Igor commands
  - API routes refactor
  - Memory substrate tests
blocking_issues:
  - Orchestration wiring incomplete
next_priority:
  - Complete Wire-Orchestrators GMP
  - Add integration tests
```

**workflow_state.md Updated:**
- Recent changes: Compressed to last 5
- Next steps: Reprioritized
- Open questions: 2 resolved, 1 new

---

### 🎯 Stage 3: YNP (Your Next Play)

**Primary:** Complete Wire-Orchestrators GMP (unblocks 3 downstream tasks)

**Why:** Highest cascade effect — blocking task router, command pipeline, and agent dispatch

**Scope:** 
- Files: orchestration/task_router.py, core/agents/executor.py
- Tier: RUNTIME_TIER
- Estimated: 2-3 hours

**Batch Opportunity:**
Chain with integration tests (same scope) for single focused session

**Timeline:**
- Today: Complete wiring
- Tomorrow: Integration tests + deploy prep

---

### 📊 Recalibration Metrics

| Metric | Before | After |
|--------|--------|-------|
| Active TODOs | 15 | 8 |
| Stale Items | 5 | 0 |
| Context Size | 2500 tokens | 1200 tokens |
| Priority Clarity | Medium | High |
```

---

## USAGE

### Standard Recalibration
```
/pipeline-midstream

Full 3-stage recalibration of current project state.
```

### Target Focus
```
/pipeline-midstream @core/

Focus recalibration on specific area.
```

### Quick Check
```
/pipeline-midstream --quick

Just state check + YNP, skip deep cleaning.
```

### Deep Clean
```
/pipeline-midstream --deep

More aggressive noise removal, archive old items.
```

---

## RECALIBRATION TRIGGERS

### Automatic Triggers (When to Run)

| Trigger | When |
|---------|------|
| **Time-based** | Every 2-3 days of active work |
| **Context growth** | workflow_state.md > 500 lines |
| **Drift feeling** | "What was I working on?" |
| **Phase transition** | Moving from one GMP to next |
| **Return from break** | After 24+ hours away |

### Warning Signs (Need Recalibration)

- TODOs accumulating without resolution
- Recent changes section growing long
- Open questions not getting answered
- Multiple GMP runs without clear progress
- Uncertainty about next step

---

## CLEANING RULES

### What Gets Cleaned

| Item | Action |
|------|--------|
| Completed TODOs | Archive with completion date |
| Stale TODOs (> 7 days no progress) | Flag for decision: complete or cancel |
| Duplicate notes | Merge into single entry |
| Resolved questions | Move to decision log |
| Outdated next steps | Remove or update |

### What Gets Preserved

| Item | Why |
|------|-----|
| Active blockers | Still relevant |
| Recent decisions | Context for future |
| Current phase | Essential state |
| Priority queue | Guides work |

---

## COMPRESSION PATTERNS

### Before (Noisy)
```markdown
## Recent Changes
- Fixed bug in executor
- Added logging
- Removed old code
- Fixed another bug
- Added more logging
- Refactored slightly
- Fixed import issue
- Added test
- Fixed test
- Updated docs
```

### After (Compressed)
```markdown
## Recent Changes
- GMP-11: Igor commands complete (executor, logging, tests)
- API cleanup: Removed deprecated routes
- Docs: Updated for new API
```

---

## FLAGS & OPTIONS

| Flag | Description | Default |
|------|-------------|---------|
| `--quick` | Skip deep clean, just state + YNP | false |
| `--deep` | Aggressive cleaning | false |
| `--archive` | Archive resolved items to file | false |
| `--json` | Output as JSON | false |

---

## INTEGRATION

- **Run after:** Long work sessions, before major changes
- **Chains to:** `/ynp` (always), `/gmp` (if action needed)
- **Updates:** `workflow_state.md` with cleaned state
- **Feeds into:** `/forge` or `/gmp` for next action

---

## ANTI-PATTERNS

❌ **DON'T:** Skip recalibration for weeks
❌ **DON'T:** Let workflow_state.md grow unbounded
❌ **DON'T:** Ignore bottlenecks
❌ **DON'T:** Keep stale TODOs "just in case"

✅ **DO:** Recalibrate every 2-3 days
✅ **DO:** Clean aggressively
✅ **DO:** Update workflow_state.md
✅ **DO:** Act on the YNP recommendation

---

## EXAMPLES

### Example 1: Regular Checkpoint
```
/pipeline-midstream

🔄 MIDSTREAM RECALIBRATION

📍 Current State:
- Phase: 2 (Implementation)
- Health: 82% overall
- Bottleneck: 1 (test coverage)

🧹 Cleaned:
- 3 stale TODOs archived
- Recent changes compressed

🎯 YNP: Continue with current GMP (on track)
```

### Example 2: Feeling Lost
```
/pipeline-midstream

🔄 MIDSTREAM RECALIBRATION

📍 Current State:
- Phase: 2 (Implementation)
- Health: 65% overall
- Bottlenecks: 3 (wiring, tests, docs)

⚠️ Drift Detected:
- 5 TODOs > 7 days old
- Context grown to 2500 tokens
- Last recalibration: 8 days ago

🧹 Deep Clean Applied:
- Archived 5 stale items
- Compressed context by 60%
- Clarified priority queue

🎯 YNP: Focus on Wire-Orchestrators (highest cascade)
```

### Example 3: Quick Check
```
/pipeline-midstream --quick

🔄 QUICK RECALIBRATION

📍 State: Phase 2, 🟠 HIGH priority
📊 Health: 78% overall
🎯 YNP: Continue GMP-14 (2 TODOs remaining)
```
