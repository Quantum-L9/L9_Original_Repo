"""Safety Service Interface - Typed contracts for policy enforcement.

This module defines the abstract interface that Safety module must implement.
Kernel depends ONLY on these abstract types, never on implementation details.

Safety is responsible for:
  1. Query validation and injection detection
  2. Capability enforcement
  3. Regional compliance controls
  4. Security event generation and logging
  5. Rate limiting and abuse prevention
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class SafetyDecision(str, Enum):
    """Outcome of a safety check."""
    ALLOW = "allow"
    BLOCK = "block"
    REQUIRE_APPROVAL = "require_approval"
    THROTTLE = "throttle"


@dataclass(frozen=True)
class SafetyEvent:
    """Immutable security event."""
    event_type: str
    decision: SafetyDecision
    caller_id: str
    user_id: str
    query_hash: str
    policy_rule: str
    reason: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


SAFETY_EVENT_TYPES = {
    "injection_detected": "SQL/NoSQL injection detected",
    "capability_denied": "Caller lacks capability",
    "region_denied": "Blocked by regional policy",
    "rate_limit": "Rate limit exceeded",
}


@dataclass(frozen=True)
class SafetyPolicyBundle:
    """Versioned set of safety policies."""
    version: str
    rules: List[str]
    created_at: datetime
    created_by: str


class SafetyService(ABC):
    """Abstract interface for Safety module."""
    
    @abstractmethod
    async def check_query(self,
        query: str,
        caller_id: str,
        user_id: str,
        operation: str = "search",
    ) -> SafetyDecision:
        """Check if query is safe to execute."""
        pass
    
    @abstractmethod
    async def check_capability(self,
        caller_id: str,
        capability: str,
        resource_id: Optional[str] = None,
    ) -> bool:
        """Check if caller has required capability."""
        pass
    
    @abstractmethod
    async def emit_event(self, event: SafetyEvent) -> None:
        """Log a security event."""
        pass
    
    @abstractmethod
    async def load_policy_bundle(self, version: str) -> SafetyPolicyBundle:
        """Load versioned policy bundle."""
        pass
    
    @abstractmethod
    async def is_region_allowed(self, region: str, operation: str) -> bool:
        """Check if operation allowed in region."""
        pass


__all__ = [
    "SafetyDecision",
    "SafetyEvent",
    "SafetyPolicyBundle",
    "SafetyService",
    "SAFETY_EVENT_TYPES",
]
