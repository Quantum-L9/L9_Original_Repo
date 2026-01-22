"""
L9 Core Governance - Protected Files Policy Loader
===================================================

Single source of truth for protected file definitions.

Loads protected file policies from config/policies/protected_files.yaml.

GMP-104: Consolidates PROTECTED_BY_LCTO and SUBSYSTEM_PROTECTED definitions.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Protected Files Policy",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-19T22:00:00Z",
    "updated_at": "2026-01-19T22:00:00Z",
    "layer": "foundation",
    "domain": "governance",
    "module_name": "protected_files_policy",
    "type": "utility",
    "status": "active",
}
# ============================================================================

from pathlib import Path
from typing import Dict, Set

import structlog
import yaml

logger = structlog.get_logger(__name__)


# =============================================================================
# Cached Policy Data
# =============================================================================

_PROTECTED_FILES_POLICY: Dict = {}


def _load_protected_files_policy() -> Dict:
    """Load protected files policy from YAML file."""
    global _PROTECTED_FILES_POLICY

    if _PROTECTED_FILES_POLICY:
        return _PROTECTED_FILES_POLICY

    policy_path = (
        Path(__file__).parent.parent.parent
        / "config"
        / "policies"
        / "protected_files.yaml"
    )

    if policy_path.exists():
        try:
            with open(policy_path) as f:
                data = yaml.safe_load(f)
                _PROTECTED_FILES_POLICY = data.get("protected_files", {})
                logger.debug(
                    "protected_files_policy.loaded",
                    path=str(policy_path),
                    lcto_count=len(_PROTECTED_FILES_POLICY.get("lcto_controlled", [])),
                    subsystems=list(
                        _PROTECTED_FILES_POLICY.get("subsystems", {}).keys()
                    ),
                )
        except Exception as e:
            logger.warning(
                "protected_files_policy.load_failed",
                path=str(policy_path),
                error=str(e),
            )

    # Fallback to hardcoded defaults
    if not _PROTECTED_FILES_POLICY:
        _PROTECTED_FILES_POLICY = {
            "lcto_controlled": [
                {"path": "runtime/websocket_orchestrator.py"},
                {"path": "runtime/kernel_loader.py"},
                {"path": "docker-compose.yml"},
                {"path": "runtime/redis_client.py"},
                {"path": "core/agents/executor.py"},
            ],
            "subsystems": {
                "agents": {
                    "files": [
                        "core/agents/executor.py",
                        "core/agents/registry.py",
                        "core/agents/__init__.py",
                    ]
                },
                "memory": {
                    "files": [
                        "memory/substrate_service.py",
                        "memory/substrate_dag.py",
                        "memory/__init__.py",
                    ]
                },
                "tools": {
                    "files": [
                        "core/tools/registry_adapter.py",
                        "core/tools/tool_graph.py",
                        "core/tools/__init__.py",
                    ]
                },
            },
        }
        logger.debug("protected_files_policy.using_fallback")

    return _PROTECTED_FILES_POLICY


# =============================================================================
# Public API
# =============================================================================


def get_lcto_controlled_files() -> Set[str]:
    """Get set of LCTO-controlled file paths.

    Returns:
        Set of file paths that L (CTO) controls
    """
    policy = _load_protected_files_policy()
    lcto = policy.get("lcto_controlled", [])
    return {item["path"] if isinstance(item, dict) else item for item in lcto}


def get_subsystem_protected_files() -> Dict[str, Set[str]]:
    """Get subsystem-protected files by subsystem name.

    Returns:
        Dict mapping subsystem name to set of protected file paths
    """
    policy = _load_protected_files_policy()
    subsystems = policy.get("subsystems", {})
    return {name: set(config.get("files", [])) for name, config in subsystems.items()}


def get_all_protected_files() -> Set[str]:
    """Get all protected file paths.

    Returns:
        Set of all protected file paths (LCTO + subsystem)
    """
    lcto = get_lcto_controlled_files()
    subsystem_files = set()
    for files in get_subsystem_protected_files().values():
        subsystem_files |= files
    return lcto | subsystem_files


def is_protected(file_path: str) -> bool:
    """Check if a file is protected.

    Args:
        file_path: Path to check

    Returns:
        True if file is protected
    """
    return file_path in get_all_protected_files()


def is_lcto_controlled(file_path: str) -> bool:
    """Check if a file is LCTO-controlled.

    Args:
        file_path: Path to check

    Returns:
        True if file is LCTO-controlled
    """
    return file_path in get_lcto_controlled_files()


def get_file_subsystem(file_path: str) -> str | None:
    """Get the subsystem that owns a file.

    Args:
        file_path: Path to check

    Returns:
        Subsystem name or None if not in a subsystem
    """
    for subsystem, files in get_subsystem_protected_files().items():
        if file_path in files:
            return subsystem
    return None


# =============================================================================
# Module-level constants (backward compatibility)
# =============================================================================

PROTECTED_BY_LCTO: Set[str] = get_lcto_controlled_files()
SUBSYSTEM_PROTECTED: Dict[str, Set[str]] = get_subsystem_protected_files()
ALL_PROTECTED: Set[str] = get_all_protected_files()
