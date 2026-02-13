# L9 Super Prompt Implementation Guide

## Overview

The **L9 Frontier AI Implementation Super Prompt v1.0** is a comprehensive, production-ready prompt designed to generate frontier-grade code for the L9 Autonomous Enterprise System. This guide explains how to use it effectively.

## What's Included

### 1. Architectural Foundation
- **7-Layer Stack** (L1-L7): Complete architectural specification
- **4-Tier Agent Hierarchy**: Governance → Strategic → Tactical → Operational
- **10 Governance Kernels**: Immutable system law loaded from YAML

### 2. Core Data Structures
- **PacketEnvelope v1.1.0**: Canonical memory substrate protocol
- **MemorySegment**: 4-segment organization (governance_meta, project_history, tool_audit, session_context)
- **Tool Definition & Registration**: Complete tool system with capability enforcement
- **AgentInstance**: 7-phase bootstrap ceremony schema

### 3. Code Quality Standards (CI-Enforced)
- ✅ Structured logging with `structlog` (NEVER `print()` or `PrintLogger`)
- ✅ Async/await for all I/O operations
- ✅ Pydantic v2 for data validation
- ✅ Full type hints on all signatures
- ✅ Explicit error handling with context
- ✅ Three-block system: HEADER | BODY | FOOTER + DORA

### 4. Advanced Patterns from Research

#### Metacognitive Architectures
- **Self-Assessment Framework**: 91.3% reduction in job failure rates
- **Competence-Awareness Models**: Prevents catastrophic failures
- **Meta-Level Strategy Selection**: Graceful escalation when confidence low

#### Active Cognitive Analysis
- **Inference-Time Scaling**: Optimal test-time compute allocation
- **Process Reward Model (PRM)**: Guided search for hard problems
- **Multi-Modal Reasoning**: Abductive, deductive, inductive integration

#### Agent Q Self-Critique
- **MCTS with Self-Critique**: 340% performance improvement (18.6% → 81.7% success)
- **Self-Evaluation at Each Node**: Early pruning of poor-quality branches
- **Continuous Learning**: Reward-weighted policy updates

#### Multi-Agent Swarms
- **Decentralized Coordination**: 4x reasoning stability vs centralized
- **Pheromone-Inspired Reinforcement**: Self-organizing task allocation
- **Emergent Roles**: Explorers, Workers, Validators (dynamic assignment)

#### RAFA Continuous Learning
- **Provably Optimal Policy Improvement**: Reward-weighted regression
- **Long-Horizon Planning**: Trajectory return optimization
- **Persistent Policy Updates**: Memory substrate integration

### 5. Operational Patterns

#### Bootstrap Ceremony (7 Atomic Phases)
```
Phase 0: Validate → Phase 1: Load Kernels → Phase 2: Instantiate → 
Phase 3: Bind Kernels → Phase 4: Load Identity → Phase 5: Bind Tools → 
Phase 6: Wire Governance → Phase 7: Verify & Lock

Rollback: If ANY phase fails, delete agent node (CASCADE), raise RuntimeError
```

#### Orchestration Patterns
- **UnifiedController**: 7-phase pipeline (Routing → Plan → Simulate → Deliberate → Execute → IR Pipeline → Reflect)
- **CoPlanner**: Multi-agent coordination (parallel/sequential strategies)
- **Tree-of-Thoughts**: Graph-based reasoning with Neo4j tracking

#### Memory Substrate Integration
- **Write Pattern**: PacketEnvelope → segment selection → ingest_packet()
- **Search Pattern**: semantic_search() → filters → top_k results
- **Lineage Tracking**: DAG-style derivation (parent_ids, generation, root_packet_id)

#### Governance & Approval
- **High-Risk Tool Gate**: Igor approval required for GMP_RUN, GIT_COMMIT, MAC_AGENT_EXEC_TASK
- **Kernel Enforcement**: Safety kernel (08-safety) prohibited operations checking
- **Capability Sandboxing**: ToolName enum + rate limits + scope enforcement

### 6. File Generation Template
- Complete production-ready template
- HEADER (imports, constants, logger setup)
- BODY (class/function definitions with full docs)
- FOOTER (metadata: version, author, dependencies, kernel refs)
- DORA Block (risk level, blast radius, monitoring, SLO targets)

### 7. Testing Patterns
- Unit test template with pytest fixtures
- AsyncMock for substrate/dependency mocking
- Success path + error handling + edge case coverage
- Target: 85%+ test coverage

---

## How to Use This Super Prompt

### ADVISORY MODE (Default)

