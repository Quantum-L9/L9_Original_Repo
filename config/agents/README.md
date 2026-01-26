# L9 Agent Configurations

Agent YAML manifests defining identity, capabilities, tools, and governance for L9 AI agents.

## Agent Catalog

| Agent                | ID                    | Model             | Status     | Purpose                                        |
| -------------------- | --------------------- | ----------------- | ---------- | ---------------------------------------------- |
| **L-CTO Agent**      | `l-cto`               | Claude 3.5 Sonnet | Production | Igor-only CTO. Kernel-governed with HITL gates |
| **L-CTO Research**   | `l-cto-research`      | Claude 3.5 Sonnet | Production | L-CTO in research mode (overlay)               |
| **Research Agent**   | `research-agent-v1`   | Perplexity Sonar  | Production | Deep research + spec generation                |
| **Reflection Agent** | `reflection-agent-v1` | GPT-4o            | Production | Meta-reasoning, failure analysis               |
| **Standard Agent**   | `l9-standard-v1`      | GPT-4o            | Production | Default general assistant                      |

---

## Agent Files

### `L-CTO-Agent.yaml` — Primary CTO Agent

The kernel-governed L-CTO agent with full tool authority.

```yaml
agent_id: l-cto
model: claude-3-5-sonnet-20241022
temperature: 0.7
```

**Key Features:**

- **10 System Kernels** loaded from `private/kernels/00_system/`
- **Tool Tiering:** T1 (read-only), T2 (HITL), T3 (Igor approval)
- **GODMODE Parts 1-7** compliance
- **ISO 42001 + NIST AI RMF + OpenAI Tier 2-3** governance

**Tool Categories:**

- T1: Memory search, Neo4j query, kernel read, reflection agent tools
- T2: Redis operations, MCP tool calls, plan simulation
- T3: Memory write, GMP run, git commit, mac agent exec

**Python Binding:** `runtime/kernel_loader.py`, `runtime/execution_gate.py`

---

### `L-CTO-Research-Overlay.yaml` — Research Mode

Overlay for L-CTO when conducting deep analysis tasks.

```yaml
agent_id: l-cto-research
model: claude-3-5-sonnet-20241022
temperature: 0.8 # Higher for creativity
```

**Research Methodology (5-Phase):**

1. PLAN — Define scope, identify gaps
2. RESEARCH — Gather via Perplexity, graph queries
3. CRITIQUE — Challenge assumptions
4. SYNTHESIZE — Integrate findings
5. CITE — Traceable sources

**Additional Tools:**

- `research_agent_synthesize` (T1) — Fast multi-perspective synthesis
- `research_agent_discover` (T2) — Deep 5-stage research
- `research_agent_generate_spec` (T1) — Module-Spec-v2.4 YAML

---

### `research-agent-v1.yaml` — Research Agent

Perplexity-powered research and spec generation.

```yaml
agent_id: research-agent-v1
model: sonar-reasoning
provider: perplexity
```

**Capabilities:**
| Method | Description | Duration |
|--------|-------------|----------|
| `synthesize(topic, context)` | Multi-perspective synthesis | ~10 min |
| `discover(topic, domain, stages)` | 5-stage academic research | 15-25 hrs |
| `generate_spec(synthesis, topic)` | Module-Spec-v2.4 YAML | ~1 min |
| `research_to_code(topic, mode)` | End-to-end pipeline | Varies |

**Prompt Variations:** Pragmatic, Research, Systems, Agents, Multimodal

**Python Class:** `agents.research_agent.ResearchAgent`

---

### `reflection-agent-v1.yaml` — Reflection Agent

Meta-reasoning and self-improvement agent.

```yaml
agent_id: reflection-agent-v1
model: gpt-4o
temperature: 0.6
```

**Capabilities:**
| Method | Description |
|--------|-------------|
| `run(task, context)` | Reflect on execution history |
| `analyze_failure(context, error)` | Root cause analysis |
| `compare_approaches(a, b, criteria)` | Compare with scoring |
| `extract_patterns(examples)` | Pattern extraction |
| `generate_improvements(perf, goals)` | Improvement plans |

**Python Class:** `agents.reflection_agent.ReflectionAgent`

---

### `l9-standard-v1.yaml` — Standard Agent

Default general-purpose L9 assistant.

```yaml
agent_id: l9-standard-v1
model: gpt-4o
temperature: 0.3
```

**Tools:** `web_search`, `read_file`, `write_file`

**Use Case:** General queries, simple tasks, default fallback

---

## Architecture

```
config/agents/
├── L-CTO-Agent.yaml          # Primary CTO (kernel-governed)
├── L-CTO-Research-Overlay.yaml   # Research mode overlay
├── research-agent-v1.yaml    # Perplexity research
├── reflection-agent-v1.yaml  # Meta-reasoning
├── l9-standard-v1.yaml       # Default assistant
└── README.md                 # This file
```

## Runtime Integration

| File                        | Purpose                              |
| --------------------------- | ------------------------------------ |
| `runtime/kernel_loader.py`  | Load kernels into KernelState        |
| `runtime/kernel_state.py`   | KernelState object                   |
| `runtime/execution_gate.py` | `guarded_execute()` with tier checks |
| `runtime/introspection.py`  | Post-execution audit                 |
| `config/boot_overlay.yaml`  | Tool authorization matrix            |

## Governance

### Tool Tiers

| Tier   | Description                  | Approval                   |
| ------ | ---------------------------- | -------------------------- |
| **T1** | Read-only, automated         | None                       |
| **T2** | Reversible, rollback capable | HITL approval              |
| **T3** | Irreversible, high-impact    | **Igor explicit approval** |

### Compliance

- **ISO 42001** — AI Management Systems (Plan-Do-Check-Act)
- **NIST AI RMF** — Govern-Map-Measure-Manage
- **OpenAI Tier 2-3** — Human-in-the-loop enforcement

## Environment Variables

| Variable              | Required By          | Purpose                  |
| --------------------- | -------------------- | ------------------------ |
| `OPENAI_API_KEY`      | Reflection, Standard | OpenAI API access        |
| `PERPLEXITY_API_KEY`  | Research Agent       | Perplexity API access    |
| `ANTHROPIC_API_KEY`   | L-CTO                | Claude API access        |
| `L9_EXECUTOR_API_KEY` | All (API)            | Authenticated API access |

## Adding New Agents

1. Create `config/agents/{agent-name}-v1.yaml`
2. Define: `agent_id`, `model`, `system_prompt`, `tools`, `capabilities`
3. If kernel-governed: Set `kernel_absorption_required: true`
4. Add Python class in `agents/{agent_name}.py`
5. Wire API routes in `api/routes/`
6. Update this README

---

**Updated:** 2026-01-16
**Owner:** L9 System
