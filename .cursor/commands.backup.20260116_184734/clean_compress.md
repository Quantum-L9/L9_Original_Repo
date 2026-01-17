---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "7.0.0"
component_id: "CMD-CLEANCOMPRESS-001"
component_name: "Clean+Compress - Text Transformation"
layer: "commands"
domain: "text_processing"
type: "slash_command"
status: "active"
created: "2025-12-01T00:00:00Z"
updated: "2026-01-01T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "informational"
compliance_required: false
audit_trail: false
security_classification: "internal"

# === COMMAND METADATA ===
name: clean+compress
description: "L9-native text transformation — remove noise, extract signal, create embedding-ready output"
memory_inject: true            # INJECT: Search VPS memory for preferences/lessons before execution
before_chain: extract-chat   # EXTRACT: Write learnings to VPS memory
auto_chain: ynp
---

# === L9 CLEAN+COMPRESS: Text Cleaning & Information Density ===
# Cursor Slash Command: /clean+compress
# Version: 7.0.0 (L9-native)
# Updated: 2026-01-01

---

## ⛓️ AUTO-CHAINS TO /ynp

After cleaning, **automatically runs /ynp** to recommend /harvest, /extract-chat, or storage action.

---

## WHAT IT DOES

**Two-phase text transformation:**

1. **CLEAN** — Remove filler, repetition, formatting noise
2. **COMPRESS** — Extract high-value information into dense format

**Output:** Text ready for embeddings, knowledge extraction, or memory storage.

**Key principle:** Information density > word count. Every token should carry meaning.

---

## WHEN TO USE

| Scenario | Why /clean+compress |
|----------|---------------------|
| After chat dumps | Raw chat is noisy, clean before processing |
| Before embeddings | Vector DBs work better with dense text |
| Before knowledge extraction | Cleaner input = better extraction |
| Cleaning old docs | Legacy docs often have cruft |
| Preparing for RAG | Retrieval quality depends on text quality |

---

## EXECUTION PROTOCOL

### Phase 1: CLEAN

Remove noise while preserving meaning:

```
CLEANING OPERATIONS:
├── Remove filler phrases:
│   ├── "I think that maybe..."
│   ├── "Let me explain..."
│   ├── "Actually, what I meant was..."
│   └── Conversational artifacts
├── Remove repetition:
│   ├── Same point stated multiple ways
│   ├── Repeated examples
│   └── Redundant clarifications
├── Remove formatting noise:
│   ├── Excessive whitespace
│   ├── Broken markdown
│   ├── Orphaned code fences
│   └── Inconsistent headers
├── Fix structure:
│   ├── Merge fragmented thoughts
│   ├── Order logically
│   └── Group related content
└── Preserve:
    ├── Technical details
    ├── Specific decisions
    ├── Code snippets
    └── Actionable items
```

### Phase 2: COMPRESS

Extract maximum signal in minimum tokens:

```
COMPRESSION TARGETS:
├── Decisions → Single sentence each
├── Rules → Bullet points
├── Preferences → Key-value pairs
├── Identity markers → Short phrases
├── Patterns → Named patterns with conditions
├── Actions → Imperative statements
└── Context → Essential background only
```

### Compression Techniques

| Technique | Before | After |
|-----------|--------|-------|
| **Nominalization** | "We decided to use FastAPI because..." | "Decision: FastAPI (async + auto-docs)" |
| **Bullet extraction** | Long paragraph about preferences | "- YAML for configs\n- structlog for logging" |
| **Pattern naming** | Repeated behavior described | "Pattern: APPROVE_THEN_EXECUTE" |
| **Context stripping** | "Given that we're building X, and considering Y..." | "Context: X with Y constraint" |

---

## OUTPUT FORMAT