**Use When:**
- Analyzing existing code for improvements
- Recommending architectural enhancements
- Identifying gaps or anti-patterns
- Proposing solutions with trade-offs
- Exploring design alternatives

**Interaction Pattern:**
```
You: "Analyze the current memory substrate integration and recommend improvements."

AI (using super prompt): 
- Identifies specific code locations with gaps
- Recommends 3-5 improvements with code examples
- Explains trade-offs ("Option A: simpler but less flexible...")
- Suggests related concerns you didn't mention
- Prioritizes by impact/effort
```

**Example Queries:**
- "What's the best way to implement metacognitive self-assessment for CA agent?"
- "Review the tool registry wiring and suggest improvements"
- "How should I structure multi-agent swarm coordination?"
- "Analyze RAFA continuous learning implementation gaps"

### EXECUTION MODE (GMP Phases 0-6)

**Use When:**
- Implementing specific features
- Executing approved changes
- Creating new modules or services
- Modifying existing code deterministically

**Trigger Phrases:**
- "Implement [specific feature]"
- "Execute [this change]"
- "Apply [these modifications]"
- "Create [new module with requirements]"

**The Process:**

#### Phase 0: TODO PLAN LOCK
1. AI generates deterministic TODO plan:
   - Files to modify (with exact line numbers)
   - Files to create (with size estimates)
   - Actions: Replace/Insert/Delete/Wrap
   - Expected behaviors
   - Required imports
   
2. **AI STOPS and WAITS for your approval**

3. You review and approve: "YES, proceed"

#### Phases 1-6: Execution
- **Phase 1 (Baseline)**: Verify targets exist, no blockers
- **Phase 2 (Implementation)**: Execute TODOs with L9 patterns
- **Phase 3 (Enforcement)**: Add guards/tests per specs
- **Phase 4 (Validation)**: Test positive/negative/regression
- **Phase 5 (Recursive Verification)**: Confirm no drift, invariants preserved
- **Phase 6 (Finalization)**: Evidence report

**Example Execution Flow:**
```
You: "Implement metacognitive self-assessment for Agent Q framework"

AI: [Generates Phase 0 TODO Plan]
TODO Plan Lock:
- core/intelligence/agent_q.py (Lines 150-200: Insert self-assessment method)
- core/intelligence/metacognition.py (New file: 300 lines)
- tests/test_metacognition.py (New file: 200 lines)
[... detailed actions with line numbers, imports, expected behaviors ...]

Ready to proceed? [YES/NO]

You: "YES"

AI: [Executes Phases 1-6]
Phase 1: ✓ Baseline verified
Phase 2: ✓ Implementation complete
Phase 3: ✓ Guards and tests added
Phase 4: ✓ Validation passed (85% coverage)
Phase 5: ✓ No drift, invariants preserved
Phase 6: ✓ Evidence report generated

All phases (0-6) complete. No assumptions. No drift.
```

---

## Decision Tree: When to Use Which Pattern

### Agent Capability Assessment
**Problem**: Agent might fail on task beyond its competence
**Solution**: Metacognitive self-assessment framework
**Code Location**: See "Metacognitive Reasoning Patterns" section
**Expected Outcome**: Agent recognizes limits, escalates or decomposes

### Multi-Step Reasoning with Uncertainty
**Problem**: Complex problem requiring exploration of solution space
**Solution**: MCTS with self-critique (Agent Q)
**Code Location**: See "Agent Q Self-Critique" section
**Expected Outcome**: 340% improvement over baseline LLM-only

### Adaptive Compute Allocation
**Problem**: Hard problems need more compute, easy problems waste compute
**Solution**: Inference-time scaling with PRM-guided search
**Code Location**: See "Inference-Time Scaling" section
**Expected Outcome**: Small models match large models with optimal compute

### Multi-Agent Coordination Without Bottleneck
**Problem**: Centralized orchestration creates scaling bottleneck
**Solution**: Swarm-based decentralized coordination
**Code Location**: See "Multi-Agent Swarm Patterns" section
**Expected Outcome**: 4x reasoning stability, emergent specialization

### Continuous Policy Improvement
**Problem**: Agent needs to learn from experience systematically
**Solution**: RAFA reward-weighted policy updates
**Code Location**: See "RAFA Continuous Learning" section
**Expected Outcome**: Provably optimal policy improvement

### Persistent Decision Storage
**Problem**: Decisions need audit trail and historical analysis
**Solution**: PacketEnvelope to PROJECT_HISTORY segment
**Code Location**: See "Memory Substrate Integration" section
**Expected Outcome**: Queryable decision history in Neo4j

