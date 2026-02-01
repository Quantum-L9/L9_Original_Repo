"""L9 Control Plane - Configuration, Secrets, Feature Flags.

Bounded Context: Control Plane
Domain: Configuration management, feature flags, secrets, policy bundles.
Owner: L (CTO)

Control Plane is responsible for:
  1. Unified configuration (environment + YAML/JSON overlays)
  2. Feature flag management with rollout control
  3. Secrets retrieval (KMS, Vault, environment)
  4. Policy bundle versioning
  5. Governance rule enforcement configuration
  6. A/B testing and canary controls

Control Plane MUST implement:
  - Settings (global config interface)
  - FeatureFlagService (rollout queries)
  - SecretProvider (pluggable backends)
  - PolicyBundleRegistry (versioned policies)

Control Plane MUST NOT:
  - Enforce policies directly (Safety does that)
  - Make business decisions
  - Depend on kernel/memory_substrate/safety

Control Plane is the ONLY place where runtime configuration is read.
All other modules depend on control_plane.settings.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Configuration, Secrets, Feature Flags.",
    "module_version": "1.0.0",
    "created_by": "cryptoxdog",
    "created_at": "2026-01-25T05:41:25Z",
    "updated_at": "2026-01-31T22:21:56Z",
    "layer": "integration",
    "domain": "mcp_integration",
    "module_name": "__init__",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from control_plane.config import Settings, get_settings
from control_plane.feature_flags import FeatureFlagService
from control_plane.policies import PolicyBundleRegistry
from control_plane.secrets import SecretProvider

__all__ = [
    "FeatureFlagService",
    "PolicyBundleRegistry",
    "SecretProvider",
    "Settings",
    "get_settings",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MCP-INTE-017",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["integration", "mcp-integration", "security", "testing", "utility"],
    "keywords": [
        "configuration",
        "configuration,",
        "control",
        "depend",
        "environment",
        "feature",
        "flags",
        "flags.",
    ],
    "business_value": "Utility module for   init  ",
    "last_modified": "2026-01-31T22:21:56Z",
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
