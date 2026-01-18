# ============================================================================
__dora_meta__ = {
    "component_name": "Webhook Waba",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-11T02:49:53Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "webhook_waba",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": ["GET /waba/webhook", "POST /waba/webhook"],
        "datasources": ["HTTP API"],
        "memory_layers": ["semantic_memory"],
        "imported_by": ["api.server", "api.server_memory"],
    },
}
# ============================================================================

import os
import hashlib
import hmac
import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
import structlog
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)

# WABA credentials
WABA_PHONE_NUMBER_ID = os.getenv("WABA_PHONE_NUMBER_ID")
WABA_BUSINESS_ACCOUNT_ID = os.getenv("WABA_BUSINESS_ACCOUNT_ID")
WABA_ACCESS_TOKEN = os.getenv("WABA_ACCESS_TOKEN")
WABA_WEBHOOK_VERIFY_TOKEN = os.getenv(
    "WABA_WEBHOOK_VERIFY_TOKEN", "L9_WABA_VERIFY_2025"
)
EXECUTOR_API_KEY = os.getenv("L9_EXECUTOR_API_KEY")

if not all([WABA_PHONE_NUMBER_ID, WABA_ACCESS_TOKEN, EXECUTOR_API_KEY]):
    raise RuntimeError("WABA environment variables not fully configured")

router = APIRouter()

CHAT_URL = "http://127.0.0.1:8000/chat"
MEMORY_EMBEDDINGS_URL = "http://127.0.0.1:8000/memory/embeddings"
WABA_API_BASE = "https://graph.instagram.com/v18.0"


def verify_webhook_signature(request_body: str, x_hub_signature: str) -> bool:
    """Verify Meta's webhook signature."""
    if not x_hub_signature:
        return False
    hash_obj = hmac.new(
        WABA_ACCESS_TOKEN.encode(), request_body.encode(), hashlib.sha256
    )
    expected_signature = f"sha256={hash_obj.hexdigest()}"
    return hmac.compare_digest(expected_signature, x_hub_signature)


async def download_media(media_id: str, mime_type: str) -> bytes:
    """Download media from WABA using Media ID."""
    url = f"{WABA_API_BASE}/{media_id}"
    headers = {"Authorization": f"Bearer {WABA_ACCESS_TOKEN}"}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            raise Exception(f"Failed to get media URL: {resp.text}")

        media_url_data = resp.json()
        media_url = media_url_data.get("url")

        # Download actual media
        media_resp = await client.get(media_url, headers=headers)
        if media_resp.status_code != 200:
            raise Exception(f"Failed to download media: {media_resp.text}")

        return media_resp.content


async def send_waba_message(to_number: str, message_type: str, content: dict):
    """Send message back via WABA API."""
    url = f"{WABA_API_BASE}/{WABA_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WABA_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": message_type,
        message_type: content,
    }

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code not in [200, 201]:
            logger.error(f"WABA send failed: {resp.text}")
            raise Exception(f"Failed to send WABA message: {resp.text}")

        return resp.json()


@router.get("/waba/webhook", response_class=JSONResponse)
@must_stay_async("FastAPI/ASGI route handler")
async def verify_waba_webhook(request: Request):
    """
    Meta webhook verification challenge.
    Meta calls this with mode=subscribe and a challenge token.
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == WABA_WEBHOOK_VERIFY_TOKEN:
        return JSONResponse(content={"hub.challenge": challenge})
    else:
        raise HTTPException(status_code=403, detail="Invalid verification token")


@router.post("/waba/webhook", response_class=JSONResponse)
async def waba_webhook(request: Request):
    """
    WABA incoming message webhook.
    Handles:
    - Text messages
    - Images with captions
    - Audio files
    - Video files
    - Documents
    - Location
    """
    body_raw = await request.body()
    x_hub_signature = request.headers.get("x-hub-signature-256", "")

    # Verify signature (allow localhost for testing)
    client_ip = request.client.host if request.client else "unknown"
    is_localhost = client_ip in ("127.0.0.1", "::1", "localhost")
    if not is_localhost and not verify_webhook_signature(
        body_raw.decode(), x_hub_signature
    ):
        logger.warning("Invalid webhook signature from %s", client_ip)
        raise HTTPException(status_code=403, detail="Invalid signature")

    data = await request.json()

    # Extract entry
    entry = data.get("entry", [{}])[0]
    changes = entry.get("changes", [{}])

    for change in changes:
        value = change.get("value", {})
        messages = value.get("messages", [])

        for message in messages:
            from_number = message.get("from")
            message_type = message.get("type")
            message_id = message.get("id")

            try:
                # Route by message type
                if message_type == "text":
                    text_body = message.get("text", {}).get("body", "")
                    prompt = f"WhatsApp message from {from_number}: {text_body}"

                elif message_type == "image":
                    image_data = message.get("image", {})
                    media_id = image_data.get("id")
                    caption = image_data.get("caption", "")

                    # Download image
                    image_bytes = await download_media(media_id, "image/jpeg")

                    # For now, just note it in the message
                    # In production, you'd process the image with Vision API
                    prompt = f"WhatsApp image from {from_number}. Caption: {caption}. Image size: {len(image_bytes)} bytes"

                elif message_type == "audio":
                    audio_data = message.get("audio", {})
                    media_id = audio_data.get("id")

                    # Download audio
                    audio_bytes = await download_media(media_id, "audio/ogg")

                    # In production: transcribe with Whisper
                    prompt = f"WhatsApp audio from {from_number}. Duration: unknown. Audio size: {len(audio_bytes)} bytes"

                elif message_type == "video":
                    video_data = message.get("video", {})
                    media_id = video_data.get("id")
                    caption = video_data.get("caption", "")

                    # Download video
                    video_bytes = await download_media(media_id, "video/mp4")

                    prompt = f"WhatsApp video from {from_number}. Caption: {caption}. Video size: {len(video_bytes)} bytes"

                elif message_type == "document":
                    doc_data = message.get("document", {})
                    media_id = doc_data.get("id")
                    filename = doc_data.get("filename", "document")

                    # Download document
                    doc_bytes = await download_media(media_id, "application/pdf")

                    prompt = f"WhatsApp document from {from_number}. Filename: {filename}. Size: {len(doc_bytes)} bytes"

                else:
                    logger.warning(f"Unsupported message type: {message_type}")
                    prompt = f"Unsupported message type: {message_type}"

                # Send to chat endpoint
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(
                        CHAT_URL,
                        json={"message": prompt},
                        headers={"Authorization": f"Bearer {EXECUTOR_API_KEY}"},
                    )

                if resp.status_code != 200:
                    logger.error(f"Chat endpoint failed: {resp.text}")
                    reply = "I encountered an error processing your message."
                else:
                    reply = resp.json().get("reply", "No response generated.")

                # Send reply back via WABA
                await send_waba_message(
                    from_number, "text", {"preview_url": False, "body": reply}
                )

                logger.info(f"Processed WABA message {message_id} from {from_number}")

            except Exception as e:
                logger.error(f"Error processing WABA message: {e}")
                try:
                    await send_waba_message(
                        from_number,
                        "text",
                        {
                            "preview_url": False,
                            "body": "Error processing message. Please try again.",
                        },
                    )
                except Exception:
                    pass

    return JSONResponse(content={"status": "ok"})


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "API-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": [
        "api",
        "api-gateway",
        "async",
        "auth",
        "endpoint",
        "http-client",
        "logging",
        "messaging",
        "operations",
        "router",
    ],
    "keywords": ["download", "media", "send", "signature", "verify", "waba", "webhook"],
    "business_value": "Utility module for webhook waba",
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
