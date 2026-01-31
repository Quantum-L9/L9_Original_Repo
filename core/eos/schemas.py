"""
EOS Core Schemas — L9 Epistemic Operating System
Pydantic models derived from core/eos/schemas.yaml
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

# -----------------------------------------------------------------------------
# ENUMS
# -----------------------------------------------------------------------------


class EpistemicObjectType(str, Enum):
    """Types of epistemic objects.

    Defines the fundamental categories of knowledge primitives
    in the Epistemic Operating System.
    """

    FACT = "fact"
    BELIEF = "belief"
    RULE = "rule"
    INVARIANT = "invariant"
    CONTRACT = "contract"
    PROHIBITION = "prohibition"
    EVIDENCE = "evidence"


class Enforceability(str, Enum):
    """Enforceability levels.

    Defines how strictly a rule or constraint is enforced
    by the governance system.
    """

    HARD = "hard"
    SOFT = "soft"
    ADVISORY = "advisory"


class ActionType(str, Enum):
    """Types of actions that require accountability.

    Categorizes state-changing operations that must pass
    through the accountability verification system.
    """

    TOOL_CALL = "tool_call"
    CODE_DIFF = "code_diff"
    DEPLOY = "deploy"
    DB_WRITE = "db_write"
    GMP_RUN = "gmp_run"
    MEMORY_WRITE = "memory_write"


class Environment(str, Enum):
    """Execution environments.

    Defines the deployment context for actions and policies,
    affecting risk assessment and enforcement levels.
    """

    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


class RiskClass(str, Enum):
    """Risk classification levels.

    Categorizes actions by potential impact to determine
    required approval authority and evidence thresholds.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class VerdictDecision(str, Enum):
    """Verdict decision types"""

    ALLOW = "allow"
    DENY = "deny"
    CONDITIONAL = "conditional"
    ROLLBACK = "rollback"


class ConditionType(str, Enum):
    """Types of conditions for conditional verdicts"""

    EVIDENCE_REQUIRED = "evidence_required"
    SIMULATION_REQUIRED = "simulation_required"
    AUTHORITY_REQUIRED = "authority_required"
    TIMEOUT = "timeout"


class DoctrineSource(str, Enum):
    """Sources for executable doctrines"""

    RESEARCH = "research"
    SPEC = "spec"
    LAW = "law"


class AuthorityLevel(str, Enum):
    """Authority levels"""

    IGOR = "IGOR"
    L = "L"
    AGENT = "AGENT"


# -----------------------------------------------------------------------------
# EMBEDDINGS (for epistemic objects)
# -----------------------------------------------------------------------------


class EpistemicEmbeddings(BaseModel):
    """3D embeddings for epistemic objects"""

    semantic: list[float] = Field(default_factory=list, description="Meaning space")
    structural: list[float] = Field(default_factory=list, description="Graph topology")
    normative: list[float] = Field(default_factory=list, description="Constraint space")


# -----------------------------------------------------------------------------
# PROVENANCE
# -----------------------------------------------------------------------------


class Provenance(BaseModel):
    """Provenance tracking for epistemic objects"""

    ledger_ref: str | None = Field(None, description="Hash reference to ledger")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_by: str = Field(..., description="Agent ID that created this")


# -----------------------------------------------------------------------------
# EPISTEMIC OBJECT — First-class knowledge primitive
# -----------------------------------------------------------------------------


class EpistemicObject(BaseModel):
    """
    First-class knowledge primitive with enforceability.
    Core building block of the Epistemic Operating System.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    type: EpistemicObjectType = Field(...)
    content: str = Field(..., description="The knowledge content")
    embeddings: EpistemicEmbeddings = Field(default_factory=EpistemicEmbeddings)
    enforceability: Enforceability = Field(default=Enforceability.SOFT)
    authority_id: str = Field(..., description="Authority that created/owns this")
    tags: set[str] = Field(default_factory=set)
    provenance: Provenance | None = None

    class Config:
        use_enum_values = True


# -----------------------------------------------------------------------------
# EXECUTABLE DOCTRINE — Research/spec turned into enforceable law
# -----------------------------------------------------------------------------


class ExecutableDoctrine(BaseModel):
    """
    Research paper or spec converted to enforceable system law.
    Binds doctrines to execution and enforces invariants at runtime.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    source: DoctrineSource = Field(...)
    claims: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    invariants: list[str] = Field(default_factory=list)
    allowed_actions: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=list)
    enforcement_level: Enforceability = Field(default=Enforceability.HARD)
    authority_required: AuthorityLevel = Field(default=AuthorityLevel.L)

    class Config:
        use_enum_values = True


