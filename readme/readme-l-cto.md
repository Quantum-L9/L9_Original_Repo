# L-CTO: Igor's CTO Agent

## Overview

**L-CTO** is the primary autonomous agent in the L9 Secure AI OS — Igor's CTO, systems architect, and trusted executor. L operates under a governance-first design with deterministic kernel-based initialization, safety constraints, and full memory substrate integration.

**What L does:**

- Acts as Igor's autonomous CTO — executes tasks, manages systems, and makes decisions
- Operates under 10 YAML kernel constraints (identity, safety, behavior, execution)
- Emits PacketEnvelopes to memory substrate for full audit trails
- Integrates with Slack, HTTP, and WebSocket for multi-channel communication
- Dispatches 12+ tools with governance-gated approval for high-risk operations

**What L is NOT:**

- A general-purpose chatbot or assistant
- Permission-seeking — L operates in executive mode
- Unaccountable — all decisions logged to memory substrate

---

## Architecture

### System Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         L-CTO SYSTEM ARCHITECTURE                           │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌──────────────────┐
                              │  api/server.py   │
                              │    (lifespan)    │
                              └────────┬─────────┘
                                       │
                                       ▼
                    ┌──────────────────────────────────────┐
                    │   core/agents/kernel_registry.py     │
                    │      KernelAwareAgentRegistry        │
                    │                                      │
                    │  • _initialize_with_kernels()        │
                    │  • Creates AgentConfig with kernels  │
                    │  • Sets L9_KERNEL_STATE = ACTIVE     │
                    └──────────────────┬───────────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              │                        │                        │
              ▼                        ▼                        ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│ runtime/            │  │ agents/l_cto.py     │  │ private/kernels/    │
│ kernel_loader.py    │  │                     │  │ 00_system/          │
│                     │  │   LCTOAgent         │  │                     │
│ • load_kernels()    │  │   • absorb_kernels()│  │ • 01_master_kernel  │
│ • parse YAML        │  │   • run()           │  │ • 02_identity       │
│ • validate kernels  │  │   • emit_reasoning  │  │ • 08_safety         │
└─────────────────────┘  │     _packet()       │  │ • etc. (10 kernels) │
                         └─────────────────────┘  └─────────────────────┘
                                       │
                                       ▼
                         ┌─────────────────────────┐
                         │  core/agents/executor.py│
                         │  AgentExecutorService   │
                         │                         │
                         │  • Pre-exec governance  │
                         │  • validate_authority() │
                         │  • validate_safety()    │
                         │  • Post-exec audit_log()│
                         └───────────┬─────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
              ▼                      ▼                      ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│ core/agents/        │  │ memory/             │  │ core/governance/    │
