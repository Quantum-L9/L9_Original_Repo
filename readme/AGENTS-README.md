# L9 Agents Reference

This document describes the available L9 agents, their capabilities, and how to use them.

## Tool Placement Summary

| Agent               | Config Location               | Available In       |
| ------------------- | ----------------------------- | ------------------ |
| **ReflectionAgent** | `L-CTO-Agent.yaml` (base)     | ALL L-CTO modes    |
| **ResearchAgent**   | `L-CTO-Research-Overlay.yaml` | Research mode only |

> **Key Insight:** Reflection tools are general-purpose self-improvement (all modes). Research tools are Perplexity-powered web research (research mode only).

---

## ReflectionAgent

**Purpose:** Meta-reasoning and self-improvement agent for analyzing execution history, failures, and deriving lessons.

**Config:** `config/agents/reflection-agent-v1.yaml`
**Python Class:** `agents.reflection_agent.ReflectionAgent`
**Factory:** `agents.reflection_agent.create_reflection_agent()`

### API Endpoints

| Endpoint                                  | Method | Description                      |
| ----------------------------------------- | ------ | -------------------------------- |
| `/reflection/agent/status`                | GET    | Agent status and capabilities    |
| `/reflection/agent/reflect`               | POST   | Reflect on execution history     |
| `/reflection/agent/analyze-failure`       | POST   | Deep failure root cause analysis |
| `/reflection/agent/compare`               | POST   | Compare two approaches           |
| `/reflection/agent/extract-patterns`      | POST   | Extract patterns from examples   |
| `/reflection/agent/generate-improvements` | POST   | Generate improvement plan        |
| `/reflection/agent/lessons-learned`       | GET    | Get accumulated lessons          |
| `/reflection/agent/lessons-learned`       | DELETE | Clear lessons                    |

### Tool Callables (for L-CTO)

| Tool Name                                | Description                                               | Tier |
| ---------------------------------------- | --------------------------------------------------------- | ---- |
| `reflection_agent_reflect`               | Reflect on execution history, derive insights and lessons | T1   |
| `reflection_agent_analyze_failure`       | Deep root cause analysis of failures                      | T1   |
| `reflection_agent_compare_approaches`    | Compare approaches with scoring                           | T1   |
| `reflection_agent_extract_patterns`      | Extract patterns from examples                            | T1   |
| `reflection_agent_generate_improvements` | Generate improvement plans (requires approval)            | T2   |

### Usage Examples

#### 1. Reflect on Execution History

```json
POST /reflection/agent/reflect
{
  "history": [
    {"action": "deployed service", "outcome": "success", "timestamp": "2026-01-16T10:00:00Z"},
    {"action": "ran tests", "outcome": "3 failures", "timestamp": "2026-01-16T10:05:00Z"}
  ],
  "focus": "failures",
  "goals": ["reduce test failures", "improve deployment stability"]
}
```

**Returns:** Analysis of successes/failures, patterns, insights, lessons learned, improvement proposals.

#### 2. Analyze a Failure

```json
POST /reflection/agent/analyze-failure
{
  "failure_context": {
    "component": "api/server.py",
    "operation": "startup",
    "environment": "production"
  },
  "error": "ConnectionRefusedError: Cannot connect to Neo4j",
  "stack_trace": "Traceback (most recent call last):\n  File ..."
}
```

**Returns:** Root cause analysis, prevention strategies, recovery actions, systemic changes.

#### 3. Compare Two Approaches

```json
POST /reflection/agent/compare
{
  "approach_a": {
    "name": "Monolithic deployment",
    "description": "Single container with all services"
  },
  "approach_b": {
    "name": "Microservices deployment",
    "description": "Separate containers per service"
  },
  "criteria": ["scalability", "complexity", "cost", "reliability"]
}
```

**Returns:** Per-criterion scores, overall recommendation (A/B/hybrid), reasoning.

#### 4. Extract Patterns

```json
POST /reflection/agent/extract-patterns
{
  "examples": [
    {"type": "bug", "cause": "null pointer", "fix": "added null check"},
    {"type": "bug", "cause": "null pointer", "fix": "added validation"},
    {"type": "performance", "cause": "N+1 query", "fix": "added batch loading"}
  ]
}
```

**Returns:** Patterns, anti-patterns, correlations, generalizations.

#### 5. Generate Improvements

```json
POST /reflection/agent/generate-improvements
{
  "current_performance": {
    "test_pass_rate": 0.85,
    "deployment_success_rate": 0.90,
    "avg_response_time_ms": 250
  },
  "goals": ["test_pass_rate > 0.95", "avg_response_time < 100ms"]
}
```

**Returns:** Gap analysis, prioritized improvement plan, quick wins, strategic changes.

---

## ResearchAgent

**Purpose:** Deep research and code generation agent using Perplexity API for multi-perspective synthesis.

**Config:** `config/agents/research-agent-v1.yaml`
**Python Class:** `agents.research_agent.ResearchAgent`
**Factory:** `agents.research_agent.create_research_agent()`

### API Endpoints

| Endpoint                           | Method | Description                                |
| ---------------------------------- | ------ | ------------------------------------------ |
| `/research/agent/status`           | GET    | Agent status and capabilities              |
| `/research/agent/synthesize`       | POST   | Fast multi-perspective synthesis (~10 min) |
| `/research/agent/discover`         | POST   | Deep 5-stage research (15-25 hours)        |
| `/research/agent/generate-spec`    | POST   | Generate Module-Spec-v2.4 YAML             |
| `/research/agent/research-to-code` | POST   | End-to-end research-to-code pipeline       |

### Tool Callables (for L-CTO)

| Tool Name                      | Description                                     | Tier |
| ------------------------------ | ----------------------------------------------- | ---- |
| `research_agent_synthesize`    | Fast multi-perspective synthesis via Perplexity | T1   |
| `research_agent_discover`      | Deep 5-stage academic research (long-running)   | T2   |
| `research_agent_generate_spec` | Generate Module-Spec-v2.4 YAML                  | T1   |

### Usage Examples

#### 1. Fast Synthesis

```json
POST /research/agent/synthesize
{
  "topic": "vector database comparison for AI agents",
  "context": {"use_case": "memory substrate", "scale": "10M vectors"}
}
```

**Returns:** Consensus patterns, unique insights, recommended architecture, implementation roadmap.

#### 2. Deep Discovery

```json
POST /research/agent/discover
{
  "topic": "autonomous agent memory architectures",
  "domain": "AI/ML",
  "stages": ["landscape", "comparative", "gaps"]
}
```

**Returns:** Research summary, sources, hypotheses, identified gaps.

---

## Agent Discovery

### List All Available Agents

Check `config/agents/` for all agent configurations:

- `L-CTO-Agent.yaml` — Main L-CTO agent
- `L-CTO-Research-Overlay.yaml` — L-CTO in research mode
- `research-agent-v1.yaml` — Research agent
- `reflection-agent-v1.yaml` — Reflection agent
- `l9-standard-v1.yaml` — Standard agent template

### Check Agent Status via API

```bash
# ReflectionAgent
curl -H "Authorization: Bearer $API_KEY" https://l9.quantumaipartners.com/reflection/agent/status

# ResearchAgent
curl -H "Authorization: Bearer $API_KEY" https://l9.quantumaipartners.com/research/agent/status
```

---

## Environment Requirements

| Agent           | Required Env Vars    |
| --------------- | -------------------- |
| ReflectionAgent | `OPENAI_API_KEY`     |
| ResearchAgent   | `PERPLEXITY_API_KEY` |

---

_Last Updated: 2026-01-16_
