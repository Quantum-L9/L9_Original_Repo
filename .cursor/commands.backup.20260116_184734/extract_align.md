---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "7.0.0"
component_id: "CMD-EXTRACTALIGN-001"
component_name: "Extract+Align - Insight Mining"
layer: "commands"
domain: "extraction"
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
name: extract+align
description: "L9-native insight extraction — mine decisions, rules, patterns and align with governance"
memory_inject: true            # INJECT: Search VPS memory for preferences/lessons before execution
before_chain: extract-chat   # EXTRACT: Write learnings to VPS memory
auto_chain: ynp
---

# === L9 EXTRACT+ALIGN: Insight Mining & Governance Alignment ===
# Cursor Slash Command: /extract+align
# Version: 7.0.0 (L9-native)
# Updated: 2026-01-01

---

## ⛓️ AUTO-CHAINS TO /ynp

After extraction, **automatically runs /ynp** to recommend /harvest, /consolidate, or governance update.

---

## WHAT IT DOES

**Two-phase knowledge mining:**

1. **EXTRACT** — Pull high-value insights from text (decisions, rules, preferences, patterns)
2. **ALIGN** — Validate against L9 governance and reformat for integration

**Output:** Structured, governance-aligned insights ready for L9 memory or kernels.

**Key principle:** Raw text → Structured knowledge → Governed integration.

---

## WHEN TO USE

| Scenario | Why /extract+align |
|----------|-------------------|
| After long chats | Extract decisions buried in conversation |
| Mining legacy prompts | Convert old prompts to L9 format |
| Before kernel updates | Extract patterns that should become rules |
| Knowledge base building | Structured extraction for memory substrate |
| Onboarding new context | Align external info with L9 governance |

---

## EXECUTION PROTOCOL

### Phase 1: EXTRACT

Mine 6 categories of high-value information:

```
EXTRACTION CATEGORIES:
├── DECISIONS
│   ├── Architectural choices
│   ├── Technology selections
│   ├── Process decisions
│   └── Tradeoff resolutions
├── RULES
│   ├── Constraints
│   ├── Policies
│   ├── Requirements
│   └── Prohibitions
├── PREFERENCES
│   ├── Style choices
│   ├── Tool preferences
│   ├── Communication patterns
│   └── Workflow preferences
├── IDENTITY MARKERS
│   ├── L's capabilities
│   ├── L's constraints
│   ├── Igor's expectations
│   └── Relationship dynamics
├── PATTERNS
│   ├── Repeated behaviors
│   ├── Trigger → action mappings
│   ├── Error handling patterns
│   └── Success patterns
└── ACTIONS
    ├── TODOs
    ├── Commitments
    ├── Follow-ups
    └── Blockers
```

### Phase 2: ALIGN

Validate and format for L9 integration:

```
ALIGNMENT CHECKS:
├── Governance Consistency
│   ├── Does this contradict existing kernels?
│   ├── Does this align with safety constraints?
│   └── Is authority hierarchy respected?
├── Format Compliance
│   ├── L9 naming conventions
│   ├── Proper categorization
│   └── Required metadata present
├── Integration Readiness
│   ├── Target location identified
│   ├── Dependencies resolved
│   └── Conflicts flagged
└── Priority Classification
    ├── CRITICAL: Affects safety/governance
    ├── HIGH: Affects behavior
    ├── MEDIUM: Affects preferences
    └── LOW: Nice-to-have
```

---

## OUTPUT FORMAT

```markdown
## 🔍 EXTRACT+ALIGN OUTPUT

### 📊 Extraction Summary
- **Source:** [file/chat name]
- **Insights Found:** [count]
- **Alignment Issues:** [count]
- **Ready for Integration:** [count]

---

### 📋 EXTRACTED INSIGHTS

#### 🎯 Decisions
| ID | Decision | Rationale | Status |
|----|----------|-----------|--------|
| D1 | [decision] | [why] | ✅ Aligned |
| D2 | [decision] | [why] | ⚠️ Review |

#### 📏 Rules
| ID | Rule | Scope | Priority |
|----|------|-------|----------|
| R1 | [rule] | [where applies] | 🔴 CRITICAL |
| R2 | [rule] | [where applies] | 🟡 MEDIUM |

#### 💡 Preferences
| Key | Value | Source |
|-----|-------|--------|
| [pref] | [value] | [where found] |

#### 🆔 Identity Markers
- **L's Role:** [description]
- **Igor's Expectations:** [description]
- **Relationship:** [dynamics]

#### 🔄 Patterns
| Pattern Name | Trigger | Behavior |
|--------------|---------|----------|
| [NAME] | [when] | [what happens] |

#### ✅ Actions
| ID | Action | Owner | Priority |
|----|--------|-------|----------|
| A1 | [action] | [who] | [priority] |

---

### ⚠️ ALIGNMENT ISSUES

| # | Issue | Insight | Resolution |
|---|-------|---------|------------|
| 1 | [issue type] | [which insight] | [how to fix] |

---

### 🔌 INTEGRATION TARGETS

| Insight | Target Location | Action Needed |
|---------|-----------------|---------------|
| R1 | kernels/08-safety-kernel.yaml | Add constraint |
| D1 | workflow_state.md decision log | Record |
| P1 | Agent memory substrate | Store preference |

---

### 🎯 YNP (Your Next Play)
**Primary:** [Recommended action with extracted insights]
**Batch Opportunity:** [Related actions if applicable]
```

