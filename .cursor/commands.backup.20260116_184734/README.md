---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "1.0.0"
component_id: "DOC-CMDREADME-001"
component_name: "Commands README"
layer: "documentation"
domain: "commands"
type: "readme"
status: "active"
created: "2025-12-01T00:00:00Z"
updated: "2026-01-04T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "informational"
compliance_required: false
audit_trail: false
security_classification: "internal"
---

# L9 Cursor Commands

**Your AI-powered toolkit for L9 development.** These slash commands give you superpowers for exploring, building, and maintaining the L9 Secure AI OS.

---

## 📋 Quick Reference

| Command | What It Does | When to Use |
|---------|--------------|-------------|
| `/ynp` | Tells you your next best move | After any command, when stuck |
| `/rules` | Shows current rules and project state | Start of every session |
| `/plan` | Enterprise planning chain (analyze → reason → approve) | Strategic planning, complex features |
| `/analyze` | Quick exploration of code structure | New to a module, exploring |
| `/evaluate` | Deep audit for production readiness | Before commit, before deploy |
| `/analyze+evaluate` | Both combined with cross-referencing | Full picture before major work |
| `/reasoning` | Multi-modal reasoning (abductive/deductive/inductive) | Deep problem analysis, decisions |
| `/gmp` | Tracked code changes (/rules → /analyze → execute → /ynp) | All tracked changes, any tier |
| `/forge` | Fast autonomous execution, no stops | Quick builds, UX-tier work |
| `/harvest` | Extract code/insights from chat logs | After Perplexity/Claude sessions |
| `/wire` | Integrate generated files (redirects to /gmp for KERNEL) | After /harvest or /forge |
| `/consolidate` | Clean up files (redirects to /gmp for KERNEL) | Periodic maintenance |
| `/extract-chat` | Pull learnings from conversations | After important chats |
| `/lcto` | Start L9 locally | Morning startup, testing |
| `/pipeline-precommit` | Full audit + tests + CI before commit | Before every git commit |
| `/pipeline-midstream` | Recalibrate when feeling lost | Every 2-3 days of work |
| `/spec` | Generate system specification | Before /forge, new features |
| `/governance` | Strict compliance validation | Before commit, CI pipeline |
| `/clean+compress` | Remove noise, densify text | Before embeddings, after chats |
| `/extract+align` | Mine insights, align with governance | Mining legacy prompts, chats |

---

## 🎯 Commands Explained (Non-Technical)

### `/ynp` — Your Next Play

**What it does:** Looks at everything you're working on and tells you the single most important thing to do next.

**When to use:** 
- After finishing something and wondering "what now?"
- When you have too many options and need focus
- At the end of any other command (most auto-chain to this)

**Example:** After running `/evaluate`, YNP might say "Fix the bare except in service.py — it's blocking deploy."

---

### `/rules` — Load the Playbook + Auto-Route

**What it does:** Reads all project rules and state, then **automatically routes** to the right command:
- If work touches KERNEL files → routes to `/gmp` with Phase 0 TODO plan
- If work touches other files → routes to `/ynp` for next action

**When to use:**
- At the start of every work session
- When switching to a different part of the project
- Before any significant work

**Example:** Shows you're in Phase 2, detects KERNEL_TIER files in scope, auto-generates GMP TODO plan.

**Key benefit:** You don't need to remember when to use `/gmp` — `/rules` decides for you.

---

### `/plan` — Enterprise Planning Chain 🆕

**What it does:** Chains multiple commands into one comprehensive planning flow:
1. `/rules` → Load state and context
2. `/analyze_evaluate` → Deep analysis + evaluation
3. Synthesis → Create structured plan with options
4. `/reasoning` → Refine with multi-modal reasoning (abductive/deductive/inductive)
5. Approval generation → Package for Igor approval
6. `/ynp` → Recommend next action

**When to use:**
- Before implementing complex features
- When multiple implementation paths exist
- Strategic planning requiring approval
- Need optimal path with risk assessment
- L9-grade enterprise planning

**Think of it as:** The master planner that analyzes, synthesizes, reasons, and packages everything for approval — all in one command.

**Output includes:**
- Structure map + health scan + cross-references
- Multiple implementation options with pros/cons
- Multi-modal reasoning refinement with confidence scores
- GMP-ready TODO plan for immediate execution
- Risk assessment with mitigations

**Flags:**
- `--quick` — Skip reasoning refinement (faster)
- `--time 2h` — Constrain plan to time budget
- `--risk LOW` — Set risk tolerance
- `--gmp-ready` — Output GMP Action file directly

**Example:** `/plan "Add WebSocket support to Slack adapter"` produces a complete plan with 3 options, recommends option B, includes 5 TODOs, and a YNP to execute with `/gmp`.

