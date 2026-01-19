---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "7.1.0"
component_id: "CMD-EXTRACTCHAT-001"
component_name: "Extract-Chat - Chat Transcript Extraction"
layer: "commands"
domain: "memory"
type: "slash_command"
status: "active"
created: "2025-12-01T00:00:00Z"
updated: "2026-01-07T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "operational"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === COMMAND METADATA ===
name: extract-chat
description: "L9-native chat extraction — pull insights, files, decisions from chat transcripts"
auto_chain: ynp
aliases: ["extract-memory"]  # Legacy alias for backwards compatibility
---

# === L9 EXTRACT-CHAT: Chat Transcript Extraction ===
# Cursor Slash Command: /extract-chat
# Version: 7.1.0 (L9-native)
# Updated: 2026-01-07
# Renamed from: /extract-memory (to differentiate from /mem)

---

## ⛓️ AUTO-CHAINS TO /ynp

After extraction, **automatically runs /ynp** to recommend /wire, /forge, or further processing.

---

## WHAT IT DOES

**Extracts semantic insights and file artifacts from chat transcripts:**

1. **File Extraction** — Code blocks, configs, scripts, migrations
2. **Insight Mining** — Strategic decisions, tactical preferences, learnings
3. **Iterative Scanning** — Multiple passes until complete
4. **Quality Validation** — 6 governance checkpoints
5. **Output Generation** — Organized files + YAML manifest

**Key principle:** Chat history = untapped knowledge. Extract everything useful in one pass.

---

## EXECUTION PROTOCOL

### Step 0: STATE_SYNC

```
1. Glance at workflow_state.md
2. Note current context
3. Identify extraction scope
```

### Step 1: PRE-PROCESSING

```
1. Parse chat file(s)
2. Segment into logical sections
3. Identify: Technical chat vs planning vs debugging
4. Calculate extraction complexity
```

### Step 2: FILE EXTRACTION (Pattern-Based)

Scan for extractable artifacts:

```
ARTIFACT TYPES:
├── CODE_BLOCK: ```python, ```sql, ```yaml, etc.
├── CONFIG: Settings, env vars, docker-compose fragments
├── SCRIPT: Executable scripts (sh, py, js)
├── MIGRATION: SQL DDL statements
├── SCHEMA: Data models, Pydantic classes
├── PROMPT: AI prompts, system instructions
└── TEMPLATE: Jinja2, string templates
```

### Step 3: INSIGHT EXTRACTION (L9 Reasoning)

Extract semantic insights across 4 categories:

| Category | What to Extract | Example |
|----------|-----------------|---------|
| **Strategic** | Architecture decisions, framework choices | "Use FastAPI for async support" |
| **Tactical** | Code preferences, patterns, conventions | "Always use structlog" |
| **Operational** | Workflows, approval gates, processes | "Igor approves high-risk tools" |
| **Learning** | Corrections, mistakes, lessons learned | "Use explicit node names in n8n" |

### Step 4: REASONING CHAINS

For each insight, capture:

```yaml
insight:
  id: "insight_001"
  category: "strategic"
  content: "Use FastAPI for backend"
  rationale: "Async support + automatic API docs"
  alternatives_considered: ["Flask", "Django"]
  source_lines: [45, 52]
  confidence: 0.92