---

## USAGE

### Standard Extract+Align
```
/extract+align @long_chat.md

Extracts insights and aligns with L9 governance.
```

### Focus on Specific Category
```
/extract+align @chat.md --focus decisions
/extract+align @chat.md --focus rules
/extract+align @chat.md --focus patterns
```

### From Multiple Sources
```
/extract+align @chat1.md @chat2.md @doc.md

Extracts from all, deduplicates, aligns.
```

### Dry Run (Extraction Only)
```
/extract+align @chat.md --extract-only

Skip alignment, just show what would be extracted.
```

---

## L9-SPECIFIC EXTRACTION

### Priority Extraction Targets

```yaml
# Always extract these L9-critical items:
l9_priority_targets:
  - Igor decisions about L's behavior
  - Approval gate requirements
  - Safety constraints
  - Memory substrate patterns
  - Kernel configuration hints
  - Tool permission rules
  - Escalation triggers
```

### Governance Alignment Checks

| Check | Pass | Fail Action |
|-------|------|-------------|
| Safety constraint respected | ✅ | 🔴 Flag for Igor review |
| Authority hierarchy intact | ✅ | 🔴 Restructure insight |
| Kernel consistency | ✅ | ⚠️ Note potential update |
| Memory pattern compliance | ✅ | ⚠️ Suggest format change |

---

## EXTRACTION PATTERNS

### Decision Extraction

```
Look for:
- "We decided to..."
- "Going with..."
- "Choosing X over Y because..."
- "The approach will be..."
- Igor's explicit approvals

Extract:
- Decision statement
- Rationale
- Alternatives considered
- Date/context
```

### Rule Extraction

```
Look for:
- "Always..."
- "Never..."
- "Must..."
- "Should not..."
- Imperative statements

Extract:
- Rule statement
- Scope (when applies)
- Priority (CRITICAL/HIGH/MEDIUM/LOW)
- Source
```

### Pattern Extraction

```
Look for:
- Repeated behaviors
- "When X, do Y"
- Error handling descriptions
- Success criteria

Extract:
- Pattern name
- Trigger condition
- Expected behavior
- Examples
```

---

## INTEGRATION WORKFLOW

```
/extract+align @source.md
  ↓
Review extracted insights
  ↓
/harvest (if files to extract too)
  ↓
/wire (if kernel updates needed)
  ↓
Update workflow_state.md decision log
  ↓
/ynp for next action
```

---

## EXAMPLES

### Example 1: Chat Mining

**Input:** 500-line deployment discussion

**Output:**
```
## Extracted Insights

### Decisions
- D1: Use Caddy for reverse proxy (simpler than nginx)
- D2: Cloudflare for DNS/SSL (already have account)
- D3: Docker Compose on VPS (not K8s, overkill)

### Rules
- R1: Never expose MCP server directly (always via Caddy)
- R2: All API calls through /api/v1/* path

### Patterns
- DEPLOY_CHECKLIST: PR → Tests → Merge → Docker build → Deploy
- ROLLBACK_TRIGGER: Any 5xx errors → immediate rollback

### Integration Targets
- D1, D2, D3 → workflow_state.md decision log
- R1 → deployment manifest
- DEPLOY_CHECKLIST → CI/CD docs
```

### Example 2: Legacy Prompt Mining

**Input:** Old system prompt from previous project

**Output:**
```
## Extracted Insights

### Identity Markers
- L is CTO-level AI assistant
- Igor has final approval on all high-risk operations
- L should escalate uncertainty, not guess

### Rules (Align with current kernels)
- R1: No silent partial work ✅ Already in 08-safety-kernel
- R2: Explicit failure semantics ✅ Already in 08-safety-kernel
- R3: Audit-first logging ⚠️ Add to governance

### Preferences
- YAML over JSON for configs
- Minimal dependencies
- Type hints everywhere
```

---

## ANTI-PATTERNS

❌ **DON'T:** Extract vague or ambiguous statements
❌ **DON'T:** Skip alignment phase
❌ **DON'T:** Extract contradictions without flagging
❌ **DON'T:** Lose source context for decisions

✅ **DO:** Be aggressive on rule extraction
✅ **DO:** Flag all governance conflicts
✅ **DO:** Link insights to integration targets
✅ **DO:** Preserve decision rationales