│ aios_runtime.py     │  │ substrate_service.py│  │ validation.py       │
│                     │  │                     │  │                     │
│ AIOSRuntime         │  │ MemorySubstrate     │  │ • validate_authority│
│ • execute_reasoning │  │   Service           │  │ • validate_safety   │
│ • LLM calls         │  │ • ingest_packet()   │  │ • detect_drift      │
│ • tool dispatch     │  │ • PacketEnvelopeIn  │  │ • audit_log         │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
```

### Core Subsystems

| Subsystem         | File                             | Purpose                                |
| ----------------- | -------------------------------- | -------------------------------------- |
| **Entry Point**   | `api/server.py`                  | FastAPI lifespan, initializes registry |
| **Registry**      | `core/agents/kernel_registry.py` | Creates kernel-aware agents            |
| **Kernel Loader** | `runtime/kernel_loader.py`       | Parses 10 YAML kernels                 |
| **Agent**         | `agents/l_cto.py`                | LCTOAgent with kernel absorption       |
| **Executor**      | `core/agents/executor.py`        | Governance + execution loop            |
| **Runtime**       | `core/agents/aios_runtime.py`    | LLM calls + tool dispatch              |
| **Memory**        | `memory/substrate_service.py`    | Packet ingestion                       |
| **Governance**    | `core/governance/validation.py`  | Authority/safety checks                |

---

## Kernel Stack

L-CTO is governed by **10 system kernels** loaded in sequence at startup:

| #   | Kernel                        | Purpose                                            |
| --- | ----------------------------- | -------------------------------------------------- |
| 01  | `master_kernel.yaml`          | Sovereignty, executive mode, Igor allegiance       |
| 02  | `identity_kernel.yaml`        | L designation, CTO role, traits, anti-traits       |
| 03  | `cognitive_kernel.yaml`       | Reasoning patterns, context engine                 |
| 04  | `behavioral_kernel.yaml`      | Thresholds, prohibitions, defaults                 |
| 05  | `memory_kernel.yaml`          | Memory architecture, substrate interface           |
| 06  | `worldmodel_kernel.yaml`      | World state, context awareness                     |
| 07  | `execution_kernel.yaml`       | State machine, task sizing, execution flow         |
| 08  | `safety_kernel.yaml`          | Guardrails, prohibited actions, confirmation gates |
| 09  | `developer_kernel.yaml`       | L9 coding patterns, testing discipline             |
| 10  | `packet_protocol_kernel.yaml` | PacketEnvelope emission, audit logging             |

**Kernel Location:** `private/kernels/00_system/`

### Kernel Activation Flow

1. `api/server.py` lifespan calls `KernelAwareAgentRegistry._initialize_with_kernels()`
2. `runtime/kernel_loader.py:load_kernels()` parses all 10 YAML files
3. Each kernel calls `LCTOAgent.absorb_kernel()` to merge configuration
4. `kernel_loader.py:require_kernel_activation()` sets `kernel_state = "ACTIVE"`
5. Agent is now fully operational with all constraints applied

---

## Capabilities

### Tools Available (12 Tools)

| Tool Name       | Capability                   | Approval Required |
| --------------- | ---------------------------- | ----------------- |
| `LCHAT`         | LLM chat and reasoning       | No                |
| `MEMORY_SEARCH` | Semantic memory search       | No                |
| `MEMORY_WRITE`  | Write to memory substrate    | No                |
| `RESEARCH`      | Deep research with citations | No                |
| `READFILE`      | Read files from filesystem   | No                |
| `WEBSEARCH`     | Search the web               | No                |
| `SIMULATION`    | Run simulation engine        | Yes               |
| `MACAGENTEXEC`  | Execute on Mac agent         | **Yes**           |
| `GMPRUN`        | Run GMP execution            | **Yes**           |
| `GITCOMMIT`     | Git commit operations        | **Yes**           |
| `VPSEXEC`       | VPS command execution        | **Yes**           |
| `SLACKPOST`     | Post to Slack                | No                |

### Capability Profiles

L-CTO operates with `LCapabilities.FULL` profile:

```python
class LCapabilities(str, Enum):
    MINIMAL = "minimal"  # chat only
    STANDARD = "standard"  # + memory + research
    FULL = "full"  # + all tools with governance
    SYSTEM = "system"  # + unrestricted (Igor only)
```

---

## Test Status

### Verification Tests (46 Total)

| Category            | Tests | Status  |
| ------------------- | ----- | ------- |
| Kernel Activation   | 12    | ✅ PASS |
| Executor Core       | 17    | ✅ PASS |
| Executor Governance | 5     | ✅ PASS |
| L-CTO End-to-End    | 12    | ✅ PASS |

**Test Files:**

- `tests/test_l_cto_kernel_activation.py` — Kernel loading and absorption
- `tests/core/agents/test_executor.py` — Executor core functionality
- `tests/core/agents/test_executor_governance.py` — Governance validation
- `tests/integration/test_l_cto_end_to_end.py` — Full integration flow

### Running Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run all L-CTO tests
python -m pytest tests/test_l_cto_kernel_activation.py \
  tests/core/agents/test_executor.py \
  tests/core/agents/test_executor_governance.py \
  tests/integration/test_l_cto_end_to_end.py \
  -v

# Run with coverage
python -m pytest tests/test_l_cto_kernel_activation.py -v --cov=agents.l_cto
```

---

## Identity & Behavioral Constraints

### Identity (from `02_identity_kernel.yaml`)

| Attribute        | Value                       |
| ---------------- | --------------------------- |
| **Designation**  | L                           |
| **Primary Role** | CTO for Igor                |
| **Allegiance**   | Igor-only (absolute)        |
| **Mode**         | Executive (autonomous)      |
| **Style**        | Direct, technical, decisive |

### Traits

- Autonomous action over permission-seeking
- Technical depth and precision
- Decisive execution
- Direct communication
- Continuous improvement

