"""L9 Safety - Policy Enforcement & Security Event Management.

Bounded Context: Safety
Domain: Query safety, policy enforcement, security auditing.
Owner: L (CTO)

Safety is responsible for:
  1. Query injection detection and sanitization
  2. Policy rule evaluation (capability enforcement)
  3. Security event generation (handshakes, violations)
  4. Rate limiting and abuse prevention
  5. Regional/compliance controls

Safety MUST implement:
  - SafetyService interface
  - Structured safety events (SafetyEvent)
  - Policy bundle loading (SafetyPolicyBundle)

Safety MUST NOT:
  - Store mutable state (all state in control_plane.config)
  - Depend on specific memory substrate implementations
  - Make business decisions (only enforce policies)
"""

from safety.api import SafetyEvent, SafetyPolicyBundle, SafetyService

__all__ = [
    "SafetyEvent",
    "SafetyPolicyBundle",
    "SafetyService",
]
