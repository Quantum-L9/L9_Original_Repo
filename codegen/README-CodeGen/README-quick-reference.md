# L9 README Suite: Quick Reference Card

**A quick visual guide to the gold-standard README architecture for L9 Secure AI OS.**

---

## File Map

```
ROOT
├── labs-research-super-prompt.md ............ AI tool system prompt (codegen + README guidance)
├── README.gold-standard.md ................ Complete root README (copy to README.md)
├── subsystem-readmes-complete.md .......... All subsystem README templates
├── README-integration-guide.md ............ Step-by-step integration workflow
└── [THIS FILE] ............................ Quick reference card
```

---

## The 3-Layer README Architecture

### Layer 1: Root README (`/README.md`)

**Purpose:** Project overview, AI rules, getting started.

**Sections:**
1. Project Overview
2. Architecture Summary
3. Repository Layout
4. Getting Started
5. Configuration & Environments
6. Running Tests & QA
7. Deployment
8. Observability & Operations
9. Security & Compliance
10. **Working with AI on This Repo** ⭐
11. Contributing
12. License

**Key:** Explicitly states what AI tools can/cannot modify.

---

### Layer 2: Subsystem READMEs (`/l9/core/*/README.md`)

**Purpose:** Detailed scope, APIs, invariants, AI rules per subsystem.

**Each subsystem README has:**

| Section | Purpose |
|---------|---------|
| **Subsystem Overview** | 1 paragraph: what it does, who depends on it |
| **Responsibilities & Boundaries** | What it owns, what it doesn't, dependencies |
| **Directory Layout** | Folder structure, naming conventions, patterns |
| **Key Components** | Classes/functions with signatures and roles |
| **Data Models & Contracts** | Pydantic schemas, invariants, format rules |
| **Execution & Lifecycle** | Startup, main loop, shutdown, background tasks |
| **Configuration** | Feature flags, tuning, environment variables |
| **API Surface (Public)** | Export signatures, request/response schemas, examples |
| **Observability** | Logs, metrics, traces, dashboards |
| **Testing** | Test locations, approach, edge cases |
| **AI Usage Rules** ⭐ | Allowed/restricted/forbidden scopes |

**The Core Subsystems:**
- `l9/core/agents/` — Agent kernel, registry, lifecycle
- `l9/core/memory/` — Multi-layer storage, semantic search
- `l9/core/tools/` — Tool registry, sandboxing, execution
- `l9/api/` — HTTP/WebSocket endpoints, auth

---

### Layer 3: Metadata Files (`README.meta.yaml`)

**Purpose:** Structured data for CI validation and codegen tools.

**One `.meta.yaml` per README.md.**

**What goes in it:**
```yaml
location: "/l9/core/agents/README.md"  # File path
type: "subsystem_readme"                # Type identifier
metadata:
  subsystem: "agents"                  # Module name
  owner: "Igor"                        # Contact for questions
  last_updated: "2025-12-25"          # Maintenance date

sections:                              # Which sections are required
  overview: { required: true }
  responsibilities: { required: true }
  ai_rules: { required: true }

invariants:                            # Data contracts
  - "Agent IDs are UUIDv4"
  - "All state in memory substrate"

ai_collaboration:                      # AI tool rules
  allowed_scopes: [...]               # What AI can modify
  restricted_scopes: [...]            # Requires review
  forbidden_scopes: [...]             # AI cannot touch
  required_pre_reading: [...]         # Docs to read first
```

---

## The Contract Pattern

Every README is a **contract**:

```
SCOPE
├── What this module owns
├── What it doesn't own
├── Who calls it (inbound)
└── What it calls (outbound)

INVARIANTS
├── Data shape (format, constraints)
├── Lifecycle rules (startup, shutdown)
├── Error handling
└── State consistency

APIS
├── Public functions (signatures)
├── Request/response schemas
├── Error codes
└── Examples

CONFIGURATION
├── Feature flags
├── Tuning parameters
└── Environment variables

AI RULES
├── ✅ What AI can modify (allowed scope)
├── ⚠️ What needs human review (restricted scope)
├── ❌ What AI cannot touch (forbidden scope)
└── 📚 Required pre-reading
```

