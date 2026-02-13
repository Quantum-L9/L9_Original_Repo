# L9 Quick Reference Cheat Sheet

## Essential Patterns at a Glance

### 📦 PacketEnvelope (Memory Write)

```python
from core.schemas.packet_envelope import PacketEnvelope, PacketMetadata, MemorySegment

packet = PacketEnvelope(
    packet_type="decision|memory_write|reasoning_trace|insight",
    payload={"your": "data"},
    metadata=PacketMetadata(agent="l-cto", domain="governance"),
    tags=["priority", "strategic"],
    thread_id=task.thread_id,  # Optional
    ttl=None  # None = permanent
)

await substrate.ingest_packet(packet, MemorySegment.PROJECT_HISTORY)
```

**Memory Segments**: `GOVERNANCE_META` | `PROJECT_HISTORY` | `TOOL_AUDIT` | `SESSION_CONTEXT`

---

### 🔧 Tool Registration

```python
from core.schemas.capabilities import ToolName, Capability

# 1. Add to ToolName enum (core/schemas/capabilities.py)
class ToolName(str, Enum):
    MY_TOOL = "my_tool"

# 2. Add capability (core/schemas/capabilities.py)
DEFAULT_L_CAPABILITIES = {
    ToolName.MY_TOOL: Capability(
        tool=ToolName.MY_TOOL,
        allowed=True,
        rate_limit=100,
        scope="internal"  # or "requires_igor_approval" for high-risk
    )
}

# 3. Implement executor (runtime/l_tools.py)
async def my_tool(arg: str, **kwargs) -> dict:
    """Tool implementation."""
    return {"result": arg}

TOOL_EXECUTORS["my_tool"] = my_tool

# 4. Register with metadata (core/tools/registry_adapter.py)
ToolDefinition(
    name="my_tool",
    description="Does something useful",
    category="custom",
    scope="internal",
    risk_level="low"
)
```

**Risk Levels**: `low` | `medium` | `high`
**Scopes**: `internal` | `external` | `requires_igor_approval`

---

### 🤖 Agent Bootstrap (7 Phases)

```python
from core.agents.bootstrap.orchestrator import AgentBootstrapOrchestrator
from core.agents.schemas import AgentConfig

config = AgentConfig(
    agent_id="my-agent",
    name="MyAgent",
    model="gpt-4o",
    kernel_refs=["01-master", "02-identity", "08-safety"]
)

orchestrator = AgentBootstrapOrchestrator(substrate_service=substrate)
instance = await orchestrator.bootstrap(config)

# Returns: AgentInstance with status="READY" or raises RuntimeError
```

**Phases**: Validate → Load Kernels → Instantiate → Bind Kernels → Load Identity → Bind Tools → Wire Governance → Verify & Lock

---

### 🧠 Metacognitive Self-Assessment

```python
class MetacognitiveAgent:
    async def assess_competence(self, task: str) -> dict:
        """Returns: {competence_score, confidence, recommendation}"""
        similar_tasks = await self.memory.search(query=task, top_k=20)
        success_rate = sum(1 for t in similar_tasks if t["success"]) / len(similar_tasks)
        
        if success_rate > 0.7:
            return {"recommendation": "proceed_autonomously"}
        elif success_rate > 0.4:
            return {"recommendation": "proceed_with_monitoring"}
        else:
            return {"recommendation": "escalate_or_decompose"}
```

**When to Use**: Before attempting novel or high-stakes tasks
**Outcome**: 91.3% reduction in job failure rates

---

### 🌲 Agent Q (MCTS + Self-Critique)

```python
class AgentQSelfCritique:
    async def mcts_search_with_critique(
        self,
        task: str,
        simulation_budget: int = 100
    ) -> dict:
        root = MCTSNode(state=task)
        
        for _ in range(simulation_budget):
            node = self._select(root)
            node = await self._expand(node)
            
            # Self-critique before simulation
            critique = await self._self_critique(node)
            if critique["quality"] == "poor":
                node.mark_pruned(reason=critique["reason"])
                continue
            
            reward = await self._simulate(node)
            self._backpropagate(node, reward)
        
        return self._select_best_action(root)
```

**When to Use**: Complex multi-step reasoning with uncertainty
**Outcome**: 340% performance improvement (18.6% → 81.7% success)

---

### ⚡ Inference-Time Scaling

```python
class InferenceTimeScaling:
    async def scale_compute_by_difficulty(self, problem: str, budget: int = 100):
        difficulty = await self._assess_difficulty(problem)
        
        if difficulty == "easy":
            return await self.llm.generate(problem)  # 1 forward pass
        
        elif difficulty == "medium":
            candidates = await asyncio.gather(*[
                self.llm.generate(problem) for _ in range(5)
            ])
            return await self._select_best_with_prm(candidates)  # Best-of-N
        
        else:  # hard
            return await self._mcts_search_with_prm(problem, budget)  # Full search
```

**When to Use**: Adaptive compute allocation based on problem complexity
**Outcome**: Smaller models match 14x larger models with optimal compute

