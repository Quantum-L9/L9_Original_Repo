# L9 README Suite Integration Guide

**Date:** December 25, 2025  
**Target:** L9 Secure AI OS Repository  
**Purpose:** Complete gold-standard README setup with contracts, codegen guidance, and AI collaboration rules.

---

## Overview

This guide provides a **complete README suite** for your L9 OS repository. It treats each README as a **binding contract** that specifies:

- **Scope:** What the module owns and does not own.
- **APIs:** Public functions, schemas, error codes, lifecycle.
- **Invariants:** Data shape, format, lifecycle, transformation rules.
- **Configuration:** Feature flags, tuning parameters, environment variables.
- **AI usage rules:** What AI tools can modify, what requires human review, what is forbidden.

The suite includes:

1. **Labs research super prompt** — System prompt for AI tools researching codegen and README architecture.
2. **Root README.md** — Project overview, getting started, security, AI rules.
3. **Subsystem README templates** — Agents, memory, tools, API (one per subsystem).
4. **README.meta.yaml templates** — Metadata for codegen validation.
5. **Integration guide** — This document; shows how to use the suite in your repo.

---

## Files in This Suite

### 1. `labs-research-super-prompt.md`

**Purpose:** System prompt for AI tools researching codegen and README architecture.

**When to use:** Copy this prompt into any AI tool (ChatGPT, Claude, Copilot) when asking it to:
- Generate code for L9 subsystems
- Draft or update README files
- Design architecture
- Analyze codegen patterns

**Key principles:**
- Documentation is a contract (scope, APIs, invariants, AI rules)
- Code generation must verify ground truth first
- Governance-first design (feature flags, audit trails, change gates)
- Production-grade quality only (no stubs, no hallucination)

**Structure:**
- Core principles (4 sections)
- README architecture standard (hierarchy, templates)
- Codegen workflow (GMP phases 0–6)
- Evidence validation (3 categories)
- Critical files (always verify)
- Success criteria

---

### 2. `README.gold-standard.md`

**Purpose:** Complete root README for L9 Secure AI OS.

**File location:** `README.md` (at repo root)

**Sections:**
1. **Project Overview** — What L9 is, who it serves, goals/non-goals.
2. **Architecture Summary** — Four core subsystems, how they work together.
3. **Repository Layout** — Directory structure with entrypoints.
4. **Getting Started** — Prerequisites, installation, quickstart commands.
5. **Configuration and Environments** — .env, config.yaml, required secrets.
6. **Running Tests** — pytest commands, quality gates, coverage.
7. **Deployment** — Strategy, production entrypoints, procedures.
8. **Observability and Operations** — Logging, metrics, dashboards, incident response.
9. **Security and Compliance** — Threat model, sensitive components, data handling.
10. **Working with AI on This Repo** — Allowed/restricted/forbidden scopes, pre-reading, change policy.
11. **Contributing** — Issue/PR workflow, coding standards, escalation.
12. **License** — MIT, ownership, contacts.

**How to integrate:**
1. Copy content into your `/README.md`.
2. Update placeholders:
   - `<repo-url>` → actual Git repository URL
   - `igor@l9os.dev` → real contact email
   - Database/Redis/service URLs → your actual deployment URLs
3. Customize sections based on your actual tech stack (e.g., if not using PostgreSQL, update DB references).

---

### 3. `subsystem-readmes-complete.md`

**Purpose:** Complete README templates for major subsystems (agents, memory, tools, API).

**Subsystems covered:**
1. **Agents** — Agent kernel, registry, lifecycle, execution model.
2. **Memory** — Multi-layer storage, semantic search, retention.
3. **Tools** — Tool registry, sandboxing, resource limits.
4. **API** — HTTP/WebSocket endpoints, authentication, validation.

