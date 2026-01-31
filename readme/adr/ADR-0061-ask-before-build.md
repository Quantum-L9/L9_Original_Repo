# ADR-0061: Ask Before Build

**Status:** Accepted  
**Date:** 2026-01-31  
**Author:** Igor Beylin  

## Context

Building first and asking questions later wastes enormous time. A 5-minute conversation upfront prevents 4-8 hours of rework when assumptions are wrong.

Pattern observed: Agent builds elaborate solution, user says "that's not what I wanted," entire effort discarded.

## Decision

**Policy: Ask strategic questions BEFORE building anything complex.**

### Question Tiers

**Tier 1: Always Ask (Before ANY Build)**
1. "What does success look like when this is done?"
2. "Are there existing solutions I should know about?"
3. "What's the scope boundary — what should I NOT touch?"

**Tier 2: Ask for Features**
4. "Are placeholders acceptable or prohibited?"
5. "What data do we have access to?"
6. "Who/what will consume this output?"

**Tier 3: Ask for Complex Systems**
7. "What are the performance requirements?"
8. "Should this have confidence scores? How calculated?"
9. "What's the error handling strategy?"
10. "What's the rollback plan if this fails?"

### When to Ask vs When to Build

| Scenario | Action |
|----------|--------|
| Simple, clear task (< 5 min) | Build directly |
| Ambiguous requirements | Ask first |
| Multiple valid approaches | Ask which one |
| Touches protected files | Ask first |
| User says "build X" but X is vague | Ask for specifics |

### Question Quality

Good questions:
- Are specific, not generic
- Reveal hidden requirements
- Challenge assumptions
- Suggest alternatives user hasn't considered

Bad questions:
- "Is this okay?" (too vague)
- "Should I proceed?" (yes/no isn't helpful)
- "Any concerns?" (puts burden on user)

### Anti-Patterns

| Anti-Pattern | Why It's Wrong |
|--------------|----------------|
| "Let me build this real quick" | Skips understanding |
| "I'll figure it out as I go" | Wastes time on wrong path |
| "I assumed you wanted X" | Assumptions cause rework |
| Asking 20 questions at once | Overwhelming, not strategic |

## Implementation

### Pre-Build Checklist

Before any build > 15 minutes:

- [ ] Success criteria defined
- [ ] Scope boundaries clear
- [ ] Existing solutions checked
- [ ] Data availability confirmed
- [ ] Error handling decided

### Communication Pattern

```
Before I build this, a few quick questions:

1. [Most important question]
2. [Second question]
3. [Third question]

Once I understand these, I'll create a plan for your review before implementing.
```

## Consequences

### Positive
- Far less rework
- User feels heard
- Better solutions (uncovers hidden requirements)
- Builds trust and credibility

### Negative
- Slightly slower start
- Requires patience

## Related
- ADR-0060: Surgical Edits Only
