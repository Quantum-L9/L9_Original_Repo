"""
L9 Core Boundary Module
=======================

PRIVATE_BOUNDARY enforcement at the orchestrator edge.

Provides:
- Boundary specification loading and parsing
- Prompt/response enforcement (redaction)
- Payload field protection

Version: 1.0.0
"""

from core.boundary.enforcer import (  # Functions; Classes; Constants
    BOUNDARY_FILE,
    BoundaryEnforcer,
    BoundarySpec,
    enforce_boundary,
    enforce_payload_boundary,
    enforce_response_boundary,
    get_default_enforcer,
    load_boundary_spec,
    parse_boundary_spec,
)

__all__ = [
    # Constants
    "BOUNDARY_FILE",
    "BoundaryEnforcer",
    # Classes
    "BoundarySpec",
    "enforce_boundary",
    "enforce_payload_boundary",
    "enforce_response_boundary",
    "get_default_enforcer",
    # Functions
    "load_boundary_spec",
    "parse_boundary_spec",
]
