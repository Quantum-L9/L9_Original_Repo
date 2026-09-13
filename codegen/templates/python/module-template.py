#!/usr/bin/env python3
"""
================================================================================
Module: {component_name}
Purpose: {one_sentence_business_value}
================================================================================

Summary:
    {2-3 sentence description of what this module does, why it matters,
    and how it fits into the L9 system}

Extended Metadata:

================================================================================
# HEADER META - Module Identity (Static, set on generation)
# component_id: {LAYER}-{ABBREV}-{NUM}
# layer: {foundation|intelligence|operations|learning|security}
# domain: {domain_name}
# governance_level: {critical|high|medium|low}
# created_at: {YYYY-MM-DDTHH:MM:SSZ}
================================================================================
"""


# ============================================================================
# STANDARD LIBRARY IMPORTS

import logging  # noqa: ADR-0019
from typing import Any

from l9.core.governance import Igor

# ============================================================================
# THIRD-PARTY IMPORTS
# ============================================================================
# L9 FRAMEWORK IMPORTS
# ============================================================================
# MODULE IMPORTS
from . import config

# ============================================================================
# LOGGER CONFIGURATION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

audit_logger = logging.getLogger(f"{__name__}.audit")
audit_logger.setLevel(logging.INFO)

metrics_logger = logging.getLogger(f"{__name__}.metrics")
metrics_logger.setLevel(logging.DEBUG)

# ============================================================================
# MODULE CONSTANTS

MODULE_ID = "{LAYER}-{ABBREV}-{NUM}"
MODULE_NAME = "{component_name}"
MODULE_VERSION = "1.0.0"

# Feature flags (L9 Governance)
FEATURE_FLAGS = {
    "L9_ENABLE_STRICT_MODE": config.get_flag("L9_ENABLE_STRICT_MODE", True),
    "L9_ENABLE_GOVERNANCE_ENFORCEMENT": config.get_flag(
        "L9_ENABLE_GOVERNANCE_ENFORCEMENT", True
    ),
}

# ============================================================================
# INITIALIZATION

_igor_client: Igor | None = None
_governance_enabled = config.GOVERNANCE_ENABLED


async def initialize_module():
    """Initialize module at startup."""
    global _igor_client
    logger.info(f"Initializing {MODULE_NAME} (v{MODULE_VERSION})")

    try:
        if _governance_enabled:
            from l9.governance import get_igor_client

            _igor_client = await get_igor_client()
            logger.info("✓ Governance bridge wired")

        logger.info(f"✓ {MODULE_NAME} ready")
    except Exception as e:
        logger.error(f"✗ {MODULE_NAME} initialization failed: {e}")
        if config.STRICT_MODE:
            raise


async def health_check() -> dict[str, Any]:
    """Perform module health check."""
    return {
        "ready": True,
        "module": MODULE_NAME,
        "version": MODULE_VERSION,
    }


# ============================================================================
# MAIN MODULE CONTENT


async def example_function(param1: str) -> dict[str, Any]:
    """
    Example public function.

    Args:
        param1: Description

    Returns:
        Dict with result
    """
    audit_logger.info(f"{MODULE_NAME}.example_function called")
    return {"result": param1}


# ============================================================================
# FOOTER META - Extended Metadata (Static, set on generation)
# ============================================================================
# Header points here. CI/CD validates this block.
# DO NOT MODIFY STRUCTURE - only replace {PLACEHOLDER} values on generation.


# ============================================================================
# MODULE EXPORTS

__all__ = [
    "MODULE_ID",
    "MODULE_NAME",
    "MODULE_VERSION",
    "example_function",
    "health_check",
    "initialize_module",
]

# This is the L9_TRACE_TEMPLATE - 100% machine-managed
# Updates automatically on EVERY execution - never human-edited

# Runtime execution trace - updated automatically on every execution
