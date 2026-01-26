"""
EOS — L9 Epistemic Operating System

The Epistemic Operating System sits between planning and execution.
It validates epistemic objects, enforces normative embeddings,
and blocks execution paths that violate high-authority constraints.

Core Principle: No verdict → no execution. No ledger entry → no verdict.
"""

from .accountability_engine import AccountabilityEngine
from .hypergraph_client import EOSHypergraphClient, create_eos_hypergraph_client
from .ledger_writer import EOSLedgerWriter, create_eos_ledger_writer
from .schemas import (
    ActionEnvelope,
    ActionType,
    AuthorityLevel,
    Condition,
    ConditionType,
    DoctrineSource,
    Enforceability,
    Environment,
    # Models
    EpistemicEmbeddings,
    EpistemicObject,
    # Enums
    EpistemicObjectType,
    Evidence,
    ExecutableDoctrine,
    LedgerEntry,
    Provenance,
    RiskClass,
    Verdict,
    VerdictDecision,
)

__all__ = [
    # Engine
    "AccountabilityEngine",
    "ActionEnvelope",
    "ActionType",
    "AuthorityLevel",
    "Condition",
    "ConditionType",
    "DoctrineSource",
    # Clients
    "EOSHypergraphClient",
    "EOSLedgerWriter",
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
    "create_eos_hypergraph_client",
    "create_eos_ledger_writer",
]
