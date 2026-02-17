# tests/invariant/test_execution_memory_contracts.py
"""
Invariant tests enforcing canonical execution and memory boundaries.

Validates:
1. Fail-closed principal_id enforcement
2. No bypass patterns outside allowed files
3. Tool kernel enforcement
4. Memory boundary enforcement
"""
import ast
import pathlib
import pytest
from typing import Set
from unittest.mock import AsyncMock, Mock

# System under test
from core.tools.registry_adapter import ExecutorToolRegistry, SYSTEM_PRINCIPAL_ID as TOOL_SYSTEM_PRINCIPAL
from memory.substrate_service import MemorySubstrateService, SYSTEM_PRINCIPAL_ID as MEMORY_SYSTEM_PRINCIPAL
from core.schemas.packets import PacketEnvelopeIn


class TestToolKernelBoundary:
    """Test tool kernel boundary enforcement."""

    @pytest.mark.asyncio
    async def test_guarded_execute_requires_principal_id(self):
        """guarded_execute must reject None principal_id."""
        mock_registry = Mock()
        mock_agent = Mock()
        mock_agent.kernel_state = Mock(initialized=True, kernels=["kernel1"])

        registry = ExecutorToolRegistry(base_registry=mock_registry)

        # None principal_id
        with pytest.raises(RuntimeError, match="principal_id REQUIRED"):
            await registry.guarded_execute(
                mock_agent,
                "test_tool",
                {},
                {},
                principal_id=None,
            )

        # Empty string
        with pytest.raises(RuntimeError, match="principal_id REQUIRED"):
            await registry.guarded_execute(
                mock_agent,
                "test_tool",
                {},
                {},
                principal_id="",
            )

    @pytest.mark.asyncio
    async def test_dispatch_tool_call_requires_principal_id(self):
        """dispatch_tool_call must reject None principal_id."""
        mock_registry = AsyncMock()
        registry = ExecutorToolRegistry(base_registry=mock_registry)

        with pytest.raises(RuntimeError, match="principal_id REQUIRED"):
            await registry.dispatch_tool_call(
                "test_tool",
                {},
                {},
                principal_id=None,
            )


class TestMemoryBoundary:
    """Test memory boundary enforcement."""

    @pytest.mark.asyncio
    async def test_write_packet_requires_principal_id(self):
        """write_packet must reject None principal_id."""
        mock_repo = AsyncMock()
        mock_embedding = AsyncMock()
        service = MemorySubstrateService(repository=mock_repo, embedding_provider=mock_embedding)

        packet_in = PacketEnvelopeIn(
            packet_type="TestPacket",
            payload={"test": "data"},
        )

        # None principal_id
        with pytest.raises(RuntimeError, match="principal_id REQUIRED"):
            await service.write_packet(packet_in, principal_id=None)

        # Empty string
        with pytest.raises(RuntimeError, match="principal_id REQUIRED"):
            await service.write_packet(packet_in, principal_id="")

        # Whitespace-only
        with pytest.raises(RuntimeError, match="principal_id REQUIRED"):
            await service.write_packet(packet_in, principal_id="   ")

    @pytest.mark.asyncio
    async def test_semantic_search_requires_principal_id(self):
        """semantic_search must reject None principal_id."""
        mock_repo = AsyncMock()
        mock_embedding = AsyncMock()
        service = MemorySubstrateService(repository=mock_repo, embedding_provider=mock_embedding)

        with pytest.raises(RuntimeError, match="principal_id REQUIRED"):
            await service.semantic_search("test query", principal_id=None)

        with pytest.raises(RuntimeError, match="principal_id REQUIRED"):
            await service.semantic_search("test query", principal_id="")

    @pytest.mark.asyncio
    async def test_read_packet_requires_principal_id(self):
        """read_packet must reject None principal_id."""
        mock_repo = AsyncMock()
        mock_embedding = AsyncMock()
        service = MemorySubstrateService(repository=mock_repo, embedding_provider=mock_embedding)

        with pytest.raises(RuntimeError, match="principal_id REQUIRED"):
            await service.read_packet("packet-123", principal_id=None)

    @pytest.mark.asyncio
    async def test_system_principal_is_valid(self):
        """SYSTEM_PRINCIPAL_ID should be accepted."""
        mock_repo = AsyncMock()
        mock_repo.write_packet = AsyncMock(return_value="packet-id-123")
        mock_embedding = AsyncMock()
        service = MemorySubstrateService(repository=mock_repo, embedding_provider=mock_embedding)

        packet_in = PacketEnvelopeIn(
            packet_type="SystemPacket",
            payload={"internal": "operation"},
        )

        # Should not raise
        packet_id = await service.write_packet(packet_in, principal_id=MEMORY_SYSTEM_PRINCIPAL)

        assert packet_id == "packet-id-123"
        mock_repo.write_packet.assert_called_once()


