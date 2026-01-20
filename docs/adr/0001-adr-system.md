# ADR-0001: ADR System for L9

## Status

**Status:** Accepted  
**Date:** 2026-01-20  
**Author:** @l-cto  
**Stakeholders:** @kernel-team, @qa-team, @all-engineers  
**Supersedes:** None  
**Superseded by:** None

## Context

L9 had a basic `architecture_decisions.md` file in the root directory with 2 decisions documented. This approach had several limitations:

1. **No standardization** - Ad-hoc format, inconsistent structure
2. **No unique identifiers** - Decisions couldn't be referenced easily
3. **No status tracking** - No way to mark decisions as deprecated or superseded
4. **No tooling** - Manual creation, no validation, no automation
5. **No governance integration** - No T3 approval gates for breaking changes
6. **No searchability** - Hard to find relevant decisions
7. **No relationship tracking** - Couldn't link related decisions
8. **No CI/CD integration** - No automated validation

As L9 grows in complexity with kernel architecture, DI/DIP patterns, and governance frameworks, we need a production-grade ADR system to maintain architectural integrity.

## Decision

Implement a comprehensive ADR system with:

1. **Standardized template** - Consistent structure for all decisions
2. **Sequential numbering** - Unique IDs (ADR-0001, ADR-0002, etc.)
3. **Status tracking** - Proposed, Accepted, Deprecated, Superseded
4. **CLI tooling** - Automated ADR creation, validation, and management
5. **Metadata indexing** - Searchable index.json for discovery
6. **Governance tiers** - T1/T2/T3 classification for approval gates
7. **CI/CD integration** - Automated validation on PRs
8. **Kernel integration** - T3 approval gates for breaking changes

## Rationale

### Why a Formal ADR System?

1. **Architectural Integrity** - Prevents accidental breaking changes
2. **Knowledge Preservation** - Captures the "why" behind decisions
3. **Team Alignment** - Shared understanding of architectural direction
4. **Governance Enforcement** - T3 approval gates for critical changes
5. **Historical Context** - Future engineers understand past decisions
6. **Decision Traceability** - Link decisions to PRs and implementations

### Why This Specific Design?

1. **Industry Standard** - Based on Michael Nygard's ADR format
2. **L9 Aligned** - Integrates with kernel architecture and T3 governance
3. **Automated** - CLI tooling reduces manual effort
4. **Validated** - CI/CD ensures ADR quality
5. **Searchable** - Metadata index enables discovery

## Alternatives Considered

### Alternative 1: Keep Simple Markdown File

- **Pros:** Lightweight, no tooling needed
- **Cons:** Doesn't scale, no governance, no automation
- **Why rejected:** Insufficient for L9's complexity and governance needs

### Alternative 2: Use External ADR Tool (adr-tools)

- **Pros:** Battle-tested, community support
- **Cons:** Not L9-aware, no kernel integration, no T3 governance
- **Why rejected:** Doesn't integrate with L9's unique architecture

### Alternative 3: Use Confluence/Notion for ADRs

- **Pros:** Rich formatting, collaboration features
- **Cons:** Not in git, no CI/CD integration, not code-adjacent
- **Why rejected:** ADRs should live with code for traceability

### Alternative 4: Use RFCs Instead of ADRs

- **Pros:** More detailed, includes implementation plans
- **Cons:** Too heavyweight, slows down decision-making
- **Why rejected:** ADRs are lighter-weight and faster

## Consequences

### Positive

1. **Improved Governance** - T3 approval gates prevent breaking changes
2. **Better Documentation** - Standardized format improves consistency
3. **Faster Onboarding** - New engineers understand architectural decisions
4. **Automated Validation** - CI/CD ensures ADR quality
5. **Searchability** - Metadata index enables quick discovery
6. **Traceability** - Link decisions to PRs and implementations
7. **Knowledge Preservation** - Captures reasoning for future reference

### Negative

1. **Initial Overhead** - Time to set up system and migrate existing decisions
2. **Learning Curve** - Engineers need to learn ADR format and CLI
3. **Maintenance Burden** - ADRs need to be kept up-to-date
4. **Process Overhead** - T3 ADRs require approval gates

### Neutral

1. **Cultural Shift** - Engineers need to adopt ADR-first mindset
2. **Tooling Dependency** - Relies on CLI tooling for automation
3. **Index Maintenance** - index.json needs to be kept in sync

## Implementation

### Migration Path

**Phase 1: Foundation (Week 1)**
1. Create `docs/adr/` directory structure
2. Create ADR template (`template.md`)
3. Migrate existing decisions to new format
4. Create ADR README with usage guide
5. Create ADR index (`index.json`)

**Phase 2: CLI Tooling (Week 2)**
1. Implement `tools/adr/adr_cli.py` (create, list, show, update)
2. Implement `tools/adr/adr_validator.py` (validate ADR structure)
3. Implement `tools/adr/adr_indexer.py` (build/update index)
4. Add tests for ADR tooling (30+ tests)

**Phase 3: Kernel Integration (Week 3)**
1. Implement `tools/adr/adr_kernel_integration.py`
2. Add T3 ADR validation (requires approval)
3. Integrate with CODEOWNERS
4. Add tests for kernel integration (20+ tests)

**Phase 4: CI/CD Integration (Week 4)**
1. Create `.github/workflows/adr-validation.yml`
2. Add ADR validation to PR checks
3. Add T3 ADR approval gate
4. Add tests for CI/CD integration (10+ tests)

### Rollback Strategy

If the ADR system proves too burdensome:

1. **Disable CLI validation** - Remove CI/CD checks
2. **Simplify template** - Remove optional sections
3. **Revert to simple markdown** - Move ADRs back to single file
4. **Keep existing ADRs** - Preserve historical decisions

### Validation

Success criteria:
- ✅ All existing decisions migrated to new format
- ✅ CLI tooling functional (create, list, show, validate)
- ✅ ADR index up-to-date
- ✅ CI/CD validation passing
- ✅ T3 approval gates enforced
- ✅ Engineers using ADR system for new decisions

## Metadata

**Category:** Process  
**Impact:** High  
**Tier:** T2 (Reversible, requires tests)  
**Related PRs:** #24  
**Related ADRs:** None (first ADR)  
**References:**
- [Michael Nygard's ADR format](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
- [ThoughtWorks ADR Tools](https://github.com/npryce/adr-tools)
- [MADR (Markdown Any Decision Records)](https://adr.github.io/madr/)
- [L9 Phase 0-6 Roadmap](../../L9-PHASE-0-6-EXECUTION-ROADMAP.md)

## Notes

This ADR documents the decision to implement the ADR system itself (meta-ADR). It serves as both a template example and a historical record of why we chose this approach.

Future ADRs should follow the template structure and include all required sections. The CLI tooling will help enforce consistency and validation.

The ADR system is designed to evolve over time. If we discover better practices or tooling, we can create new ADRs to document those changes.
