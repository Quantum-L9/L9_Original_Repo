# ADR 0003: Documentation Standards for AI-Readable Codebase

## Status

Accepted

## Context

L9 is maintained and extended by both human developers and AI agents (Cursor, L-CTO,
CodeGenAgent). Code must be unambiguous, self-documenting, and machine-parseable to
enable reliable automated analysis, code generation, and refactoring.

Current challenges:

- AI agents may misinterpret patterns without explicit documentation
- Type hints alone don't convey architectural intent
- Scattered documentation makes it hard to understand design decisions
- Different documentation styles across modules create inconsistency

## Decision

Adopt a **multi-method documentation strategy** that combines five complementary
approaches for maximum clarity and coverage:

### Documentation Methods (All Required for New Code)

| Method                        | Location                | Purpose                                               | Audience                             |
| ----------------------------- | ----------------------- | ----------------------------------------------------- | ------------------------------------ |
| **A: Module Docstring**       | Top of file             | Full architectural context, patterns used, references | Developers, AI agents reading source |
| **B: Inline Comment**         | At import/critical code | Why this specific code exists                         | AI reviewers, code auditors          |
| **C: Type Hints + Annotated** | Parameters, returns     | Per-element context with metadata                     | IDE users, type checkers, AI         |
| **D: ADR Document**           | `readme/adr/`           | Formal decision record                                | Architecture reviews, onboarding     |
| **E: DORA Metadata**          | `__dora_meta__` block   | Machine-readable patterns                             | Automated tooling, L9 system         |

### Method A: Module Docstring Template

Every Python module MUST have a docstring following this template:

```python
"""
L9 [Domain] - [Component Name]
Version: X.Y.Z

[One-line description of what this module does.]

ARCHITECTURE NOTES
==================
[Document any non-obvious patterns, such as:]
- Circular import prevention (ADR-0002)
- Singleton patterns
- Async requirements
- Thread safety considerations

DEPENDENCIES
============
- [List key dependencies and why they're needed]

USAGE
=====
[Brief usage example if applicable]

REFERENCES
==========
- ADR-XXXX: [Related ADR title]
- PEP XXX: [If using specific Python features]
- [External documentation links]

AI REVIEWER GUIDANCE
====================
[Explicit instructions for AI code reviewers about what NOT to flag]
"""
```

### Method B: Inline Comment Template

Use at critical code locations (imports, complex logic, architectural decisions):

```python
# =============================================================================
# [PATTERN NAME] (ADR-XXXX)
# =============================================================================
# Why: [One sentence explaining why this code exists]
# What: [One sentence explaining what it does]
# AI Guidance: [What NOT to flag or refactor]
# =============================================================================
```

### Method C: Type Hints with Annotated

**MANDATORY**: Use `Annotated` for all public API parameters and return types.

```python
from typing import Annotated, Optional
from typing_extensions import Doc  # Use comment fallback until Python 3.13

class MyService:
    def __init__(
        self,
        # Pattern: Annotated[Type, Doc("description")] or comment fallback
        repository: Annotated[
            SubstrateRepository,
            Doc("Database repository for persistence operations")
        ],
        # For TYPE_CHECKING imports, use comment format
        service: Optional[MemorySubstrateService] = None,  # ADR-0002: TYPE_CHECKING import for audit packet emission
        # For simple types with context
        enable_metrics: Annotated[
            bool,
            Doc("Enable Prometheus metrics collection. Default: True")
        ] = True,
        # For complex defaults
        timeout_seconds: Annotated[
            int,
            Doc("Request timeout in seconds. 0 = no timeout. Must be >= 0")
        ] = 30,
    ) -> None:
        ...
```

**Fallback for Python < 3.13** (until `Doc` is standard):

```python
def process_packet(
    self,
    packet: PacketEnvelopeIn,  # Input packet to process (validated via PacketValidator)
    tenant_id: str,            # RLS tenant UUID (derived server-side, ADR-XXXX)
    audit_mode: bool = True,   # If True, run PII redaction and injection detection
) -> PacketWriteResult:        # Contains status, packet_id, written_tables, error_message
    ...
```

### Method D: ADR Document Requirements

Every architectural decision affecting multiple files MUST have an ADR:

1. **File naming**: `readme/adr/XXXX-short-title.md`
2. **Number sequence**: Increment from highest existing number
3. **Required sections**: Status, Context, Decision, Consequences, AI Reviewer Guidance
4. **Cross-references**: Link related ADRs and affected files