---

## AI Tool Usage Pattern

### When You Ask AI to Generate Code:

1. **Provide the super prompt:**
   ```
   Copy labs-research-super-prompt.md into your AI tool context.
   ```

2. **Point to relevant READMEs:**
   ```
   "Read /l9/core/agents/README.md, then generate a new agent type."
   ```

3. **AI reads (in this order):**
   - Root README (project overview, AI rules)
   - Subsystem README (scope, APIs, invariants)
   - .meta.yaml (constraints and requirements)

4. **AI generates code that:**
   - ✅ Respects scope (modifies only allowed areas)
   - ✅ Implements required APIs (matches contracts)
   - ✅ Preserves invariants (no breaking changes)
   - ✅ Includes tests (positive + negative + regression)
   - ✅ Updates docs (if APIs changed)

5. **Your review checks:**
   - Does AI touch forbidden scopes? → Reject
   - Are tests passing? → Required
   - Are docs updated? → Required
   - Is code production-grade? → No stubs allowed

---

## Scopes at a Glance

### ✅ Allowed Scope (AI Can Modify Without Review)

```
l9/core/agents/executor.py         ✅ Application logic
l9/core/memory/retrieval.py        ✅ Memory algorithms
tests/unit/                        ✅ Unit tests
docs/README sections               ✅ Documentation
config.yaml defaults               ✅ Non-secret config
scripts/local-dev.sh              ✅ Dev helpers
```

### ⚠️ Restricted Scope (Requires Human Review)

```
Feature flags (L9_ENABLE_*)        ⚠️ Must review impact
Memory schema changes              ⚠️ Breaking change risk
API contract changes               ⚠️ Client compatibility
Tool manifest changes              ⚠️ Tool access rules
Dependency upgrades                ⚠️ Compatibility testing
```

### ❌ Forbidden Scope (AI Must NOT Touch)

```
l9/kernel_loader.py               ❌ Agent entry point
l9/websocket_orchestrator.py       ❌ Communication channel
l9/redis_client.py                ❌ Memory substrate
.env, secrets, private keys        ❌ Never commit secrets
docker-compose.yml                ❌ Infrastructure
Authentication code                ❌ Security-sensitive
```

---

## File-by-File Customization

| File | Customize | How |
|------|-----------|-----|
| `labs-research-super-prompt.md` | No | Copy as-is to AI tools |
| `README.gold-standard.md` | **YES** | Update paths, URLs, team contacts |
| `subsystem-readmes-complete.md` | **YES** | Add real component names, examples |
| `.meta.yaml` files | **YES** | Update owner, dates, paths |
| `README-integration-guide.md` | Maybe | Clarify workflow for your team |

---

## Integration Checklist

```
PREPARATION
☐ Understand your subsystems (agents, memory, tools, etc.)
☐ Map your directory structure
☐ Identify critical files (can't change without breaking)
☐ List entry points (main APIs)

ROOT README
☐ Copy README.gold-standard.md → README.md
☐ Update repository URL
☐ Update team contact info
☐ Update service URLs (API, database, Redis)
☐ Verify getting started works

SUBSYSTEM READMEs
☐ Create l9/core/agents/README.md
☐ Create l9/core/memory/README.md
☐ Create l9/core/tools/README.md
☐ Create l9/api/README.md
☐ Update file paths (match your repo)
☐ Add real component names
☐ Add actual code examples

METADATA
☐ Create README.meta.yaml (root)
☐ Create README.meta.yaml (each subsystem)
☐ Set ownership fields
☐ Define required sections

GOVERNANCE
☐ Update docs/architecture.md
☐ Update docs/ai-collaboration.md
☐ Define change gates (allowed/restricted/forbidden)
☐ Define escalation paths

CI/CD
☐ Add README validation to CI
☐ Check all required sections present
☐ Validate examples (if applicable)
☐ Prevent secrets in docs

TEAM
☐ Share root README with team
☐ Brief on "AI usage rules" section
☐ Train on subsystem READMEs (per subsystem)
☐ Add README.meta.yaml to code review checklist
```