class ForbiddenPatternVisitor(ast.NodeVisitor):
    """AST visitor to detect forbidden direct persistence calls."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.violations: list[dict] = []

    def visit_Call(self, node: ast.Call):
        """Check for forbidden call patterns."""
        if isinstance(node.func, ast.Attribute):
            # Direct Redis calls
            if node.func.attr in ("set", "get", "delete", "hset", "hget", "lpush", "rpush", "expire"):
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "redis":
                    self.violations.append({
                        "file": self.filepath,
                        "line": node.lineno,
                        "pattern": f"redis.{node.func.attr}()",
                        "message": "Direct Redis call bypasses canonical boundary",
                    })

            # Direct SQL calls
            if node.func.attr == "execute":
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "session":
                    self.violations.append({
                        "file": self.filepath,
                        "line": node.lineno,
                        "pattern": "session.execute()",
                        "message": "Direct SQL call bypasses canonical boundary",
                    })

            # Direct Neo4j calls
            if node.func.attr == "run":
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "session":
                    self.violations.append({
                        "file": self.filepath,
                        "line": node.lineno,
                        "pattern": "session.run()",
                        "message": "Direct Neo4j call bypasses canonical boundary",
                    })

        self.generic_visit(node)


def is_allowed_file(filepath: pathlib.Path, allowed_patterns: Set[str]) -> bool:
    """Check if file is in the allowed bypass list."""
    filepath_str = str(filepath)
    return any(pattern in filepath_str for pattern in allowed_patterns)


class TestNoBypassScan:
    """Test that no direct persistence bypasses exist outside allowed files."""

    # Files allowed to have direct persistence calls
    ALLOWED_FILES = {
        "runtime/redis_client.py",
        "memory/substrate_repository.py",
        "memory/graph_client.py",
        "memory/cache/working_memory_service.py",
        "memory/predictive_cache.py",
        "memory/saga.py",
        "world_model/repository.py",
    }

    def test_no_direct_persistence_bypass(self):
        """Scan repo for forbidden direct persistence calls."""
        repo_root = pathlib.Path(__file__).parent.parent.parent

        violations = []

        for pyfile in repo_root.rglob("*.py"):
            # Skip test files
            if "/tests/" in str(pyfile):
                continue

            # Skip allowed files
            if is_allowed_file(pyfile, self.ALLOWED_FILES):
                continue

            try:
                content = pyfile.read_text()
                tree = ast.parse(content, filename=str(pyfile))

                visitor = ForbiddenPatternVisitor(filepath=str(pyfile))
                visitor.visit(tree)

                violations.extend(visitor.violations)
            except SyntaxError:
                continue

        # Assert no violations
        if violations:
            violation_report = "\n".join(
                f"  {v['file']}:{v['line']} - {v['pattern']} - {v['message']}"
                for v in violations
            )
            pytest.fail(
                f"Found {len(violations)} canonical boundary bypass violations:\n{violation_report}\n\n"
                f"Fix: Use MemorySubstrateService/ExecutorToolRegistry methods with explicit principal_id."
            )

    def test_allowlist_files_exist(self):
        """Verify that allowed bypass files actually exist."""
        repo_root = pathlib.Path(__file__).parent.parent.parent

        for allowed_file in self.ALLOWED_FILES:
            filepath = repo_root / allowed_file
            assert filepath.exists(), f"Allowlisted file does not exist: {allowed_file}"


class TestMCPRouteInvariants:
    """Test MCP routes enforce principal_id validation."""

    @pytest.mark.asyncio
    async def test_save_memory_rejects_none_user_id(self):
        """save_memory_handler must reject None user_id."""
        from mcp.memory.src.routes.memory_unified import save_memory_handler

        with pytest.raises(ValueError, match="user_id.*REQUIRED"):
            await save_memory_handler(
                content="Test memory",
                kind="note",
                scope="user",
                duration="persistent",
                user_id=None,
            )

    @pytest.mark.asyncio
    async def test_search_memory_rejects_none_user_id(self):
        """search_memory_handler must reject None user_id."""
        from mcp.memory.src.routes.memory_unified import search_memory_handler

        with pytest.raises(ValueError, match="user_id.*REQUIRED"):
            await search_memory_handler(
                query="test query",
                user_id=None,
            )