---

### 🐝 Swarm Coordination

```python
class SwarmCoordination:
    async def coordinate_swarm(self, problem: str, agent_count: int = 10):
        # Initialize agents
        agents = [SwarmAgent(f"agent_{i}") for i in range(agent_count)]
        
        # Pheromone-based coordination
        while not self._convergence_achieved():
            actions = await asyncio.gather(*[
                agent.act(search_space, self.pheromone_map)
                for agent in agents
            ])
            
            # Update pheromones on successful paths
            for action in actions:
                if action["quality"] > 0.7:
                    self._deposit_pheromone(action["task_id"], action["quality"])
            
            self._evaporate_pheromones(rate=0.1)
        
        return await self._synthesize_swarm_results()
```

**Emergent Roles**: Explorer (low pheromone areas) | Worker (high pheromone) | Validator (quality assurance)
**Outcome**: 4x reasoning stability vs centralized orchestration

---

### 📚 RAFA Continuous Learning

```python
class RAFAContinuousLearning:
    async def update_policy(self, trajectory: list[dict], outcome: dict):
        # Compute trajectory return
        trajectory_return = sum(step["reward"] for step in trajectory)
        
        # Reward-weighted policy update
        weighted_updates = [
            {"state": step["state"], "action": step["action"], "weight": trajectory_return}
            for step in trajectory
        ]
        
        new_policy_params = await self._aggregate_updates(weighted_updates)
        await self.save_policy_update(new_policy_params)
        
        return {"version": self._next_version(), "params": new_policy_params}
```

**When to Use**: After task completion to improve future performance
**Outcome**: Provably optimal policy improvement guarantees

---

### 🔒 High-Risk Tool Approval Gate

```python
from core.governance.approvals import ApprovalService

async def execute_with_approval_gate(
    tool_name: ToolName,
    arguments: dict,
    agent_id: str
):
    capability = DEFAULT_L_CAPABILITIES[tool_name]
    
    if capability.scope == "requires_igor_approval":
        approval = await approval_service.check_approval(agent_id, tool_name, arguments)
        
        if not approval["approved"]:
            request = await approval_service.request_approval(
                agent_id, tool_name, arguments, rationale="..."
            )
            return {"status": "BLOCKED", "request_id": request["request_id"]}
    
    result = await TOOL_EXECUTORS[tool_name.value](**arguments)
    await log_tool_execution(agent_id, tool_name, arguments, result)
    return result
```

**High-Risk Tools**: `GMP_RUN` | `GIT_COMMIT` | `MAC_AGENT_EXEC_TASK` | `SHELL` | `FILE_DELETE` | `DATABASE_WRITE`

---

### 🎼 UnifiedController (7-Phase Orchestration)

```python
class UnifiedController:
    async def handle_request(self, text: str, context: dict) -> dict:
        result = {"status": "pending", "phases": []}
        
        result = await self.phase_routing(text, context, result)      # 1. Routing
        result = await self.phase_plan(result)                        # 2. Plan
        
        if self.should_simulate(result):
            result = await self.phase_simulate(result)                # 3. Simulate
        
        if self.should_deliberate(result):
            result = await self.phase_deliberate(text, result)        # 4. Deliberate
        
        result = await self.phase_execute(context, result)            # 5. Execute
        result = await self.phase_ir_pipeline(text, context, result) # 6. IR Pipeline
        result = await self.phase_reflect(context, result)            # 7. Reflect
        
        return result
```

**Use For**: Complex workflows requiring routing → planning → simulation → execution → reflection

---

### 📝 Logging (structlog Only!)

```python
import structlog

logger = structlog.get_logger(__name__)

# ✅ CORRECT
logger.info("agent_initialized", agent_id=agent_id, tools_count=len(tools))
logger.error("operation_failed", error=str(e), exc_info=True)
logger.debug("search_completed", query=query[:50], result_count=len(results))

# ❌ FORBIDDEN (CI will fail)
print(f"Agent {agent_id} initialized")
PrintLogger.log("Something happened")
```

**Log Levels**: `debug` | `info` | `warning` | `error` | `critical`

---

### 🧪 Testing Pattern

```python
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_substrate():
    substrate = AsyncMock(spec=MemorySubstrateService)
    substrate.ingest_packet.return_value = {"packet_id": uuid4()}
    return substrate

@pytest.mark.asyncio
async def test_operation_success(mock_substrate):
    service = MyService(substrate=mock_substrate)
    result = await service.operation("test")
    
    assert result["status"] == "success"
    mock_substrate.ingest_packet.assert_called_once()
```

**Target**: 85%+ test coverage

---

### 📄 File Template (Minimal)