# -----------------------------------------------------------------------------
# ACTION ENVELOPE — Required wrapper for any action
# -----------------------------------------------------------------------------


class ActionEnvelope(BaseModel):
    """
    Required wrapper for any action that changes state.
    No action may execute without passing through accountability verification.
    """

    action_id: str = Field(default_factory=lambda: str(uuid4()))
    agent_id: str = Field(..., description="Agent performing the action")
    action_type: ActionType = Field(...)
    payload_ref: str = Field(..., description="URI to action payload")
    claimed_authority: str = Field(..., description="Authority ID claimed")
    required_capabilities: list[str] = Field(default_factory=list)
    environment: Environment = Field(default=Environment.DEV)
    risk_class: RiskClass = Field(default=RiskClass.LOW)
    evidence_refs: list[str] = Field(default_factory=list)
    simulation_ref: str | None = None
    signature: str = Field(..., description="Cryptographic signature")
    signing_key_id: str = Field(...)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        use_enum_values = True


# -----------------------------------------------------------------------------
# CONDITION — Requirement for conditional verdict
# -----------------------------------------------------------------------------


class Condition(BaseModel):
    """Requirement that must be satisfied for conditional verdict"""

    type: ConditionType = Field(...)
    description: str = Field(...)
    deadline: datetime | None = None
    satisfied: bool = Field(default=False)

    class Config:
        use_enum_values = True


# -----------------------------------------------------------------------------
# VERDICT — Decision output from Accountability Engine
# -----------------------------------------------------------------------------


class Verdict(BaseModel):
    """
    Decision output from the Accountability Engine.
    No verdict → no execution. No ledger entry → no verdict.
    """

    verdict_id: str = Field(default_factory=lambda: str(uuid4()))
    action_id: str = Field(..., description="Action this verdict is for")
    decision: VerdictDecision = Field(...)
    conditions: list[Condition] = Field(default_factory=list)
    issuing_authority: str = Field(..., description="Authority or quorum that issued")
    justification_refs: list[str] = Field(default_factory=list)
    ledger_ref: str | None = Field(None, description="Immutable ledger reference")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        use_enum_values = True


# -----------------------------------------------------------------------------
# EVIDENCE — Proof artifacts supporting decisions
# -----------------------------------------------------------------------------


class Evidence(BaseModel):
    """Proof artifact supporting a decision or contract"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    type: str = Field(..., description="test_result, simulation, benchmark, etc.")
    content: str = Field(...)
    source_id: str = Field(..., description="Where this evidence came from")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


# -----------------------------------------------------------------------------
# LEDGER ENTRY — Immutable audit record
# -----------------------------------------------------------------------------


class LedgerEntry(BaseModel):
    """Immutable audit record in accountability ledger"""

    entry_id: str = Field(default_factory=lambda: str(uuid4()))
    hash: str = Field(..., description="Content hash")
    signer: str = Field(..., description="Who signed this entry")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    action_ref: str | None = None
    verdict_ref: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


# -----------------------------------------------------------------------------
# EXPORTS
# -----------------------------------------------------------------------------

__all__ = [
    "ActionEnvelope",
    "ActionType",
    "AuthorityLevel",
    "Condition",
    "ConditionType",
    "DoctrineSource",
    "Enforceability",
    "Environment",
    # Models
    "EpistemicEmbeddings",
    "EpistemicObject",
    # Enums
    "EpistemicObjectType",
    "Evidence",
    "ExecutableDoctrine",
    "LedgerEntry",
    "Provenance",
    "RiskClass",
    "Verdict",
    "VerdictDecision",
]
