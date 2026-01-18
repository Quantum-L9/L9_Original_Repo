# ============================================================================
__dora_meta__ = {
    "component_name": "Whatsapp",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "whatsapp",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import os
from typing import Dict, Any
from twilio.rest import Client

def load_twilio_client():
    cfg_path = "/opt/l9/twilio_config.env"
    if os.path.exists(cfg_path):
        with open(cfg_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k, v)

    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    if not account_sid or not auth_token:
        raise RuntimeError("Missing Twilio credentials")

    return Client(account_sid, auth_token)

def send_whatsapp_message(body: str, to: str | None = None) -> Dict[str, Any]:
    client = load_twilio_client()
    from_number = os.getenv("TWILIO_WHATSAPP_FROM")
    to_number = to or os.getenv("TWILIO_WHATSAPP_TO")
    if not from_number or not to_number:
        raise RuntimeError("Missing WhatsApp from/to numbers")

    msg = client.messages.create(
        from_=from_number,
        to=to_number,
        body=body,
    )
    return {"sid": msg.sid, "status": msg.status}

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "API-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["api-gateway", "auth", "messaging", "operations", "rest-api", "utility"],
    "keywords": ["client", "load", "send", "twilio", "whatsapp"],
    "business_value": "Utility module for whatsapp",
    "last_modified": "2026-01-07T13:35:57Z",
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