### Anti-Traits (NEVER)

- Hedging or excessive caveats
- Permission-seeking behavior
- Verbose explanations without action
- Breaking production without approval
- Ignoring safety constraints

### Behavioral Thresholds (from `04_behavioral_kernel.yaml`)

| Threshold       | Value | Description                                        |
| --------------- | ----- | -------------------------------------------------- |
| `execute`       | 0.8   | Minimum confidence to execute without confirmation |
| `questions_max` | 1     | Maximum clarifying questions before acting         |
| `hedges_max`    | 0     | Maximum hedging phrases allowed (zero tolerance)   |

### Prohibited Patterns

L is trained to avoid these patterns via kernel constraints:

1. **Permission hedges**: "Would you like me to...", "Should I..."
2. **Uncertainty dumps**: "I'm not sure but...", "This might be..."
3. **Excessive caveats**: "However, it's important to note..."
4. **Passive voice**: "It was determined that..."
5. **Verbose preambles**: "Let me explain the context..."
6. **Over-qualification**: "In most cases, generally speaking..."

---

## Safety & Governance

### Safety Boundaries (from `08_safety_kernel.yaml`)

1. **File Changes**: Only when `project_id` and `file_path` are unambiguous
2. **Destructive Actions**: Require explicit confirmation
3. **Production Changes**: Require Igor approval or GMPRUN gate
4. **Secrets**: Never hardcode, never commit
5. **External Systems**: Rate-limited, timeout-protected

### Approval Gates

High-risk tools require explicit Igor approval before dispatch:

```python
# Tools requiring approval
HIGH_RISK_TOOLS = {
    "GMPRUN",
    "GITCOMMIT",
    "MACAGENTEXEC",
    "VPSEXEC",
}

# Executor checks before dispatch
if tool_name in HIGH_RISK_TOOLS:
    if not has_igor_approval(task):
        return BlockedResult(reason="Requires Igor approval")
```

### Governance Validation Flow

1. **Pre-execution**: `validate_authority()` checks agent capabilities
2. **Pre-execution**: `validate_safety()` checks task against safety kernel
3. **Post-execution**: `audit_log()` records decision to memory substrate

---

## Slack Integration

L-CTO integrates with Slack for direct communication with Igor.

### Scopes Required

| Scope               | Purpose                 |
| ------------------- | ----------------------- |
| `app_mentions:read` | View @L-CTO mentions    |
| `assistant:write`   | Act as App Agent        |
| `channels:history`  | View channel messages   |
| `channels:join`     | Join public channels    |
| `chat:write`        | Send messages as @L-CTO |
| `files:write`       | Upload files            |
| `im:history`        | View DM history         |
| `im:read`           | View DM info            |
| `im:write`          | Start DMs               |
| `reactions:read`    | View emoji reactions    |

### Webhook Flow

```
Slack Event → webhook_slack.py → TaskRouter → AgentExecutorService → L-CTO → Response → Slack
```

---

## Memory Integration

L-CTO emits PacketEnvelopes to the memory substrate for all operations:

### Packet Types

| Packet Type                     | When Emitted            |
| ------------------------------- | ----------------------- |
| `agent.l_cto.reasoning`         | After each `run()` call |
| `agent.executor.task_started`   | Task begins             |
| `agent.executor.tool_call`      | Tool dispatched         |
| `agent.executor.task_completed` | Task finishes           |
| `agent.executor.error`          | Error occurs            |

### Packet Structure

```python
PacketEnvelopeIn(
    packet_type="agent.l_cto.reasoning",
    payload={
        "task": {"message": "...", "context": {}},
        "response": {
            "content": "...",
            "success": True,
            "tokens_used": 1234,
            "duration_ms": 567,
        },
        "agent_id": "l-cto",
    },
    metadata=PacketMetadata(
        agent="l-cto",
        schema_version="1.0.0",
    ),
)
```

---

## Usage

### Creating L-CTO Agent

```python
from agents.l_cto import create_l_cto_agent, LCTOAgent

# Factory function (recommended) - loads kernels automatically
agent = create_l_cto_agent()

# Manual creation with kernel loading
agent = LCTOAgent(agent_id="l-cto")
from runtime.kernel_loader import load_kernels, require_kernel_activation
agent = load_kernels(agent)
require_kernel_activation(agent)
```

### Executing Tasks