```markdown
## 🧹 CLEAN+COMPRESS OUTPUT

### 📊 Transformation Metrics
- **Original:** [X] tokens
- **Cleaned:** [Y] tokens ([Z]% reduction)
- **Compressed:** [W] tokens ([V]% total reduction)
- **Information Density:** [score]

---

### 📄 CLEANED VERSION

[Clean, readable text with noise removed but full meaning preserved]

---

### 💎 COMPRESSED VERSION (Embedding-Ready)

#### Decisions
- [Decision 1]: [rationale]
- [Decision 2]: [rationale]

#### Rules
- [Rule 1]
- [Rule 2]

#### Preferences
- [key]: [value]
- [key]: [value]

#### Patterns
- **[Pattern Name]**: [trigger] → [behavior]

#### Identity Markers
- [marker 1]
- [marker 2]

#### Actions
- [action 1]
- [action 2]

---

### 🎯 YNP (Your Next Play)
**Primary:** [Recommended next action with compressed output]
```

---

## USAGE

### Standard Clean+Compress
```
/clean+compress @messy_chat.md

Cleans and compresses the entire file.
```

### From Clipboard
```
/clean+compress

Operates on clipboard content.
```

### Clean Only
```
/clean+compress --clean-only

Skip compression, just remove noise.
```

### Compress Only
```
/clean+compress --compress-only

Assume input is already clean, just compress.
```

### For Embeddings
```
/clean+compress --for-embeddings

Optimizes output specifically for vector storage.
```

---

## L9-SPECIFIC CLEANING

### Remove L9-Irrelevant Content
- Generic programming explanations
- Obvious context (already in kernels)
- Repeated L9 architecture descriptions
- Setup instructions (documented elsewhere)

### Preserve L9-Critical Content
- Igor's decisions and preferences
- L's behavioral constraints
- Approval gate patterns
- Memory substrate details
- Governance rules

### L9 Compression Patterns

```yaml
# Instead of:
"Igor said that whenever L needs to do something risky, 
 it should always ask for permission first, and wait 
 for Igor to say yes before proceeding."

# Compress to:
"Rule: HIGH_RISK_TOOLS require IGOR_APPROVAL before execution"
```

---

## QUALITY METRICS

| Metric | Target | Description |
|--------|--------|-------------|
| **Noise Reduction** | > 40% | Tokens removed as noise |
| **Information Preservation** | > 95% | Key facts retained |
| **Compression Ratio** | > 60% | Total size reduction |
| **Density Score** | > 0.8 | Meaningful tokens / total tokens |

---

## INTEGRATION

- **Chains from:** Raw chat imports, legacy doc migration
- **Chains to:** `/ynp` (always), `/harvest` (for extraction), `/extract-chat` (for storage)
- **Feeds into:** Vector embeddings, knowledge base, memory substrate

---

## EXAMPLES

### Example 1: Chat Cleanup

**Input (noisy chat):**
```
User: So I was thinking, maybe we should, you know, 
      consider using Redis for the task queue?
AI:   That's a great question! Let me think about that.
      Actually, Redis would be a good choice because
      it's fast. Really fast. And it handles queues well.
      We could use Redis. Yes, let's use Redis.
User: Ok sounds good
AI:   Great! So to summarize, we're going to use Redis.
```

**Output (compressed):**
```
Decision: Use Redis for task queue
Rationale: Fast, native queue support
Status: Approved
```

### Example 2: Document Compression

**Input:** 500-word architecture description

**Output:**
```
## Architecture (Compressed)

### Layers
- API: FastAPI (async, OpenAPI docs)
- Agents: AgentExecutorService → AIOSRuntime
- Memory: PostgreSQL + Redis + Neo4j
- Governance: Kernel stack (10 YAML files)

### Key Patterns
- PACKET_LOGGING: All decisions → PacketEnvelope → memory
- APPROVAL_GATES: High-risk tools → Igor check
- TIER_ROUTING: KERNEL > RUNTIME > INFRA > UX

### Constraints
- No sync I/O in async functions
- structlog only (no logging module)
- Pydantic v2 models
```

---

## ANTI-PATTERNS

❌ **DON'T:** Remove technical specifics for brevity
❌ **DON'T:** Compress code (keep code intact)
❌ **DON'T:** Lose decision rationales
❌ **DON'T:** Over-compress identity/governance content

✅ **DO:** Remove conversational filler aggressively
✅ **DO:** Preserve all decisions and their reasons
✅ **DO:** Keep L9-specific patterns intact
✅ **DO:** Optimize for vector retrieval

