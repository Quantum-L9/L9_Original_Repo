
import base64
import hashlib
import hmac
import os

import httpx
import structlog
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse

from api.routes.registry import router_registry

logger = structlog.get_logger(__name__)

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_SMS_NUMBER = os.getenv("TWILIO_SMS_NUMBER")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
EXECUTOR_API_KEY = os.getenv("L9_EXECUTOR_API_KEY")

_TWILIO_CONFIGURED = all(
    [TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_SMS_NUMBER, EXECUTOR_API_KEY]
)
if not _TWILIO_CONFIGURED:
    logger.warning(
        "Twilio environment variables not fully configured — routes will reject requests"
    )

router = APIRouter()

router_registry.register(
    router=router,
    prefix="/twilio",
    tags=["twilio"],
    module_id="twilio_webhook",
    display_name="Twilio SMS/WhatsApp Webhook",
)

CHAT_URL = "http://127.0.0.1:8000/chat"


def verify_twilio_signature(
    url: str, params: dict, signature: str, auth_token: str | None
) -> bool:
    """
    Verify Twilio request signature using HMAC-SHA1 base64.

    Twilio signs requests by:
    1. Taking the full URL
    2. Sorting POST params alphabetically and appending key=value pairs
    3. Computing HMAC-SHA1 with auth token and base64 encoding
    """
    if not auth_token:
        return False

    # Build the signature base string: URL + sorted params
    s = url
    for key in sorted(params.keys()):
        s += f"{key}{params[key]}"

    # Compute HMAC-SHA1 and base64 encode
    computed = base64.b64encode(
        hmac.new(auth_token.encode(), s.encode(), hashlib.sha1).digest()
    ).decode()

    return hmac.compare_digest(computed, signature)


@router.post("/twilio/webhook", response_class=PlainTextResponse)
async def twilio_webhook(
    request: Request,
    x_twilio_signature: str = Header(None, alias="X-Twilio-Signature"),
):
    """
    Minimal Twilio SMS/WhatsApp webhook:
    - Reads incoming message body and from number
    - Forwards text to /chat
    - Returns plain text reply in TwiML-compatible form
    """
    if not _TWILIO_CONFIGURED:
        raise HTTPException(status_code=503, detail="Twilio not configured")
    form = await request.form()
    if not x_twilio_signature:
        raise HTTPException(status_code=401, detail="Missing Twilio signature")
    if not verify_twilio_signature(
        str(request.url), dict(form), x_twilio_signature, TWILIO_AUTH_TOKEN
    ):
        raise HTTPException(status_code=401, detail="Invalid Twilio signature")
    from_number = form.get("From")
    body = form.get("Body")

    if not body:
        raise HTTPException(status_code=400, detail="Missing Body")

    prompt = f"Message from {from_number}: {body}"

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            resp = await client.post(
                CHAT_URL,
                json={"message": prompt},
                headers={"Authorization": f"Bearer {EXECUTOR_API_KEY}"},
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Chat call failed: {e}") from e

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    data = resp.json()
    reply = data.get("reply", "I could not generate a response.")

    # Twilio expects plain text for simple replies (it will wrap into SMS)
    return PlainTextResponse(reply)


# Runtime execution trace - updated automatically on every execution