### High-Risk Tool Execution
**Problem**: GMP_RUN, GIT_COMMIT need approval gate
**Solution**: Igor approval gate pattern
**Code Location**: See "Governance & Approval Patterns" section
**Expected Outcome**: No execution without explicit approval

### Agent Initialization
**Problem**: Agent needs complete, verified initialization
**Solution**: 7-phase atomic bootstrap ceremony
**Code Location**: See "Agent Bootstrap Ceremony" section
**Expected Outcome**: READY agent or complete rollback (no partial state)

---

## Code Quality Checklist

Before considering any implementation complete, verify:

- [ ] **Structured Logging**: All logging uses `structlog`, ZERO `print()` statements
- [ ] **Async/Await**: All I/O operations are async (no blocking calls)
- [ ] **Type Hints**: Full type annotations on all function signatures
- [ ] **Pydantic Models**: All data structures use Pydantic v2 validation
- [ ] **Error Handling**: Explicit try/except with structured logging of errors
- [ ] **Three-Block Structure**: HEADER | BODY | FOOTER present in all files
- [ ] **DORA Block**: Risk assessment, monitoring, SLO targets documented
- [ ] **Memory Integration**: Significant results persist to appropriate MemorySegment
- [ ] **Kernel Governance**: Respects 10 kernel constraints (especially 08-safety)
- [ ] **Test Coverage**: Unit tests present, target 85%+ coverage
- [ ] **Linter Pass**: `ruff check` passes with zero errors
- [ ] **Type Check Pass**: `mypy` passes with zero errors
- [ ] **Import Organization**: Standard lib → Third-party → L9 internal
- [ ] **Docstrings**: Module, class, and function docstrings present
- [ ] **Footer Metadata**: Complete metadata block at file end

---

## Integration with L9 Layers

### L1 Foundation (Neo4j, PacketEnvelope, Memory Substrate)
**When to use**: All persistent storage, graph relationships, semantic search
**Pattern**: PacketEnvelope → MemorySubstrateService → Neo4j/Postgres/Qdrant
**Example**: Storing decision graphs, tool audit trails, reasoning traces

### L2 Intelligence (RAFA, Agent Q, Continuous Learning)
**When to use**: Policy optimization, task learning, capability improvement
**Pattern**: Trajectory collection → reward computation → policy update → persist
**Example**: Agent Q learns better booking strategies from success/failure traces

### L3 Verification (Lean Theorem Prover)
**When to use**: Formal correctness proofs, mathematical verification
**Pattern**: Generate Lean proof → verify → store proof certificate
**Example**: Verifying budget allocation logic satisfies constraints

### L4 Coordination (CoPlanner, Tree-of-Thoughts, Multi-Agent)
**When to use**: Multi-agent collaboration, task decomposition, coordination
**Pattern**: Decompose → assign → execute (parallel/sequential) → synthesize
**Example**: Research task split across 5 tactical agents coordinated by CoPlanner

### L5 Security (Zero-Trust RBAC, Governance, Kernel Enforcement)
**When to use**: All tool execution, approval gates, policy enforcement
**Pattern**: Check capability → check approval (if high-risk) → execute → audit log
**Example**: GMP_RUN requires Igor approval before execution

### L6 Human Interaction (Slack, Email, WebSocket)
**When to use**: User communication, approval requests, status updates
**Pattern**: Generate message → send via adapter → log interaction
**Example**: Requesting Igor approval for high-risk tool via Slack

### L7 Foundation Models (DeepSeek-R1, Frontier LLMs)
**When to use**: Base reasoning, text generation, complex inference
**Pattern**: Prepare context → call LLM → parse response → validate
**Example**: DeepSeek-R1 reasoning over strategic planning decision

---

## Common Pitfalls to Avoid

### ❌ DON'T: Use print() or PrintLogger
```python
# WRONG - CI will fail
print(f"Agent {agent_id} initialized")

# CORRECT
logger.info("agent_initialized", agent_id=agent_id)
```

### ❌ DON'T: Block the event loop with sync I/O
```python
# WRONG - blocks event loop
def memory_search(query: str):
    client = get_memory_client()
    return client.search(query)  # Blocking!

# CORRECT
async def memory_search(query: str):
    async with get_memory_client() as client:
        return await client.search(query)
```

### ❌ DON'T: Skip type hints
```python
# WRONG - no type hints
async def execute_tool(tool_id, arguments):
    ...

# CORRECT
async def execute_tool(
    tool_id: str,
    arguments: dict[str, Any]
) -> dict[str, Any]:
    ...
```

