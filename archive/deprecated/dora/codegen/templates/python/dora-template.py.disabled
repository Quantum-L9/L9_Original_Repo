#!/usr/bin/env python3
"""
================================================================================
Module: {component_name}
Purpose: {one_sentence_business_value}
================================================================================

Summary:
    {2-3 sentence description of what this module does, why it matters,
    and how it fits into the L9 system}

DORA Protocol:
    - Header Meta: Module identity at top (this section)
    - Footer Meta: Extended metadata at bottom (see __footer_meta__)
    - DORA Block: Runtime trace at very end (see __l9_trace__, auto-updates)

================================================================================
# HEADER META - Module Identity (Static, set on generation)
# component_id: {LAYER}-{ABBREV}-{NUM}
# layer: {foundation|intelligence|operations|learning|security}
# domain: {domain_name}
# governance_level: {critical|high|medium|low}
# created_at: {YYYY-MM-DDTHH:MM:SSZ}
# See footer meta for extended metadata.
================================================================================
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Dora-Template",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-06T16:58:22Z",
    "layer": "foundation",
    "domain": "code_generation",
    "module_name": "dora-template",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

# ============================================================================
# STANDARD LIBRARY IMPORTS

import logging  # noqa: ADR-0019
from typing import Any

# ============================================================================
# THIRD-PARTY IMPORTS
# ============================================================================
# L9 FRAMEWORK IMPORTS
from runtime.dora import l9_traced

# ============================================================================
# LOGGER CONFIGURATION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ============================================================================
# MODULE CONSTANTS

MODULE_ID = "{LAYER}-{ABBREV}-{NUM}"
MODULE_NAME = "{component_name}"
MODULE_VERSION = "1.0.0"

# ============================================================================
# MAIN MODULE CONTENT


@l9_traced(patterns=["{pattern_1}", "{pattern_2}"])
async def example_function(param1: str, param2: int) -> dict[str, Any]:
    """
    Example function with DORA tracing.

    Args:
        param1: Description
        param2: Description

    Returns:
        Dict with result
    """
    logger.info(f"{MODULE_NAME}.example_function called with param1={param1}")
    return {"result": param1, "value": param2}


# ============================================================================
# FOOTER META - Extended Metadata (Static, set on generation)
# ============================================================================
# Header points here. CI/CD validates this block.

__footer_meta__ = {
    # Component Identity (REQUIRED)
    "component_id": "{LAYER}-{ABBREV}-{NUM}",
    "component_name": "{component_name}",
    "module_version": "1.0.0",
    # Authorship (REQUIRED)
    "created_at": "{YYYY-MM-DDTHH:MM:SSZ}",
    "created_by": "{creator_name}",
    # Classification (REQUIRED)
    "layer": "{foundation|intelligence|operations|learning|security}",
    "domain": "{domain_name}",
    "type": "{service|collector|tracker|engine|utility|adapter}",
    "status": "active",
    # Governance (REQUIRED)
    "governance_level": "{critical|high|medium|low}",
    "compliance_required": True,
    "audit_trail": True,
    # Business Context (REQUIRED)
    "purpose": "{one_sentence_description}",
    "summary": "{2-3_sentence_description}",
    # Dependencies
    "dependencies": [],
}

# ============================================================================
# MODULE EXPORTS

__all__ = [
    "MODULE_ID",
    "MODULE_NAME",
    "MODULE_VERSION",
    "__footer_meta__",
    "__l9_trace__",
    "example_function",
]

# This is the L9_TRACE_TEMPLATE - 100% machine-managed
# Updates automatically on EVERY execution - never human-edited

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COD-FOUN-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["runtime.dora"],
    "tags": [
        "async",
        "auth",
        "code-generation",
        "foundation",
        "pydantic",
        "service",
        "tracing",
        "validation",
    ],
    "keywords": ["dora", "example", "function", "template"],
    "business_value": "Utility module for dora-template",
    "last_modified": "2026-01-06T16:58:22Z",
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
