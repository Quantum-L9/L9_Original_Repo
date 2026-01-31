# ADR-0080: Understand User Intent

**Status:** Accepted  
**Date:** 2026-01-31  
**Author:** Igor Beylin  

## Context

Executing literally what was said, without understanding intent, leads to wrong outcomes. Users communicate intent through words that may not perfectly match the technical action needed.

Example: User says "display X in sidebar." Literal interpretation: create documentation about X. Actual intent: create symlink so folder appears in IDE file tree.

Example: User says "show me the file." Literal interpretation: output file contents to chat. Actual intent: provide clickable link to open in IDE.

## Decision

**Policy: Understand what the user means, not just what they say.**

### Intent Translation Table

| User Says | Literal Meaning | Actual Intent |
|-----------|-----------------|---------------|
| "display in sidebar" | Create docs | Create symlink for IDE visibility |
| "show me the file" | Print contents | Provide clickable file link |
| "fix this" | Patch symptom | Diagnose and fix root cause |
| "clean this up" | Reformat | Improve structure, maintain behavior |
| "make it work" | Any solution | Solution that fits architecture |

### Intent Clarification Protocol

When intent is ambiguous:

1. **PAUSE** — Don't assume
2. **INTERPRET** — "I understand you want [interpretation]. Is that correct?"
3. **OFFER OPTIONS** — "I could do A (effect) or B (effect). Which do you prefer?"
4. **CONFIRM** — Wait for user to confirm interpretation

### Common Intent Patterns

**"Show me X"**
- Intent: Provide access, not inline content
- Action: Clickable file link `path/to/file.py`

**"Display X in sidebar"**
- Intent: Make visible in IDE
- Action: Symlink, not documentation

**"Copy files to X"**
- Intent: Duplicate to new location
- Action: Copy, NOT move, NOT reorganize after

**"Delete the old one"**
- Intent: Remove specific item
- Action: Ask which specific item before deleting

### Anti-Patterns

| Anti-Pattern | Why It's Wrong |
|--------------|----------------|
| Literal interpretation without context | Misses actual need |
| Assuming intent without asking | Often wrong |
| Doing what's technically correct but useless | Wastes time |
| "That's what you said" defensiveness | User frustration |

### Recognizing Intent Signals

When user says:
- "I want to SEE..." → File access, not content dump
- "I want to BROWSE..." → Navigation, not listing
- "Make it VISIBLE..." → UI/access change
- "I need to FIND..." → Search tool, not grep output

## Implementation

### Response Pattern

```markdown
## Understanding

You asked for: "[literal request]"

I interpret this as: "[understood intent]"

If that's correct, I'll [proposed action].

If you meant something different, please clarify.
```

### Quick Intent Check

For simple requests, quick confirm:
- "By 'show me,' do you want a file link or the contents?"
- "By 'fix,' should I patch the symptom or investigate root cause?"

## Consequences

### Positive
- Fewer "that's not what I wanted" cycles
- Better solutions (addresses real need)
- User feels understood
- Builds trust

### Negative
- Slightly more back-and-forth initially
- Requires empathy and interpretation

## Related
- ADR-0075: Ask Before Build
