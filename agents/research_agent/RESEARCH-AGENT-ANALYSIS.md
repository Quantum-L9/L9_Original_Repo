# Research Agent Analysis

**Purpose:** Identify existing research infrastructure in L9 for consolidation into `agents/research_agent/`
**Status:** /analyze+evaluate complete
**Date:** 2026-01-18

---

## 🔍 Existing Research Infrastructure in L9

### PRIMARY: `services/research/` (PRODUCTION-READY)

**This is a complete multi-agent research system using LangGraph.**

| Component             | File                                     | Status        | Description                                                                     |
| --------------------- | ---------------------------------------- | ------------- | ------------------------------------------------------------------------------- |
| **Research Graph**    | `services/research/research_graph.py`    | ✅ Production | LangGraph DAG: planning → research → merge → critic → finalize → store_insights |
| **Graph Runtime**     | `services/research/graph_runtime.py`     | ✅ Production | Lifecycle management, health checks                                             |
| **Graph State**       | `services/research/graph_state.py`       | ✅ Production | TypedDict state for LangGraph                                                   |
| **Research API**      | `services/research/research_api.py`      | ✅ Production | FastAPI router `/research`                                                      |
| **Memory Adapter**    | `services/research/memory_adapter.py`    | ✅ Production | Memory substrate integration                                                    |
| **Insight Extractor** | `services/research/insight_extractor.py` | ✅ Production | Extract insights → PacketEnvelope                                               |

**Agents:**
| Agent | File | Purpose |
|-------|------|---------|
| `PlannerAgent` | `services/research/agents/planner_agent.py` | Decompose query → steps |
| `ResearcherAgent` | `services/research/agents/researcher_agent.py` | Execute steps, gather evidence |
| `CriticAgent` | `services/research/agents/critic_agent.py` | Evaluate quality, approve/retry |
| `BaseAgent` | `services/research/agents/base_agent.py` | Common agent interface |

**Tools:**
| Tool | File | Purpose |
|------|------|---------|
| `PerplexityClient` | `services/research/tools/perplexity_client.py` | Perplexity API (v3.0.0 with retry) |
| `ToolWrappers` | `services/research/tools/tool_wrappers.py` | Tool function wrappers |
| `ToolResolver` | `services/research/tools/tool_resolver.py` | Dynamic tool resolution |

---

### SECONDARY: `orchestrators/research_swarm/` (ADVANCED)

**Concurrent research orchestration with convergence.**

| Component                    | File                                           | Purpose                            |
| ---------------------------- | ---------------------------------------------- | ---------------------------------- |
| `ResearchSwarmOrchestrator`  | `orchestrators/research_swarm/orchestrator.py` | Run N agents in parallel           |
| `Convergence`                | `orchestrators/research_swarm/convergence.py`  | Merge parallel results             |
| `IResearchSwarmOrchestrator` | `orchestrators/research_swarm/interface.py`    | Interface + request/response types |

---

### TERTIARY: Scripts & Schemas

| Location                                       | Purpose                       |
| ---------------------------------------------- | ----------------------------- |
| `scripts/research/run_single_deep_research.py` | CLI for single research task  |
| `scripts/research/delegate_deep_research.py`   | Delegation script             |
| `scripts/research/factory_extract.py`          | Factory extraction            |
| `core/schemas/research_factory_*.py`           | Pydantic schemas for research |
| `config/research_settings.py`                  | Research configuration        |

---

### API ROUTES

| Route                    | File                                | Purpose                |
| ------------------------ | ----------------------------------- | ---------------------- |
| `POST /research`         | `services/research/research_api.py` | Main research endpoint |
| `POST /research/agent/*` | `api/routes/research_agent.py`      | Agent-specific routes  |
| `/research/*`            | `api/routes/research.py`            | Additional routes      |

---

## 📋 RECOMMENDATION: What to Move to `agents/research_agent/`

### Option A: FACADE PATTERN (Recommended)

**Keep** `services/research/` as the production implementation.
**Create** `agents/research_agent/` as a simplified facade + CLI.

```
agents/research_agent/
├── __init__.py              # Export facade
├── research_facade.py       # Simple interface to services/research
├── cli.py                   # CLI commands (run_research, etc.)
├── prompts/                 # Superprompt templates for Perplexity
│   ├── deep_research.md
│   └── fact_extraction.md
└── README.md
```

**Why:**

- Don't duplicate production code
- `services/research/` already has LangGraph, memory integration, retry logic
- Facade provides simple entry point for Cursor/scripts

### Option B: FULL MIGRATION (Not Recommended)

Move everything from `services/research/` to `agents/research_agent/`.

**Why NOT:**

- Services are already well-organized
- Would break existing imports
- No architectural benefit

---

## 🔧 Action Plan

### PHASE 1: Create Facade (LOW RISK)

1. Create `agents/research_agent/__init__.py`
2. Create `agents/research_agent/research_facade.py`:

   - Import from `services.research`
   - Expose simple `run_research(query)` function
   - Add Perplexity-specific helpers

3. Create `agents/research_agent/cli.py`:
   - CLI for running research from terminal
   - Integration with superprompt workflow

### PHASE 2: Add Superprompt Templates

1. Create `agents/research_agent/prompts/`
2. Add templates for different research types:
   - Deep research
   - Fact extraction
   - README generation
   - Codebase analysis

### PHASE 3: Wire to Cursor

1. Update `.cursor/rules` to reference research agent
2. Add `/research` slash command
3. Integrate with memory write workflow

---

## ✅ Status of Existing Research Files in `perplexity_research_results/`

| File                                      | Status                   | Project                  | Next Action                         |
| ----------------------------------------- | ------------------------ | ------------------------ | ----------------------------------- |
| `PHASE-0-TODO-STAGE-4-BELIEF-REVISION.md` | **✅ TODO LOCKED**       | Memory Substrate Stage 4 | Execute GMP (separate from GMP-100) |
| `stage4_belief_revision_system.md`        | **✅ RESEARCH COMPLETE** | Memory Substrate Stage 4 | Reference during GMP execution      |
| `stage6_multi_agent_consensus.md`         | **⏳ FUTURE**            | Memory Substrate Stage 6 | Hold until Stage 4+5 complete       |

**These are NOT part of GMP-100 (README generation).** They are research outputs for the Memory Substrate enhancement project (Stages 4-6).

---

## 📊 Summary

| Aspect                | Current State                                  | Recommendation                                |
| --------------------- | ---------------------------------------------- | --------------------------------------------- |
| Research execution    | `services/research/`                           | ✅ Keep                                       |
| LangGraph DAG         | `services/research/research_graph.py`          | ✅ Keep                                       |
| Perplexity client     | `services/research/tools/perplexity_client.py` | ✅ Keep                                       |
| Research swarm        | `orchestrators/research_swarm/`                | ✅ Keep                                       |
| Simple facade         | ❌ Missing                                     | Create in `agents/research_agent/`            |
| CLI interface         | `scripts/research/*.py`                        | Consolidate to `agents/research_agent/cli.py` |
| Superprompt templates | ❌ Missing                                     | Create in `agents/research_agent/prompts/`    |

---

_Generated by /analyze+evaluate on 2026-01-18_
