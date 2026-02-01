"""
L9 LLM Module

Unified LLM interfaces implementing the LLMService protocol.

Provides:
- OpenAILLMService: OpenAI GPT models (GPT-4, GPT-4o, GPT-3.5)
- AnthropicLLMService: Anthropic Claude models (future)
- MockLLMService: Testing implementation

Version: 1.0.0
GMP: GMP-116-llm-service-implementation
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-24T13:02:20Z",
    "updated_at": "2026-01-31T22:21:46Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "__init__",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Anthropic API", "OpenAI API"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from core.llm.llm_service import (
    MockLLMService,
    OpenAILLMService,
    create_llm_service,
    get_default_model,
)

__all__ = [
    "MockLLMService",
    "OpenAILLMService",
    "create_llm_service",
    "get_default_model",
]

__version__ = "1.0.0"
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-043",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.llm.llm_service"],
    "tags": ["core", "foundation", "mocking", "testing", "utility"],
    "keywords": ["implementation", "models", "module", "service"],
    "business_value": "OpenAILLMService: OpenAI GPT models (GPT-4, GPT-4o, GPT-3.5) AnthropicLLMService: Anthropic Claude models (future) MockLLMService: Testing implementation Version: 1.0.0 GMP: GMP-116-llm-service-implem",
    "last_modified": "2026-01-31T22:21:46Z",
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
