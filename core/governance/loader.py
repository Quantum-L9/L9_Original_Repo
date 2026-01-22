"""
L9 Core Governance - Policy Loader
==================================

Loads governance policies from YAML manifest files.

The loader:
- Reads all YAML files from a directory
- Parses them into Policy objects
- Validates policy structure
- Fails on any invalid policy (fail-closed)

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Policy Loader",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-20T15:08:40Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "foundation",
    "domain": "error_handling",
    "module_name": "loader",
    "type": "exception",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "api.server",
            "core.governance.engine",
            "tests.core.governance.test_engine",
        ],
    },
}
# ============================================================================

from pathlib import Path
from typing import Any

import structlog
import yaml

from core.governance.schemas import (Condition, ConditionOperator, Policy,
                                     PolicyEffect)

logger = structlog.get_logger(__name__)


# =============================================================================
# Exceptions
# =============================================================================


class PolicyLoadError(Exception):
    """Raised when policy loading fails."""

    def __init__(self, file_path: str, message: str):
        self.file_path = file_path
        self.message = message
        super().__init__(f"Failed to load policy from {file_path}: {message}")


class InvalidPolicyError(PolicyLoadError):
    """Raised when a policy file is invalid."""


# =============================================================================
# Policy Loader
# =============================================================================


class PolicyLoader:
    """
    Loads governance policies from YAML files.

    Policies are loaded from a manifest directory at startup.
    Invalid policies cause a hard failure (fail-closed).

    Attributes:
        policies: List of loaded Policy objects
        policy_count: Number of loaded policies
    """

    def __init__(self) -> None:
        self._policies: list[Policy] = []
        self._loaded_files: list[str] = []

    @property
    def policies(self) -> list[Policy]:
        """Get loaded policies, sorted by priority (highest first)."""
        return sorted(self._policies, key=lambda p: p.priority, reverse=True)

    @property
    def policy_count(self) -> int:
        """Get number of loaded policies."""
        return len(self._policies)

    @property
    def loaded_files(self) -> list[str]:
        """Get list of loaded file paths."""
        return self._loaded_files.copy()

    def load_from_directory(self, directory: str | Path) -> int:
        """
        Load all policies from a directory.

        Reads all .yaml and .yml files in the directory.
        Fails if any file is invalid (fail-closed).

        Args:
            directory: Path to policy manifest directory

        Returns:
            Number of policies loaded

        Raises:
            PolicyLoadError: If directory doesn't exist or is not readable
            InvalidPolicyError: If any policy file is invalid
        """
        dir_path = Path(directory)

        if not dir_path.exists():
            raise PolicyLoadError(str(dir_path), "Directory does not exist")

        if not dir_path.is_dir():
            raise PolicyLoadError(str(dir_path), "Path is not a directory")

        # Find all YAML files
        yaml_files = list(dir_path.glob("*.yaml")) + list(dir_path.glob("*.yml"))

        if not yaml_files:
            logger.warning(
                "governance.loader.no_files: directory=%s",
                str(dir_path),
            )
            return 0

        # Load each file
        for yaml_file in yaml_files:
            self._load_file(yaml_file)

        logger.info(
            "governance.loader.load.success: policy_files_loaded=%d, policy_count=%d",
            len(self._loaded_files),
            self.policy_count,
        )

        return self.policy_count

    def load_from_file(self, file_path: str | Path) -> int:
        """
        Load policies from a single file.

        Args:
            file_path: Path to policy YAML file

        Returns:
            Number of policies loaded from file

        Raises:
            InvalidPolicyError: If file is invalid
        """
        return self._load_file(Path(file_path))

    def _load_file(self, file_path: Path) -> int:
        """Load policies from a single file."""
        if not file_path.exists():
            raise PolicyLoadError(str(file_path), "File does not exist")

        try:
            with open(file_path, "r") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            logger.critical(
                "governance.loader.load.failed: file_path=%s, error=%s",
                str(file_path),
                str(e),
            )
            raise InvalidPolicyError(str(file_path), f"Invalid YAML: {e}")

        if data is None:
            logger.warning(
                "governance.loader.empty_file: file_path=%s",
                str(file_path),
            )
            return 0

        # Parse policies from file
        policies_loaded = 0

        # Support both single policy and list of policies
        if isinstance(data, dict):
            if "policies" in data:
                # File contains a list of policies
                for policy_data in data["policies"]:
                    self._parse_and_add_policy(policy_data, file_path)
                    policies_loaded += 1
            else:
                # File is a single policy
                self._parse_and_add_policy(data, file_path)
                policies_loaded = 1
        elif isinstance(data, list):
            # File is a list of policies
            for policy_data in data:
                self._parse_and_add_policy(policy_data, file_path)
                policies_loaded += 1
        else:
            raise InvalidPolicyError(
                str(file_path),
                f"Expected dict or list, got {type(data).__name__}",
            )

        self._loaded_files.append(str(file_path))

        logger.debug(
            "governance.loader.file_loaded: file_path=%s, policies=%d",
            str(file_path),
            policies_loaded,
        )

        return policies_loaded

    def _parse_and_add_policy(self, data: dict[str, Any], source: Path) -> None:
        """Parse a policy dict and add to loaded policies."""
        try:
            # Parse conditions if present
            conditions = []
            if "conditions" in data:
                for cond_data in data["conditions"]:
                    conditions.append(
                        Condition(
                            field=cond_data["field"],
                            operator=ConditionOperator(cond_data["operator"]),
                            value=cond_data["value"],
                        )
                    )

            # Parse effect
            effect = PolicyEffect(data.get("effect", "deny"))

            # Create policy
            policy = Policy(
                id=data["id"],
                name=data.get("name", data["id"]),
                description=data.get("description"),
                effect=effect,
                priority=data.get("priority", 0),
                subjects=data.get("subjects", ["*"]),
                actions=data.get("actions", []),
                resources=data.get("resources", ["*"]),
                conditions=conditions,
                enabled=data.get("enabled", True),
            )

            self._policies.append(policy)

        except KeyError as e:
            raise InvalidPolicyError(str(source), f"Missing required field: {e}")
        except ValueError as e:
            raise InvalidPolicyError(str(source), f"Invalid value: {e}")
        except Exception as e:
            raise InvalidPolicyError(str(source), f"Parse error: {e}")

    def get_policies_for_action(self, action: str) -> list[Policy]:
        """
        Get all policies that could apply to an action.

        Args:
            action: The action to filter by

        Returns:
            List of policies sorted by priority (highest first)
        """
        matching = []
        for policy in self.policies:
            if not policy.actions:
                # Empty actions means matches all
                matching.append(policy)
            elif any(
                self._action_matches(action, pattern) for pattern in policy.actions
            ):
                matching.append(policy)
        return matching

    def _action_matches(self, action: str, pattern: str) -> bool:
        """Check if action matches pattern."""
        if pattern == "*":
            return True
        if pattern == action:
            return True
        if pattern.endswith("*") and action.startswith(pattern[:-1]):
            return True
        if pattern.startswith("*") and action.endswith(pattern[1:]):
            return True
        return False

    def clear(self) -> None:
        """Clear all loaded policies."""
        self._policies.clear()
        self._loaded_files.clear()


# =============================================================================
# Factory Function
# =============================================================================


def load_policies_from_directory(directory: str | Path) -> PolicyLoader:
    """
    Create a PolicyLoader and load policies from a directory.

    Args:
        directory: Path to policy manifest directory

    Returns:
        PolicyLoader with policies loaded

    Raises:
        PolicyLoadError: If loading fails
    """
    loader = PolicyLoader()
    loader.load_from_directory(directory)
    return loader


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "PolicyLoader",
    "PolicyLoadError",
    "InvalidPolicyError",
    "load_policies_from_directory",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-091",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.governance.schemas"],
    "tags": [
        "api",
        "config",
        "debugging",
        "error-handling",
        "exception",
        "filesystem",
        "foundation",
        "loader",
        "logging",
        "messaging",
    ],
    "keywords": [
        "action",
        "clear",
        "count",
        "directory",
        "files",
        "governance",
        "invalid",
        "load",
    ],
    "business_value": "Reads all YAML files from a directory Parses them into Policy objects Validates policy structure Fails on any invalid policy (fail-closed) Version: 1.0.0",
    "last_modified": "2026-01-07T13:35:57Z",
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
