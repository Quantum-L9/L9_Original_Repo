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

from control_plane.config import Settings, get_settings
from control_plane.feature_flags import FeatureFlagService
from control_plane.secrets import SecretProvider
from control_plane.policies import PolicyBundleRegistry

__all__ = [
    "Settings",
    "get_settings",
    "FeatureFlagService",
    "SecretProvider",
    "PolicyBundleRegistry",
]