```python
"""Module description."""

# ============================================================================
# HEADER: Imports and Constants
# ============================================================================
from typing import Optional, Any
import structlog

logger = structlog.get_logger(__name__)

# ============================================================================
# BODY: Class and Function Definitions
# ============================================================================

class MyService:
    """Service description."""
    
    async def method(self, param: str) -> dict[str, Any]:
        """Method description with Args, Returns, Raises."""
        logger.info("method_called", param=param[:50])
        try:
            result = await self._internal_operation(param)
            return result
        except Exception as e:
            logger.error("method_failed", error=str(e), exc_info=True)
            raise RuntimeError(f"Failed: {e}") from e

# ============================================================================
# FOOTER: Metadata
# ============================================================================

__module_name__ = "my_service"
__version__ = "1.0.0"
__author__ = "L9 System"
__kernel_governed__ = True
__kernel_refs__ = ["07-execution", "08-safety"]
__status__ = "production"
__test_coverage__ = 85
```

---

## Code Quality Checklist (5-Second Scan)

- [ ] `import structlog` present, NO `print()` statements
- [ ] All I/O operations are `async def` + `await`
- [ ] All function signatures have full type hints
- [ ] Significant operations write to memory substrate
- [ ] High-risk tools check Igor approval first
- [ ] Exceptions caught with structured logging
- [ ] Footer metadata block present

---

## Quick Imports Reference

```python
# Memory
from core.memory.substrate_service import MemorySubstrateService, get_substrate
from core.schemas.packet_envelope import PacketEnvelope, PacketMetadata, MemorySegment

# Tools
from core.schemas.capabilities import ToolName, Capability, DEFAULT_L_CAPABILITIES
from core.tools.registry_adapter import ExecutorToolRegistry
from runtime.l_tools import TOOL_EXECUTORS

# Agents
from core.agents.agent_instance import AgentInstance, AgentConfig
from core.agents.executor import AgentExecutorService
from core.agents.bootstrap.orchestrator import AgentBootstrapOrchestrator

# Orchestration
from orchestration.unified_controller import UnifiedController
from orchestration.coplanner import CoPlanner

# Logging
import structlog
logger = structlog.get_logger(__name__)
```

---

## L9 Layer Quick Map

| Layer | Purpose | When to Use |
|-------|---------|-------------|
| **L1 Foundation** | Neo4j graph, PacketEnvelope, memory substrate | All persistent storage, graph queries, semantic search |
| **L2 Intelligence** | RAFA, Agent Q, continuous learning | Policy optimization, task learning, capability improvement |
| **L3 Verification** | Lean Theorem Prover | Formal correctness proofs, constraint verification |
| **L4 Coordination** | CoPlanner, Tree-of-Thoughts, multi-agent | Task decomposition, parallel execution, collaboration |
| **L5 Security** | Zero-trust RBAC, governance, kernel enforcement | All tool execution, approval gates, policy checks |
| **L6 Human Interaction** | Slack, Email, WebSocket | User communication, approval requests, status updates |
| **L7 Foundation Models** | DeepSeek-R1, frontier LLMs | Base reasoning, complex inference, text generation |

---

## Common Anti-Patterns (Avoid!)

| ❌ WRONG | ✅ CORRECT |
|---------|-----------|
| `print("message")` | `logger.info("event", key=value)` |
| `def sync_io():` | `async def async_io():` |
| `def func(arg):` | `def func(arg: str) -> dict:` |
| `return {}  # TODO` | `return complete_implementation()` |
| Execute high-risk tool directly | Check Igor approval first |
| Ignore memory substrate | Persist to PacketEnvelope |

---

## Decision Tree (Which Pattern?)

```
Task requires capability assessment?
├─ YES → Metacognitive Self-Assessment
└─ NO → Continue

Multi-step reasoning with uncertainty?
├─ YES → Agent Q (MCTS + Self-Critique)
└─ NO → Continue

Adaptive compute needed?
├─ YES → Inference-Time Scaling
└─ NO → Continue

Multi-agent coordination?
├─ YES → Need centralized control?
│   ├─ YES → CoPlanner
│   └─ NO → Swarm Coordination
└─ NO → Continue

Learn from experience?
├─ YES → RAFA Continuous Learning
└─ NO → Continue

High-risk operation?
├─ YES → Igor Approval Gate
└─ NO → Execute with capability check
```

---

## Emergency Commands

```bash
# Check code quality
ruff check .

# Run type checking
mypy .

# Run tests
pytest --cov=core --cov-report=term-missing

# Check tool wiring
python ci/check_tool_wiring.py

# View logs
docker logs l9-api -f --tail=100
```

---

## Key Metrics from Research

- **Metacognition**: 91.3% ↓ job failure rate
- **Agent Q**: 340% performance improvement (18.6% → 81.7% success)
- **Swarm**: 4x reasoning stability vs centralized
- **Inference Scaling**: Small models match 14x larger models with optimal compute
- **RAFA**: Provably optimal policy improvement

---

**Remember**: Default to ADVISORY mode (analyze, recommend). Switch to EXECUTION mode only when ready to implement with Phase 0 approval.

**Core Principle**: Ground truth first → L9 patterns only → Production-ready code

---

**Version**: 1.0.0 (2026-01-08)
**Source**: L9 Frontier AI Super Prompt v1.0
