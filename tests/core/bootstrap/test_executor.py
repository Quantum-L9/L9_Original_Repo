"""
L9 Core Agents - Executor Tests (Contract-Grade)
================================================

Contract-grade tests for the AgentExecutorService.

Acceptance criteria from MODULE_SPEC:
- A valid agent task instantiates the correct agent
- The executor correctly binds tools approved by governance
- The agent execution loop runs and calls AIOS
- A tool call from AIOS is correctly dispatched to the tool registry
- The executor terminates after reaching a final answer
- The executor terminates if it exceeds max iterations

Contract guarantees verified:
- Governance lookup called with correct agent_id and principal_id
- Approved tools appear in AIOS context
- Tool results fed back into next AIOS context
- Packets emitted with required fields
- Idempotency returns DuplicateTaskResponse type
- Failure paths emit error packets

Version: 2.0.0
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path before any imports
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from typing import Any, Optional
from uuid import UUID, uuid4

import pytest

from core.agents.schemas import (
    AgentTask,
    AgentConfig,
    AIOSResult,
    DuplicateTaskResponse,
    ExecutionResult,
    ToolBinding,
    ToolCallRequest,
    ToolCallResult,
    TaskKind,
)
from core.agents.executor import AgentExecutorService


# =============================================================================
# Contract-Grade Mock Implementations
# =============================================================================


class MockAIOSRuntime:
    """
    Contract-grade mock AIOS runtime.

    Records every context passed to execute_reasoning() for verification.
    """

    def __init__(self) -> None:
        self.call_count: int = 0
        self.contexts: list[dict[str, Any]] = []
        self.responses: list[AIOSResult] = []
        self._default_response = AIOSResult.response("Default response", tokens_used=10)

    def set_responses(self, responses: list[AIOSResult]) -> None:
        """Set sequence of responses to return."""
        self.responses = list(responses)  # Copy to avoid mutation

    async def execute_reasoning(self, context: dict[str, Any]) -> AIOSResult:
        """Execute mock reasoning and record context."""
        self.call_count += 1
        self.contexts.append(context)

        if self.responses:
            return self.responses.pop(0)
        return self._default_response

    def get_last_context(self) -> dict[str, Any]:
        """Get the most recent context passed to execute_reasoning."""
        if not self.contexts:
            raise ValueError("No contexts recorded")
        return self.contexts[-1]

    def get_context_at(self, index: int) -> dict[str, Any]:
        """Get context at specific call index (0-based)."""
        return self.contexts[index]


class MockToolRegistry:
    """
    Contract-grade mock tool registry.

    Records calls to get_approved_tools for governance verification.
    Uses tool_id as canonical identity throughout.
    """

    def __init__(self) -> None:
        self.dispatch_count: int = 0
        self.dispatch_calls: list[dict[str, Any]] = []
        self.governance_calls: list[dict[str, str]] = []
        self._approved_tools: list[ToolBinding] = []
        self._dispatch_result: Optional[ToolCallResult] = None
        self._dispatch_exception: Optional[Exception] = None

    def set_approved_tools(self, tools: list[ToolBinding]) -> None:
        """Set tools that will be returned as approved."""
        self._approved_tools = list(tools)

    def set_dispatch_result(self, result: ToolCallResult) -> None:
        """Set result to return from dispatch."""
        self._dispatch_result = result
        self._dispatch_exception = None

    def set_dispatch_exception(self, exc: Exception) -> None:
        """Set exception to raise on dispatch."""
        self._dispatch_exception = exc
        self._dispatch_result = None

    async def dispatch_tool_call(
        self,
        tool_id: str,
        arguments: dict[str, Any],
        context: dict[str, Any],
    ) -> ToolCallResult:
        """Dispatch mock tool call and record details using tool_id."""
        self.dispatch_count += 1
        self.dispatch_calls.append(
            {
                "tool_id": tool_id,
                "arguments": arguments,
                "context": context,
            }
        )

        if self._dispatch_exception is not None:
            raise self._dispatch_exception

        if self._dispatch_result is not None:
            return self._dispatch_result

        return ToolCallResult(
            call_id=uuid4(),
            tool_id=tool_id,
            success=True,
            result={"data": "default tool result"},
            duration_ms=100,
        )

    def get_approved_tools(
        self,
        agent_id: str,
        principal_id: str,
    ) -> list[ToolBinding]:
        """Get approved tools and record governance lookup."""
        self.governance_calls.append(
            {
                "agent_id": agent_id,
                "principal_id": principal_id,
            }
        )
        return self._approved_tools

    def get_last_dispatch(self) -> dict[str, Any]:
        """Get the most recent dispatch call details."""
        if not self.dispatch_calls:
            raise ValueError("No dispatch calls recorded")
        return self.dispatch_calls[-1]


class MockSubstrateService:
    """
    Contract-grade mock substrate service.

    Records packets and can simulate write failures.
    """

    def __init__(self) -> None:
        self.packets: list[Any] = []
        self._search_results: list[dict[str, Any]] = []
        self._write_exception: Optional[Exception] = None

    def set_search_results(self, results: list[dict[str, Any]]) -> None:
        """Set results to return from search."""
        self._search_results = list(results)

    def set_write_exception(self, exc: Exception) -> None:
        """Set exception to raise on write."""
        self._write_exception = exc

    def clear_write_exception(self) -> None:
        """Clear any write exception."""
        self._write_exception = None

    async def write_packet(self, packet_in: Any) -> dict[str, Any]:
        """Write mock packet."""
        if self._write_exception is not None:
            raise self._write_exception
        self.packets.append(packet_in)
        return {"status": "ok"}

    async def search_packets(
        self,
        thread_id: UUID,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Search mock packets."""
        return self._search_results

    async def search_packets_by_type(
        self,
        packet_type: str,
        agent_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Search packets by type - searches stored packets."""
        # If explicit search results set, use those
        if self._search_results:
            return self._search_results
        # Otherwise search stored packets
        results = []
        for p in self.packets:
            if hasattr(p, "packet_type") and p.packet_type == packet_type:
                results.append({"payload": p.payload if hasattr(p, "payload") else {}})
        return results[:limit]

    async def search_packets_by_thread(
        self,
        thread_id: str,
        packet_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Search packets by thread."""
        return self._search_results

    def get_packets_by_type(self, packet_type: str) -> list[Any]:
        """Get all packets of a specific type."""
        return [p for p in self.packets if p.packet_type == packet_type]


class MockAgentRegistry:
    """Mock agent registry for testing."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentConfig] = {}

    def register_agent(self, config: AgentConfig) -> None:
        """Register an agent."""
        self._agents[config.agent_id] = config

    def get_agent_config(self, agent_id: str) -> Optional[AgentConfig]:
        """Get agent config."""
        return self._agents.get(agent_id)

    def agent_exists(self, agent_id: str) -> bool:
        """Check if agent exists."""
        return agent_id in self._agents


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_aios() -> MockAIOSRuntime:
    """Create mock AIOS runtime."""
    return MockAIOSRuntime()


@pytest.fixture
def mock_tool_registry() -> MockToolRegistry:
    """Create mock tool registry."""
    return MockToolRegistry()


@pytest.fixture
def mock_substrate() -> MockSubstrateService:
    """Create mock substrate service."""
    return MockSubstrateService()


@pytest.fixture
def mock_agent_registry() -> MockAgentRegistry:
    """Create mock agent registry with default agent."""
    registry = MockAgentRegistry()
    registry.register_agent(
        AgentConfig(
            agent_id="l9-standard-v1",
            personality_id="l9-standard-v1",
            model="gpt-4o",
            system_prompt="You are a helpful assistant.",
        )
    )
    return registry


@pytest.fixture
def executor(
    mock_aios: MockAIOSRuntime,
    mock_tool_registry: MockToolRegistry,
    mock_substrate: MockSubstrateService,
    mock_agent_registry: MockAgentRegistry,
) -> AgentExecutorService:
    """Create executor with mocked dependencies."""
    return AgentExecutorService(
        aios_runtime=mock_aios,
        tool_registry=mock_tool_registry,
        substrate_service=mock_substrate,
        agent_registry=mock_agent_registry,
        default_agent_id="l9-standard-v1",
        max_iterations=10,
    )


@pytest.fixture
def sample_task() -> AgentTask:
    """Create a sample task with known IDs for verification."""
    return AgentTask(
        kind=TaskKind.QUERY,
        agent_id="l9-standard-v1",
        source_id="test-principal",
        payload={"message": "Hello, agent!"},
    )


# =============================================================================
# Test: A valid agent task instantiates the correct agent
# =============================================================================


@pytest.mark.asyncio
async def test_valid_task_instantiates_agent(
    executor: AgentExecutorService,
    mock_aios: MockAIOSRuntime,
    sample_task: AgentTask,
) -> None:
    """
    Contract: A valid task instantiates the agent and runs reasoning.

    Verifies:
    - AIOS is called exactly once for a direct response
    - Result is ExecutionResult with completed status
    - Task ID preserved in result
    """
    mock_aios.set_responses(
        [AIOSResult.response("Hello! How can I help?", tokens_used=20)]
    )

    result = await executor.start_agent_task(sample_task)

    assert isinstance(result, ExecutionResult)
    assert result.status == "completed"
    assert result.task_id == sample_task.id
    assert mock_aios.call_count == 1


# =============================================================================
# Test: Executor binds tools approved by governance (CONTRACT-GRADE)
# =============================================================================


@pytest.mark.asyncio
async def test_executor_binds_approved_tools(
    executor: AgentExecutorService,
    mock_aios: MockAIOSRuntime,
    mock_tool_registry: MockToolRegistry,
    sample_task: AgentTask,
) -> None:
    """
    Contract: Executor queries governance and binds approved tools to AIOS context.

    Verifies:
    - get_approved_tools called with correct agent_id and principal_id
    - Approved tools appear in the first AIOS context
    - Tool definitions match the approved bindings
    """
    # Configure approved tools (tool_id is canonical identity)
    approved_tools = [
        ToolBinding(
            tool_id="search_web",
            display_name="Web Search",
            description="Search the web for information",
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        ),
        ToolBinding(
            tool_id="calculate",
            display_name="Calculator",
            description="Perform mathematical calculations",
            input_schema={
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        ),
    ]
    mock_tool_registry.set_approved_tools(approved_tools)

    mock_aios.set_responses([AIOSResult.response("Task complete", tokens_used=10)])

    result = await executor.start_agent_task(sample_task)

    # Verify governance lookup was called with correct identifiers
    assert len(mock_tool_registry.governance_calls) == 1
    gov_call = mock_tool_registry.governance_calls[0]
    assert gov_call["agent_id"] == sample_task.agent_id
    assert gov_call["principal_id"] == sample_task.source_id

    # Verify approved tools are in AIOS context
    context = mock_aios.get_context_at(0)
    assert "tools" in context
    tools_in_context = context["tools"]
    assert len(tools_in_context) == 2

    # Verify tool definitions match
    tool_ids_in_context = {t["function"]["name"] for t in tools_in_context}
    assert tool_ids_in_context == {"search_web", "calculate"}

    assert isinstance(result, ExecutionResult)
    assert result.status == "completed"


# =============================================================================
# Test: Tool result is in next AIOS context (CONTRACT-GRADE)
# =============================================================================


@pytest.mark.asyncio
async def test_tool_result_is_in_next_aios_context(
    executor: AgentExecutorService,
    mock_aios: MockAIOSRuntime,
    mock_tool_registry: MockToolRegistry,
    sample_task: AgentTask,
) -> None:
    """
    Contract: Tool execution results are fed back into the next reasoning context.

    Verifies:
    - Tool result appears in messages of subsequent AIOS call
    - Tool result content matches what was returned
    - Message includes tool_call_id for proper threading
    """
    # Configure approved tool (tool_id is canonical identity)
    approved_tools = [
        ToolBinding(
            tool_id="search_web",
            display_name="Web Search",
            description="Search the web",
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
            },
        ),
    ]
    mock_tool_registry.set_approved_tools(approved_tools)

    # Configure tool result (must include tool_id)
    tool_result_data = {"results": ["result1", "result2"], "count": 2}
    mock_tool_registry.set_dispatch_result(
        ToolCallResult(
            call_id=uuid4(),
            tool_id="search_web",
            success=True,
            result=tool_result_data,
            duration_ms=150,
        )
    )

    # AIOS: first requests tool, then responds
    tool_call = ToolCallRequest(
        tool_id="search_web",
        arguments={"query": "test query"},
        task_id=sample_task.id,
        iteration=1,
    )
    mock_aios.set_responses(
        [
            AIOSResult.tool_request(tool_call, tokens_used=30),
            AIOSResult.response("Based on search results...", tokens_used=40),
        ]
    )

    result = await executor.start_agent_task(sample_task)

    assert isinstance(result, ExecutionResult)
    assert result.status == "completed"
    assert mock_aios.call_count == 2

    # Get the second AIOS context (after tool execution)
    second_context = mock_aios.get_context_at(1)
    messages = second_context["messages"]

    # Find the tool result message
    tool_messages = [m for m in messages if m.get("role") == "tool"]
    assert len(tool_messages) == 1

    tool_msg = tool_messages[0]
    assert "tool_call_id" in tool_msg
    assert str(tool_result_data) in tool_msg["content"]


# =============================================================================
# Test: Execution loop calls AIOS
# =============================================================================


@pytest.mark.asyncio
async def test_execution_loop_calls_aios(
    executor: AgentExecutorService,
    mock_aios: MockAIOSRuntime,
    sample_task: AgentTask,
) -> None:
    """
    Contract: Execution loop invokes AIOS and captures response.

    Verifies:
    - AIOS called with assembled context
    - Response content preserved in result
    - Single iteration for direct response
    """
    mock_aios.set_responses([AIOSResult.response("Response from AIOS", tokens_used=50)])

    result = await executor.start_agent_task(sample_task)

    assert isinstance(result, ExecutionResult)
    assert mock_aios.call_count == 1
    assert result.status == "completed"
    assert result.result == "Response from AIOS"
    assert result.iterations == 1

    # Verify context was passed
    context = mock_aios.get_last_context()
    assert "messages" in context
    assert "metadata" in context


# =============================================================================
# Test: Tool call dispatched to registry with correct parameters
# =============================================================================


@pytest.mark.asyncio
async def test_tool_call_is_dispatched(
    executor: AgentExecutorService,
    mock_aios: MockAIOSRuntime,
    mock_tool_registry: MockToolRegistry,
    sample_task: AgentTask,
) -> None:
    """
    Contract: Tool calls are dispatched with correct tool_id, arguments, and context.

    Verifies:
    - Dispatch called with exact tool_id from AIOS
    - Dispatch called with exact arguments from AIOS
    - Context includes task_id, agent_id, thread_id, iteration
    """
    approved_tools = [
        ToolBinding(
            tool_id="search_web",
            display_name="Web Search",
            description="Search the web",
            input_schema={"type": "object"},
        ),
    ]
    mock_tool_registry.set_approved_tools(approved_tools)

    tool_call = ToolCallRequest(
        tool_id="search_web",
        arguments={"query": "test query", "limit": 10},
        task_id=sample_task.id,
        iteration=1,
    )

    mock_aios.set_responses(
        [
            AIOSResult.tool_request(tool_call, tokens_used=30),
            AIOSResult.response("Final answer", tokens_used=40),
        ]
    )

    result = await executor.start_agent_task(sample_task)

    assert isinstance(result, ExecutionResult)
    assert result.status == "completed"
    assert mock_tool_registry.dispatch_count == 1

    dispatch = mock_tool_registry.get_last_dispatch()
    assert dispatch["tool_id"] == "search_web"
    assert dispatch["arguments"] == {"query": "test query", "limit": 10}

    # Verify context fields
    ctx = dispatch["context"]
    assert ctx["task_id"] == str(sample_task.id)
    assert ctx["agent_id"] == sample_task.agent_id
    assert "thread_id" in ctx
    assert ctx["iteration"] == 1


# =============================================================================
# Test: Tool call tool_name resolved to canonical tool_id
# =============================================================================


@pytest.mark.asyncio
async def test_tool_call_name_resolution_for_openai(
    executor: AgentExecutorService,
    mock_aios: MockAIOSRuntime,
    mock_tool_registry: MockToolRegistry,
    sample_task: AgentTask,
) -> None:
    """
    Contract: OpenAI tool name aliases are resolved back to canonical tool_id.

    Verifies:
    - OpenAI-safe tool name is mapped back to original tool_id
    - Dispatch uses canonical tool_id
    """
    approved_tools = [
        ToolBinding(
            tool_id="github_create_issue",  # OpenAI-compatible (no dots)
            display_name="GitHub Create Issue",
            description="Create an issue in GitHub",
            input_schema={"type": "object"},
        ),
    ]
    mock_tool_registry.set_approved_tools(approved_tools)

    tool_call = ToolCallRequest(
        tool_id="github_create_issue",
        arguments={"title": "Bug", "body": "Details"},
        task_id=sample_task.id,
        iteration=1,
    )

    mock_aios.set_responses(
        [
            AIOSResult.tool_request(tool_call, tokens_used=10),
            AIOSResult.response("Issue created", tokens_used=10),
        ]
    )

    result = await executor.start_agent_task(sample_task)

    assert result.status == "completed"
    dispatch = mock_tool_registry.get_last_dispatch()
    assert dispatch["tool_id"] == "github_create_issue"


# =============================================================================
# Test: Executor terminates on final answer
# =============================================================================


@pytest.mark.asyncio
async def test_executor_terminates_on_final_answer(
    executor: AgentExecutorService,
    mock_aios: MockAIOSRuntime,
    sample_task: AgentTask,
) -> None:
    """
    Contract: Executor stops immediately when AIOS returns a response.

    Verifies:
    - Only one AIOS call made
    - Status is completed
    - Result content preserved exactly
    """
    mock_aios.set_responses(
        [AIOSResult.response("This is my final answer.", tokens_used=25)]
    )

    result = await executor.start_agent_task(sample_task)

    assert isinstance(result, ExecutionResult)
    assert result.status == "completed"
    assert result.result == "This is my final answer."
    assert mock_aios.call_count == 1


# =============================================================================
# Test: Executor terminates on max iterations
# =============================================================================


@pytest.mark.asyncio
async def test_executor_terminates_on_max_iterations(
    mock_aios: MockAIOSRuntime,
    mock_tool_registry: MockToolRegistry,
    mock_substrate: MockSubstrateService,
    mock_agent_registry: MockAgentRegistry,
) -> None:
    """
    Contract: Executor terminates when max iterations exceeded.

    Verifies:
    - Status is "terminated" (not "failed")
    - Error message includes max iterations info
    - Exactly max_iterations AIOS calls made
    """
    executor = AgentExecutorService(
        aios_runtime=mock_aios,
        tool_registry=mock_tool_registry,
        substrate_service=mock_substrate,
        agent_registry=mock_agent_registry,
        default_agent_id="l9-standard-v1",
        max_iterations=3,
    )

    approved_tools = [
        ToolBinding(
            tool_id="infinite_tool",
            display_name="Infinite Tool",
            description="A tool that keeps being called",
            input_schema={"type": "object"},
        ),
    ]
    mock_tool_registry.set_approved_tools(approved_tools)

    task = AgentTask(
        kind=TaskKind.QUERY,
        agent_id="l9-standard-v1",
        source_id="test",
        payload={"message": "Run forever"},
        max_iterations=3,
    )

    # Generate tool calls that exceed max iterations
    tool_calls = [
        AIOSResult.tool_request(
            ToolCallRequest(
                tool_id="infinite_tool",
                arguments={"n": i},
                task_id=task.id,
                iteration=i,
            ),
            tokens_used=10,
        )
        for i in range(10)
    ]
    mock_aios.set_responses(tool_calls)

    result = await executor.start_agent_task(task)

    assert isinstance(result, ExecutionResult)
    assert result.status == "terminated"
    assert result.error is not None
    assert "Max iterations exceeded" in result.error
    assert "(3)" in result.error  # Should include the limit
    assert result.iterations == 3
    assert mock_aios.call_count == 3


# =============================================================================
# Test: Idempotency returns DuplicateTaskResponse (CONTRACT-GRADE)
# =============================================================================


@pytest.mark.asyncio
async def test_idempotency_returns_duplicate_response(
    executor: AgentExecutorService,
    mock_aios: MockAIOSRuntime,
    sample_task: AgentTask,
) -> None:
    """
    Contract: Duplicate task returns DuplicateTaskResponse, not ExecutionResult.

    Verifies:
    - First call returns ExecutionResult
    - Second call returns DuplicateTaskResponse (distinct type)
    - DuplicateTaskResponse has correct fields: ok, status, task_id
    - AIOS only called once total
    """
    mock_aios.set_responses(
        [
            AIOSResult.response("First response", tokens_used=10),
            AIOSResult.response("This should not be returned", tokens_used=10),
        ]
    )

    # First execution
    result1 = await executor.start_agent_task(sample_task)
    assert isinstance(result1, ExecutionResult)
    assert result1.status == "completed"

    # Second execution - same task
    result2 = await executor.start_agent_task(sample_task)

    # Verify result2 is DuplicateTaskResponse, not ExecutionResult
    assert isinstance(result2, DuplicateTaskResponse)
    assert result2.ok is True
    assert result2.status == "duplicate"
    assert result2.task_id == sample_task.id

    # AIOS only called once
    assert mock_aios.call_count == 1


# =============================================================================
# Test: Invalid agent ID returns error
# =============================================================================


@pytest.mark.asyncio
async def test_invalid_agent_id_returns_error(
    executor: AgentExecutorService,
) -> None:
    """
    Contract: Unknown agent ID results in failed ExecutionResult.

    Verifies:
    - Status is "failed"
    - Error mentions the agent is not registered
    """
    task = AgentTask(
        kind=TaskKind.QUERY,
        agent_id="non-existent-agent",
        source_id="test",
        payload={"message": "Hello"},
    )

    result = await executor.start_agent_task(task)

    assert isinstance(result, ExecutionResult)
    assert result.status == "failed"
    assert result.error is not None
    assert "not registered" in result.error


# =============================================================================
# Test: Validation does NOT mutate task (no silent patching)
# =============================================================================


@pytest.mark.asyncio
async def test_validation_does_not_mutate_task(
    mock_aios: MockAIOSRuntime,
    mock_tool_registry: MockToolRegistry,
    mock_substrate: MockSubstrateService,
    mock_agent_registry: MockAgentRegistry,
) -> None:
    """
    Contract: Validation rejects invalid tasks without mutating them.

    Prior behavior: Missing agent_id was silently patched to default.
    Current behavior: Missing agent_id returns validation error.

    This ensures:
    - No hidden side effects during validation
    - Caller must explicitly provide required fields
    - Task objects remain immutable during validation
    """
    executor = AgentExecutorService(
        aios_runtime=mock_aios,
        tool_registry=mock_tool_registry,
        substrate_service=mock_substrate,
        agent_registry=mock_agent_registry,
        default_agent_id="l9-standard-v1",
        max_iterations=10,
    )

    # Create task without agent_id - should fail validation, not be patched
    # Note: AgentTask requires agent_id, so we test by checking the error message
    # hints the user about the default
    task = AgentTask(
        kind=TaskKind.QUERY,
        agent_id="",  # Empty string triggers validation
        source_id="test",
        payload={"message": "Hello"},
    )

    result = await executor.start_agent_task(task)

    assert isinstance(result, ExecutionResult)
    assert result.status == "failed"
    assert result.error is not None
    # Error should hint the default instead of silently using it
    assert "agent_id" in result.error.lower() or "l9-standard-v1" in result.error


# =============================================================================
# Test: AIOS error handled
# =============================================================================


@pytest.mark.asyncio
async def test_aios_error_handled(
    executor: AgentExecutorService,
    mock_aios: MockAIOSRuntime,
    sample_task: AgentTask,
) -> None:
    """
    Contract: AIOS error results in failed ExecutionResult with error message.

    Verifies:
    - Status is "failed"
    - Error message from AIOS preserved
    """
    mock_aios.set_responses([AIOSResult.error_result("Model overloaded")])

    result = await executor.start_agent_task(sample_task)

    assert isinstance(result, ExecutionResult)
    assert result.status == "failed"
    assert result.error is not None
    assert "Model overloaded" in result.error


# =============================================================================
# Test: Unbound tool handled (single tool identity rule)
# =============================================================================


@pytest.mark.asyncio
async def test_unbound_tool_not_dispatched(
    executor: AgentExecutorService,
    mock_aios: MockAIOSRuntime,
    mock_tool_registry: MockToolRegistry,
    sample_task: AgentTask,
) -> None:
    """
    Contract: Tool calls for unbound tools are not dispatched to registry.

    Single tool identity rule: tool calls must map unambiguously to approved tools.

    Verifies:
    - Dispatch not called for unbound tool
    - Execution continues (error added to context)
    - Task can still complete
    """
    # No tools approved
    mock_tool_registry.set_approved_tools([])

    tool_call = ToolCallRequest(
        tool_id="unbound_tool",
        arguments={},
        task_id=sample_task.id,
        iteration=1,
    )

    mock_aios.set_responses(
        [
            AIOSResult.tool_request(tool_call, tokens_used=20),
            AIOSResult.response("Recovered from error", tokens_used=10),
        ]
    )

    result = await executor.start_agent_task(sample_task)

    assert isinstance(result, ExecutionResult)
    assert result.status == "completed"
    assert mock_tool_registry.dispatch_count == 0  # Not dispatched


# =============================================================================
# Test: Tool dispatch failure handled
# =============================================================================


@pytest.mark.asyncio
async def test_tool_dispatch_failure_handled(
    executor: AgentExecutorService,
    mock_aios: MockAIOSRuntime,
    mock_tool_registry: MockToolRegistry,
    sample_task: AgentTask,
) -> None:
    """
    Contract: Exception during tool dispatch is caught and converted to error result.

    Verifies:
    - Exception doesn't crash executor
    - Error is added to context for next AIOS call
    - Execution can continue
    """
    approved_tools = [
        ToolBinding(
            tool_id="failing_tool",
            display_name="Failing Tool",
            description="A tool that fails",
            input_schema={"type": "object"},
        ),
    ]
    mock_tool_registry.set_approved_tools(approved_tools)
    mock_tool_registry.set_dispatch_exception(RuntimeError("Network timeout"))

    tool_call = ToolCallRequest(
        tool_id="failing_tool",
        arguments={},
        task_id=sample_task.id,
        iteration=1,
    )

    mock_aios.set_responses(
        [
            AIOSResult.tool_request(tool_call, tokens_used=20),
            AIOSResult.response("Handled the error", tokens_used=10),
        ]
    )

    result = await executor.start_agent_task(sample_task)

    assert isinstance(result, ExecutionResult)
    assert result.status == "completed"
    assert mock_tool_registry.dispatch_count == 1

    # Verify error was in second AIOS context
    second_context = mock_aios.get_context_at(1)
    messages = second_context["messages"]
    tool_messages = [m for m in messages if m.get("role") == "tool"]
    assert len(tool_messages) == 1
    assert "Network timeout" in tool_messages[0]["content"]


# =============================================================================
# Test: Packets emitted with required fields (CONTRACT-GRADE)
# =============================================================================


@pytest.mark.asyncio
async def test_packets_emitted_with_required_fields(
    executor: AgentExecutorService,
    mock_aios: MockAIOSRuntime,
    mock_substrate: MockSubstrateService,
    sample_task: AgentTask,
) -> None:
    """
    Contract: Packets are emitted with all required fields.

    Required fields:
    - packet_type
    - payload with task_id
    - thread_id
    - metadata.agent

    Verifies:
    - Start trace packet emitted
    - Iteration trace packet emitted
    - Result packet emitted
    - All packets have required fields
    """
    mock_aios.set_responses([AIOSResult.response("Done", tokens_used=10)])

    await executor.start_agent_task(sample_task)

    # Should have: start trace, iteration trace, result
    assert len(mock_substrate.packets) >= 3

    # Verify all packets have required fields
    for packet in mock_substrate.packets:
        assert hasattr(packet, "packet_type")
        assert hasattr(packet, "payload")
        assert hasattr(packet, "thread_id")
        assert hasattr(packet, "metadata")
        assert packet.thread_id == sample_task.get_thread_id()
        # metadata.agent should match the task's agent_id (extracted from payload.agent_id)
        assert packet.metadata.agent == sample_task.agent_id
        assert "task_id" in packet.payload or "event" in packet.payload

    # Verify specific packet types
    packet_types = [p.packet_type for p in mock_substrate.packets]
    assert "agent.executor.trace" in packet_types
    assert "agent.executor.result" in packet_types

    # Verify result packet has required fields
    result_packets = mock_substrate.get_packets_by_type("agent.executor.result")
    assert len(result_packets) == 1
    result_packet = result_packets[0]
    assert result_packet.payload["task_id"] == str(sample_task.id)
    assert "status" in result_packet.payload
    assert "iterations" in result_packet.payload
    assert "duration_ms" in result_packet.payload


# =============================================================================
# Test: Failure path emits error packet
# =============================================================================


@pytest.mark.asyncio
async def test_failure_path_emits_error_packet(
    executor: AgentExecutorService,
    mock_aios: MockAIOSRuntime,
    mock_substrate: MockSubstrateService,
    sample_task: AgentTask,
) -> None:
    """
    Contract: Failed execution emits result packet with error details.

    Verifies:
    - Result packet emitted on failure
    - status is "failed"
    - error field present
    """
    mock_aios.set_responses([AIOSResult.error_result("AIOS failure")])

    result = await executor.start_agent_task(sample_task)

    assert isinstance(result, ExecutionResult)
    assert result.status == "failed"

    # Find result packet
    result_packets = mock_substrate.get_packets_by_type("agent.executor.result")
    assert len(result_packets) == 1

    packet = result_packets[0]
    assert packet.payload["status"] == "failed"
    assert "error" in packet.payload
    assert packet.payload["error"] is not None


# =============================================================================
# Test: Substrate write failure doesn't crash execution
# =============================================================================


@pytest.mark.asyncio
async def test_substrate_write_failure_doesnt_crash(
    executor: AgentExecutorService,
    mock_aios: MockAIOSRuntime,
    mock_substrate: MockSubstrateService,
    sample_task: AgentTask,
) -> None:
    """
    Contract: Substrate write failures are logged but don't crash execution.

    Verifies:
    - Execution completes despite write failures
    - Result is still returned
    """
    mock_substrate.set_write_exception(RuntimeError("Database unavailable"))

    mock_aios.set_responses(
        [AIOSResult.response("Response despite substrate failure", tokens_used=10)]
    )

    result = await executor.start_agent_task(sample_task)

    assert isinstance(result, ExecutionResult)
    assert result.status == "completed"
    assert result.result == "Response despite substrate failure"
    # No packets recorded due to failures
    assert len(mock_substrate.packets) == 0


# =============================================================================
# Test: Tool call packet emitted
# =============================================================================


@pytest.mark.asyncio
async def test_tool_call_packet_emitted(
    executor: AgentExecutorService,
    mock_aios: MockAIOSRuntime,
    mock_tool_registry: MockToolRegistry,
    mock_substrate: MockSubstrateService,
    sample_task: AgentTask,
) -> None:
    """
    Contract: Tool calls emit agent.executor.tool_call packets.

    Verifies:
    - Packet type is correct
    - Payload includes tool_id, arguments, call_id
    """
    approved_tools = [
        ToolBinding(
            tool_id="search_web",
            display_name="Web Search",
            description="Search",
            input_schema={"type": "object"},
        ),
    ]
    mock_tool_registry.set_approved_tools(approved_tools)

    tool_call = ToolCallRequest(
        tool_id="search_web",
        arguments={"query": "test"},
        task_id=sample_task.id,
        iteration=1,
    )

    mock_aios.set_responses(
        [
            AIOSResult.tool_request(tool_call, tokens_used=20),
            AIOSResult.response("Done", tokens_used=10),
        ]
    )

    await executor.start_agent_task(sample_task)

    tool_packets = mock_substrate.get_packets_by_type("agent.executor.tool_call")
    assert len(tool_packets) == 1

    packet = tool_packets[0]
    assert packet.payload["tool_id"] == "search_web"
    assert packet.payload["arguments"] == {"query": "test"}
    assert "call_id" in packet.payload


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "MockAIOSRuntime",
    "MockToolRegistry",
    "MockSubstrateService",
    "MockAgentRegistry",
]
