"""
Core Schemas - Tool Capabilities with role-based filtering.

Enhancements:
- Tag-based capability evaluation
- Role permission enforcement (admin-only, read-only)
- Integration with governance for approval requirements
"""

import logging  # noqa: ADR-0019
from dataclasses import dataclass

logger = logging.getLogger(__name__)  # noqa: ADR-0019


@dataclass
class ToolCapability:
    """Enhanced tool capability with role permissions."""

    tool_id: str
    allowed: bool
    requires_approval: bool
    reason: str
    tags: list[str]


class ToolCapabilities:
    """
    Tool capabilities manager with role-based filtering.

    Responsibilities:
    - Evaluate tool permissions per agent/role
    - Enforce tag-based access control
    - Integrate with governance approval system
    """

    def __init__(
        self,
        agent_role: str = "user",
        allowed_tags: list[str] | None = None,
    ):
        """
        Initialize capabilities for an agent.

        Args:
            agent_role: Agent role ("user", "admin", "readonly")
            allowed_tags: Explicit tag allowlist (None = infer from role)
        """
        self.agent_role = agent_role
        self.allowed_tags = allowed_tags or self._infer_allowed_tags(agent_role)

    def _infer_allowed_tags(self, role: str) -> list[str]:
        """Infer allowed tags from agent role."""
        role_tag_map = {
            "admin": ["read-only", "write", "admin-only"],
            "user": ["read-only", "write"],
            "readonly": ["read-only"],
        }

        return role_tag_map.get(role, ["read-only"])

    def get_capability(self, tool_id: str) -> ToolCapability:
        """
        Get capability evaluation for a tool.

        Args:
            tool_id: Tool identifier

        Returns:
            ToolCapability with permission decision

        Enhancement: Considers tags + governance
        """
        try:
            from runtime.tool_registry import get_tool_registry

            registry = get_tool_registry()
            metadata = registry.get_tool_metadata(tool_id)

            if not metadata:
                return ToolCapability(
                    tool_id=tool_id,
                    allowed=False,
                    requires_approval=False,
                    reason="Tool not found",
                    tags=[],
                )

            # Check tag-based permissions
            if not self._check_tag_permissions(metadata.tags):
                return ToolCapability(
                    tool_id=tool_id,
                    allowed=False,
                    requires_approval=False,
                    reason=f"Role {self.agent_role} lacks required tags",
                    tags=metadata.tags,
                )

            # Check governance approval requirement
            requires_approval = metadata.requires_approval

            return ToolCapability(
                tool_id=tool_id,
                allowed=True,
                requires_approval=requires_approval,
                reason="Permitted by role and tags",
                tags=metadata.tags,
            )

        except Exception as e:
            logger.error(f"Error evaluating capability for {tool_id}: {e}")

            return ToolCapability(
                tool_id=tool_id,
                allowed=False,
                requires_approval=False,
                reason=f"Capability evaluation error: {e}",
                tags=[],
            )

    def _check_tag_permissions(self, tool_tags: list[str]) -> bool:
        """
        Check if agent role allows tool tags.

        Args:
            tool_tags: Tags on the tool

        Returns:
            True if agent is permitted, False otherwise

        Logic:
        - If tool has "admin-only" tag, only "admin" role allowed
        - If tool has no tags, allowed by default
        - Otherwise, agent must have at least one matching tag
        """
        if not tool_tags:
            return True  # No restrictions

        # Admin-only enforcement
        if "admin-only" in tool_tags and self.agent_role != "admin":
            return False

        # At least one tag must match
        return any(tag in self.allowed_tags for tag in tool_tags)

    def is_tool_allowed(self, tool_id: str) -> bool:
        """Quick check if tool is allowed."""
        capability = self.get_capability(tool_id)
        return capability.allowed

    def list_allowed_tools(self, tool_ids: list[str]) -> list[str]:
        """
        Filter tool list to only allowed tools.

        Args:
            tool_ids: Candidate tool IDs

        Returns:
            Filtered list of allowed tool IDs
        """
        allowed = []

        for tool_id in tool_ids:
            if self.is_tool_allowed(tool_id):
                allowed.append(tool_id)

        logger.info(
            f"Filtered {len(tool_ids)} tools to {len(allowed)} allowed "
            f"(role={self.agent_role})"
        )

        return allowed

    def list_denied_tools(self, tool_ids: list[str]) -> list[str]:
        """Get list of denied tools from candidate set."""
        denied = []

        for tool_id in tool_ids:
            if not self.is_tool_allowed(tool_id):
                denied.append(tool_id)

        return denied

    def requires_igor_approval(self, tool_id: str) -> bool:
        """Check if tool requires Igor approval."""
        capability = self.get_capability(tool_id)
        return capability.requires_approval


def filter_tools_by_capabilities(
    tool_ids: list[str],
    agent_role: str = "user",
) -> list[str]:
    """
    Convenience function to filter tools by agent role.

    Args:
        tool_ids: Candidate tool IDs
        agent_role: Agent role

    Returns:
        Filtered tool IDs
    """
    capabilities = ToolCapabilities(agent_role=agent_role)
    return capabilities.list_allowed_tools(tool_ids)