### Method E: DORA Metadata Requirements

Every Python module MUST include `__dora_meta__` with these fields:

```python
__dora_meta__ = {
    "component_name": "Human-readable name",
    "module_version": "X.Y.Z",
    "created_by": "Author name",
    "created_at": "ISO timestamp",
    "updated_at": "ISO timestamp",
    "layer": "core|learning|api|runtime|...",
    "domain": "Domain classification",
    "module_name": "Python module name",
    "type": "service|dataclass|router|...",
    "status": "active|deprecated|experimental",

    # REQUIRED for AI comprehension
    "architecture_patterns": [
        "Pattern name (ADR-XXXX)",
        ...
    ],
    "pep_compliance": ["PEP 563", "PEP 544", ...],

    "integrates_with": {
        "api_endpoints": [...],
        "datasources": [...],
        "memory_layers": [...],
        "imported_by": [...],
    },
}
```

## AI Agent Requirements

### Startup Protocol

AI agents (Cursor, L-CTO, CodeGenAgent) MUST read all ADRs before code operations:

```
REQUIRED AT SESSION START:
1. Read all files in readme/adr/*.md
2. Parse ADR status (Accepted, Deprecated, Superseded)
3. Index patterns mentioned in ADRs
4. Apply ADR guidance during code analysis

REQUIRED BEFORE GMP EXECUTION:
1. Re-check readme/adr/ for new/updated ADRs
2. Verify GMP scope doesn't violate ADR constraints
3. Reference relevant ADRs in GMP documentation
```

### Code Review Guidance

When reviewing code, AI agents MUST:

1. **Check for ADR references**: If code uses a pattern documented in an ADR, do not flag it
2. **Verify documentation completeness**: Flag missing docstrings, type hints, or DORA metadata
3. **Respect AI Reviewer Guidance sections**: These are explicit "do not flag" instructions
4. **Cross-reference TYPE_CHECKING imports**: These are intentional per ADR-0002

## Consequences

### Positive

- Unambiguous code that AI agents can reliably parse
- Self-documenting architecture decisions
- Consistent documentation style across codebase
- Reduced false positives in AI code reviews
- Better onboarding for new contributors (human and AI)

### Neutral

- Increased initial documentation effort
- Larger file sizes due to comprehensive documentation
- Requires discipline to maintain

### Negative

- Technical debt if not enforced consistently
- May slow down rapid prototyping (acceptable trade-off for production code)

## Enforcement

### Pre-commit Checks

The following will be enforced via pre-commit hooks:

1. Module docstring present and non-empty
2. `__dora_meta__` block present
3. Public functions have type hints
4. ADR references are valid (file exists)

### CI Pipeline

The CI pipeline will check:

1. All new files have required documentation
2. Modified files maintain documentation standards
3. ADR numbers are sequential and unique
4. Cross-references between ADRs are valid

## Examples

### Fully Documented Module

See `memory/agent_persistence.py` for a reference implementation of all five
documentation methods applied together.

### Minimal Compliant Module

```python
"""
L9 Utils - String Helpers
Version: 1.0.0

Utility functions for string manipulation.

AI REVIEWER GUIDANCE
====================
No special patterns. Standard utility module.
"""

__dora_meta__ = {
    "component_name": "String Helpers",
    "module_version": "1.0.0",
    "type": "utility",
    "status": "active",
    "architecture_patterns": [],
}

def truncate(
    text: str,           # Input text to truncate
    max_length: int,     # Maximum length (must be > 0)
    suffix: str = "...", # Suffix to append if truncated
) -> str:               # Truncated string with suffix if needed
    """Truncate text to max_length, appending suffix if truncated."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
```

## Related ADRs

- ADR-0002: Circular Import Prevention (example of pattern requiring documentation)
- ADR-0001: Path Safety (example of existing ADR format)

## References

- PEP 257: Docstring Conventions (https://peps.python.org/pep-0257/)
- PEP 484: Type Hints (https://peps.python.org/pep-0484/)
- PEP 563: Postponed Evaluation of Annotations (https://peps.python.org/pep-0563/)
- PEP 727: Documentation in Annotated Metadata (https://peps.python.org/pep-0727/)
- Google Python Style Guide: Documentation (https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
