"""
L9 Runtime - MCP Client
========================

MCP (Model Context Protocol) client for connecting to MCP servers.

Provides:
- List tools from MCP servers
- Call tools on MCP servers
- Registry of allowed MCP tools

Version: 1.0.0
"""

from __future__ import annotations

from core.decorators import must_stay_async
from core.singleton_auto_registry import register_singleton

# ============================================================================
__dora_meta__ = {
    "component_name": "MCP Client",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-25T18:55:20Z",
    "updated_at": "2026-01-13T15:37:09Z",
    "layer": "operations",
    "domain": "runtime_operations",
    "module_name": "mcp_client",
    "type": "client",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API"],
        "memory_layers": ["semantic_memory"],
        "imported_by": [
            "core.singleton_registry",
            "runtime.l_tools",
            "runtime.mcp_tool",
        ],
    },
}
# ============================================================================

import asyncio
import contextlib
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)


# =============================================================================
# MCP Server Process Manager
# =============================================================================


class MCPServerProcess:
    """
    Manages a single MCP server subprocess.

    Handles JSON-RPC 2.0 communication over stdio.
    """

    def __init__(
        self,
        server_id: str,
        command: list[str],
        env: dict[str, str] | None = None,
    ):
        self.server_id = server_id
        self.command = command
        self.env = env or {}
        self._process: asyncio.subprocess.Process | None = None
        self._lock = asyncio.Lock()
        self._request_id = 0
        self._pending_requests: dict[str, asyncio.Future] = {}
        self._reader_task: asyncio.Task | None = None

    async def start(self) -> bool:
        """Start the MCP server process."""
        async with self._lock:
            if self._process is not None:
                return True

            try:
                # Merge environment
                process_env = os.environ.copy()
                process_env.update(self.env)

                self._process = await asyncio.create_subprocess_exec(
                    *self.command,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=process_env,
                )

                # Start response reader
                self._reader_task = asyncio.create_task(self._read_responses())

                logger.info(
                    "MCP server process started",
                    server_id=self.server_id,
                    pid=self._process.pid,
                )
                return True

            except Exception as e:
                logger.error(
                    "Failed to start MCP server",
                    server_id=self.server_id,
                    error=str(e),
                )
                return False

    async def stop(self) -> None:
        """Stop the MCP server process."""
        async with self._lock:
            if self._reader_task:
                self._reader_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._reader_task
                self._reader_task = None

            if self._process:
                self._process.terminate()
                try:
                    await asyncio.wait_for(self._process.wait(), timeout=5.0)
                except TimeoutError:
                    self._process.kill()
                    await self._process.wait()

                logger.info("MCP server process stopped", server_id=self.server_id)
                self._process = None

            # Cancel pending requests
            for future in self._pending_requests.values():
                if not future.done():
                    future.set_exception(Exception("Server stopped"))
            self._pending_requests.clear()

    async def _read_responses(self) -> None:
        """Read responses from stdout and dispatch to pending requests."""
        if not self._process or not self._process.stdout:
            return

        try:
            while True:
                line = await self._process.stdout.readline()
                if not line:
                    break

                try:
                    response = json.loads(line.decode().strip())
                    request_id = response.get("id")

                    if request_id and request_id in self._pending_requests:
                        future = self._pending_requests.pop(request_id)
                        if not future.done():
                            if "error" in response:
                                future.set_exception(
                                    Exception(
                                        response["error"].get(
                                            "message", "Unknown error"
                                        )
                                    )
                                )
                            else:
                                future.set_result(response.get("result"))

                except json.JSONDecodeError:
                    logger.warning(
                        "Invalid JSON from MCP server", server_id=self.server_id
                    )

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(
                "MCP response reader error", server_id=self.server_id, error=str(e)
            )

    @must_stay_async("callers use await")
    async def send_request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        timeout: float = 30.0,
    ) -> Any:
        """
        Send a JSON-RPC request and wait for response.

        Args:
            method: JSON-RPC method name
            params: Method parameters
            timeout: Request timeout in seconds

        Returns:
            Result from the MCP server
        """
        if not self._process or not self._process.stdin:
            raise Exception(f"MCP server {self.server_id} not running")

        self._request_id += 1
        request_id = f"{self.server_id}-{self._request_id}"

        request = {
            "jsonrpc": "2.0",
            "method": method,
            "id": request_id,
        }
        if params:
            request["params"] = params

        # Create future for response
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future

        try:
            # Send request
            request_line = json.dumps(request) + "\n"
            self._process.stdin.write(request_line.encode())
            await self._process.stdin.drain()

            # Wait for response
            return await asyncio.wait_for(future, timeout=timeout)

        except TimeoutError:
            self._pending_requests.pop(request_id, None)
            raise Exception(f"MCP request timed out: {method}") from None
        except Exception:
            self._pending_requests.pop(request_id, None)
            raise

    @property
    def is_running(self) -> bool:
        """Check if the process is running."""
        return self._process is not None and self._process.returncode is None