---

### `/analyze` — Quick Look Around

**What it does:** Quickly maps out a piece of code — what it does, how it's structured, where the important parts are.

**When to use:**
- First time looking at code you didn't write
- Want to understand how something works
- Need a quick orientation before diving in

**Think of it as:** A 30-second tour of a new neighborhood.

---

### `/evaluate` — Deep Inspection

**What it does:** Thoroughly checks if code is production-ready — tests, patterns, compliance, everything.

**When to use:**
- Before committing changes
- Before deploying to production
- When preparing for code review

**Think of it as:** A home inspection before buying.

---

### `/analyze+evaluate` — Full Picture

**What it does:** Combines quick exploration with deep audit, plus finds connections between issues.

**When to use:**
- Before major refactoring
- Comparing two modules
- Need complete understanding before changing anything

**Special power:** Shows "if you fix X, it unblocks Y and Z" — helps prioritize.

---

### `/gmp` — The One Powerful Command

**What it does:** Makes tracked code changes through a complete chain:
1. Calls `/rules` at start (loads state + protocols)
2. Calls `/analyze` if your request is unclear (clarifies scope)
3. Executes 7-phase protocol (plan → implement → validate)
4. Calls `/ynp` at end (recommends next action)

**When to use:**
- Any code change you want tracked
- Changes to any tier (KERNEL, RUNTIME, INFRA, UX)
- When you want full audit trail

**Think of it as:** The complete pipeline — context in, code change + audit trail out.

**Note:** No "quick mode" — just one rigorous, unified protocol.

---

### `/forge` — Fast Building

**What it does:** Builds things quickly and autonomously — no stopping to ask questions.

**When to use:**
- Simple additions and fixes
- Non-critical code (docs, scripts, UI)
- When you've already answered the "what to build" questions

**Think of it as:** A skilled craftsman who just needs the blueprint and builds without interruption.

**⚠️ Note:** Won't work on critical files (use /gmp for those).

---

### `/harvest` — Extract from Chats

**What it does:** Reads through chat transcripts and pulls out all the useful bits — code, configs, decisions, lessons learned.

**When to use:**
- After a long Perplexity research session
- After working through a problem with Claude
- When you have valuable code buried in conversation

**Example:** Feed it a 2000-line chat, get back organized files + insights + lessons.

---

### `/wire` — Connect the Pieces

**What it does:** Takes generated files and properly integrates them into the codebase — adds imports, registers routes, etc.

**When to use:**
- After /harvest extracts files
- After /forge creates new modules
- Whenever you have files in generated/ that need to work

**Think of it as:** The electrician who connects new appliances to the house wiring.

---

### `/consolidate` — Spring Cleaning

**What it does:** Finds duplicates, orphans, and messy organization, then cleans it up.

**When to use:**
- Periodically (every few weeks)
- When the codebase feels cluttered
- Before major architectural changes

**Think of it as:** Marie Kondo for your codebase.

---

### `/extract-chat` — Learn from History

**What it does:** Reads chat histories and extracts strategic decisions, tactical preferences, and lessons learned.

**When to use:**
- After important planning sessions
- After debugging sessions with insights
- To build up project knowledge base

**Think of it as:** Taking notes from a meeting you want to remember.

---

### `/lcto` — Start L9 Locally

**What it does:** Starts the L9 system on your local machine with all dependencies.

**When to use:**
- Start of day
- After restarting your computer
- Before testing changes locally

**Example:** One command instead of starting Postgres, Redis, and the server separately.

---

### `/pipeline-precommit` — Gate Before Commit

**What it does:** Runs a full audit before you commit — analysis, governance checks, then tells you if you're clear to commit.

**When to use:**
- Before EVERY commit
- Before merging to main
- Before creating a PR

**Think of it as:** TSA checkpoint before boarding — catches problems before they fly.

---

### `/pipeline-midstream` — Recalibrate

**What it does:** Cleans up accumulated noise, compresses context, and refocuses your priorities.

**When to use:**
- Every 2-3 days of active work
- When you feel lost or overwhelmed
- After returning from a break

**Think of it as:** Stopping to check the map and clean your glasses during a hike.

---

### `/spec` — System Specification

**What it does:** Generates a complete specification document — goals, constraints, design, acceptance criteria, roadmap.

**When to use:**
- Before building any new feature
- When clarifying what to build
- Before major architectural changes

**Think of it as:** The blueprint before construction begins.

---

### `/governance` — Compliance Check

**What it does:** Validates code against L9 rules — headers, versions, patterns, policies.

**When to use:**
- Before committing (part of pipeline-precommit)
- In CI/CD pipelines
- After bulk changes