```

### Step 5: GOVERNANCE VALIDATION

Run 6 checkpoints:

1. **Awareness Check** — All context considered?
2. **Assumption Check** — Assumptions explicit?
3. **Bias Check** — Balanced perspectives?
4. **Completeness Check** — All insights captured?
5. **Confidence Check** — Scores calibrated?
6. **Contradiction Check** — No conflicting insights?

### Step 6: OUTPUT GENERATION

Generate:
- Organized file directory
- Complete YAML manifest
- Human-readable summary
- Cross-reference maps

---

## OUTPUT STRUCTURE

```
/chat_output_[timestamp]/
├── extracted_files/
│   ├── explicit/          # Confidence >= 0.8
│   │   ├── config/
│   │   ├── scripts/
│   │   ├── prompts/
│   │   └── code/
│   ├── inferred/          # 0.6 <= Confidence < 0.8
│   └── ambiguous/         # Confidence < 0.6 (flagged)
│
├── insights.yaml          # All insights with reasoning
├── insights_summary.md    # Human-readable summary
├── synthetic_memory.yaml  # Complete integrated output
├── cross_reference.json   # Files ↔ Insights mapping
└── validation_report.yaml # Quality metrics
```

---

## OUTPUT FORMAT

```markdown
## 🧠 EXTRACTION COMPLETE

### 📊 Summary
- **Source:** [chat file]
- **Files extracted:** [count]
- **Insights extracted:** [count]
- **Quality score:** [percentage]

### 📁 Extracted Files

| # | File | Type | Confidence | Path |
|---|------|------|------------|------|
| 1 | config_docker_compose.yaml | config | 95% ✅ | explicit/config/ |
| 2 | script_deploy.py | script | 88% ✅ | explicit/scripts/ |
| 3 | schema_task.py | code | 72% ⚠️ | inferred/code/ |

### 💡 Key Insights

#### Strategic (Architecture)
1. **FastAPI for Backend** [92%]
   - Rationale: Async support + auto docs
   - Source: Lines 45-52

2. **Microservices Architecture** [88%]
   - Rationale: Independent scaling + team autonomy
   - Source: Lines 120-135

#### Tactical (Preferences)
1. **YAML for Configs** [92%]
   - Scope: All config files
   - Source: Lines 230, 456

#### Operational (Workflows)
1. **Code Review Gate** [95%]
   - Workflow: Generate → Review → Approve → Deploy
   - Source: Lines 89, 134

#### Learning (Corrections)
1. **n8n Expression Syntax** [98%]
   - Mistake: Used generic $json
   - Correction: Use explicit node names
   - Source: Lines 156-158

### ✅ Validation
- Governance checkpoints: 6/6 passed
- Files flagged for review: [count]
- Contradictions found: 0

### 🎯 YNP (Your Next Play)
**Primary:** /wire extracted files to repo
**Alternates:** Review flagged items, /forge to implement insights
```

---

## USAGE

### Simple Extraction
```
/extract-chat @chat_history.md

Uses production-ready defaults.
```

### Multiple Chats
```
/extract-chat @chat1.md @chat2.md @chat3.md

Extracts and merges from all, deduplicates.
```

### Dense Chat (Exhaustive)
```
/extract-chat @dense_chat.md --exhaustive

More passes for chats with 200+ insights.
```

### Files Only
```
/extract-chat @chat.md --files-only

Skip insight extraction, just get code blocks.
```

### Insights Only
```
/extract-chat @chat.md --insights-only

Skip file extraction, just get semantic insights.
```

### Specific Categories
```
/extract-chat @chat.md --categories strategic,learning

Only extract strategic decisions and lessons learned.
```

---

## SMART DEFAULTS

```yaml
defaults:
  mode: "full"                    # Both files and insights
  max_iterations: 3               # Up to 3 full passes
  duplicate_threshold: 0.90       # 90% similarity = duplicate
  confidence_threshold: 0.6       # Include >= 60% confidence
  categories: "all"               # All 4 insight categories
  governance: true                # 6 checkpoints enabled
  output_format: "yaml + markdown"
```

**You only customize when:**
- Chat is extremely dense → use `--exhaustive`
- Want only insights → use `--insights-only`
- Want only files → use `--files-only`

---

## FILE NAMING CONVENTION

```
Pattern: {type}_{domain}_{name}.{ext}

