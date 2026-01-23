---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "2.1.0"
component_id: "CMD-HARVEST-001"
component_name: "Harvest - Artifact Extraction"
layer: "commands"
domain: "extraction"
type: "slash_command"
status: "active"
created: "2025-12-01T00:00:00Z"
updated: "2026-01-05T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "operational"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === COMMAND METADATA ===
name: harvest
description: "Extract production-ready specs, code, configs, and docs from Perplexity/chat transcripts — USES TERMINAL EXTRACTION (not write tool)"
memory_inject: true            # INJECT: Search VPS memory for preferences/lessons before execution
before_chain: extract-chat   # EXTRACT: Write learnings to VPS memory
auto_chain: ynp
---

# === L9 HARVEST: Extract Artifacts from Chat Transcripts ===
# Cursor Slash Command: /harvest
# Version: 2.1.0
# Updated: 2026-01-05

---

## 🚨 CRITICAL: TERMINAL-BASED EXTRACTION IS MANDATORY

**THIS IS NOT A PLANNING COMMAND — THIS IS AN EXECUTION COMMAND.**
**THIS DOES NOT USE THE `write` TOOL — IT USES `sed` VIA TERMINAL.**

When `/harvest` is invoked:

1. **READ SOURCE FILE ONCE** to identify artifacts (paths + line ranges only)
2. **USE `sed` VIA TERMINAL** to extract code blocks directly
3. **CONTENT NEVER FLOWS THROUGH LLM** — only line numbers and paths do
4. **VALIDATE WITH `py_compile`** — confirm syntax is valid
5. **OUTPUT MANIFEST** — confirm what was extracted

```
TOKEN COST COMPARISON:

❌ OLD (wasteful): read_file → LLM sees content → write(contents=...) → file
   Token cost: O(2n) - content flows through LLM TWICE

✅ NEW (efficient): read_file → identify line ranges → sed extract → file  
   Token cost: O(1) - only line numbers, content NEVER touches LLM
```

**Why this matters:**
- ⏱️ **Saves 2x tokens** — content never passes through LLM
- ⏱️ **Saves time** — sed is instant, no regeneration
- 🎯 **Eliminates errors** — verbatim extraction, not interpretation
- 🔄 **Ready to use** — files in repo immediately
- 🔁 **Fewer iterations** — single pass extraction

---

## ⛓️ AUTO-CHAINS TO /ynp

This command **automatically runs /ynp at the end** to recommend whether to `/wire`, validate, or proceed with next extraction.

---

## WHAT IT DOES

Scans source file and **EXTRACTS files directly via terminal**:
- **Code blocks** → `sed -n 'START,ENDp'` → Python modules, configs, SQL migrations
- **Embedded docs** → `sed -n 'START,ENDp'` → Standalone markdown files
- **YAML/JSON specs** → `sed -n 'START,ENDp'` → Module specs, configs, schemas

**The output is FILES IN YOUR REPO via terminal commands, not LLM content handling.**

Files are created with:
- Exact code from source (verbatim `sed` extraction)
- Proper file paths (from source context)
- Zero LLM content processing (only line range identification)
- Ready to use immediately

**Key principles:**
1. **IDENTIFY, don't read content** — only capture line numbers and paths
2. **EXTRACT via terminal** — `sed -n 'START,ENDp'` bypasses LLM
3. **VALIDATE syntax** — `python3 -m py_compile` confirms valid code
4. **ONE pass** — extract everything in single terminal batch

---

## EXECUTION PROTOCOL

### Step 1: READ SOURCE & IDENTIFY ARTIFACTS

Read the source file to identify extractable artifacts.

