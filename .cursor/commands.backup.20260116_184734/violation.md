---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "1.0.0"
component_id: "CMD-VIOLATION-001"
component_name: "Violation - Rule Breach Logger"
layer: "commands"
domain: "learning"
type: "slash_command"
status: "active"
created: "2025-12-01T00:00:00Z"
updated: "2026-01-02T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "critical"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === COMMAND METADATA ===
name: violation
description: "Log a lesson violation when Cursor breaks a learned rule"
aliases: ["/v"]
auto_chain: null
---

# === L9 VIOLATION: Log Lesson Violation ===
# Cursor Slash Command: /violation
# Version: 1.0.0 (L9-native)
# Updated: 2026-01-02

---

## WHAT IT DOES

**Logs a violation** when you (Cursor) break a rule from `repeated-mistakes.md`.

1. Records to local audit log
2. Syncs to MCP Memory for cross-session tracking
3. Triggers feedback loop for lesson reinforcement

---

## USAGE

```
/violation lesson-id "context description"
```

### Examples
```
/violation lesson-015 "Speculated without checking codebase"
/violation lesson-013 "Used hardcoded /Users/ib-mac/ path"
```

---

## EXECUTION PROTOCOL

### 1. ACKNOWLEDGE
```markdown
## 🔴 VIOLATION ACKNOWLEDGED
**Lesson:** [lesson-id] - [name]
**What happened:** [brief description]
```

### 2. LOG
```bash
python3 .cursor-commands/ops/scripts/violation_tracker.py \
  --lesson-id [lesson-id] \
  --context "[what happened]" \
  --severity critical
```

### 3. CORRECT
Apply the correct behavior immediately.

---

## LESSON ID QUICK REFERENCE

| ID | Lesson |
|----|--------|
| lesson-001 | Data Fabrication |
| lesson-004 | Proof Required |
| lesson-005 | Search First |
| lesson-010 | Read Rules First |
| lesson-011 | Proactive Execution |
| lesson-012 | Dropbox Not Library |
| lesson-013 | Use $HOME Variable |
| lesson-014 | Root docker-compose |
| lesson-015 | Investigate First |

---

## AUTO-DETECTION

```bash
python3 .cursor-commands/ops/scripts/violation_tracker.py --detect-text "may not be fully implemented"
python3 .cursor-commands/ops/scripts/violation_tracker.py --stats
```

---

## FILES

| File | Purpose |
|------|---------|
| `repeated-mistakes.md` | Lesson database |
| `violations.jsonl` | Violation log |
| `violation_tracker.py` | Python tracker |

---

## ANTI-PATTERNS

❌ Ignore user calling out mistake
❌ Make excuses instead of correcting

✅ Acknowledge immediately
✅ Log every violation
✅ Apply correction right away
