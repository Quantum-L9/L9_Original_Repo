"""
L9 Igor Command Interface - Schemas
===================================

Pydantic models for Igor command parsing and intent extraction.

Version: 1.0.0 (GMP-11)
"""

from __future__ import annotations


import re
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CommandType(str, Enum):
    """Recognized structured command types."""

    PROPOSE_GMP = "propose_gmp"
    ANALYZE = "analyze"
    APPROVE = "approve"
    ROLLBACK = "rollback"
    QUERY = "query"
    STATUS = "status"
    HELP = "help"


class IntentType(str, Enum):
    """Intent categories for NLP extraction."""

    PROPOSE = "propose"
    ANALYZE = "analyze"
    APPROVE = "approve"
    REJECT = "reject"
    ROLLBACK = "rollback"
    QUERY = "query"
    DEPLOY = "deploy"
    EXECUTE = "execute"
    UNKNOWN = "unknown"


class RiskLevel(str, Enum):
    """Risk level for command execution."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Command(BaseModel):
    """Structured command parsed from Igor input."""

    id: UUID = Field(default_factory=uuid4, description="Unique command ID")
    type: CommandType = Field(..., description="Command type")
    raw_text: str = Field(..., description="Original input text")
    target: str | None = Field(
        None, description="Target entity (e.g., task_id, entity_id)"
    )
    description: str | None = Field(
        None, description="Description for propose commands"
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Additional parameters"
    )
    risk_level: RiskLevel = Field(default=RiskLevel.LOW, description="Risk level")

    @property
    def requires_confirmation(self) -> bool:
        """Commands with HIGH or CRITICAL risk require Igor confirmation."""
        return self.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)


class NLPPrompt(BaseModel):
    """Natural language prompt requiring intent extraction."""

    id: UUID = Field(default_factory=uuid4, description="Unique prompt ID")
    text: str = Field(..., description="Natural language input")
    raw_text: str = Field(..., description="Original input text")


class IntentModel(BaseModel):
    """Extracted intent from NLP text."""

    id: UUID = Field(default_factory=uuid4, description="Unique intent ID")
    intent_type: IntentType = Field(..., description="Classified intent type")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    entities: dict[str, Any] = Field(
        default_factory=dict, description="Extracted entities"
    )
    ambiguities: list[str] = Field(
        default_factory=list, description="Ambiguous elements"
    )
    original_text: str = Field(..., description="Original NLP text")
    suggested_command: Command | None = Field(
        None, description="Suggested structured command"
    )

    @property
    def is_ambiguous(self) -> bool:
        """Intent is ambiguous if confidence < 0.8 or ambiguities exist."""
        return self.confidence < 0.8 or len(self.ambiguities) > 0


class ConfirmationResult(BaseModel):
    """Result of Igor confirmation for high-risk commands."""

    confirmed: bool = Field(..., description="Whether Igor confirmed the action")
    command_id: UUID = Field(..., description="Command ID being confirmed")
    confirmed_by: str = Field(default="Igor", description="Confirmer identity")
    reason: str | None = Field(None, description="Confirmation/rejection reason")
    timestamp: str = Field(..., description="ISO timestamp of confirmation")


class CommandResult(BaseModel):
    """Result of command execution."""

    success: bool = Field(..., description="Whether command executed successfully")
    command_id: UUID = Field(..., description="Command ID")
    task_id: UUID | None = Field(None, description="Created task ID if applicable")
    message: str = Field(..., description="Result message")
    data: dict[str, Any] = Field(default_factory=dict, description="Result data")


# Command pattern regex matchers
COMMAND_PATTERNS: dict[str, re.Pattern] = {
    "propose_gmp": re.compile(
        r"^@[Ll]\s+propose\s+gmp:\s*(.+)$",
        re.IGNORECASE | re.DOTALL,
    ),
    "analyze": re.compile(
        r"^@[Ll]\s+analyze\s+(.+)$",
        re.IGNORECASE,
    ),
    "approve": re.compile(
        r"^@[Ll]\s+approve\s+([a-zA-Z0-9_-]+)$",
        re.IGNORECASE,
    ),
    "rollback": re.compile(
        r"^@[Ll]\s+rollback\s+([a-zA-Z0-9_-]+)$",
        re.IGNORECASE,
    ),
    "status": re.compile(
        r"^@[Ll]\s+status(?:\s+([a-zA-Z0-9_-]+))?$",
        re.IGNORECASE,
    ),
    "help": re.compile(
        r"^@[Ll]\s+help$",
        re.IGNORECASE,
    ),
}

# Runtime execution trace - updated automatically on every execution
