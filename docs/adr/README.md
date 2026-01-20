# L9 Architecture Decision Records (ADRs)

## 📚 What are ADRs?

Architecture Decision Records (ADRs) are documents that capture important architectural decisions made in the L9 project, along with their context and consequences. They serve as a historical record of why certain choices were made and help future contributors understand the reasoning behind the current architecture.

## 🎯 Purpose

ADRs help us:
- **Document decisions** - Capture the reasoning behind architectural choices
- **Maintain context** - Preserve the "why" behind decisions for future reference
- **Enable collaboration** - Share decision-making process with the team
- **Track evolution** - See how the architecture has evolved over time
- **Prevent revisiting** - Avoid rehashing old discussions
- **Enforce governance** - Apply T3 approval gates for breaking changes

## 📐 ADR Format

All ADRs follow a standardized template (see `template.md`) with the following sections:

1. **Status** - Current state (Proposed, Accepted, Deprecated, Superseded)
2. **Context** - The issue motivating the decision
3. **Decision** - The change being proposed/implemented
4. **Rationale** - Why this decision was made
5. **Alternatives Considered** - Other options evaluated
6. **Consequences** - Positive, negative, and neutral impacts
7. **Implementation** - Migration path, rollback strategy, validation
8. **Metadata** - Category, impact, tier, related PRs/ADRs

## 🔢 ADR Numbering

ADRs are numbered sequentially starting from 0001:
- `0001-adr-system.md` - This ADR system
- `0002-cursor-file-org.md` - Cursor file organization
- `0003-typeddict-vs-pydantic.md` - Type system strategy
- `0004-di-dip-foundation.md` - DI/DIP foundation
- `0005-kernel-config-externalization.md` - Kernel config externalization

## 🛠️ Creating a New ADR

### Using CLI (Recommended)

```bash
# Create new ADR
$ python -m tools.adr new "Use Protocol Buffers for IPC"
Created: docs/adr/0042-use-protobuf-for-ipc.md

# List all ADRs
$ python -m tools.adr list

# Show ADR details
$ python -m tools.adr show 0042

# Update ADR status
$ python -m tools.adr update-status 0042 accepted

# Validate all ADRs
$ python -m tools.adr validate
```

### Manual Creation

1. Copy `template.md` to a new file with the next sequential number
2. Fill in all sections of the template
3. Update `index.json` with the new ADR metadata
4. Submit a PR with the new ADR

## 📊 ADR Categories

**Architecture** - Structural decisions about the system
- Example: DI/DIP foundation, kernel architecture

**Infrastructure** - Deployment, hosting, and operations decisions
- Example: Kubernetes deployment strategy

**Process** - Development workflow and governance decisions
- Example: ADR system, code review process

**Tooling** - Tools and technologies used in development
- Example: Black for formatting, Ruff for linting

## 🔒 ADR Governance Tiers

ADRs are classified by L9 governance tiers:

**T3 (Protocol-Breaking, Requires Approval)**
- Changes to kernel loading order
- Changes to protocol definitions
- Changes to DI container architecture
- Breaking changes to core abstractions
- **Approval required:** @l-cto + @kernel-team

**T2 (Reversible, Requires Tests)**
- New substrate implementations
- Orchestration changes
- Agent capability changes
- **Approval required:** 1 reviewer + tests

**T1 (Safe, No Approval)**
- Documentation improvements
- Observability additions
- Diagnostic tools
- **Approval required:** None

## 🔄 ADR Lifecycle

```
Proposed → Accepted → [Deprecated | Superseded]
```

**Proposed** - ADR is under review, not yet implemented  
**Accepted** - ADR is approved and implemented  
**Deprecated** - ADR is no longer relevant (but not replaced)  
**Superseded** - ADR is replaced by a newer ADR

## 📋 ADR Index

All ADRs are indexed in `index.json` for searchability and tooling. The index contains:
- ADR ID, title, status
- Author, date, category
- Impact, tier, tags
- Related ADRs and PRs
- File path

## 🔍 Finding ADRs

### By Number
```bash
$ python -m tools.adr show 0042
```

### By Keyword
```bash
$ python -m tools.adr search "kernel"
```

### By Status
```bash
$ python -m tools.adr list --status accepted
```

### By Category
```bash
$ python -m tools.adr list --category architecture
```

## 📚 ADR Best Practices

1. **Write ADRs early** - Document decisions as they're made, not after
2. **Be concise** - Focus on the decision, not implementation details
3. **Document alternatives** - Show what was considered and why it was rejected
4. **Update status** - Keep ADR status current (accepted, deprecated, etc.)
5. **Link related ADRs** - Show relationships between decisions
6. **Include consequences** - Document both positive and negative impacts
7. **Provide migration path** - Explain how to transition to the new decision
8. **Define rollback strategy** - Explain how to revert if needed

## 🎯 When to Write an ADR

Write an ADR when:
- Making a significant architectural decision
- Choosing between multiple viable alternatives
- Making a decision that will be hard to reverse
- Making a decision that affects multiple teams
- Making a decision that requires governance approval (T2/T3)

Don't write an ADR for:
- Trivial decisions (e.g., variable naming)
- Obvious choices with no alternatives
- Temporary workarounds
- Implementation details (use code comments instead)

## 📖 References

**Industry Standards:**
- [Michael Nygard's ADR format](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
- [ThoughtWorks ADR Tools](https://github.com/npryce/adr-tools)
- [MADR (Markdown Any Decision Records)](https://adr.github.io/madr/)

**L9 Integration:**
- [Phase 0-6 Execution Roadmap](../../L9-PHASE-0-6-EXECUTION-ROADMAP.md)
- [T3 Governance Framework](../../docs/architecture/governance-framework.md)
- [DI Container Guide](../architecture/di-container-guide.md)

## 🤝 Contributing

To contribute a new ADR:
1. Create a new ADR using the CLI or template
2. Fill in all required sections
3. Update `index.json` (or run `python -m tools.adr reindex`)
4. Submit a PR with the ADR
5. Request review from appropriate stakeholders
6. Update status to "Accepted" after approval

## 📞 Questions?

For questions about ADRs, contact:
- **ADR System:** @l-cto
- **T3 Governance:** @kernel-team
- **Process:** @qa-team

---

**Last Updated:** 2026-01-20  
**Maintained by:** L9 Kernel Team
