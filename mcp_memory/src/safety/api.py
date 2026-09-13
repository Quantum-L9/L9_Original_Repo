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


from abc import (  # noqa: ADR-0026 - ABC provides shared implementation
    ABC,
    abstractmethod,
)
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from core.decorators import must_stay_async


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
    metadata: dict[str, Any] | None = None


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
    rules: list[str]
    created_at: datetime
    created_by: str


class SafetyService(ABC):
    """Abstract interface for Safety module."""

    @abstractmethod
    @must_stay_async("callers use await")
    async def check_query(
        self,
        query: str,
        caller_id: str,
        user_id: str,
        operation: str = "search",
    ) -> SafetyDecision:
        """Check if query is safe to execute."""
        pass

    @abstractmethod
    @must_stay_async("callers use await")
    async def check_capability(
        self,
        caller_id: str,
        capability: str,
        resource_id: str | None = None,
    ) -> bool:
        """Check if caller has required capability."""
        pass

    @abstractmethod
    @must_stay_async("callers use await")
    async def emit_event(self, event: SafetyEvent) -> None:
        """Log a security event."""
        pass

    @abstractmethod
    @must_stay_async("callers use await")
    async def load_policy_bundle(self, version: str) -> SafetyPolicyBundle:
        """Load versioned policy bundle."""
        pass

    @abstractmethod
    @must_stay_async("callers use await")
    async def is_region_allowed(self, region: str, operation: str) -> bool:
        """Check if operation allowed in region."""
        pass


__all__ = [
    "SAFETY_EVENT_TYPES",
    "SafetyDecision",
    "SafetyEvent",
    "SafetyPolicyBundle",
    "SafetyService",
]

# Runtime execution trace - updated automatically on every execution
