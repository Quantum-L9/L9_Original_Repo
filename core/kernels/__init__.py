"""
L9 Core Kernels Module
======================

Kernel integrity verification.

Note: Kernel loading functions have been consolidated into runtime.kernel_loader.
This module re-exports them for backward compatibility.

Components:
- integrity: Hash-based tamper detection
- runtime.kernel_loader: YAML kernel loading (canonical location)

Version: 1.1.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.1.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-31T22:21:46Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "__init__",
    "type": "utility",
    "status": "deprecated",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import warnings

from core.kernels.integrity import (
    KERNEL_HASH_FILE,
    IntegrityChange,
    check_kernel_integrity,
    compute_kernel_hashes,
    get_detailed_changes,
    hash_file,
    initialize_kernel_hashes,
    load_kernel_hashes,
    save_kernel_hashes,
    verify_specific_file,
)

# Re-export from canonical location (runtime.kernel_loader)
# Backward compatibility for code using core.kernels.private_loader
from runtime.kernel_loader import (
    DEFAULT_KERNEL_PATH,
    KERNEL_EXTENSIONS,
    get_enabled_rules,
    get_kernel_by_name,
    get_rules_by_type,
    load_all_private_kernels,
    load_kernel_file,
    load_layered_kernels,
    validate_all_kernels,
    validate_kernel_structure,
)


# Emit deprecation warning when accessing via this module
def __getattr__(name: str):
    if name in (
        "load_kernel_file",
        "load_all_private_kernels",
        "load_layered_kernels",
        "get_kernel_by_name",
        "get_enabled_rules",
        "get_rules_by_type",
        "validate_kernel_structure",
        "validate_all_kernels",
    ):
        warnings.warn(
            f"core.kernels.{name} is deprecated. Use runtime.kernel_loader.{name} instead.",
            DeprecationWarning,
            stacklevel=2,
        )
    raise AttributeError(f"module 'core.kernels' has no attribute '{name}'")


__all__ = [
    "DEFAULT_KERNEL_PATH",
    "KERNEL_EXTENSIONS",
    "KERNEL_HASH_FILE",
    "IntegrityChange",
    "check_kernel_integrity",
    "compute_kernel_hashes",
    "get_detailed_changes",
    "get_enabled_rules",
    "get_kernel_by_name",
    "get_rules_by_type",
    # Integrity
    "hash_file",
    "initialize_kernel_hashes",
    "load_all_private_kernels",
    # Private Loader
    "load_kernel_file",
    "load_kernel_hashes",
    "load_layered_kernels",
    "save_kernel_hashes",
    "validate_all_kernels",
    "validate_kernel_structure",
    "verify_specific_file",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-012",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.kernels.integrity", "runtime.kernel_loader"],
    "tags": ["core", "foundation", "security", "utility"],
    "keywords": ["detection", "integrity", "kernel", "loading", "module", "runtime"],
    "business_value": "This module re-exports them for backward compatibility. integrity: Hash-based tamper detection runtime.kernel_loader: YAML kernel loading (canonical location) Version: 1.1.0",
    "last_modified": "2026-01-31T22:21:46Z",
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