**Each subsystem README includes:**
- Overview (one paragraph + dependencies)
- Responsibilities and boundaries (what it owns, what it doesn't)
- Directory layout (file structure + naming conventions)
- Key components (classes/functions with signatures)
- Data models (Pydantic schemas + invariants)
- Execution and lifecycle (startup, main loop, shutdown)
- Configuration (feature flags, tuning, env vars)
- API surface (public functions with examples)
- Observability (logs, metrics, traces)
- Testing (unit/integration tests, edge cases)
- AI usage rules (allowed/restricted/forbidden scopes)

**How to integrate:**
1. Copy each subsystem README to its location:
   - `l9/core/agents/README.md`
   - `l9/core/memory/README.md`
   - `l9/core/tools/README.md`
   - `l9/api/README.md`
2. Customize content:
   - Update file paths to match your actual directory structure.
   - Add real component names and function signatures from your codebase.
   - Update examples with actual code from your repo.
   - Adjust feature flags and config parameters to match your implementation.

---

### 4. README.meta.yaml Templates

**Purpose:** Metadata files for codegen validation and automation.

**One per README:** Each `README.md` gets a corresponding `README.meta.yaml`.

**Example structure:**
```yaml
location: "/l9/core/agents/README.md"
type: "subsystem_readme"
metadata:
  subsystem: "agents"
  module_path: "l9/core/agents/"
  owner: "Igor"
  last_updated: "2025-12-25"

purpose: |
  Documents the agent kernel, registry, and execution model.

sections:
  overview: { required: true }
  responsibilities: { required: true }
  components: { required: true }
  data_models: { required: true }
  api_surface: { required: true }
  ai_rules: { required: true }

invariants:
  - "Agent IDs are UUIDv4"
  - "Agent execution uses kernel entry point"

ai_collaboration:
  allowed_scopes: ["Application logic", "Tests", "Documentation"]
  restricted_scopes: ["Kernel entry points", "Manifest schema"]
  forbidden_scopes: ["kernel.py", "Auth", "Memory substrate"]
  required_pre_reading: ["docs/architecture.md", "docs/ai-collaboration.md"]
```

**How to integrate:**
1. Create `README.meta.yaml` files next to each README.
2. Use metadata in:
   - **CI/CD validation:** Ensure all required sections are present.
   - **Codegen tools:** Tools can read these to understand scope and constraints.
   - **Change gates:** Restricted scope changes trigger human review.

---

## Integration Workflow

### Step 1: Prepare Your Repository

Before integrating the suite, understand your codebase:

1. **Identify subsystems** — What are your major modules?
   - Agents? Memory? Tools? API? Scheduler? Integrations?
2. **Map file structure** — Where does each subsystem live?
   - `l9/core/agents/`, `l9/core/memory/`, etc.?
3. **Document entry points** — What are the main APIs?
   - `Kernel.execute()`, `memory.search()`, `tool_registry.invoke()`?
4. **List critical files** — What cannot change without breaking the system?
   - Kernel loaders? Substrate bindings? Auth layers?

### Step 2: Create Directory Structure for Docs

```bash
mkdir -p docs/api docs/operational-playbooks docs/adr
touch docs/architecture.md docs/ai-collaboration.md
touch docs/capabilities.md docs/memory-and-tools.md
touch docs/agents.md docs/governance.md
touch docs/deployments.md docs/troubleshooting.md
touch docs/maintenance-tasks.md docs/roadmap.md
touch docs/api/http-api.md docs/api/webhooks.md docs/api/integrations.md
touch docs/operational-playbooks/oncall-runbook.md docs/operational-playbooks/incident-response.md
touch docs/adr/README.md
```

### Step 3: Integrate Root README

1. Copy `README.gold-standard.md` → `README.md`
2. Update placeholders with your actual configuration:
   - Repository URL
   - API keys and service URLs
   - Team contact information
   - Deployment details
3. Add your logo (if desired)
4. Review for factual accuracy against your codebase

### Step 4: Create Subsystem READMEs

For each major subsystem:

1. Use the template from `subsystem-readmes-complete.md`
2. Customize:
   - File paths (use your actual paths)
   - Component names (use your actual classes)
   - Configuration parameters (use your actual flags)
   - Examples (use your actual code)
3. Include real API signatures from your codebase
4. Add actual test file locations

### Step 5: Create README.meta.yaml Files

For each README, create a `.meta.yaml` file:

```bash
# Example
touch README.meta.yaml
touch l9/core/agents/README.meta.yaml
touch docs/architecture.meta.yaml
```

Each file should specify:
- Sections and whether they're required
- Invariants that must hold
- AI collaboration rules (allowed/restricted/forbidden)
- Required pre-reading documents

### Step 6: Fill in Supporting Documentation

Using the framework provided, draft these key documents:

1. **`docs/architecture.md`** — System design, subsystems, data flow, diagrams.
2. **`docs/ai-collaboration.md`** — How AI tools integrate, change workflow, approval gates.
3. **`docs/capabilities.md`** — What the system can do (human + machine-readable).
4. **`docs/memory-and-tools.md`** — Memory architecture, tool registry, schemas.
5. **`docs/agents.md`** — Agent profiles, roles, responsibilities, delegation rules.

### Step 7: Set Up CI/CD Validation

Add checks to your CI pipeline:

```bash
# Check that all READMEs have required sections
python scripts/validate-readmes.py

# Validate all YAML manifests match their contracts
python scripts/validate-manifests.py

# Ensure no secrets in docs
grep -r "OPENAI_API_KEY\|DATABASE_URL" docs/ && exit 1 || true

# Type-check docs examples (if applicable)
python scripts/validate-doc-examples.py
```

### Step 8: Create AI Collaboration Guidelines

In `docs/ai-collaboration.md`, explicitly define:

1. **Allowed scopes** — What AI can modify without human review.
2. **Restricted scopes** — What requires human review before merge.
3. **Forbidden scopes** — What AI must never touch.
4. **Required pre-reading** — Docs AI must digest before suggesting changes.
5. **Change policy** — How to propose, test, and land AI-generated changes.

**Example:**
```markdown
## Allowed Scopes for AI Changes

AI tools (e.g., Copilot, Claude) **are allowed** to modify:

- Application logic: `l9/core/agents/executor.py`, `l9/core/memory/retrieval.py`
- Tests: unit tests, fixtures, integration tests
- Documentation: READMEs, guides, examples
- Non-critical configuration: `config.yaml` defaults (not secrets)

## Restricted Scopes Requiring Human Review

⚠️ High-risk changes need explicit human approval:

- Feature flags: L9_ENABLE_* changes must be reviewed by Igor
- Memory substrate: Any change to redis_client.py, schemas
- API contracts: Endpoint signatures, WebSocket messages
- Dependency upgrades: Major version bumps
```

---

## Usage Examples

### Example 1: AI Tool Requests Code Generation

**Scenario:** You ask an AI tool to generate a new agent type.

**Workflow:**
1. Copy `labs-research-super-prompt.md` into your AI prompt.
2. Add specific request: "Generate a `DataAnalystKernel` agent that can call SQL tools."
3. AI tool reads `docs/architecture.md`, `docs/ai-collaboration.md`, `l9/core/agents/README.md`.
4. AI understands:
   - What scope it can modify (agents subsystem application logic)
   - What it cannot touch (kernel.py, tool registry)
   - What tests it must write (unit tests + integration with real tools)
   - What documentation to update (agents.md, new agent's README)
5. AI proposes a scoped PR with code, tests, and docs.

### Example 2: Team Member Updates Memory Subsystem

**Scenario:** A team member wants to add semantic caching to memory retrieval.

**Workflow:**
1. They read `l9/core/memory/README.md` to understand:
   - What memory owns (multi-layer storage, retrieval, retention)
   - Public APIs (memory.search(), memory.write(), memory.delete())
   - Invariants (all data must be in memory substrate, audit trails)
   - What requires review (schema changes, retention policy)
2. They create a feature branch and propose changes.
3. CI checks run (tests, type checking, doc validation).
4. Code review focuses on:
   - Memory contract preservation (can't break existing code)
   - Test coverage (positive + negative + regression)
   - Documentation updates (if APIs change)
5. Merge happens only after all checks pass.

### Example 3: Onboarding a New Engineer

**Scenario:** New engineer joins the team.

**Workflow:**
1. They start with `README.md` — project overview, getting started, architecture summary.
2. They read `docs/architecture.md` — understand subsystem boundaries.
3. For their specific subsystem, they read the subsystem README:
   - `l9/core/agents/README.md` if working on agents
   - `l9/core/memory/README.md` if working on memory
   - etc.
4. They understand:
   - What the subsystem owns and doesn't own
   - Key components and how they interact
   - Data models and invariants
   - How to run tests and observability
   - AI collaboration rules (what they can ask AI to help with)
5. They can now make confident contributions.

---

## Maintenance and Updates

### Keeping READMEs in Sync with Code

**Problem:** Code changes but documentation doesn't.

**Solution:** Make READMEs part of your change process:

1. **In PR template:** Add checklist item: "[ ] README updated (if APIs or scope changed)"
2. **In CI:** Fail the build if code changes API signatures but README not updated.
3. **In reviews:** Reviewers check that examples in README still work.

### Updating Subsystem READMEs

When a subsystem changes:

1. **API changes?** Update the "API Surface" section.
2. **Config changes?** Update the "Configuration" section.
3. **New components?** Add them to "Key Components".
4. **Data model changes?** Update "Data Models and Contracts".
5. **Invariant violations?** Discuss with the team before committing.

### Rotating Ownership

When ownership of a subsystem changes:

1. Update the `owner` field in `README.meta.yaml`.
2. Update `docs/governance.md` with new owner.
3. Ensure new owner reads the subsystem README.
4. Add new owner as co-reviewer for that subsystem's PRs.

---

## Governance Integration

### Change Gates

Using the README suite as a source of truth for change gates:

| Type of Change | Scope | Review | Gate |
|---|---|---|---|
| Feature/bugfix | Allowed scope | Code review | Automated tests |
| Config tuning | Restricted scope | Human review | Tests + human approval |
| API change | Restricted scope | Human review | Tests + human approval |
| Kernel/substrate change | Forbidden scope | Architecture review | Fail at PR time |
| Docs-only | Documentation | Fast track | Grammar/clarity |

### AI Change Approval

For AI-generated code:

1. **Phase 0:** AI reads pre-reading docs and understands scope.
2. **Phase 1–2:** AI generates code, tests, docs.
3. **Phase 3–4:** Code passes automated checks (tests, linting, type checking).
4. **Phase 5:** Code is reviewed by a human (not just automated).
5. **Phase 6:** Merge happens only after human approval.

**Key principle:** AI-generated code is not automatically trusted. It must be reviewed and tested like any other contribution.

---

## Template Customization Checklist

- [ ] Copy `labs-research-super-prompt.md` to your AI tools
- [ ] Copy `README.gold-standard.md` to `/README.md` and customize
- [ ] Create `/l9/core/agents/README.md` from `subsystem-readmes-complete.md`
- [ ] Create `/l9/core/memory/README.md` (customize from template)
- [ ] Create `/l9/core/tools/README.md` (customize from template)
- [ ] Create `/l9/api/README.md` (customize from template)
- [ ] Create `README.meta.yaml` files for each README
- [ ] Customize `docs/architecture.md` with your actual system design
- [ ] Customize `docs/ai-collaboration.md` with your AI collaboration rules
- [ ] Set up CI validation for README structure and examples
- [ ] Update team documentation / onboarding guides to reference READMEs

---

## Success Criteria

A successful README suite integration means:

✅ **Clarity** — New team members can understand scope and APIs from READMEs.  
✅ **Governance** — Change gates are enforced via scope definitions.  
✅ **AI integration** — AI tools understand what they can modify.  
✅ **Contract enforcement** — Invariants are documented and tested.  
✅ **Onboarding** — New engineers can get productive without heavy mentoring.  
✅ **Maintenance** — READMEs stay in sync with code via CI checks.  

---

## Support and Questions

**Questions about this suite?**
- Review the individual files (super prompt, root README, subsystem templates).
- Check the "Usage Examples" section above.
- Reach out to your team architect or Igor.

**Customizing for your codebase?**
- Start with the checklist above.
- Update file paths, component names, and config to match your actual code.
- Add real examples from your codebase.
- Get team consensus on governance rules (what requires review, etc.).

**Using this with AI tools?**
- Copy the `labs-research-super-prompt.md` into your AI tool's context.
- Provide the AI tool with a link or copy of your README suite.
- Ask the AI to read pre-reading docs before proposing changes.
- Review AI-generated code just like any other contribution.

---

**L9 Secure AI OS — Building the future of governed, secure agent execution.**

Version: 1.0  
Date: December 25, 2025  
Author: Igor and Team