class ToolMeta:
    """Metadata for an MCP tool."""

    def __init__(
        self,
        name: str,
        description: str = "",
        input_schema: dict[str, Any] | None = None,
    ):
        self.name = name
        self.description = description
        self.input_schema = input_schema or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


class MCPClient:
    """
    MCP client for connecting to MCP servers.

    Supports multiple MCP servers (GitHub, Notion, Vercel, GoDaddy).
    Configuration via environment variables.

    Uses JSON-RPC 2.0 over stdio for communication.
    """

    def __init__(self):
        """Initialize MCP client with server configurations."""
        self._servers: dict[str, dict[str, Any]] = {}
        self._allowed_tools: dict[str, list[str]] = {}  # server_id -> [tool_names]
        self._processes: dict[str, MCPServerProcess] = {}  # server_id -> process
        self._load_servers()

    def _load_servers(self) -> None:
        """Load MCP server configurations from environment."""
        # GitHub MCP - uses @modelcontextprotocol/server-github
        github_token = os.getenv("MCP_GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN")
        github_command = os.getenv(
            "MCP_GITHUB_COMMAND", "npx -y @modelcontextprotocol/server-github"
        )
        if github_token:
            self._servers["github"] = {
                "command": github_command.split(),
                "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": github_token},
                "enabled": True,
            }
            self._allowed_tools["github"] = [
                "create_issue",
                "create_pull_request",
                "merge_pull_request",
                "get_file_contents",
                "list_issues",
                "search_repositories",
            ]
            logger.info("GitHub MCP server configured")

        # Notion MCP - uses notion MCP server
        notion_token = os.getenv("MCP_NOTION_TOKEN") or os.getenv("NOTION_API_KEY")
        notion_command = os.getenv(
            "MCP_NOTION_COMMAND", "npx -y @modelcontextprotocol/server-notion"
        )
        if notion_token:
            self._servers["notion"] = {
                "command": notion_command.split(),
                "env": {"NOTION_API_KEY": notion_token},
                "enabled": True,
            }
            self._allowed_tools["notion"] = [
                "create_page",
                "update_page",
                "get_page",
                "search",
                "query_database",
            ]
            logger.info("Notion MCP server configured")

        # Filesystem MCP - for local file operations
        fs_command = os.getenv(
            "MCP_FILESYSTEM_COMMAND", "npx -y @modelcontextprotocol/server-filesystem"
        )
        fs_allowed_dirs = os.getenv(
            "MCP_FILESYSTEM_ALLOWED_DIRS", str(Path.home() / "Projects")
        )
        self._servers["filesystem"] = {
            "command": fs_command.split() + fs_allowed_dirs.split(","),
            "env": {},
            "enabled": True,
        }
        self._allowed_tools["filesystem"] = [
            "read_file",
            "write_file",
            "list_directory",
            "create_directory",
        ]
        logger.info("Filesystem MCP server configured")

        # Memory MCP - for knowledge graph operations (upstream MCP server)
        memory_command = os.getenv(
            "MCP_MEMORY_COMMAND", "npx -y @modelcontextprotocol/server-memory"
        )
        self._servers["memory"] = {
            "command": memory_command.split(),
            "env": {},
            "enabled": True,
        }
        self._allowed_tools["memory"] = [
            "create_entities",
            "create_relations",
            "search_nodes",
            "read_graph",
        ]
        logger.info("Memory MCP server configured")

        # ========================================================================
        # L9 Memory MCP (Active as of 2026-01-09)
        # ========================================================================
        # MCP server is live at https://l9.quantumaipartners.com/mcp
        # Uses unified substrate (packet_store + memory_embeddings)
        # All memory operations go through MCP tools (save_memory, search_memory, etc.)
        # See: mcp_memory/README.md for details
        #
        # Cursor integration:
        #   - mcp.json configured with l9-memory server (SSE connection)
        #   - cursor_memory_client.py uses MCP tools via /mcp/call endpoint
        #   - /mem command uses MCP exclusively
        # ========================================================================

    def is_server_available(self, server_id: str) -> bool:
        """Check if an MCP server is configured and available."""
        return server_id in self._servers and self._servers[server_id].get(
            "enabled", False
        )

    def get_allowed_tools(self, server_id: str) -> list[str]:
        """Get list of allowed tools for a server."""
        return self._allowed_tools.get(server_id, [])

    def is_tool_allowed(self, server_id: str, tool_name: str) -> bool:
        """Check if a tool is allowed for a server."""
        allowed = self._allowed_tools.get(server_id, [])
        # Check both with and without server prefix
        return tool_name in allowed or f"{server_id}.{tool_name}" in allowed

    async def _get_or_start_server(self, server_id: str) -> MCPServerProcess:
        """Get or start an MCP server process."""
        if server_id in self._processes and self._processes[server_id].is_running:
            return self._processes[server_id]

        server_config = self._servers.get(server_id)
        if not server_config:
            raise Exception(f"MCP server {server_id} not configured")

        process = MCPServerProcess(
            server_id=server_id,
            command=server_config["command"],
            env=server_config.get("env", {}),
        )

        if not await process.start():
            raise Exception(f"Failed to start MCP server {server_id}")

        self._processes[server_id] = process

        # Initialize the server (MCP handshake)
        try:
            await process.send_request(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "L9", "version": "1.0.0"},
                },
            )
            logger.info("MCP server initialized", server_id=server_id)
        except Exception as e:
            logger.warning(
                "MCP initialize failed (may be optional)",
                server_id=server_id,
                error=str(e),
            )

        return process

    async def stop_all_servers(self) -> None:
        """Stop all running MCP server processes."""
        for _server_id, process in list(self._processes.items()):
            await process.stop()
        self._processes.clear()
        logger.info("All MCP servers stopped")

    async def list_tools(self, server_id: str) -> list[ToolMeta]:
        """
        List available tools from an MCP server.

        Queries the server via JSON-RPC tools/list method.
        Falls back to configured allowed tools if server unavailable.

        Args:
            server_id: Server identifier (e.g., "github", "notion")

        Returns:
            List of ToolMeta objects
        """
        if not self.is_server_available(server_id):
            logger.warning(f"MCP server {server_id} not available")
            return []

        try:
            # Get or start the server process
            process = await self._get_or_start_server(server_id)

            # Query available tools
            result = await process.send_request(
                method="tools/list",
                params={},
                timeout=30.0,
            )

            tools = []
            for tool_data in result.get("tools", []):
                tool_name = tool_data.get("name", "")

                # Only include allowed tools
                if self.is_tool_allowed(server_id, tool_name):
                    tool_meta = ToolMeta(
                        name=tool_name,
                        description=tool_data.get("description", ""),
                        input_schema=tool_data.get("inputSchema", {}),
                    )
                    tools.append(tool_meta)

            logger.info(f"Listed {len(tools)} tools from MCP server {server_id}")
            return tools

        except Exception as e:
            logger.warning(
                "Failed to list MCP tools, using fallback",
                server_id=server_id,
                error=str(e),
            )

            # Fallback to configured allowed tools
            allowed_tool_names = self._allowed_tools.get(server_id, [])
            tools = []
            for tool_name in allowed_tool_names:
                tool_meta = ToolMeta(
                    name=tool_name,
                    description=f"{tool_name} via {server_id} MCP",
                    input_schema={},
                )
                tools.append(tool_meta)

            return tools

    @must_stay_async("callers use await")
    async def call_tool(
        self,
        server_id: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Call a tool on an MCP server.

        Supports both stdio-based (JSON-RPC over subprocess) and HTTP-based servers.

        Args:
            server_id: Server identifier (e.g., "github", "notion", "l9-memory")
            tool_name: Tool name (e.g., "create_issue", "saveMemory")
            arguments: Tool arguments

        Returns:
            Tool result dictionary with success, result, and error fields
        """
        if not self.is_server_available(server_id):
            return {
                "success": False,
                "error": f"MCP server {server_id} not available",
                "result": None,
            }

        if not self.is_tool_allowed(server_id, tool_name):
            return {
                "success": False,
                "error": f"Tool {tool_name} not allowed for server {server_id}",
                "result": None,
            }

        logger.info(
            "Calling MCP tool",
            server_id=server_id,
            tool_name=tool_name,
            arguments=arguments,
        )

        server_config = self._servers.get(server_id, {})

        # Check if HTTP-based server (like l9-memory)
        if server_config.get("type") == "http":
            return await self._call_http_tool(server_id, tool_name, arguments)

        # Standard stdio-based MCP server
        try:
            # Get or start the server process
            process = await self._get_or_start_server(server_id)

            # Call the tool via JSON-RPC
            result = await process.send_request(
                method="tools/call",
                params={
                    "name": tool_name,
                    "arguments": arguments,
                },
                timeout=60.0,
            )

            logger.info(
                "MCP tool call succeeded",
                server_id=server_id,
                tool_name=tool_name,
            )

            return {
                "success": True,
                "result": result,
                "error": None,
            }

        except Exception as e:
            logger.error(
                "MCP tool call failed",
                server_id=server_id,
                tool_name=tool_name,
                error=str(e),
            )
            return {
                "success": False,
                "error": str(e),
                "result": None,
            }

    @must_stay_async("callers use await")
    async def _call_http_tool(
        self,
        server_id: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Call a tool on an HTTP-based MCP server (like l9-memory).

        Uses the /mcp/call endpoint with POST request.
        """
        server_config = self._servers.get(server_id, {})
        base_url = server_config.get("url", "")
        headers = server_config.get("headers", {})

        if not base_url:
            return {
                "success": False,
                "error": f"No URL configured for HTTP MCP server {server_id}",
                "result": None,
            }

        # Get user_id from arguments or environment (for multi-tenant scoping)
        # - Cursor IDE: defaults to "cursor"
        # - L-CTO agent: should pass "l-cto"
        # - Other agents: pass their agent_id
        user_id = arguments.pop("user_id", None) or os.getenv("MCP_USER_ID", "cursor")

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{base_url}/mcp/call",
                    headers={
                        "Content-Type": "application/json",
                        **headers,
                    },
                    json={
                        "tool_name": tool_name,
                        "arguments": arguments,
                        "user_id": user_id,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    logger.info(
                        "HTTP MCP tool call succeeded",
                        server_id=server_id,
                        tool_name=tool_name,
                    )
                    return {
                        "success": True,
                        "result": data.get("result"),
                        "error": None,
                    }
                error_text = response.text
                logger.error(
                    "HTTP MCP tool call failed",
                    server_id=server_id,
                    tool_name=tool_name,
                    status=response.status_code,
                    error=error_text,
                )
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {error_text}",
                    "result": None,
                }

        except Exception as e:
            logger.error(
                "HTTP MCP tool call exception",
                server_id=server_id,
                tool_name=tool_name,
                error=str(e),
            )
            return {
                "success": False,
                "error": str(e),
                "result": None,
            }


@lru_cache(maxsize=1)
@register_singleton(
    name="mcp_client",
    lifecycle="lazy",
    description="MCP (Model Context Protocol) client for tool execution",
)
def get_mcp_client() -> MCPClient:
    """Get or create the global MCP client instance. CACHED."""
    return MCPClient()


__all__ = [
    "MCPClient",
    "MCPServerProcess",
    "ToolMeta",
    "get_mcp_client",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "RUN-OPER-014",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "async",
        "caching",
        "client",
        "event-driven",
        "http-client",
        "logging",
        "messaging",
        "operations",
        "runtime-operations",
    ],
    "keywords": [
        "all",
        "allowed",
        "available",
        "client",
        "mcp",
        "meta",
        "process",
        "running",
    ],
    "business_value": "List tools from MCP servers Call tools on MCP servers Registry of allowed MCP tools Version: 1.0.0",
    "last_modified": "2026-01-13T15:37:09Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
