"""
Tests for DORA Block Auto-Update Functionality
"""

__dora_meta__ = {
    "component_name": "DORA Auto-Update Tests",
    "module_version": "1.0.0",
    "created_by": "Manus AI Agent",
    "created_at": "2026-01-25T00:00:00Z",
    "updated_at": "2026-01-25T00:00:00Z",
    "layer": "testing",
    "domain": "runtime_operations",
    "module_name": "tests.runtime.test_dora_auto_update",
    "type": "test",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}

import asyncio
import tempfile
from pathlib import Path

import pytest

from runtime.dora import (
    DoraTraceBlock,
    emit_executor_trace,
    format_dora_block_python,
    l9_traced,
    update_dora_block_in_file,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def temp_python_file():
    """Create a temporary Python file with DORA block."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write('"""\nTest module for DORA auto-update.\n"""\n\n')
        f.write("def test_function():\n")
        f.write('    return "test"\n\n')
        # Add empty DORA block
        f.write("# " + "=" * 76 + "\n")
        f.write("# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT\n")
        f.write("# " + "=" * 76 + "\n")
        f.write("__l9_trace__ = {\n")
        f.write('    "trace_id": "",\n')
        f.write('    "task": "",\n')
        f.write('    "timestamp": "",\n')
        f.write('    "patterns_used": [],\n')
        f.write('    "graph": {"nodes": [], "edges": []},\n')
        f.write('    "inputs": {},\n')
        f.write('    "outputs": {},\n')
        f.write(
            '    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},\n'
        )
        f.write("}\n")
        f.write("# " + "=" * 76 + "\n")
        f.write("# END L9 DORA BLOCK\n")
        f.write("# " + "=" * 76 + "\n")
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


# =============================================================================
# Test DoraTraceBlock Creation
# =============================================================================


def test_dora_trace_block_create():
    """Test creating a DoraTraceBlock."""
    trace = DoraTraceBlock.create(
        task="test_task",
        inputs={"arg1": "value1"},
        outputs={"result": "success"},
        patterns_used=["pattern1"],
        duration_ms=100,
        errors=None,
    )

    assert trace.task == "test_task"
    assert trace.inputs == {"arg1": "value1"}
    assert trace.outputs == {"result": "success"}
    assert trace.patterns_used == ["pattern1"]
    assert trace.metrics.duration_ms == 100
    assert trace.metrics.stability_score == "1.0"
    assert trace.metrics.confidence == "0.95"
    assert len(trace.trace_id) == 8  # UUID first 8 chars


def test_dora_trace_block_with_errors():
    """Test creating a DoraTraceBlock with errors."""
    trace = DoraTraceBlock.create(
        task="test_task",
        inputs={},
        outputs={},
        errors=["Error 1", "Error 2"],
    )

    assert trace.metrics.errors_detected == ["Error 1", "Error 2"]
    assert trace.metrics.stability_score == "0.5"
    assert trace.metrics.confidence == "0.7"


# =============================================================================
# Test DORA Block File Operations
# =============================================================================


def test_format_dora_block_python():
    """Test formatting DORA block for Python files."""
    trace = DoraTraceBlock.create(
        task="test_task",
        inputs={"x": 1},
        outputs={"y": 2},
        duration_ms=50,
    )

    formatted = format_dora_block_python(trace)

    assert "L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT" in formatted
    assert "__l9_trace__ = {" in formatted
    assert '"task": "test_task"' in formatted
    assert "END L9 DORA BLOCK" in formatted


def test_update_dora_block_in_file(temp_python_file):
    """Test updating DORA block in a file."""
    # Create trace
    trace = DoraTraceBlock.create(
        task="updated_task",
        inputs={"input1": "test"},
        outputs={"output1": "result"},
        patterns_used=["test_pattern"],
        duration_ms=123,
    )

    # Update file
    success = update_dora_block_in_file(temp_python_file, trace)
    assert success is True

    # Read file and verify update
    content = temp_python_file.read_text()
    assert '"task": "updated_task"' in content
    assert '"input1": "test"' in content
    assert '"output1": "result"' in content
    assert '"test_pattern"' in content
    assert trace.trace_id in content


def test_update_dora_block_nonexistent_file():
    """Test updating DORA block in nonexistent file."""
    fake_path = Path("/tmp/nonexistent_file.py")
    trace = DoraTraceBlock.create(task="test", inputs={}, outputs={})

    success = update_dora_block_in_file(fake_path, trace)
    assert success is False


# =============================================================================
# Test @l9_traced Decorator
# =============================================================================


def test_l9_traced_decorator_default_update_source(temp_python_file):
    """Test that @l9_traced now defaults to update_source=True."""

    # Create a traced function
    @l9_traced(source_file=temp_python_file)
    def test_func(x: int) -> int:
        return x * 2

    # Execute function
    result = test_func(5)
    assert result == 10

    # Verify DORA block was updated (default update_source=True)
    content = temp_python_file.read_text()
    assert '"task": "test_func"' in content
    assert '"x": 5' in content
    assert '"output": 10' in content


def test_l9_traced_decorator_explicit_no_update():
    """Test @l9_traced with update_source=False."""

    @l9_traced(update_source=False)
    def test_func(x: int) -> int:
        return x * 2

    # Execute function (should not try to update any file)
    result = test_func(5)
    assert result == 10


@pytest.mark.asyncio
async def test_l9_traced_async_function(temp_python_file):
    """Test @l9_traced with async function."""

    @l9_traced(source_file=temp_python_file)
    async def async_test_func(x: int) -> int:
        await asyncio.sleep(0.01)
        return x * 3

    # Execute async function
    result = await async_test_func(7)
    assert result == 21

    # Verify DORA block was updated
    content = temp_python_file.read_text()
    assert '"task": "async_test_func"' in content
    assert '"x": 7' in content
    assert '"output": 21' in content


def test_l9_traced_with_patterns(temp_python_file):
    """Test @l9_traced with custom patterns."""

    @l9_traced(
        patterns=["safety_check", "validation"],
        task_name="custom_task",
        source_file=temp_python_file,
    )
    def test_func(data: str) -> str:
        return data.upper()

    result = test_func("hello")
    assert result == "HELLO"

    # Verify patterns in DORA block
    content = temp_python_file.read_text()
    assert '"task": "custom_task"' in content
    assert '"safety_check"' in content
    assert '"validation"' in content


def test_l9_traced_with_error(temp_python_file):
    """Test @l9_traced captures errors."""

    @l9_traced(source_file=temp_python_file)
    def failing_func(x: int) -> int:
        if x < 0:
            raise ValueError("Negative value not allowed")
        return x * 2

    # Execute with error
    with pytest.raises(ValueError):
        failing_func(-5)

    # Verify error was captured in DORA block
    content = temp_python_file.read_text()
    assert '"task": "failing_func"' in content
    assert "ValueError" in content
    assert "Negative value not allowed" in content


# =============================================================================
# Test emit_executor_trace
# =============================================================================


@pytest.mark.asyncio
async def test_emit_executor_trace_basic():
    """Test emit_executor_trace creates trace."""
    trace = await emit_executor_trace(
        task_id="task-123",
        task_name="test_task",
        agent_id="agent-456",
        inputs={"input": "data"},
        outputs={"output": "result"},
        duration_ms=250,
    )

    assert trace.task == "agent-456:test_task"
    assert trace.inputs["task_id"] == "task-123"
    assert trace.inputs["agent_id"] == "agent-456"
    assert trace.inputs["input"] == "data"
    assert trace.outputs == {"output": "result"}
    assert trace.metrics.duration_ms == 250


@pytest.mark.asyncio
async def test_emit_executor_trace_with_file_update(temp_python_file):
    """Test emit_executor_trace updates source file."""
    trace = await emit_executor_trace(
        task_id="task-789",
        task_name="executor_task",
        agent_id="agent-abc",
        inputs={"param": "value"},
        outputs={"status": "completed"},
        duration_ms=500,
        patterns=["execution", "monitoring"],
        source_file=temp_python_file,
    )

    assert trace is not None

    # Verify file was updated
    content = temp_python_file.read_text()
    assert '"task": "agent-abc:executor_task"' in content
    assert '"task_id": "task-789"' in content
    assert '"status": "completed"' in content
    assert '"execution"' in content
    assert '"monitoring"' in content


@pytest.mark.asyncio
async def test_emit_executor_trace_with_errors(temp_python_file):
    """Test emit_executor_trace captures errors."""
    trace = await emit_executor_trace(
        task_id="task-error",
        task_name="failing_task",
        agent_id="agent-xyz",
        inputs={},
        outputs={},
        duration_ms=100,
        errors=["Error 1", "Error 2"],
        source_file=temp_python_file,
    )

    assert trace.metrics.errors_detected == ["Error 1", "Error 2"]

    # Verify errors in file
    content = temp_python_file.read_text()
    assert '"Error 1"' in content
    assert '"Error 2"' in content


# =============================================================================
# Integration Tests
# =============================================================================


def test_full_workflow_sync(temp_python_file):
    """Test full workflow: decorate -> execute -> verify update."""

    @l9_traced(
        task_name="integration_test",
        patterns=["integration"],
        source_file=temp_python_file,
    )
    def process_data(data: dict) -> dict:
        return {"processed": data.get("value", 0) * 10}

    # Execute
    result = process_data({"value": 42})
    assert result == {"processed": 420}

    # Verify DORA block
    content = temp_python_file.read_text()
    assert '"task": "integration_test"' in content
    assert '"integration"' in content
    assert '"value": 42' in content
    assert '"processed": 420' in content
    assert "L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT" in content


@pytest.mark.asyncio
async def test_full_workflow_async(temp_python_file):
    """Test full workflow with async function."""

    @l9_traced(
        task_name="async_integration_test",
        patterns=["async", "integration"],
        source_file=temp_python_file,
    )
    async def async_process(x: int, y: int) -> int:
        await asyncio.sleep(0.01)
        return x + y

    # Execute
    result = await async_process(10, 20)
    assert result == 30

    # Verify DORA block
    content = temp_python_file.read_text()
    assert '"task": "async_integration_test"' in content
    assert '"async"' in content
    assert '"x": 10' in content
    assert '"y": 20' in content
    assert '"output": 30' in content


# =============================================================================
# END TESTS
# =============================================================================

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TEST-DORA-001",
    "governance_level": "low",
    "compliance_required": False,
    "audit_trail": False,
    "dependencies": ["runtime.dora"],
    "tags": ["async", "testing", "dora", "runtime-operations"],
    "keywords": ["test", "dora", "trace", "decorator", "auto-update"],
    "business_value": "Ensures DORA block auto-update functionality works correctly",
    "last_modified": "2026-01-25T00:00:00Z",
    "modified_by": "Manus_AI_Agent",
    "change_summary": "Initial test suite for DORA auto-update fix",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# ============================================================================
__l9_trace__ = {
    "trace_id": "<pending>",
    "task": "<pending_first_run>",
    "timestamp": "<auto-updates on execution>",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {
        "confidence": "",
        "errors_detected": [],
        "stability_score": "",
        "duration_ms": None,
    },
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
