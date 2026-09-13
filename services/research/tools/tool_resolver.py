"""
L9 Research Factory - Tool Resolver
Version: 1.0.0

Resolves which tools are available for a given agent/role.
Enforces access control and rate limits.
"""


from typing import Any

import structlog

from core.decorators import must_stay_async
from core.singleton_auto_registry import register_singleton
from core.tools.base_registry import ToolMetadata, ToolRegistry, get_tool_registry

logger = structlog.get_logger(__name__)


class ToolResolver:
    """
    Tool resolver with RBAC and rate limiting.

    Resolves available tools based on:
    - Agent role
    - Tool availability
    - Rate limits
    """

    def __init__(self, registry: ToolRegistry | None = None):
        """
        Initialize resolver.

        Args:
            registry: Tool registry to use. If None, uses singleton.
        """
        self._registry = registry

    @property
    def registry(self) -> ToolRegistry:
        """Get the tool registry."""
        if self._registry is None:  # nosemgrep: l9-singleton-requires-lock
            self._registry = get_tool_registry()
        return self._registry

    def resolve(
        self,
        role: str,
        tool_names: list[str] | None = None,
    ) -> list[ToolMetadata]:
        """
        Resolve available tools for a role.

        Args:
            role: Agent role (e.g., "researcher", "planner")
            tool_names: Optional list of specific tools to filter by

        Returns:
            List of available tool metadata
        """
        # Get tools for role
        available = self.registry.get_for_role(role)

        # Filter by specific names if provided
        if tool_names:
            available = [t for t in available if t.id in tool_names]

        logger.debug(f"Resolved {len(available)} tools for role {role}")
        return available

    def authorize(
        self,
        tool_id: str,
        role: str,
    ) -> bool:
        """
        Check if a role is authorized to use a tool.

        Args:
            tool_id: Tool to check
            role: Role requesting access

        Returns:
            True if authorized, False otherwise
        """
        metadata = self.registry.get(tool_id)

        if not metadata:
            logger.warning(f"Tool not found: {tool_id}")
            return False

        if not metadata.enabled:
            logger.warning(f"Tool disabled: {tool_id}")
            return False

        if role not in metadata.allowed_roles:
            logger.warning(f"Role {role} not authorized for {tool_id}")
            return False

        return True

    def can_execute(
        self,
        tool_id: str,
        role: str,
    ) -> tuple[bool, str]:
        """
        Check if tool can be executed (authorization + rate limit).

        Args:
            tool_id: Tool to check
            role: Role requesting execution

        Returns:
            Tuple of (allowed, reason)
        """
        # Check authorization
        if not self.authorize(tool_id, role):
            return False, "Not authorized"

        # Check rate limit
        if not self.registry.check_rate_limit(tool_id):
            return False, "Rate limit exceeded"

        return True, "OK"

    @must_stay_async("callers use await")
    async def execute(
        self,
        tool_id: str,
        role: str,
        args: dict[str, Any],
    ) -> Any:
        """
        Execute a tool if authorized.

        Args:
            tool_id: Tool to execute
            role: Role requesting execution
            args: Arguments for tool

        Returns:
            Tool execution result

        Raises:
            PermissionError: If not authorized
            RuntimeError: If tool execution fails
        """
        # Check if can execute
        allowed, reason = self.can_execute(tool_id, role)
        if not allowed:
            raise PermissionError(f"Cannot execute {tool_id}: {reason}")

        # Get executor
        executor = self.registry.get_executor(tool_id)
        if not executor:
            raise RuntimeError(f"No executor for tool: {tool_id}")

        # Execute
        try:
            logger.info(f"Executing tool {tool_id} for role {role}")
            return await executor.execute(args)
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_id}: {e}")
            raise RuntimeError(f"Tool execution failed: {e}") from e


# Singleton instance
_resolver: ToolResolver | None = None


@register_singleton(
    name="tool_resolver", lifecycle="lazy", description="Research service tool resolver"
)
def get_tool_resolver() -> ToolResolver:
    """Get or create tool resolver singleton."""
    global _resolver
    if _resolver is None:  # nosemgrep: l9-singleton-requires-lock
        _resolver = ToolResolver()
    return _resolver


# Runtime execution trace - updated automatically on every execution
