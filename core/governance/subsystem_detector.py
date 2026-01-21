"""
L9 Subsystem Detector
=====================

Automatically detects which subsystem applies based on:
- File paths being modified
- Keywords in prompts/tasks
- Explicit subsystem specification

This enables automatic policy enforcement without manual subsystem selection.

Usage:
    from core.governance.subsystem_detector import detect_subsystem, get_subsystem_policy

    # From file paths
    subsystem = detect_subsystem(files=["core/tools/registry.py"])
    # Returns: "tools"

    # From prompt
    subsystem = detect_subsystem(prompt="Add authentication middleware")
    # Returns: "auth"

    # Get full policy
    policy = get_subsystem_policy(subsystem)

Version: 1.0.0
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

import structlog
import yaml

logger = structlog.get_logger(__name__)


# =============================================================================
# Detection Patterns
# =============================================================================

# File path patterns -> subsystem mapping
FILE_PATTERNS: dict[str, list[str]] = {
    "auth": [
        r"api/auth\.py",
        r"core/.*auth.*",
        r".*permission.*",
        r".*rbac.*",
        r".*credential.*",
        r".*session.*",
        r".*token.*",
    ],
    "tools": [
        r"core/tools/.*",
        r"runtime/tool.*",
        r".*registry.*tool.*",
        r".*capability.*",
    ],
    "memory_retrieval": [
        r"memory/retrieval.*",
        r"memory/.*search.*",
        r"memory/.*embedding.*",
        r"memory/.*ranking.*",
        r".*pgvector.*",
    ],
    "code_mutation": [
        r".*\.py$",  # Default for Python files
        r".*\.ts$",
        r".*\.tsx$",
        r".*\.js$",
    ],
}

# Keyword patterns -> subsystem mapping
KEYWORD_PATTERNS: dict[str, list[str]] = {
    "auth": [
        r"\bauth\w*\b",
        r"\blogin\b",
        r"\bpermission\b",
        r"\brbac\b",
        r"\bcredential\b",
        r"\bsession\b",
        r"\btoken\b",
        r"\bpassword\b",
        r"\bsecur\w+\b",
    ],
    "tools": [
        r"\btool\s*registry\b",
        r"\bcapabilit\w+\b",
        r"\btool\s*dispatch\b",
        r"\bregister\s*tool\b",
    ],
    "memory_retrieval": [
        r"\bretrieval\b",
        r"\bsearch\b.*\bmemory\b",
        r"\bmemory\b.*\bsearch\b",
        r"\bembedding\b",
        r"\branking\b",
        r"\bsemantic\s*search\b",
    ],
    "code_mutation": [
        r"\bimplement\b",
        r"\bcreate\b.*\b(file|class|function)\b",
        r"\brefactor\b",
        r"\badd\b.*\b(feature|endpoint|method)\b",
        r"\bbuild\b",
        r"\bwrite\b.*\bcode\b",
    ],
}

# Priority order (higher = checked first)
SUBSYSTEM_PRIORITY = ["auth", "tools", "memory_retrieval", "code_mutation"]


# =============================================================================
# Detection Functions
# =============================================================================


def detect_subsystem(
    files: Optional[list[str]] = None,
    prompt: Optional[str] = None,
    explicit: Optional[str] = None,
) -> str:
    """
    Detect the appropriate subsystem based on context.

    Priority:
    1. Explicit specification (if provided)
    2. File path matching
    3. Keyword matching in prompt
    4. Default to code_mutation

    Args:
        files: List of file paths being modified
        prompt: User prompt or task description
        explicit: Explicitly specified subsystem

    Returns:
        Subsystem name (e.g., "auth", "tools", "memory_retrieval", "code_mutation")
    """
    # 1. Explicit wins
    if explicit:
        if explicit in SUBSYSTEM_PRIORITY:
            logger.debug(f"Using explicit subsystem: {explicit}")
            return explicit
        logger.warning(
            f"Unknown explicit subsystem: {explicit}, falling back to detection"
        )

    # 2. Check file paths
    if files:
        for subsystem in SUBSYSTEM_PRIORITY:
            patterns = FILE_PATTERNS.get(subsystem, [])
            for file_path in files:
                for pattern in patterns:
                    if re.search(pattern, file_path, re.IGNORECASE):
                        # Skip generic code_mutation pattern if more specific match exists
                        if subsystem == "code_mutation" and _has_specific_match(
                            file_path
                        ):
                            continue
                        logger.debug(
                            "Detected subsystem from file",
                            subsystem=subsystem,
                            file=file_path,
                            pattern=pattern,
                        )
                        return subsystem

    # 3. Check keywords in prompt
    if prompt:
        prompt_lower = prompt.lower()
        for subsystem in SUBSYSTEM_PRIORITY:
            patterns = KEYWORD_PATTERNS.get(subsystem, [])
            for pattern in patterns:
                if re.search(pattern, prompt_lower, re.IGNORECASE):
                    logger.debug(
                        "Detected subsystem from prompt",
                        subsystem=subsystem,
                        pattern=pattern,
                    )
                    return subsystem

    # 4. Default
    logger.debug("No specific subsystem detected, defaulting to code_mutation")
    return "code_mutation"


def _has_specific_match(file_path: str) -> bool:
    """Check if file matches a specific (non-code_mutation) subsystem."""
    for subsystem in ["auth", "tools", "memory_retrieval"]:
        patterns = FILE_PATTERNS.get(subsystem, [])
        for pattern in patterns:
            if re.search(pattern, file_path, re.IGNORECASE):
                return True
    return False


def get_subsystem_config_path(subsystem: str) -> str:
    """Get the config file path for a subsystem."""
    return f"config/subsystems/{subsystem}.yaml"


def get_subsystem_policy(subsystem: str) -> dict[str, Any]:
    """
    Load the full policy for a subsystem.

    Args:
        subsystem: Subsystem name

    Returns:
        Parsed YAML config as dictionary
    """
    config_path = Path(get_subsystem_config_path(subsystem))

    if not config_path.exists():
        logger.warning(f"Subsystem config not found: {config_path}")
        return {}

    with open(config_path) as f:
        config = yaml.safe_load(f)

    return config.get("subsystem_config_v1", {})


def get_approval_requirements(subsystem: str) -> dict[str, Any]:
    """
    Get approval requirements for a subsystem.

    Returns:
        Dictionary with approval levels and criteria
    """
    policy = get_subsystem_policy(subsystem)
    return policy.get("approval_model", {})


def requires_human_approval(subsystem: str) -> bool:
    """
    Check if subsystem requires human approval for all changes.

    Args:
        subsystem: Subsystem name

    Returns:
        True if human approval is always required
    """
    if subsystem == "auth":
        return True  # Auth always requires human approval

    approval = get_approval_requirements(subsystem)
    levels = approval.get("levels", [])

    for level in levels:
        criteria = level.get("criteria", [])
        if "ALWAYS_REQUIRED" in criteria:
            return True

    return False


def get_high_risk_triggers(subsystem: str) -> list[str]:
    """
    Get high-risk triggers for a subsystem.

    Args:
        subsystem: Subsystem name

    Returns:
        List of high-risk trigger descriptions
    """
    policy = get_subsystem_policy(subsystem)
    risk_model = policy.get("risk_model", {})
    return risk_model.get("high_risk_triggers", [])


# =============================================================================
# Integration Helpers
# =============================================================================


def get_subsystem_context(
    files: Optional[list[str]] = None,
    prompt: Optional[str] = None,
    explicit: Optional[str] = None,
) -> dict[str, Any]:
    """
    Get full subsystem context for pipeline execution.

    This is the main entry point for the Cursor rules integration.

    Args:
        files: Files being modified
        prompt: User prompt
        explicit: Explicit subsystem

    Returns:
        Context dictionary with subsystem info, policy, approval requirements
    """
    subsystem = detect_subsystem(files=files, prompt=prompt, explicit=explicit)
    policy = get_subsystem_policy(subsystem)

    return {
        "subsystem": subsystem,
        "config_path": get_subsystem_config_path(subsystem),
        "requires_human_approval": requires_human_approval(subsystem),
        "high_risk_triggers": get_high_risk_triggers(subsystem),
        "metadata": policy.get("metadata", {}),
        "goals": policy.get("goals", []),
        "constraints": policy.get("constraints", []),
    }


# =============================================================================
# Quick Test
# =============================================================================

if __name__ == "__main__":
    # Test detection
    print("=== Subsystem Detection Tests ===\n")

    tests = [
        ({"files": ["api/auth.py"]}, "auth"),
        ({"files": ["core/tools/registry.py"]}, "tools"),
        ({"files": ["memory/retrieval.py"]}, "memory_retrieval"),
        ({"prompt": "Add login endpoint"}, "auth"),
        ({"prompt": "Register new tool capability"}, "tools"),
        ({"prompt": "Implement user profile feature"}, "code_mutation"),
    ]

    for kwargs, expected in tests:
        result = detect_subsystem(**kwargs)
        status = "✅" if result == expected else "❌"
        print(f"{status} {kwargs} -> {result} (expected: {expected})")

    print("\n=== Subsystem Context ===\n")
    ctx = get_subsystem_context(prompt="Add authentication middleware")
    for k, v in ctx.items():
        print(f"  {k}: {v}")