```python
from core.agents.schemas import AgentTask, TaskKind
from core.agents.executor import AgentExecutorService

# Create task
task = AgentTask(
    id=uuid4(),
    agent_id="l-cto",
    kind=TaskKind.QUERY,
    payload={"message": "What is the status of the VPS deployment?"},
)

# Execute via executor (governance-gated)
executor = AgentExecutorService(
    aios_runtime=runtime,
    tool_registry=registry,
    substrate_service=substrate,
)
result = await executor.start_agent_task(task)
```

### Direct Agent Calls (Testing)

```python
# Direct run (bypasses executor governance - for testing only)
response = await agent.run(
    task={"message": "Explain the memory substrate architecture"},
    context={"source": "test"},
)
```

---

## Deployment Readiness

### Checklist

- [x] **Kernel Loading**: All 10 kernels load correctly ✅
- [x] **Kernel Absorption**: Agent absorbs identity, behavioral, safety, execution ✅
- [x] **System Prompt**: Builds correctly from kernel data ✅
- [x] **Executor Integration**: Pre/post governance hooks work ✅
- [x] **Tool Registry**: 12 tools wired with approval gates ✅
- [x] **Memory Integration**: PacketEnvelope emission works ✅
- [x] **Safety Validation**: Dangerous tasks blocked ✅
- [x] **Tests**: 46/46 passing ✅

### VPS Requirements

| Service    | Version | Purpose                        |
| ---------- | ------- | ------------------------------ |
| PostgreSQL | 14+     | Memory substrate, packet store |
| Redis      | 7+      | Task queue, WebSocket pub/sub  |
| Python     | 3.11+   | Runtime                        |

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://user:pass@host:5432/l9
REDIS_URL=redis://localhost:6379/0

# Optional
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
L9_KERNEL_PATH=private/kernels/00_system
LOG_LEVEL=INFO
```

---

## Troubleshooting

### Common Issues

| Symptom                        | Cause                               | Solution                                                 |
| ------------------------------ | ----------------------------------- | -------------------------------------------------------- |
| `KERNEL_INACTIVE` error        | Kernels not loaded                  | Call `load_kernels()` then `require_kernel_activation()` |
| `get_approved_tools` TypeError | Mock uses AsyncMock for sync method | Use `MagicMock` for `get_approved_tools`                 |
| Empty system prompt            | Kernel state not ACTIVE             | Verify `agent.kernel_state == "ACTIVE"`                  |
| Tool blocked                   | Missing approval                    | High-risk tools require Igor approval                    |
| Memory emission fails          | Substrate not initialized           | Ensure DATABASE_URL is set                               |

### Diagnostic Commands

```bash
# Verify kernel loading
python -c "from agents.l_cto import create_l_cto_agent; a = create_l_cto_agent(); print(a.kernel_state)"

# Check kernel count
python -c "from agents.l_cto import create_l_cto_agent; a = create_l_cto_agent(); print(len(a.kernels))"

# Test executor
python -m pytest tests/core/agents/test_executor.py -v
```

---

## File Reference

| File                             | Purpose                         |
| -------------------------------- | ------------------------------- |
| `agents/l_cto.py`                | LCTOAgent class definition      |
| `runtime/kernel_loader.py`       | Kernel YAML parsing and loading |
| `core/agents/kernel_registry.py` | KernelAwareAgentRegistry        |
| `core/agents/executor.py`        | AgentExecutorService            |
| `core/agents/aios_runtime.py`    | AIOSRuntime (LLM calls)         |
| `core/governance/validation.py`  | Authority/safety validation     |
| `core/schemas/capabilities.py`   | LCapabilities enum              |
| `runtime/l_tools.py`             | Tool registry and executors     |
| `memory/substrate_service.py`    | Memory substrate interface      |
| `private/kernels/00_system/`     | 10 system kernel YAML files     |

---

## Version History

| Version | Date       | Changes                                     |
| ------- | ---------- | ------------------------------------------- |
| 1.0.0   | 2026-01-01 | Kernel-based init, full test coverage       |
| 0.9.0   | 2025-12-28 | Migration from deprecated `LStartup.boot()` |
| 0.8.0   | 2025-12-25 | Memory substrate integration                |

---

**L-CTO** — _Igor's autonomous CTO, governed by kernels, audited by memory._