**CRITICAL: You are ONLY looking for:**
1. **File paths** (e.g., `**Path**: `/l9/ops/gap_analysis/component_profiler.py``)
2. **Code fence line numbers** (where ``` appears)
3. **Content line ranges** (start = fence+1, end = fence-1)

```
ARTIFACT DETECTION PATTERN:

Look for:
├── "**Path**:" or "Path:" followed by filepath
├── "```python" or "```sql" etc. (opening fence)
├── "```" alone on a line (closing fence)
└── Calculate: content_start = fence_line + 1, content_end = closing_fence - 1

Output for each artifact:
{
  "path": "l9/ops/gap_analysis/component_profiler.py",
  "start_line": 13,
  "end_line": 233,
  "type": "python"
}
```

### Step 2: CREATE DIRECTORY STRUCTURE

```bash
mkdir -p /path/to/target/directory
```

### Step 3: EXTRACT VIA TERMINAL (MANDATORY)

**Use `sed` to extract code blocks directly - content bypasses LLM:**

```bash
SOURCE="/path/to/source.md"
TARGET="/path/to/target.py"
sed -n 'START,ENDp' "$SOURCE" > "$TARGET"
```

**Batch multiple extractions in parallel:**

```bash
# Extract all artifacts in parallel
sed -n '13,233p' "$SOURCE" > "component_profiler.py" &
sed -n '243,600p' "$SOURCE" > "frontier_research.py" &
sed -n '610,947p' "$SOURCE" > "gap_engine.py" &
wait
```

### Step 4: VALIDATE SYNTAX

```bash
python3 -m py_compile target1.py target2.py target3.py && echo "✅ Valid"
```

### Step 5: OUTPUT MANIFEST

Generate confirmation table showing what was extracted.

---

## OUTPUT FORMAT

```markdown
## 🌾 HARVEST COMPLETE

### 📊 Extraction Summary
- **Source:** {source file path}
- **Method:** Terminal `sed` extraction (content bypassed LLM)
- **Artifacts found:** {count}
- **Files EXTRACTED:** {count}

### 📁 Files Created

| # | Path | Lines | Status |
|---|------|-------|--------|
| 1 | `l9/ops/gap_analysis/component_profiler.py` | 221 | ✅ EXTRACTED |
| 2 | `l9/ops/gap_analysis/frontier_research.py` | 358 | ✅ EXTRACTED |
| 3 | `l9/ops/gap_analysis/gap_engine.py` | 338 | ✅ EXTRACTED |

**Files validated:** `py_compile` passed on all files

### 🎯 YNP (Your Next Play)
**Primary:** [Next recommended action]
**Why:** [Reasoning]
```

---

## EXTRACTION PATTERNS

### Pattern 1: Explicit Path in Source

**Source contains:**
```
## FILE 1: Component Profiler Service

**Path**: `/l9/ops/gap_analysis/component_profiler.py`

```python
# Line 13 starts here
...code...
# Line 233 ends here
```
```

**Extraction:**
```bash
# Path from "**Path**:" line
# Lines 13-233 (between fences at 12 and 234)
sed -n '13,233p' "$SOURCE" > "l9/ops/gap_analysis/component_profiler.py"
```

### Pattern 2: Multiple Code Blocks

**Source contains 3 code blocks with paths:**

| Block | Path Line | Fence Open | Fence Close | Content Lines |
|-------|-----------|------------|-------------|---------------|
| 1 | 10 | 12 | 234 | 13-233 |
| 2 | 240 | 242 | 601 | 243-600 |
| 3 | 607 | 609 | 948 | 610-947 |

**Extraction (parallel):**
```bash
sed -n '13,233p' "$SOURCE" > "component_profiler.py" &
sed -n '243,600p' "$SOURCE" > "frontier_research.py" &
sed -n '610,947p' "$SOURCE" > "gap_engine.py" &
wait
```

### Pattern 3: SQL Migrations

**Source contains:**
```sql
-- Line 45
CREATE TABLE spans (
    id UUID PRIMARY KEY,
    ...
);
-- Line 85
```

**Extraction:**
```bash
sed -n '45,85p' "$SOURCE" > "migrations/0010_spans.sql"
```

---

## LINE NUMBER CALCULATION

**Critical: Identify fence lines correctly**

```
For a code block:

Line 12: ```python     ← Opening fence (DO NOT include)
Line 13: """           ← Content START
...
Line 233: asyncio.run  ← Content END  
Line 234: ```          ← Closing fence (DO NOT include)

Extraction: sed -n '13,233p' = lines 13 through 233 inclusive
Line count: 233 - 13 + 1 = 221 lines
```

**Fence detection:**
- Opening: Line matches `^\`\`\`[a-z]*$` (e.g., ```python, ```sql)
- Closing: Line matches `^\`\`\`$` (just ``` with nothing after)

---

## BATCHING RULES

### DO:
- Extract ALL artifacts in one pass
- Use parallel `sed` commands with `&` and `wait`
- Create all directories upfront with `mkdir -p`
- Validate all Python files at once

### DON'T:
- Read file content into LLM memory
- Use `write` tool (it requires content as parameter = tokens)
- Run `/harvest` multiple times on same file
- Extract partial code blocks

---

## ANTI-PATTERNS

### 🚨 CRITICAL VIOLATIONS (Token Waste)

❌ **DON'T:** Use `write` tool — it requires passing content through LLM
❌ **DON'T:** Read content into context then output it — double token cost
❌ **DON'T:** Regenerate code — it already exists, just extract it
❌ **DON'T:** Show code in response — extract directly to file

### ✅ CORRECT BEHAVIOR

✅ **DO:** Read source ONLY to identify line ranges and paths
✅ **DO:** Use `sed -n 'START,ENDp'` to extract directly
✅ **DO:** Validate with `py_compile` after extraction
✅ **DO:** Output manifest table (not content)

---

## EXAMPLE WORKFLOW

```bash
# User invokes: /harvest @source.md

# Step 1: Agent reads source, identifies 3 artifacts:
#   - component_profiler.py: lines 13-233
#   - frontier_research.py: lines 243-600
#   - gap_engine.py: lines 610-947

# Step 2: Create directory
mkdir -p l9/ops/gap_analysis

# Step 3: Extract all via sed (parallel)
SOURCE="source.md"
sed -n '13,233p' "$SOURCE" > l9/ops/gap_analysis/component_profiler.py &
sed -n '243,600p' "$SOURCE" > l9/ops/gap_analysis/frontier_research.py &
sed -n '610,947p' "$SOURCE" > l9/ops/gap_analysis/gap_engine.py &
wait

# Step 4: Validate
python3 -m py_compile l9/ops/gap_analysis/*.py && echo "✅ Valid"

# Step 5: Output manifest table
```

---

## INTEGRATION

- **Chained from:** Perplexity research sessions, Claude chats, documentation files
- **Chains to:** `/wire` (integration), `/ynp` (next action)
- **Updates:** `workflow_state.md` with extraction results
- **Validates:** Python syntax via `py_compile`

---

## FLAGS & OPTIONS

| Flag | Description | Default |
|------|-------------|---------|
| `--output DIR` | Target directory for extracted files | (inferred from paths) |
| `--dry-run` | Show line ranges without extracting | `false` |
| `--validate` | Run py_compile after extraction | `true` |
| `--manifest` | Generate YAML manifest file | `true` |

---

## CHANGELOG

### v2.1.0 (2026-01-05)
- **BREAKING:** Switched from `write` tool to `sed` terminal extraction
- **NEW:** Content never flows through LLM — 2x token savings
- **NEW:** Parallel extraction with `&` and `wait`
- **NEW:** Mandatory `py_compile` validation
- **REMOVED:** Guidance on using `write` tool (obsolete)

### v2.0.0 (2026-01-04)
- Initial Suite 6 version with `write` tool approach

---

**Remember: /harvest = Identify line ranges → sed extract → validate → manifest**
**Content NEVER flows through LLM. Only line numbers and paths.**

