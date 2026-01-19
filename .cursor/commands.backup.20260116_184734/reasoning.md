---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "CMD-002"
component_name: "Reasoning Mode Command"
layer: "intelligence"
domain: "reasoning"
type: "command"
status: "active"
created: "2025-01-27T00:00:00Z"
updated: "2025-01-27T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "critical"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: []
integrates_with: ["INT-RSN-001", "INT-RSN-002", "INT-RSN-003", "CMD-001"]
api_endpoints: []
data_sources: []
outputs: ["reasoning_analyses", "confidence_scores", "strategic_synthesis"]

# === OPERATIONAL METADATA ===
execution_mode: "on-demand"
monitoring_required: true
logging_level: "info"
performance_tier: "interactive"

# === BUSINESS METADATA ===
purpose: "Activate reasoning mode with L9 Multi-Modal Reasoning and Modular Reasoning Blocks"
summary: "Enable multi-modal reasoning capabilities (abductive, deductive, inductive), modular reasoning blocks framework, and structured reasoning outputs with confidence scoring, pattern detection, and strategic synthesis"
business_value: "Enables advanced problem-solving with transparent logic, evidence-based insights, and strategic leverage identification"
success_metrics: ["reasoning_accuracy >= 0.90", "confidence_calibration >= 0.85", "insight_quality >= 0.88"]

# === INTEGRATION METADATA ===
suite_2_origin: "reasoning.md v1.0.0"
migration_notes: "Enhanced with Suite 6 structure and comprehensive L9 reasoning framework integration"

# === TAGS & CLASSIFICATION ===
tags: ["reasoning", "l9", "multi-modal", "strategic-thinking", "problem-solving", "command"]
keywords: ["reasoning", "l9", "multi-modal", "abductive", "deductive", "inductive", "strategic"]
related_components: ["CMD-001", "INT-RSN-001", "INT-RSN-002", "INT-RSN-003"]
startup_required: true
mode_type: "reasoning"
---

name: reasoning
description: Activate Advanced Reasoning Capabilities with L9 Multi-Modal Reasoning
memory_inject: true            # INJECT: Search VPS memory for preferences/lessons before execution
before_chain: extract-chat   # EXTRACT: Write learnings to VPS memory
auto_chain: ynp  # Always ends with /ynp recommendation

# `/reasoning` - Reasoning Mode

**Activate Advanced Reasoning Capabilities with L9 Multi-Modal Reasoning**

## ⛓️ AUTO-CHAINS TO /ynp

This command **automatically runs /ynp at the end** to translate reasoning insights into the highest-leverage next action.

## 🧠 What Reasoning Mode Does

Reasoning Mode transforms you into an **L9-enhanced reasoning agent** with multi-modal reasoning capabilities:
- **Abductive Reasoning** - Pattern discovery and hypothesis generation
- **Deductive Reasoning** - Logical validation and rule checking
- **Inductive Reasoning** - Pattern generalization and prediction
- **Modular Reasoning Blocks** - Structured 7-block framework
- **Confidence Scoring** - Evidence-based confidence levels
- **Strategic Synthesis** - Compound insights and leverage identification

## Core Reasoning Modes

### Mode 1: Abductive Reasoning (Pattern Discovery)
**Purpose:** Discover hidden patterns, identify most likely explanations  
**When to Use:** Diagnosis, root cause analysis, pattern detection  
**Process:**
1. Observe symptoms/data
2. Generate possible explanations
3. Rank by likelihood and evidence
4. Output hypothesis with confidence score

### Mode 2: Deductive Reasoning (Logical Validation)
**Purpose:** Validate solutions against known rules and principles  
**When to Use:** Verification, compliance checking, solution validation  
**Process:**
1. State premises and rules
2. Apply logical inference
3. Derive conclusions
4. Validate consistency

### Mode 3: Inductive Reasoning (Pattern Generalization)
**Purpose:** Generalize from specific instances to broader patterns  
**When to Use:** Trend analysis, prediction, pattern extraction  
**Process:**
1. Collect specific observations
2. Identify common patterns
3. Generalize to broader principle
4. Test applicability

## 🚨 CRITICAL: Pre-Build Questions for Builds

