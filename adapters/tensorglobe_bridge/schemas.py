"""
TensorGlobe Bridge Schemas — L9 PacketEnvelope + EOS-Compliant
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Schemas",
    "module_version": "1.0.0",
    "created_by": "cryptoxdog",
    "created_at": "2026-01-23T15:07:20Z",
    "updated_at": "2026-01-24T13:02:52Z",
    "layer": "operations",
    "domain": "data_models",
    "module_name": "schemas",
    "type": "enum",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import uuid4
import hashlib
from pydantic import BaseModel, Field, validator

from core.eos.schemas import ActionEnvelope, EpistemicObject, EpistemicObjectType
from core.schemas.packet_envelope import PacketEnvelope


# ─────────────────────────────────────────────────────────────────
# INPUT: TensorRequest (Wrapped in PacketEnvelope)
# ─────────────────────────────────────────────────────────────────


class TensorOperation(str, Enum):
    """Supported tensor operations"""

    SIMILARITY_SEARCH = "similarity_search"
    LINK_PREDICTION = "link_prediction"
    RANKING = "ranking"
    EMBEDDING = "embedding"


class TensorRequest(BaseModel):
    """
    TensorRequest: Untrusted query to external tensor provider.
    Must be wrapped in PacketEnvelope + ActionEnvelope for L9 routing.
    """

    request_id: str = Field(default_factory=lambda: str(uuid4()))
    domain_id: str = Field(..., description="Domain context")
    entities: List[str] = Field(..., description="Entities to process")
    operation: TensorOperation = Field(...)

    constraints: Dict[str, Any] = Field(
        default_factory=dict,
        description="max_latency_ms, max_confidence, seed_for_determinism",
    )

    # Cryptographic binding to L9
    requester_agent_id: str = Field(..., description="L9 agent initiating")
    signature: str = Field(..., description="Signed by L9 agent")
    signing_key_id: str = Field(...)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    def compute_canonical(self) -> str:
        """Canonical form for signature verification"""
        parts = [
            self.request_id,
            self.domain_id,
            ",".join(sorted(self.entities)),
            self.operation.value,
            self.requester_agent_id,
        ]
        return "|".join(parts)

    class Config:
        use_enum_values = True


# ─────────────────────────────────────────────────────────────────
# OUTPUT: TensorResponse (Becomes Evidence Object)
# ─────────────────────────────────────────────────────────────────


class TensorResult(BaseModel):
    """Single tensor result (similarity score, prediction, etc.)"""

    entity_a: str
    entity_b: Optional[str] = None
    score: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    uncertainty: float = Field(..., ge=0.0, le=1.0, description="1 - confidence")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TensorResponse(BaseModel):
    """
    TensorResponse from external provider.
    Validated, then converted to Evidence object.
    """

    request_id: str = Field(...)
    results: List[TensorResult] = Field(...)

    model_metadata: Dict[str, str] = Field(
        description="model_id, version, training_domain"
    )

    # Quality metrics
    latency_ms: float = Field(...)
    batch_processing_time_ms: float = Field(...)

    # Cryptographic binding
    signature: str = Field(..., description="Signed by TensorGlobe")
    signing_key_id: str = Field(...)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    def to_evidence_object(self, request: TensorRequest) -> EpistemicObject:
        """Convert response to L9 Evidence object"""
        content = f"TensorGlobe {request.operation.value}: {len(self.results)} results"

        return EpistemicObject(
            type=EpistemicObjectType.EVIDENCE,
            content=content,
            authority_id="tensorglobe_external",
            enforceability="soft",
            tags={"tensor", "external", request.domain_id},
        )

    class Config:
        use_enum_values = True


# ─────────────────────────────────────────────────────────────────
# L9 INTEGRATION: Wrapped Packets
# ─────────────────────────────────────────────────────────────────


class TensorRequestPacket(PacketEnvelope):
    """
    TensorRequest wrapped in L9 PacketEnvelope.
    Routes through memory substrate, auditable.
    """

    payload_type: str = "tensor_request"
    channel: str = "tensorglobe_adapter"
    payload: TensorRequest = Field(...)


class TensorResponsePacket(PacketEnvelope):
    """
    TensorResponse wrapped in L9 PacketEnvelope.
    Emitted to accountability ledger.
    """

    payload_type: str = "tensor_response"
    channel: str = "tensorglobe_adapter"
    payload: TensorResponse = Field(...)
    evidence_ref: str = Field(..., description="Evidence object ID")


# ─────────────────────────────────────────────────────────────────
# ANOMALY DETECTION
# ─────────────────────────────────────────────────────────────────


class AnomalySignal(BaseModel):
    """Anomaly detection output"""

    request_id: str
    anomaly_type: str  # "confidence_collapse", "latency_breach", etc.
    anomaly_score: float = Field(ge=0.0, le=1.0)
    severity: str  # "low", "medium", "high", "critical"
    action_taken: str  # "discard", "downgrade", "suspend", etc.


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "ADA-OPER-004",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "auth",
        "batch-processing",
        "data-models",
        "enum",
        "metrics",
        "operations",
        "pydantic",
        "security",
        "validation",
    ],
    "keywords": [
        "anomaly",
        "canonical",
        "compute",
        "evidence",
        "object",
        "operation",
        "packet",
        "schemas",
    ],
    "business_value": "Provides schemas components including TensorOperation, TensorRequest, TensorResult",
    "last_modified": "2026-01-24T13:02:52Z",
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