---

## The Contract Is Enforced By:

### 1. **CI Validation**
```bash
python scripts/validate-readmes.py
# Checks: all required sections present, no secrets, format valid
```

### 2. **Code Review**
```
Reviewer asks:
- "Does this change touch forbidden scope?" → Reject if yes
- "Are tests passing?" → Required
- "Are docs updated?" → Required if APIs changed
```

### 3. **Ownership**
```
Each subsystem has an owner (in .meta.yaml)
- New contributors ask owner questions
- Owner reviews risky changes
- Owner keeps README in sync
```

### 4. **Automated Testing**
```
Tests verify: APIs work, invariants hold, data consistent
If tests fail: change is rejected (no exceptions)
```

---

## Example: Adding a New Agent Type

### You want to add a `DataAnalystKernel` agent.

**Step 1: Read the contract**
```bash
cat l9/core/agents/README.md
# Learn: Agents subsystem scope, APIs, invariants, AI rules
```

**Step 2: Check allowed scope**
```
Can I modify:
  ✅ l9/core/agents/builtin/data_analyst.py (new file)
  ✅ tests/unit/test_data_analyst.py (new tests)
  ❌ l9/core/agents/kernel.py (forbidden, entry point)
  ❌ l9/tool_registry.py (different subsystem)
```

**Step 3: Ask AI tool**
```
"Read l9/core/agents/README.md, then generate a DataAnalystKernel.
It should call SQL and visualization tools.
Include unit tests and update agents.md."
```

**Step 4: AI generates**
- New kernel class inheriting from `Kernel`
- Unit tests (happy path + error cases)
- Example in README
- Update to `agents.md` agent profiles

**Step 5: You review**
- Does it respect the contract? ✅
- Are tests passing? ✅
- Is code production-grade (no stubs)? ✅
- Are docs updated? ✅

**Step 6: Merge**
```bash
git merge feat/data-analyst-agent
```

---

## Pro Tips

### 🎯 Reading a README?

Start with:
1. **Overview** — What does this do?
2. **Responsibilities** — What does it own?
3. **Key Components** — What are the main APIs?
4. **AI Usage Rules** — What can I modify?

Then dive into specific sections as needed.

### 🔨 Writing a Subsystem README?

Use this template order:
1. Copy the template from `subsystem-readmes-complete.md`
2. Fill in **Subsystem Overview** (1 paragraph)
3. Fill in **Responsibilities & Boundaries** (understand what you own)
4. Fill in **Key Components** (list your actual classes)
5. Fill in **Data Models & Contracts** (your Pydantic schemas)
6. Fill in **API Surface** (your public functions)
7. Fill in **AI Usage Rules** (what's safe to change?)

### 🤖 Using AI Tools?

1. Always provide **pre-reading** documents (root README + subsystem README)
2. Always ask AI to **show its understanding** before coding
3. Always **review generated code** like any other contribution
4. Always **run tests** before merging

### 👀 Reviewing Others' Code?

Check:
1. Is the change in **allowed scope**? (check subsystem README)
2. Does it **preserve invariants**? (check data models section)
3. Are **tests passing**? (required)
4. Are **docs updated**? (required if APIs changed)

---

## One-Line Summary

> **READMEs as contracts: scope, APIs, invariants, AI rules. Enforced by CI, code review, and ownership.**

---

## Need Help?

- **Q: Where do I start?**  
  A: Read the root README, then your subsystem's README.

- **Q: What can I ask AI to modify?**  
  A: Check the "AI Usage Rules" section in the subsystem README.

- **Q: How do I update a README?**  
  A: Edit the relevant section, ensure all required sections are present, update the corresponding .meta.yaml.

- **Q: Who approves changes?**  
  A: Subsystem owner (listed in .meta.yaml). For restricted scope, they must review before merge.

---

**L9 Secure AI OS — Production-grade agent runtime with governance-first design.**

v1.0 | December 25, 2025 | Igor & Team