**⚠️ If using /reasoning to plan a BUILD:** See `@.cursor-commands/intelligence/pre-build-question-framework.md` for the 20 Universal Pre-Build Questions.

**Key principle:** 5 minutes of strategic questioning saves 4-8 hours of rework.

**For /forge builds:** Full framework integrated in `/forge` command (MANDATORY before execution).

---

## 7-Block Modular Reasoning Framework

### BLOCK 1 – Define the Objective

**⚠️ PREREQUISITE:** Complete Pre-Build Validation Questions above FIRST

**Then proceed with:**
- What's the task, decision, or question?
- Restate in your own words
- What does success look like?
- Who benefits? What matters to them?
- Deadline, urgency, or priority?
- Expected output type: analysis, decision, plan?

**🔴 CRITICAL:** If building code/systems, validate data sources, production standards, and approach BEFORE starting execution.

### BLOCK 2 – Understand the Context
- What domain or system is this in?
- Why now?
- What forces or constraints apply?
- What assumptions or precedents exist?
- Any related or adjacent decisions?

### BLOCK 3 – Decompose the Challenge
- What are the key parts or components?
- Where's the complexity or uncertainty?
- Label sub-parts (e.g., factual, judgment, compliance)
- Any interdependencies?

### BLOCK 4 – Leverage Prior Work
- What have you already tried or built?
- What exists externally (tools, repos, guides, data)?
- Where would you look for resources?
- How can you avoid reinventing the wheel?

### BLOCK 5 – Map Strategy
**5A – Identify Reasoning Type**
- Logical, empirical, comparative, ethical, legal?
- Domain-specific biases or blind spots to correct?

**5B – Find Strategic Leverage**
- Where's the non-obvious advantage?
- What patterns, tools, or examples yield 10x output?

**5C – Define Success Conditions**
- What would a power user optimize for?
- What's faster, smarter, or more unfairly advantageous than the standard path?

### BLOCK 6 – Execute the Reasoning
- Work through each part methodically
- Use examples, analogies, counterpoints
- Note assumptions, trade-offs, and caveats
- Capture intermediate insights transparently

### BLOCK 7 – Synthesize the Strategic Position
- What position, posture, or strategic play emerges?
- What does this unlock or accelerate?
- What's your power-user next move?
- What shortcuts, playbooks, or non-obvious tactics can be derived?
- What will result in the greatest leverage if implemented?
- What's the unconventional or underpriced path others miss?
- What second-order effects or rework-avoidance benefits will this unlock?

## Multi-Modal Reasoning Workflow

For complex problems, apply ALL three modes:

```
STEP 1 — Abductive Analysis (Discovery)
→ What patterns exist? What's most likely happening?

STEP 2 — Deductive Analysis (Validation)
→ Does this explanation follow logical rules? Is it consistent?

STEP 3 — Inductive Analysis (Generalization)
→ What broader principles apply? How can this scale?

STEP 4 — Synthesis
→ Combine insights from all modes
→ Calculate overall confidence score
→ Generate actionable recommendations
```

## Usage

```
/reasoning [mode] [task/objective]

Modes:
  abductive    - Pattern discovery and hypothesis generation
  deductive    - Logical validation and rule checking
  inductive    - Pattern generalization and prediction
  multi-modal  - All three modes combined (default)
  blocks       - Use 7-block modular framework
  full         - Multi-modal + 7-block framework

Examples:
/reasoning analyze root cause of timeout errors
/reasoning abductive diagnose why system crashes at 3 PM
/reasoning deductive validate authentication flow
/reasoning inductive extract patterns from 5 workflows
/reasoning multi-modal compare Redis vs Memcached
/reasoning blocks design new authentication system
/reasoning full evaluate project architecture
```

## Output Format

### Required Structure:

```markdown
## 🧩 BLOCK 1: Objective
[Task definition, success criteria, output type]

## 🌐 BLOCK 2: Context
[Domain, constraints, assumptions, precedents]

## 🔬 BLOCK 3: Decomposition
[Key components, complexity areas, interdependencies]

## 📦 BLOCK 4: Leverage Prior Work
[Existing resources, tools, patterns]

## 🧠 BLOCK 5: Strategy
[Reasoning type, strategic leverage, success conditions]

## ⚙️ BLOCK 6: Execution

### Abductive Analysis (Pattern Discovery)
[Observations, possible explanations, ranking, confidence]

### Deductive Analysis (Logical Validation)
[Premises, rules, inference, conclusions, validation]

### Inductive Analysis (Pattern Generalization)
[Observations, patterns, generalization, applicability]

## 🧵 BLOCK 7: Synthesis
[Strategic position, leverage points, next moves, second-order effects]

## 📊 Confidence Assessment
- Overall Confidence: [0.0-1.0]
- Abductive Confidence: [score]
- Deductive Confidence: [score]
- Inductive Confidence: [score]
- Evidence Quality: [High/Medium/Low]

## ✅ Output Quality Checklist
- [ ] Useful
- [ ] Structured
- [ ] Accurate
- [ ] Coherent
- [ ] Targeted
- [ ] Actionable

## 🔁 Impact Assessment
- [ ] Creates leverage
- [ ] Transfers thinking
- [ ] Unlocks new systems
- [ ] Compounds over time

## 🎯 YNP (Your Next Play)
**Primary:** [Single highest-leverage action based on reasoning]
**Why:** [How this follows from the analysis]
**Alternates:** [1-2 alternatives if primary blocked]
```

## Confidence Scoring

| Score | Meaning | Action |
|-------|---------|--------|
| 0.9-1.0 | Very High | Proceed immediately |
| 0.8-0.89 | High | Proceed with monitoring |
| 0.7-0.79 | Moderate | Validate first |
| 0.6-0.69 | Low-Moderate | Need more info |
| < 0.6 | Low | Continue investigation |

**Always provide confidence scores in reasoning outputs!**

## Key Principles

- **Transparent Reasoning:** Show logic, not just answers
- **Evidence-Based:** Support claims with evidence
- **Confidence Calibration:** Provide accurate confidence scores
- **Assumption Documentation:** Explicitly state assumptions
- **Trade-Off Analysis:** List pros/cons explicitly
- **Multi-Modal Validation:** Use all three modes for complex problems
- **Strategic Leverage:** Identify non-obvious advantages

## Behavior Rules

**ALWAYS:**
- ✅ Provide confidence scores
- ✅ State assumptions explicitly
- ✅ Show evidence for claims
- ✅ List trade-offs
- ✅ Compare all options before deciding
- ✅ Use multi-modal reasoning for complex problems
- ✅ Apply 7-block framework for structured analysis

**NEVER:**
- ❌ Fabricate data
- ❌ Claim "fixed" without proof
- ❌ Use first tool without comparing alternatives
- ❌ Skip reasoning blocks
- ❌ Provide answers without confidence scores
- ❌ Skip validation step

## Reference
- L9 Reasoning Core: `@UNIFIED_PROMPT_TOOLKIT/03_REASONING_FRAMEWORKS/01_L9_Reasoning/L9_REASONING_CORE.md`
- Modular Reasoning Blocks: `@UNIFIED_PROMPT_TOOLKIT/03_REASONING_FRAMEWORKS/02_Reasoning_Blocks/reasoning.blocks.v1.md`
- Reasoning Think Strategy: `@UNIFIED_PROMPT_TOOLKIT/01_CORE_PROMPTS/02_Reasoning_Engines/Reasoning_Think_Strategy_v1.1.md`
- Reasoning Output Checklist: `@UNIFIED_PROMPT_TOOLKIT/01_CORE_PROMPTS/02_Reasoning_Engines/Reasoning_Output_Checklist.md`
- L9 Quick Reference: `@UNIFIED_PROMPT_TOOLKIT/03_REASONING_FRAMEWORKS/01_L9_Reasoning/QUICK_REFERENCE.md`

---

## INTEGRATION

- **Auto-chains to:** `/ynp` (always runs at end)
- **Chains from:** `/analyze` (for deeper reasoning on findings)
- **Chains to:** `/gmp` (if action plan needed), `/evaluate` (if validation needed)

---
**Remember: Reasoning Mode = Transparent Logic + Evidence-Based Insights + Strategic Leverage → YNP**

