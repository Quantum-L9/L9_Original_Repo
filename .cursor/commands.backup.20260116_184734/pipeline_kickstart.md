---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.1.0"
component_id: "PIPE-001"
component_name: "Pipeline Kickstart"
layer: "intelligence"
domain: "pipeline"
type: "pipeline"
status: "active"
created: "2025-12-06T00:00:00Z"
updated: "2025-12-06T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "high"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: []
integrates_with: ["CMD-013", "CMD-019", "CMD-012"]
api_endpoints: []
data_sources: ["project_context", "user_objectives"]
outputs: ["reasoned_summary", "system_spec", "ynp_recommendation"]

# === OPERATIONAL METADATA ===
execution_mode: "on-demand"
monitoring_required: true
logging_level: "info"
performance_tier: "interactive"

# === BUSINESS METADATA ===
purpose: "Convert idea into reasoning, spec, and next action in one pass"
summary: "Three-stage pipeline: /reasoning-full → /spec → /ynp for rapid project kickoff"
business_value: "Accelerates project initiation from concept to actionable spec"
success_metrics: ["kickstart_completion >= 0.95", "spec_quality >= 0.90"]

# === TAGS & CLASSIFICATION ===
tags: ["pipeline", "kickstart", "reasoning", "spec", "ynp", "suite6", "l9"]
keywords: ["kickstart", "pipeline", "project-start", "initiation"]
related_components: ["CMD-013", "CMD-019", "CMD-012"]
startup_required: false
mode_type: "pipeline"
---

name: pipeline-kickstart
description: Convert idea → reasoning → spec → YNP in one pass

## WHAT IT DOES

Converts idea → reasoning → spec → YNP in one pass.

- Stage 1: Deep reasoning analysis of objective
- Stage 2: Generate formal system specification
- Stage 3: Output highest-leverage next action

## WHEN TO USE

- Beginning of any project
- When starting new system design
- When formalizing vague requirements

# === PIPELINE ENGINE: KICKSTART ===

**STEPS:**
1. `/reasoning-full` — Execute 7-block reasoning engine
2. `/spec` — Generate system specification / PRD
3. `/ynp` — Output single highest-leverage next move

**EXECUTION:**
- Each step feeds into the next
- Reasoning informs spec structure
- Spec informs YNP recommendation

## OUTPUT FORMAT

- Reasoned Summary (7-block output)
- System Specification (PRD format)
- YNP (single next action)

## USAGE

```
/pipeline-kickstart [objective]

Examples:
/pipeline-kickstart "Build authentication system"
/pipeline-kickstart "Design data pipeline for analytics"
/pipeline-kickstart @requirements.md
```

## INTEGRATION NOTES

- Drives new system creation
- First pipeline to run on any new project
- Outputs feed into /forge for implementation