**Think of it as:** The building inspector checking everything is up to code.

---

### `/clean+compress` — Text Transformation

**What it does:** Takes noisy text (chat dumps, raw notes) and transforms it into clean, dense, embedding-ready format.

**When to use:**
- After chat dumps
- Before storing in knowledge base
- Preparing text for vector embeddings

**Think of it as:** A professional editor distilling a rambling draft into crisp prose.

---

### `/extract+align` — Insight Mining

**What it does:** Mines text for decisions, rules, patterns, and preferences, then aligns them with L9 governance.

**When to use:**
- After long planning sessions
- Mining old prompts for reusable knowledge
- Building project knowledge base

**Think of it as:** An archaeologist extracting artifacts and cataloging them properly.

---

## 🔗 Command Chains

Commands work together. Here are common flows:

### Starting a Session
```
/rules → /ynp → [work]
```

### Enterprise Planning (NEW)
```
/plan "implement feature X"
  ↓
/rules → /analyze_evaluate → Synthesis → /reasoning → Approval → /ynp
  ↓
/gmp (if approved)
```

### Exploring New Code
```
/analyze → /evaluate (if deeper needed) → /gmp (if fixing)
```

### Building Something
```
/forge → /wire → /evaluate → /ynp
```

### Extracting from Research
```
/harvest @chat.md → /wire → /ynp
```

### Before Committing
```
/pipeline-precommit → [fix if needed] → git commit
```

### Daily Maintenance
```
/pipeline-midstream → /ynp → [work on top priority]
```

---

## ⚡ Auto-Chaining

Most commands automatically run `/ynp` at the end, so you always know what to do next:

| Command | Auto-chains to |
|---------|----------------|
| `/plan` | `/analyze_evaluate` → `/reasoning` → `/ynp` |
| `/analyze` | `/ynp` |
| `/evaluate` | `/ynp` |
| `/analyze+evaluate` | `/ynp` |
| `/reasoning` | `/ynp` |
| `/forge` | `/ynp` |
| `/harvest` | `/ynp` |
| `/wire` | `/ynp` |
| `/consolidate` | `/ynp` |
| `/extract-chat` | `/ynp` |
| `/pipeline-precommit` | `/ynp` |
| `/pipeline-midstream` | `/ynp` |
| `/spec` | `/ynp` |
| `/governance` | `/ynp` |
| `/clean+compress` | `/ynp` |
| `/extract+align` | `/ynp` |
| `/gmp` | `/ynp` |

---

## 🎚️ Tier Awareness + Auto-Routing

Commands automatically adjust behavior and **redirect to /gmp** when KERNEL files are involved:

| Tier | What It Is | Command Behavior |
|------|------------|------------------|
| **KERNEL** | Core systems (executor, memory, governance) | **Auto-redirect to `/gmp`** |
| **RUNTIME** | Support systems (tools, queues, agents) | Extra validation |
| **INFRA** | Deployment (Docker, configs, scripts) | Focus on env vars |
| **UX** | Interface (docs, UI, scripts) | Full `/forge` autonomy |

### KERNEL_TIER Protection (Auto-Redirect)

These files **always** trigger redirect to `/gmp`:
- `core/kernels/kernel_loader.py`
- `core/agents/executor.py`
- `memory/substrate_service.py`
- `runtime/websocket_orchestrator.py`
- `docker-compose.yml`
- Any file in `kernels/` directory

**Commands that auto-redirect:** `/rules`, `/forge`, `/wire`, `/consolidate`

---

## 📁 File Locations

All commands live in:
```
.cursor-commands/commands/
```

Each command is a `.md` file you can read to understand the full protocol.

---

## 💡 Tips

1. **Start every session with `/rules`** — know where you are before you start
2. **Use `/ynp` when stuck** — it always has an answer
3. **Use `/forge` for speed, `/gmp` for safety** — pick based on risk
4. **Run `/pipeline-precommit` before every commit** — no exceptions
5. **Recalibrate every 2-3 days with `/pipeline-midstream`** — prevents drift

---

## 🆘 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| "Which command do I use?" | Start with `/analyze`, it'll recommend next steps |
| "Too many things to do" | Run `/ynp` for the single most important action |
| "Need to plan something complex" | Run `/plan "description"` for full enterprise planning |
| "Feeling lost" | Run `/pipeline-midstream` to recalibrate |
| "About to commit" | Run `/pipeline-precommit` first |
| "Have code in a chat" | Run `/harvest @chat.md` then `/wire` |
| "Multiple implementation options" | Run `/plan` to analyze, synthesize, and reason through them |

---

*These commands are L9-native — they understand the project structure, respect the governance rules, and always guide you toward the right next action.*

