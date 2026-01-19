---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "7.0.0"
component_id: "CMD-SPEC-001"
component_name: "Spec - Specification Generator"
layer: "commands"
domain: "specification"
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
name: spec
description: "L9-native specification — generate full PRD/architecture document before building"
memory_inject: true            # INJECT: Search VPS memory for preferences/lessons before execution
before_chain: extract-chat   # EXTRACT: Write learnings to VPS memory
auto_chain: ynp
---

# === L9 SPEC: System Specification Generator ===
# Cursor Slash Command: /spec
# Version: 7.0.0 (L9-native)
# Updated: 2026-01-01

---

## ⛓️ AUTO-CHAINS TO /ynp

After spec generation, **automatically runs /ynp** to recommend /forge, /gmp, or refinement.

---

## WHAT IT DOES

**Generates comprehensive system specification:**

1. **Context & Goals** — Why are we building this?
2. **Constraints** — What can't we change?
3. **System Overview** — High-level architecture
4. **Detailed Design** — Components and interfaces
5. **Operations** — How it runs and maintains
6. **Risks & Questions** — What could go wrong?
7. **Acceptance Criteria** — How we know it's done
8. **Roadmap** — Implementation phases

**Output:** Complete spec document ready for /forge or /gmp execution.

**Key principle:** Specify before building. Clear spec = faster implementation.

---

## WHEN TO USE

| Scenario | Why /spec |
|----------|-----------|
| Before /forge | Define what to build |
| New feature | Document before implementing |
| Clarifying scope | Resolve ambiguity |
| Architecture decisions | Document for review |
| Before major refactor | Plan the change |

---

## EXECUTION PROTOCOL

### Step 1: CONTEXT GATHERING

```
1. Read workflow_state.md for current context
2. Identify the feature/system to specify
3. Gather existing related documentation
4. Note current constraints and dependencies
```

### Step 2: SPEC GENERATION

Generate 8-section specification:

```
SPEC STRUCTURE:
├── 1. Context & Goals
│   ├── Background
│   ├── Problem statement
│   ├── Goals (measurable)
│   └── Non-goals (explicitly excluded)
├── 2. Constraints
│   ├── Technical constraints
│   ├── Business constraints
│   ├── Timeline constraints
│   └── Resource constraints
├── 3. System Overview
│   ├── Architecture diagram (ASCII)
│   ├── Key components
│   ├── Data flow
│   └── Integration points
├── 4. Detailed Design
│   ├── Component specifications
│   ├── Interface definitions
│   ├── Data models
│   └── Algorithm descriptions
├── 5. Operations
│   ├── Deployment requirements
│   ├── Monitoring needs
│   ├── Maintenance procedures
│   └── Scaling considerations
├── 6. Risks & Questions
│   ├── Technical risks
│   ├── Open questions
│   ├── Assumptions
│   └── Dependencies
├── 7. Acceptance Criteria
│   ├── Functional requirements
│   ├── Performance requirements
│   ├── Quality requirements
│   └── Test scenarios
└── 8. Roadmap
    ├── Phase 1: MVP
    ├── Phase 2: Enhancement
    ├── Phase 3: Optimization
    └── Future considerations
```

---

## OUTPUT FORMAT

```markdown
# SPEC: [System/Feature Name]

**Version:** 1.0.0
**Status:** Draft | Review | Approved
**Author:** [name]
**Date:** [YYYY-MM-DD]

---

## 1. Context & Goals

### Background
[Why does this need to exist? What problem does it solve?]

### Problem Statement
[Specific problem in one sentence]

### Goals
1. [Measurable goal 1]
2. [Measurable goal 2]
3. [Measurable goal 3]

### Non-Goals (Explicitly Excluded)
- [Thing we're NOT doing]
- [Another thing we're NOT doing]

---

## 2. Constraints

### Technical Constraints
- Must use existing L9 memory substrate
- Must integrate with current agent executor
- [other constraints]

### Business Constraints
- Must be completed by [date]
- Cannot break existing functionality

### Resource Constraints
- Single developer
- No additional infrastructure

---

## 3. System Overview

### Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Input     │────▶│  Processor  │────▶│   Output    │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Storage   │
                    └─────────────┘
```

### Key Components
| Component | Purpose | Location |
|-----------|---------|----------|
| [Name] | [What it does] | [file path] |

### Data Flow
1. [Step 1]
2. [Step 2]
3. [Step 3]

### Integration Points
- [Integration 1]
- [Integration 2]

---

## 4. Detailed Design

### Component: [Name]

**Purpose:** [What it does]

**Interface:**
```python
class ComponentName:
    async def method_name(self, param: Type) -> ReturnType:
        """Description."""
        pass
```

