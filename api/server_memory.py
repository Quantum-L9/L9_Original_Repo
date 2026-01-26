# ============================================================================
__dora_meta__ = {
    "component_name": "Server Memory",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "server_memory",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": ["GET /", "GET /health", "POST /chat"],
        "datasources": ["HTTP API", "Neo4j", "OpenAI API", "Slack API"],
        "memory_layers": ["working_memory"],
        "imported_by": ["tests.test_imports"],
    },
}
# ============================================================================

import os

import structlog
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

import api.db as db

# Local dev mode flag
LOCAL_DEV = os.getenv("LOCAL_DEV", "false").lower() == "true"
from openai import OpenAI

from api.auth import verify_api_key
from api.memory.router import router as memory_router
# Integration settings
from config.settings import settings

logger = structlog.get_logger(__name__)

# Initialize DB ONCE at boot
if not LOCAL_DEV:
    db.init_db()

# Create unified app (wraps the base server)
app = FastAPI(title="L9 Phase 2 Secure AI OS")

# OpenAI client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not configured")
client = OpenAI(api_key=OPENAI_API_KEY)


class ChatRequest(BaseModel):
    message: str
    system_prompt: str | None = None


class ChatResponse(BaseModel):
    reply: str


@app.get("/")
def root():
    return {"status": "L9 Phase 2 AI OS", "version": "0.3.0"}


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "L9 Phase 2 Memory System",
        "version": "0.3.0",
        "database": "connected",
        "memory_system": "operational",
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """
    Basic LLM chat endpoint using OpenAI.
    Ingests both request and response to memory for audit trail.
    """
    from core.schemas import PacketEnvelopeIn
    from memory.ingestion import ingest_packet

    try:
        messages = []
        if payload.system_prompt:
            messages.append({"role": "system", "content": payload.system_prompt})
        else:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "You are L, an infrastructure-focused assistant connected to an L9 "
                        "backend and memory system. Be concise, precise, and avoid destructive "
                        "actions. When appropriate, suggest using tools like the CTO agent."
                    ),
                }
            )
        messages.append({"role": "user", "content": payload.message})

        completion = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
        )
        reply = completion.choices[0].message.content

        # Ingest chat interaction to memory (audit trail)
        try:
            packet_in = PacketEnvelopeIn(
                packet_type="chat_interaction",
                payload={
                    "user_message": payload.message,
                    "system_prompt": payload.system_prompt,
                    "assistant_reply": reply,
                    "model": "gpt-4.1-mini",
                },
                metadata={"agent": "chat_api", "source": "server_memory"},
            )
            await ingest_packet(packet_in)
        except Exception as mem_err:
            # Log but don't fail the request if memory ingestion fails
            logger.warning(f"Failed to ingest chat to memory: {mem_err}")

        return ChatResponse(reply=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat backend error: {e}") from e


# Mount memory router with prefix
app.include_router(memory_router, prefix="/memory")

# === Initialize default app state values ===
# These may be overwritten by integration initializers below
app.state.substrate_service = None  # Memory substrate (optional for basic Slack)
app.state.rate_limiter = None  # Rate limiter (optional)
app.state.permission_graph = None  # Permission graph (optional)
app.state.neo4j_client = None  # Neo4j client (optional)

# === Integration Routers (gated by toggle flags) ===

# Slack Events API
if settings.slack_app_enabled:
    # Validate required tokens before mounting routes
    slack_bot_token = settings.slack_bot_token or os.getenv("SLACK_BOT_TOKEN")
    slack_signing_secret = settings.slack_signing_secret or os.getenv(
        "SLACK_SIGNING_SECRET"
    )

    if not slack_bot_token or not slack_signing_secret:
        logger.error(
            "Slack enabled but missing required tokens. "
            "Set SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET. "
            "Slack routes will NOT be mounted."
        )
        app.state.slack_validator = None
        app.state.slack_client = None
    else:
        try:
            # Initialize Slack adapter components (required for route dependencies)
            import httpx

            from api.slack_adapter import SlackRequestValidator
            from api.slack_client import SlackAPIClient

            validator = SlackRequestValidator(slack_signing_secret)
            http_client = httpx.AsyncClient()
            slack_client = SlackAPIClient(
                bot_token=slack_bot_token,
                http_client=http_client,
            )

            # Store in app state for route dependencies
            app.state.slack_validator = validator
            app.state.slack_client = slack_client
            app.state.aios_base_url = os.getenv(
                "AIOS_BASE_URL", "http://localhost:8000"
            )
            app.state.http_client = http_client

            # Use new Slack router (v2.0+) from api/routes/slack.py
            # Legacy webhook_slack.py archived to _archived/legacy_slack/
            from api.routes.slack import router as slack_router

            app.include_router(slack_router)
            logger.info(
                "Slack router mounted successfully (v2.0+) with validator initialized"
            )
        except Exception as e:
            logger.error(f"WARNING: Failed to load Slack router: {e}")
            app.state.slack_validator = None
            app.state.slack_client = None

# Mac Agent API
if settings.mac_agent_enabled:
    try:
        from api.webhook_mac_agent import router as mac_agent_router

        app.include_router(mac_agent_router)
    except Exception as e:
        logger.error(f"WARNING: Failed to load Mac Agent router: {e}")

# Twilio webhook router (disabled until ready)
if settings.twilio_enabled:
    try:
        from api.webhook_twilio import router as twilio_router

        app.include_router(twilio_router)
    except Exception as e:
        logger.error(f"WARNING: Failed to load Twilio router: {e}")

# WABA (WhatsApp Business Account - native Meta) (disabled until ready)
if settings.waba_enabled:
    try:
        from api.webhook_waba import router as waba_router

        app.include_router(waba_router)
    except Exception as e:
        logger.error(f"WARNING: Failed to load WABA router: {e}")

# Email integration
if settings.email_enabled:
    try:
        from api.webhook_email import router as email_router

        app.include_router(email_router)
    except Exception as e:
        logger.error(f"WARNING: Failed to load Email router: {e}")

    # Email Agent API
    try:
        from email_agent.router import router as email_agent_router

        app.include_router(email_agent_router)
    except Exception as e:
        logger.error(f"WARNING: Failed to load Email Agent router: {e}")

# === Debug: Print integration toggles at startup ===
logger.info(
    "L9 Integration Toggles",
    {
        "Slack": settings.slack_app_enabled,
        "Mac Agent": settings.mac_agent_enabled,
        "Email": settings.email_enabled,
        "Inbox Parser": settings.inbox_parser_enabled,
        "Twilio": settings.twilio_enabled,
        "WABA": settings.waba_enabled,
    },
)

# === DEBUG: Print all mounted routes at startup ===
for route in app.routes:
    logger.info(f"ROUTE: {route.path}")

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "API-OPER-005",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "api.auth",
        "api.db",
        "api.memory.router",
        "api.routes.slack",
        "api.slack_adapter",
    ],
    "tags": [
        "api",
        "api-gateway",
        "async",
        "auth",
        "authorization",
        "debugging",
        "endpoint",
        "event-driven",
        "http-client",
        "llm",
    ],
    "keywords": ["chat", "health", "memory", "root", "server"],
    "business_value": "Provides server memory components including ChatRequest, ChatResponse",
    "last_modified": "2026-01-17T23:47:56Z",
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