Examples:
- config_docker_compose.yaml
- script_python_deploy.py
- prompt_l9_system.md
- schema_memory_unified.yaml
```

| Type | Description |
|------|-------------|
| `config` | Configuration files |
| `script` | Executable scripts |
| `prompt` | AI prompts/instructions |
| `schema` | Data schemas |
| `kernel` | Core logic files |
| `template` | Templates |
| `manifest` | Manifests/indexes |

---

## CONFIDENCE TIERS

| Tier | Score | Directory | Action |
|------|-------|-----------|--------|
| **Explicit** | >= 80% | explicit/ | Use directly |
| **Inferred** | 60-79% | inferred/ | Review before use |
| **Ambiguous** | < 60% | ambiguous/ | Manual review required |

---

## FORGE INTEGRATION

Extracted files can be "forged" (reconstructed) with proper formatting:

```
/extract-chat @chat.md --forge

Additional steps:
1. Validate syntax of each file
2. Add proper headers
3. Apply L9 conventions
4. Generate forge manifest
```

---

## INTEGRATION

- **Chains from:** Perplexity research, Claude chats, debugging sessions
- **Chains to:** `/ynp` (always), `/wire` (for files), `/forge` (for implementation)
- **Updates:** `workflow_state.md` with extraction results

---

## ANTI-PATTERNS

❌ **DON'T:** Run multiple times on same file
❌ **DON'T:** Extract incomplete code snippets
❌ **DON'T:** Skip governance validation
❌ **DON'T:** Ignore low-confidence flags
❌ **DON'T:** Extract without checking for existing files

✅ **DO:** Extract everything in one pass
✅ **DO:** Merge related artifacts into single files
✅ **DO:** Apply L9 conventions automatically
✅ **DO:** Review ambiguous/ folder before using
✅ **DO:** Chain to /wire for integration

---

## EXAMPLES

### Example 1: VPS Deployment Chat
```
/extract-chat @"Chat - VPS Deploy L9.md"

EXTRACTION COMPLETE:

📊 Summary
- Source: Chat - VPS Deploy L9.md
- Files extracted: 12
- Insights extracted: 85
- Quality: 89%

📁 Key Files:
1. config_docker_compose.yaml (95% ✅)
2. script_python_deploy.py (94% ✅)
3. config_env_production.env (92% ✅)

💡 Key Insights:
- Strategic: Use Redis for task queue (92%)
- Tactical: Always use absolute paths in docker (88%)
- Learning: host.docker.internal only works on Mac (98%)

🎯 YNP: /wire extracted files to repo
```

### Example 2: Architecture Discussion
```
/extract-chat @"Brainstorm.md" --insights-only

EXTRACTION COMPLETE:

📊 Summary
- Insights extracted: 145

💡 Strategic Decisions:
1. Agent executor pattern for all agents (95%)
2. Packet-based memory substrate (93%)
3. Kernel stack for identity/behavior (91%)

🎯 YNP: Document insights in workflow_state.md
```

---

## TROUBLESHOOTING

| Issue | Solution |
|-------|----------|
| "Not finding enough insights" | Use `--exhaustive` mode |
| "Too many duplicates" | Normal — dedup threshold is 90% |
| "Low confidence warnings" | 5-10% is normal, review them |
| "Taking too long" | Large chat expected, progress shows |

---

## QUALITY METRICS

```yaml
quality_metrics:
  extraction_completeness: 0.87  # % of conversation mined
  file_extraction_rate: 0.95     # % of files found
  insight_confidence_avg: 0.82   # Average confidence
  duplicates_prevented: 18       # Duplicates caught
  governance_passed: 0.98        # % passed governance
  overall_quality: 0.87          # Final quality score
```

---

## DIFFERENTIATION FROM /mem

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `/mem` | Memory-aware task execution (READ → EXECUTE → WRITE) | During active coding tasks |
| `/extract-chat` | Extract insights from chat transcripts | After a session, to mine knowledge |

**Key difference:**
- `/mem` = **Live execution** with memory context
- `/extract-chat` = **Post-hoc extraction** from chat files

