"""
L9 Email Agent Router
=====================

FastAPI router for email agent endpoints.
Fully compliant with memory ingestion pipeline.
Supports multi-account mode with API key authentication.

Version: 4.0.0

Endpoints:
- POST /email/{account}/query
- POST /email/{account}/get
- POST /email/{account}/draft
- POST /email/{account}/send
- POST /email/{account}/reply
- POST /email/{account}/forward

All handlers:
1. Verify API key
2. Validate account
3. Generate trace_id
4. Ingest pre-action packet
5. Execute action
6. Ingest post-action outcome packet
7. Fail loudly if ingestion fails
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Router",
    "module_version": "4.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-14T12:48:58Z",
    "updated_at": "2026-01-14T13:21:46Z",
    "layer": "integration",
    "domain": "api_gateway",
    "module_name": "router",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [
            "POST /{account}/query",
            "POST /{account}/get",
            "POST /{account}/draft",
            "POST /{account}/send",
            "POST /{account}/reply",
            "POST /{account}/forward",
        ],
        "datasources": ["Gmail API"],
        "memory_layers": ["working_memory"],
        "imported_by": [
            "api.server",
            "api.server_memory",
            "tests.email_agent.test_email_router",
            "tests.smoke_email",
        ],
    },
}
# ============================================================================

from typing import Any, Dict, List, Optional
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel

from api.auth import verify_api_key
from email_agent.config import VALID_ACCOUNTS

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/email", tags=["email-agent"])


# =============================================================================
# Request Models
# =============================================================================


class QueryRequest(BaseModel):
    """Request model for email query."""

    query: str = ""
    max_results: int = 10


class GetRequest(BaseModel):
    """Request model for getting email."""

    id: str


class DraftRequest(BaseModel):
    """Request model for email draft."""

    to: str
    subject: str
    body: str
    attachments: Optional[List[str]] = None


class SendRequest(BaseModel):
    """Request model for sending email."""

    draft_id: Optional[str] = None
    to: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    attachments: Optional[List[str]] = None


class ReplyRequest(BaseModel):
    """Request model for replying to email."""

    id: str
    body: str


class ForwardRequest(BaseModel):
    """Request model for forwarding email."""

    id: str
    to: str
    body: str = ""


# =============================================================================
# Memory Ingestion Helper
# =============================================================================


async def ingest_email_event(
    trace_id: str,
    action: str,
    phase: str,  # "pre" or "post"
    payload: Dict[str, Any],
    error: Optional[str] = None,
) -> None:
    """
    Ingest email event to memory.

    Args:
        trace_id: Unique trace identifier for this request
        action: Action being performed (e.g., "email.igor.query", "email.l.send")
        phase: "pre" for before action, "post" for after action
        payload: Event payload (sanitized, no secrets)
        error: Error message if action failed

    Raises:
        HTTPException: If ingestion fails (fail loud policy)
    """
    from core.schemas import PacketEnvelopeIn
    from memory.ingestion import ingest_packet

    packet_type = f"email_{phase}"

    packet_in = PacketEnvelopeIn(
        packet_type=packet_type,
        payload={
            "trace_id": trace_id,
            "action": action,
            "phase": phase,
            **payload,
            **({"error": error} if error else {}),
        },
        metadata={
            "agent": "email_agent",
            "source": "email_api",
            "trace_id": trace_id,
        },
    )

    try:
        await ingest_packet(packet_in)
        logger.debug(f"[{trace_id}] Ingested email event: {action} ({phase})")
    except Exception as e:
        logger.error(f"[{trace_id}] FAILED to ingest email event: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Memory ingestion failed for {action} ({phase}): {str(e)}. trace_id={trace_id}",
        )


def generate_trace_id() -> str:
    """Generate a unique trace ID for request tracking."""
    return f"email-{uuid4().hex[:12]}"


def validate_account(account: str) -> None:
    """Validate account name."""
    if account not in VALID_ACCOUNTS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown account: {account}. Valid accounts: {VALID_ACCOUNTS}",
        )


# =============================================================================
# Email Handlers (Fully Wired with Auth)
# =============================================================================


@router.post("/{account}/query")
async def query_emails(
    request: QueryRequest,
    account: str = Path(..., pattern="^(igor|l)$"),
    _: None = Depends(verify_api_key),
):
    """
    Query emails using Gmail search. Requires API key.

    Args:
        account: Gmail account ("igor" or "l")
        request: Query parameters

    Ingests pre/post events to memory.

    Example queries:
    - "from:lawyer has:attachment"
    - "subject:meeting"
    - "is:unread"
    """
    validate_account(account)
    trace_id = generate_trace_id()
    action = f"email.{account}.query"

    # Pre-action ingestion
    await ingest_email_event(
        trace_id=trace_id,
        action=action,
        phase="pre",
        payload={
            "account": account,
            "query": request.query,
            "max_results": request.max_results,
        },
    )

    try:
        from email_agent.gmail_client import GmailClient

        client = GmailClient(account=account)
        messages = client.list_messages(request.query, request.max_results)

        # Post-action ingestion (success)
        await ingest_email_event(
            trace_id=trace_id,
            action=action,
            phase="post",
            payload={
                "account": account,
                "status": "success",
                "result_count": len(messages) if messages else 0,
            },
        )

        return {"messages": messages, "trace_id": trace_id, "account": account}

    except HTTPException:
        raise
    except Exception as e:
        # Post-action ingestion (error)
        await ingest_email_event(
            trace_id=trace_id,
            action=action,
            phase="post",
            payload={"account": account, "status": "error"},
            error=str(e),
        )
        logger.error(f"[{trace_id}] Email query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"{str(e)} (trace_id={trace_id})")


@router.post("/{account}/get")
async def get_email(
    request: GetRequest,
    account: str = Path(..., pattern="^(igor|l)$"),
    _: None = Depends(verify_api_key),
):
    """
    Get full email message with parsed body and attachments. Requires API key.

    Args:
        account: Gmail account ("igor" or "l")
        request: Message ID

    Ingests pre/post events to memory.

    Returns:
        Message dictionary with id, from, to, subject, date, body_plain, body_html, attachments
    """
    validate_account(account)
    trace_id = generate_trace_id()
    action = f"email.{account}.get"

    # Pre-action ingestion
    await ingest_email_event(
        trace_id=trace_id,
        action=action,
        phase="pre",
        payload={"account": account, "message_id": request.id},
    )

    try:
        from email_agent.gmail_client import GmailClient

        client = GmailClient(account=account)
        message = client.get_message(request.id)

        if message:
            # Post-action ingestion (success)
            await ingest_email_event(
                trace_id=trace_id,
                action=action,
                phase="post",
                payload={
                    "account": account,
                    "status": "success",
                    "message_id": request.id,
                    "has_attachments": bool(message.get("attachments")),
                },
            )
            return {"message": message, "trace_id": trace_id, "account": account}
        else:
            # Post-action ingestion (not found)
            await ingest_email_event(
                trace_id=trace_id,
                action=action,
                phase="post",
                payload={
                    "account": account,
                    "status": "not_found",
                    "message_id": request.id,
                },
            )
            raise HTTPException(
                status_code=404,
                detail=f"Message {request.id} not found (trace_id={trace_id})",
            )

    except HTTPException:
        raise
    except Exception as e:
        # Post-action ingestion (error)
        await ingest_email_event(
            trace_id=trace_id,
            action=action,
            phase="post",
            payload={"account": account, "status": "error", "message_id": request.id},
            error=str(e),
        )
        logger.error(f"[{trace_id}] Email get failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"{str(e)} (trace_id={trace_id})")


@router.post("/{account}/draft")
async def draft_email(
    request: DraftRequest,
    account: str = Path(..., pattern="^(igor|l)$"),
    _: None = Depends(verify_api_key),
):
    """
    Create email draft with optional attachments. Requires API key.

    Args:
        account: Gmail account ("igor" or "l")
        request: Draft details

    Ingests pre/post events to memory.
    """
    validate_account(account)
    trace_id = generate_trace_id()
    action = f"email.{account}.draft"

    # Pre-action ingestion (sanitized - no body content)
    await ingest_email_event(
        trace_id=trace_id,
        action=action,
        phase="pre",
        payload={
            "account": account,
            "to": request.to,
            "subject": request.subject,
            "body_length": len(request.body) if request.body else 0,
            "attachment_count": len(request.attachments) if request.attachments else 0,
        },
    )

    try:
        from email_agent.gmail_client import GmailClient

        client = GmailClient(account=account)
        draft_id = client.draft_email(
            request.to, request.subject, request.body, attachments=request.attachments
        )

        if draft_id:
            # Post-action ingestion (success)
            await ingest_email_event(
                trace_id=trace_id,
                action=action,
                phase="post",
                payload={
                    "account": account,
                    "status": "success",
                    "draft_id": draft_id,
                },
            )
            return {
                "draft_id": draft_id,
                "status": "success",
                "trace_id": trace_id,
                "account": account,
            }
        else:
            # Post-action ingestion (failure)
            await ingest_email_event(
                trace_id=trace_id,
                action=action,
                phase="post",
                payload={"account": account, "status": "error"},
                error="Draft creation returned None",
            )
            raise HTTPException(
                status_code=500, detail=f"Failed to create draft (trace_id={trace_id})"
            )

    except HTTPException:
        raise
    except Exception as e:
        # Post-action ingestion (error)
        await ingest_email_event(
            trace_id=trace_id,
            action=action,
            phase="post",
            payload={"account": account, "status": "error"},
            error=str(e),
        )
        logger.error(f"[{trace_id}] Email draft failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"{str(e)} (trace_id={trace_id})")


@router.post("/{account}/send")
async def send_email(
    request: SendRequest,
    account: str = Path(..., pattern="^(igor|l)$"),
    _: None = Depends(verify_api_key),
):
    """
    Send email (from draft or directly) with optional attachments. Requires API key.

    Args:
        account: Gmail account ("igor" or "l")
        request: Send details

    Ingests pre/post events to memory.
    """
    validate_account(account)
    trace_id = generate_trace_id()
    action = f"email.{account}.send"

    # Determine send mode
    send_mode = "draft" if request.draft_id else "direct"

    # Pre-action ingestion (sanitized)
    await ingest_email_event(
        trace_id=trace_id,
        action=action,
        phase="pre",
        payload={
            "account": account,
            "send_mode": send_mode,
            "draft_id": request.draft_id,
            "to": request.to,
            "subject": request.subject,
            "body_length": len(request.body) if request.body else 0,
            "attachment_count": len(request.attachments) if request.attachments else 0,
        },
    )

    try:
        from email_agent.gmail_client import GmailClient

        client = GmailClient(account=account)

        if request.draft_id:
            # Send existing draft
            try:
                draft = (
                    client.service.users()
                    .drafts()
                    .get(userId="me", id=request.draft_id)
                    .execute()
                )

                sent_message = (
                    client.service.users()
                    .drafts()
                    .send(userId="me", body={"id": request.draft_id})
                    .execute()
                )

                # Post-action ingestion (success)
                await ingest_email_event(
                    trace_id=trace_id,
                    action=action,
                    phase="post",
                    payload={
                        "account": account,
                        "status": "success",
                        "send_mode": "draft",
                        "message_id": sent_message.get("id"),
                        "thread_id": sent_message.get("threadId"),
                    },
                )

                return {
                    "status": "success",
                    "message": "Email sent",
                    "message_id": sent_message.get("id"),
                    "thread_id": sent_message.get("threadId"),
                    "trace_id": trace_id,
                    "account": account,
                }
            except Exception as e:
                await ingest_email_event(
                    trace_id=trace_id,
                    action=action,
                    phase="post",
                    payload={
                        "account": account,
                        "status": "error",
                        "send_mode": "draft",
                    },
                    error=str(e),
                )
                logger.error(f"[{trace_id}] Failed to send draft: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to send draft: {str(e)} (trace_id={trace_id})",
                )
        else:
            # Send directly
            if not all([request.to, request.subject, request.body]):
                await ingest_email_event(
                    trace_id=trace_id,
                    action=action,
                    phase="post",
                    payload={
                        "account": account,
                        "status": "error",
                        "send_mode": "direct",
                    },
                    error="Missing required fields: to, subject, body",
                )
                raise HTTPException(
                    status_code=400,
                    detail=f"to, subject, and body required for direct send (trace_id={trace_id})",
                )

            result = client.send_email(
                request.to,
                request.subject,
                request.body,
                attachments=request.attachments,
            )

            if result:
                # Post-action ingestion (success)
                await ingest_email_event(
                    trace_id=trace_id,
                    action=action,
                    phase="post",
                    payload={
                        "account": account,
                        "status": "success",
                        "send_mode": "direct",
                        "provider_response": result,
                    },
                )
                return {
                    "status": "success",
                    "message": "Email sent",
                    "trace_id": trace_id,
                    "account": account,
                    **result,
                }
            else:
                await ingest_email_event(
                    trace_id=trace_id,
                    action=action,
                    phase="post",
                    payload={
                        "account": account,
                        "status": "error",
                        "send_mode": "direct",
                    },
                    error="send_email returned None",
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to send email (trace_id={trace_id})",
                )

    except HTTPException:
        raise
    except Exception as e:
        await ingest_email_event(
            trace_id=trace_id,
            action=action,
            phase="post",
            payload={"account": account, "status": "error"},
            error=str(e),
        )
        logger.error(f"[{trace_id}] Email send failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"{str(e)} (trace_id={trace_id})")


@router.post("/{account}/reply")
async def reply_email(
    request: ReplyRequest,
    account: str = Path(..., pattern="^(igor|l)$"),
    _: None = Depends(verify_api_key),
):
    """
    Reply to an email message. Requires API key.

    Args:
        account: Gmail account ("igor" or "l")
        id: Original message ID to reply to
        body: Reply body

    Ingests pre/post events to memory.
    """
    validate_account(account)
    trace_id = generate_trace_id()
    action = f"email.{account}.reply"

    # Pre-action ingestion
    await ingest_email_event(
        trace_id=trace_id,
        action=action,
        phase="pre",
        payload={
            "account": account,
            "original_message_id": request.id,
            "body_length": len(request.body) if request.body else 0,
        },
    )

    try:
        from email_agent.gmail_client import GmailClient

        client = GmailClient(account=account)
        result = client.reply_to_email(request.id, request.body)

        if result:
            # Post-action ingestion (success)
            await ingest_email_event(
                trace_id=trace_id,
                action=action,
                phase="post",
                payload={
                    "account": account,
                    "status": "success",
                    "original_message_id": request.id,
                    "provider_response": result,
                },
            )
            return {
                "status": "success",
                "message": "Reply sent",
                "trace_id": trace_id,
                "account": account,
                **result,
            }
        else:
            await ingest_email_event(
                trace_id=trace_id,
                action=action,
                phase="post",
                payload={
                    "account": account,
                    "status": "error",
                    "original_message_id": request.id,
                },
                error="reply_to_email returned None",
            )
            raise HTTPException(
                status_code=500, detail=f"Failed to send reply (trace_id={trace_id})"
            )

    except HTTPException:
        raise
    except Exception as e:
        await ingest_email_event(
            trace_id=trace_id,
            action=action,
            phase="post",
            payload={
                "account": account,
                "status": "error",
                "original_message_id": request.id,
            },
            error=str(e),
        )
        logger.error(f"[{trace_id}] Email reply failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"{str(e)} (trace_id={trace_id})")


@router.post("/{account}/forward")
async def forward_email(
    request: ForwardRequest,
    account: str = Path(..., pattern="^(igor|l)$"),
    _: None = Depends(verify_api_key),
):
    """
    Forward an email message. Requires API key.

    Args:
        account: Gmail account ("igor" or "l")
        id: Original message ID to forward
        to: Recipient email address(es)
        body: Optional forward message body

    Ingests pre/post events to memory.
    """
    validate_account(account)
    trace_id = generate_trace_id()
    action = f"email.{account}.forward"

    # Pre-action ingestion
    await ingest_email_event(
        trace_id=trace_id,
        action=action,
        phase="pre",
        payload={
            "account": account,
            "original_message_id": request.id,
            "to": request.to,
            "body_length": len(request.body) if request.body else 0,
        },
    )

    try:
        from email_agent.gmail_client import GmailClient

        client = GmailClient(account=account)
        result = client.forward_email(request.id, request.to, request.body)

        if result:
            # Post-action ingestion (success)
            await ingest_email_event(
                trace_id=trace_id,
                action=action,
                phase="post",
                payload={
                    "account": account,
                    "status": "success",
                    "original_message_id": request.id,
                    "to": request.to,
                    "provider_response": result,
                },
            )
            return {
                "status": "success",
                "message": "Email forwarded",
                "trace_id": trace_id,
                "account": account,
                **result,
            }
        else:
            await ingest_email_event(
                trace_id=trace_id,
                action=action,
                phase="post",
                payload={
                    "account": account,
                    "status": "error",
                    "original_message_id": request.id,
                },
                error="forward_email returned None",
            )
            raise HTTPException(
                status_code=500, detail=f"Failed to forward email (trace_id={trace_id})"
            )

    except HTTPException:
        raise
    except Exception as e:
        await ingest_email_event(
            trace_id=trace_id,
            action=action,
            phase="post",
            payload={
                "account": account,
                "status": "error",
                "original_message_id": request.id,
            },
            error=str(e),
        )
        logger.error(f"[{trace_id}] Email forward failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"{str(e)} (trace_id={trace_id})")


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "EMA-INTE-005",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["api.auth", "core.schemas", "memory.ingestion"],
    "tags": [
        "api",
        "api-gateway",
        "async",
        "auth",
        "debugging",
        "endpoint",
        "event-driven",
        "integration",
        "logging",
        "messaging",
    ],
    "keywords": [
        "account",
        "action",
        "agent",
        "draft",
        "email",
        "emails",
        "endpoints",
        "event",
    ],
    "business_value": "Provides router components including QueryRequest, GetRequest, DraftRequest",
    "last_modified": "2026-01-14T13:21:46Z",
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