**Data Model:**
```python
class DataModel(BaseModel):
    field1: str
    field2: int
    field3: Optional[List[str]] = None
```

**Algorithm:**
1. [Step 1]
2. [Step 2]
3. [Step 3]

---

## 5. Operations

### Deployment
- [Deployment requirement 1]
- [Deployment requirement 2]

### Monitoring
- [Metric to track]
- [Alert condition]

### Maintenance
- [Maintenance task]
- [Frequency]

### Scaling
- [Scaling consideration]

---

## 6. Risks & Questions

### Technical Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| [Risk] | Medium | High | [Mitigation] |

### Open Questions
1. [Question needing answer]
2. [Another question]

### Assumptions
1. [Assumption we're making]
2. [Another assumption]

### Dependencies
- [Dependency 1]
- [Dependency 2]

---

## 7. Acceptance Criteria

### Functional Requirements
- [ ] [Requirement 1]
- [ ] [Requirement 2]
- [ ] [Requirement 3]

### Performance Requirements
- [ ] Response time < [X]ms
- [ ] Throughput > [Y] requests/sec

### Quality Requirements
- [ ] Test coverage > 80%
- [ ] No critical linter errors

### Test Scenarios
| Scenario | Given | When | Then |
|----------|-------|------|------|
| [Name] | [Setup] | [Action] | [Expected] |

---

## 8. Roadmap

### Phase 1: MVP (Week 1)
- [ ] [Task 1]
- [ ] [Task 2]
- [ ] [Task 3]

### Phase 2: Enhancement (Week 2)
- [ ] [Task 4]
- [ ] [Task 5]

### Phase 3: Optimization (Week 3)
- [ ] [Task 6]
- [ ] [Task 7]

### Future Considerations
- [Future enhancement 1]
- [Future enhancement 2]

---

## Appendix

### Related Documents
- [Link to related doc]

### Revision History
| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | [date] | [name] | Initial spec |

---

## 🎯 YNP (Your Next Play)
**Primary:** [Recommended action with spec]
```

---

## USAGE

### Generate New Spec
```
/spec [feature/system name]

Examples:
/spec Observability Module
/spec Rate Limiting System
/spec CGA Extraction Pipeline
```

### Spec from Existing
```
/spec @docs/existing_design.md

Generates full spec from partial design notes.
```

### Update Existing Spec
```
/spec --update @specs/feature.md

Updates existing spec with new information.
```

### Mini Spec (Fast)
```
/spec --mini [feature]

Generates lightweight spec (sections 1, 3, 7 only).
```

---

## L9-SPECIFIC SECTIONS

### L9 Tier Classification
Every spec must include tier classification:

```markdown
### Tier Classification
- **Tier:** [KERNEL | RUNTIME | INFRA | UX]
- **GMP Required:** [Yes | No]
- **Protected Files Affected:** [list or None]
```

### L9 Integration Points
```markdown
### L9 Integration
- **Memory Substrate:** [how it uses memory]
- **Agent Executor:** [how agents interact]
- **Governance:** [approval requirements]
- **Tool Registry:** [tools used/created]
```

---

## INTEGRATION

- **Part of:** `/pipeline-kickstart` (after `/reasoning`)
- **Chains to:** `/ynp` (always), `/forge` or `/gmp` (for implementation)
- **Outputs:** Markdown spec document
- **Feeds into:** TODO plan generation

---

## EXAMPLES

### Example 1: Feature Spec
```
/spec Rate Limiting System

# SPEC: Rate Limiting System

## 1. Context & Goals

### Background
L9 API endpoints need protection from abuse and overload.

### Goals
1. Limit requests per client to 100/minute
2. Return 429 with retry-after header when exceeded
3. Track usage for analytics

### Non-Goals
- User-specific limits (use default for all)
- Persistent storage of limits (in-memory OK)
```

### Example 2: Mini Spec
```
/spec --mini Caching Layer

# SPEC: Caching Layer (Mini)

## Context
Cache expensive LLM calls to reduce costs.

## Overview
Redis-backed cache with TTL.

## Acceptance Criteria
- [ ] Cache hit returns in <10ms
- [ ] Cache miss falls through to LLM
- [ ] TTL configurable per cache key
```

---

## ANTI-PATTERNS

❌ **DON'T:** Start /forge without a spec
❌ **DON'T:** Leave open questions unresolved
❌ **DON'T:** Skip acceptance criteria
❌ **DON'T:** Forget tier classification

✅ **DO:** Specify before building
✅ **DO:** Include measurable goals
✅ **DO:** Document non-goals
✅ **DO:** Define acceptance criteria upfront

