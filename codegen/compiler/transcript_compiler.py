# ============================================================================
__dora_meta__ = {
    "component_name": "Extracts structured artifacts from conversation transcripts.",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-08T13:57:12Z",
    "updated_at": "2026-01-13T13:44:18Z",
    "layer": "foundation",
    "domain": "code_generation",
    "module_name": "transcript_compiler",
    "type": "engine",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

# codegen/compiler/transcript_compiler.py
"""
Transcript Compiler - Extracts structured artifacts from conversation transcripts.

Converts natural language claims into typed YAML artifacts:
- decisions.yaml - Architectural decisions
- ial_candidates.yaml - Interface/abstraction layer candidates  
- typed_invariants.yaml - System invariants with enforcement targets
- work_packets.yaml - Actionable work items
"""

from .classifier import classify_claim
from .emitters import (
    decisions,
    ial_candidates,
    invariants,
    work_packets,
)
from .emitters.lexer import extract_claims
from .validator_bridge import validate_outputs


class TranscriptCompiler:
    def compile(self, transcript_text: str) -> dict:
        claims = extract_claims(transcript_text)

        buckets = {
            "decisions": [],
            "ials": [],
            "invariants": [],
            "tasks": [],
        }

        for claim in claims:
            kind, payload = classify_claim(claim)
            if kind == "decision":
                buckets["decisions"].append(payload)
            elif kind == "ial":
                buckets["ials"].append(payload)
            elif kind == "invariant":
                buckets["invariants"].append(payload)
            elif kind == "task":
                buckets["tasks"].append(payload)

        artifacts = {
            "decisions.yaml": decisions.emit(buckets["decisions"]),
            "ial_candidates.yaml": ial_candidates.emit(buckets["ials"]),
            "typed_invariants.yaml": invariants.emit(buckets["invariants"]),
            "work_packets.yaml": work_packets.emit(buckets["tasks"]),
        }

        validate_outputs(artifacts)
        return artifacts


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COD-FOUN-060",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["code-generation", "engine", "foundation"],
    "keywords": [
        "artifacts",
        "compile",
        "compiler",
        "conversation",
        "extracts",
        "structured",
        "transcript",
        "transcripts.",
    ],
    "business_value": "Implements TranscriptCompiler for transcript compiler functionality",
    "last_modified": "2026-01-13T13:44:18Z",
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
