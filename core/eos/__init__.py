"""
EOS — L9 Epistemic Operating System

The Epistemic Operating System sits between planning and execution.
It validates epistemic objects, enforces normative embeddings,
and blocks execution paths that violate high-authority constraints.

Core Principle: No verdict → no execution. No ledger entry → no verdict.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-11T18:13:39Z",
    "updated_at": "2026-01-31T22:21:48Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "__init__",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j"],
        "memory_layers": ["semantic_memory"],
        "imported_by": [],
    },
}
# ============================================================================

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
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-216",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["auth", "core", "foundation", "utility"],
    "keywords": ["epistemic", "execution", "operating", "system", "verdict"],
    "business_value": "The Epistemic Operating System sits between planning and execution. It validates epistemic objects, enforces normative embeddings, and blocks execution paths that violate high-authority constraints. C",
    "last_modified": "2026-01-31T22:21:48Z",
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
