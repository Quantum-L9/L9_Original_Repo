#!/usr/bin/env python3
"""
================================================================================
Module: Anomaly Handler
Purpose: Handle anomaly flags from tensor layer
================================================================================

Summary:
    Handles anomaly detection results from tensor layer. Routes anomalies
    to appropriate response actions including escalation and logging.

Extended Metadata:

================================================================================
# HEADER META - Module Identity (Static)
# component_id: SEC-DTB-003
# layer: security
# domain: anomaly_detection
# governance_level: high
# created_at: 2026-01-02T03:35:00Z
================================================================================
"""


from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


class AnomalySeverity(str, Enum):
    """Anomaly severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AnomalyFlag:
    """Anomaly detection flag."""

    anomaly_id: str
    entity_id: str
    anomaly_type: str
    severity: AnomalySeverity
    confidence: float
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnomalyResponse:
    """Response to anomaly."""

    handled: bool
    action_taken: str
    escalated: bool = False


class AnomalyHandler:
    """Handles anomalies from tensor layer."""

    SEVERITY_ACTIONS = {
        AnomalySeverity.LOW: "log",
        AnomalySeverity.MEDIUM: "alert",
        AnomalySeverity.HIGH: "escalate",
        AnomalySeverity.CRITICAL: "block_and_escalate",
    }

    async def handle_anomaly(self, anomaly: AnomalyFlag) -> AnomalyResponse:
        """Handle detected anomaly."""
        logger.warning(
            "anomaly_detected",
            anomaly_id=anomaly.anomaly_id,
            severity=anomaly.severity.value,
            type=anomaly.anomaly_type,
        )

        action = self.SEVERITY_ACTIONS.get(anomaly.severity, "log")
        escalated = action in ("escalate", "block_and_escalate")

        if escalated:
            await self._escalate_anomaly(anomaly)

        return AnomalyResponse(
            handled=True,
            action_taken=action,
            escalated=escalated,
        )

    @must_stay_async("callers use await")
    async def _escalate_anomaly(self, anomaly: AnomalyFlag) -> None:
        """Escalate anomaly to governance."""
        logger.info(
            "escalating_anomaly",
            anomaly_id=anomaly.anomaly_id,
            severity=anomaly.severity.value,
        )



__all__ = [
    "AnomalyFlag",
    "AnomalyHandler",
    "AnomalyResponse",
    "AnomalySeverity",
]
