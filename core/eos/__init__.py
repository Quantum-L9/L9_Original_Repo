"""
EOS — L9 Epistemic Operating System

The Epistemic Operating System sits between planning and execution.
It validates epistemic objects, enforces normative embeddings,
and blocks execution paths that violate high-authority constraints.

Core Principle: No verdict → no execution. No ledger entry → no verdict.
"""

from .schemas import (
    # Enums
    EpistemicObjectType,
    Enforceability,
    ActionType,
    Environment,
    RiskClass,
    VerdictDecision,
    ConditionType,
    DoctrineSource,
    AuthorityLevel,
    # Models
    EpistemicEmbeddings,
    Provenance,
    EpistemicObject,
    ExecutableDoctrine,
    ActionEnvelope,
    Condition,
    Verdict,
    Evidence,
    LedgerEntry,
)

from .accountability_engine import AccountabilityEngine
from .hypergraph_client import EOSHypergraphClient, create_eos_hypergraph_client
from .ledger_writer import EOSLedgerWriter, create_eos_ledger_writer


__all__ = [
    # Enums
    "EpistemicObjectType",
    "Enforceability",
    "ActionType",
    "Environment",
    "RiskClass",
    "VerdictDecision",
    "ConditionType",
    "DoctrineSource",
    "AuthorityLevel",
    # Models
    "EpistemicEmbeddings",
    "Provenance",
    "EpistemicObject",
    "ExecutableDoctrine",
    "ActionEnvelope",
    "Condition",
    "Verdict",
    "Evidence",
    "LedgerEntry",
    # Engine
    "AccountabilityEngine",
    # Clients
    "EOSHypergraphClient",
    "create_eos_hypergraph_client",
    "EOSLedgerWriter",
    "create_eos_ledger_writer",
]
