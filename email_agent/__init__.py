"""L9 Email Agent - Gmail API integration."""

# ============================================================================
__dora_meta__ = {
    "component_name": "Gmail API integration.",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-14T12:48:58Z",
    "updated_at": "2026-01-31T22:21:58Z",
    "layer": "integration",
    "domain": "email_integration",
    "module_name": "__init__",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Gmail API"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from email_agent.client import execute_email_task
from email_agent.credentials import (
    create_flow,
    exchange_code_for_tokens,
    load_client_secrets,
    load_tokens,
    save_tokens,
)
from email_agent.gmail_client import GmailClient
from email_agent.triage import run_daily_digest, summarize_inbox

__all__ = [
    "GmailClient",
    "create_flow",
    "exchange_code_for_tokens",
    "execute_email_task",
    "load_client_secrets",
    "load_tokens",
    "run_daily_digest",
    "save_tokens",
    "summarize_inbox",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "EMA-INTE-005",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["api", "email-integration", "integration", "security", "utility"],
    "keywords": ["agent", "api", "gmail", "integration."],
    "business_value": "Utility module for   init  ",
    "last_modified": "2026-01-31T22:21:58Z",
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