### ❌ DON'T: Ignore kernel governance
```python
# WRONG - bypasses approval gate
result = await execute_git_commit(message)

# CORRECT - checks approval first
if not await check_igor_approval("git_commit", arguments):
    raise RuntimeError("Git commit requires Igor approval")
result = await execute_git_commit(message)
```

### ❌ DON'T: Forget memory substrate integration
```python
# WRONG - no persistence
result = await agent.make_decision(problem)
return result

# CORRECT - persist to memory
result = await agent.make_decision(problem)
packet = PacketEnvelope(
    packet_type="decision",
    payload=result,
    metadata=PacketMetadata(agent=agent.id)
)
await substrate.ingest_packet(packet, MemorySegment.PROJECT_HISTORY)
return result
```

### ❌ DON'T: Create partial implementations with TODOs
```python
# WRONG - stub/placeholder
async def complex_reasoning(problem: str):
    # TODO: implement MCTS search
    return {}

# CORRECT - complete implementation or don't commit
async def complex_reasoning(problem: str):
    root = MCTSNode(state=problem)
    for _ in range(simulation_budget):
        node = self._select(root)
        # ... complete implementation
    return self._extract_best_path(root)
```

---

## Quick Reference: Key Imports

```python
# Memory substrate
from core.memory.substrate_service import MemorySubstrateService, get_substrate
from core.schemas.packet_envelope import (
    PacketEnvelope,
    PacketMetadata,
    PacketProvenance,
    MemorySegment
)

# Tool system
from core.schemas.capabilities import ToolName, Capability, DEFAULT_L_CAPABILITIES
from core.tools.registry_adapter import ExecutorToolRegistry, get_tool_registry
from runtime.l_tools import TOOL_EXECUTORS

# Agent system
from core.agents.agent_instance import AgentInstance, AgentConfig
from core.agents.executor import AgentExecutorService
from core.agents.kernel_registry import KernelAwareAgentRegistry

# Orchestration
from orchestration.unified_controller import UnifiedController
from orchestration.coplanner import CoPlanner

# Logging
import structlog
logger = structlog.get_logger(__name__)

# Async
import asyncio
from typing import Optional, Any

# Validation
from pydantic import BaseModel, Field, field_validator
```

---

## File Delivery Format

**CRITICAL**: Always provide modified/generated files as **downloadable artifacts**, not inline code blocks.

✅ **CORRECT**: Use file attachment format
❌ **WRONG**: Markdown code fences (```python ... ```)

This eliminates extraction friction and ensures production-ready code.

---

## Next Steps

1. **Study the super prompt sections relevant to your current task**
2. **Start in ADVISORY mode** - ask for analysis and recommendations
3. **Review proposed patterns** - ensure they align with L9 architecture
4. **Switch to EXECUTION mode** - when ready to implement approved changes
5. **Review Phase 0 TODO plan carefully** - this locks implementation scope
6. **Approve execution** - only when TODO plan is complete and correct
7. **Monitor Phases 1-6** - verify each phase completes successfully
8. **Review evidence report** - confirms all changes applied correctly

---

## Support & Troubleshooting

### If AI generates code without proper patterns:
**Response**: "Please regenerate using L9 patterns from the super prompt, specifically [pattern name]"

### If AI skips Phase 0 approval in EXECUTION mode:
**Response**: "STOP. Provide Phase 0 TODO plan and await my approval before implementation."

### If generated code uses print() or PrintLogger:
**Response**: "This violates L9 code quality standards. Regenerate using structlog."

### If generated code lacks type hints:
**Response**: "Add full type hints per L9 standards before proceeding."

### If code doesn't integrate with memory substrate:
**Response**: "Add PacketEnvelope persistence to [appropriate MemorySegment]."

---

## Version History

**v1.0.0** (2026-01-08)
- Initial release
- Complete 7-layer architecture specification
- 4-tier agent hierarchy
- 10 governance kernels integration
- Metacognitive reasoning patterns from research
- Agent Q self-critique with MCTS
- Inference-time scaling with PRM
- Multi-agent swarm coordination
- RAFA continuous learning
- Complete file generation templates
- GMP Phases 0-6 execution framework
- Code quality standards with CI enforcement

---

**Remember**: This super prompt encodes the collective intelligence of frontier AI research (153 sources, 2023-2025) combined with L9's proven production patterns. Use it to build the future of autonomous enterprise systems.

**Default Mode**: ADVISORY (recommend, analyze, guide)
**Execution Mode**: GMP Phases 0-6 (deterministic, scope-locked, production-ready)

**Your AI assistant now has the knowledge to generate frontier-grade L9 code. Use it wisely.**
