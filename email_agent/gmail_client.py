"""
Gmail API Client
================

Full-featured Gmail API wrapper with message parsing, attachment handling, and MIME support.
Supports multi-account mode (igor, l) with backward compatibility.

Version: 2.0.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Gmail Client",
    "module_version": "2.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-14T12:48:58Z",
    "updated_at": "2026-01-14T16:23:18Z",
    "layer": "integration",
    "domain": "email_integration",
    "module_name": "gmail_client",
    "type": "adapter",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Gmail API"],
        "memory_layers": [],
        "imported_by": ["_archived.legacy_slack.webhook_slack", "email_agent.__init__", "email_agent.client", "email_agent.router", "email_agent.triage", "tests.email_agent.test_email_router"],
    },
}
# ============================================================================

import os
import base64
import structlog
import re
from typing import Dict, Any, List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.utils import parseaddr

from email_agent.config import ensure_dirs

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from email_agent.credentials import load_tokens
    from email_agent.config import (
        ATTACHMENTS_DIR,
        SCOPES,
        ensure_dirs,
        get_account_config,
        GMAIL_ACCOUNT,
    )
    from email_agent.parser import (
        parse_headers,
        parse_body,
        parse_attachments,
        html_to_text,
    )

    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False
    structlog.get_logger(__name__).warning("Gmail API libraries not available")

logger = structlog.get_logger(__name__)

# Ensure legacy directories exist
ensure_dirs()


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove path components
    filename = os.path.basename(filename)
    # Remove/replace unsafe characters
    filename = re.sub(r"[^\w\s\-_\.]", "_", filename)
    # Limit length
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[: 200 - len(ext)] + ext
    return filename


class GmailClient:
    """Gmail API client wrapper with multi-account support."""

    def __init__(self, account: Optional[str] = None):
        """
        Initialize Gmail client.

        Args:
            account: Account name ("igor" or "l").
                    If None, uses legacy single-account mode.
        """
        if not GMAIL_AVAILABLE:
            raise RuntimeError("Gmail API libraries not available")

        self.account = account
        self.service = None
        self.attachments_dir = ATTACHMENTS_DIR  # Default

        if account:
            config = get_account_config(account)
            self.email = config.email
            self.attachments_dir = config.attachments_dir
            # Ensure account directories exist
            ensure_dirs(account)
            logger.info(f"GmailClient initialized for account: {account} ({config.email})")
        else:
            self.email = GMAIL_ACCOUNT
            # Ensure legacy directories exist
            ensure_dirs()
            logger.warning("GmailClient in legacy mode (no account specified)")

        self._authenticate()

    def _authenticate(self):
        """Authenticate with Gmail API using stored tokens."""
        credentials = load_tokens(self.account)
        if not credentials:
            account_label = self.account or "legacy"
            raise RuntimeError(
                f"No Gmail tokens found for account '{account_label}'. "
                f"Run: python -m email_agent.oauth_server --account {self.account or ''}\n"
                "Then visit: http://localhost:8080/oauth/start"
            )

        self.service = build("gmail", "v1", credentials=credentials)
        account_label = self.account or "legacy"
        logger.info(f"Gmail API authenticated (account={account_label})")

    def list_messages(self, query: str = "", limit: int = 20) -> List[Dict[str, Any]]:
        """
        List messages matching query.

        Args:
            query: Gmail search query (e.g., "from:lawyer has:attachment")
            limit: Maximum number of results

        Returns:
            List of message summaries with id, from, subject, date, snippet
        """
        try:
            results = (
                self.service.users()
                .messages()
                .list(userId="me", q=query, maxResults=limit)
                .execute()
            )

            messages = results.get("messages", [])
            message_list = []

            for msg in messages:
                try:
                    message = (
                        self.service.users()
                        .messages()
                        .get(
                            userId="me",
                            id=msg["id"],
                            format="metadata",
                            metadataHeaders=["From", "Subject", "Date"],
                        )
                        .execute()
                    )

                    headers = {
                        h["name"]: h["value"]
                        for h in message.get("payload", {}).get("headers", [])
                    }

                    message_list.append(
                        {
                            "id": msg["id"],
                            "from": headers.get("From", ""),
                            "subject": headers.get("Subject", ""),
                            "date": headers.get("Date", ""),
                            "snippet": message.get("snippet", ""),
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to get message {msg['id']}: {e}")

            logger.info(f"Listed {len(message_list)} messages for query: {query}")
            return message_list

        except HttpError as e:
            logger.error(f"Gmail API error listing messages: {e}")
            return []

    def get_message(self, msg_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full message content with parsed body and attachments.

        Args:
            msg_id: Gmail message ID

        Returns:
            Dictionary with:
            - id, from, to, subject, date, snippet
            - body_plain: Plain text body
            - body_html: HTML body (if available)
            - attachments: List of attachment dicts with name, path, size
        """
        try:
            message = (
                self.service.users()
                .messages()
                .get(userId="me", id=msg_id, format="full")
                .execute()
            )

            payload = message.get("payload", {})
            headers = {h["name"]: h["value"] for h in payload.get("headers", [])}

            # Decode headers
            from_addr = headers.get("From", "")
            to_addr = headers.get("To", "")
            subject = headers.get("Subject", "")
            date = headers.get("Date", "")

            # Extract body and attachments
            body_plain = ""
            body_html = ""
            attachments = []

            def extract_part(part: Dict[str, Any], parent_path: str = ""):
                """Recursively extract body and attachments from message parts."""
                nonlocal body_plain, body_html

                mime_type = part.get("mimeType", "")
                body_data = part.get("body", {})

                # Handle text parts
                if mime_type == "text/plain":
                    data = body_data.get("data")
                    if data:
                        try:
                            body_plain = base64.urlsafe_b64decode(data).decode(
                                "utf-8", errors="ignore"
                            )
                        except Exception as e:
                            logger.warning(f"Failed to decode plain text: {e}")

                elif mime_type == "text/html":
                    data = body_data.get("data")
                    if data:
                        try:
                            body_html = base64.urlsafe_b64decode(data).decode(
                                "utf-8", errors="ignore"
                            )
                        except Exception as e:
                            logger.warning(f"Failed to decode HTML: {e}")

                # Handle attachments
                elif (
                    mime_type.startswith("application/")
                    or mime_type.startswith("image/")
                    or mime_type.startswith("video/")
                ):
                    attachment_id = body_data.get("attachmentId")
                    filename = None

                    # Get filename from headers
                    for header in part.get("headers", []):
                        if header["name"].lower() == "content-disposition":
                            disposition = header["value"]
                            # Extract filename from Content-Disposition header
                            filename_match = re.search(
                                r'filename="?([^"]+)"?', disposition, re.IGNORECASE
                            )
                            if filename_match:
                                filename = filename_match.group(1)

                    if attachment_id and filename:
                        # Download attachment
                        try:
                            attachment = (
                                self.service.users()
                                .messages()
                                .attachments()
                                .get(userId="me", messageId=msg_id, id=attachment_id)
                                .execute()
                            )

                            attachment_data = base64.urlsafe_b64decode(
                                attachment["data"]
                            )
                            safe_filename = sanitize_filename(filename)
                            attachment_path = (
                                self.attachments_dir / f"{msg_id}_{safe_filename}"
                            )

                            with open(attachment_path, "wb") as f:
                                f.write(attachment_data)

                            attachments.append(
                                {
                                    "name": filename,
                                    "path": str(attachment_path),
                                    "size": len(attachment_data),
                                    "mime_type": mime_type,
                                }
                            )

                            logger.info(
                                f"Extracted attachment: {filename} ({len(attachment_data)} bytes)"
                            )
                        except Exception as e:
                            logger.warning(
                                f"Failed to extract attachment {filename}: {e}"
                            )

                # Recursively process nested parts
                for nested_part in part.get("parts", []):
                    extract_part(nested_part, parent_path)

            # Process payload
            if "parts" in payload:
                for part in payload["parts"]:
                    extract_part(part)
            else:
                # Single part message
                extract_part(payload)

            # Get thread_id
            thread_id = message.get("threadId", "")

            result = {
                "id": msg_id,
                "thread_id": thread_id,
                "from": from_addr,
                "to": to_addr,
                "subject": subject,
                "date": date,
                "snippet": message.get("snippet", ""),
                "text": body_plain,  # Use "text" as per spec
                "html": body_html,  # Use "html" as per spec
                "body_plain": body_plain,  # Backward compatibility
                "body_html": body_html,  # Backward compatibility
                "attachments": [
                    att["path"] for att in attachments
                ],  # Return local paths as per spec
                "attachments_full": attachments,  # Full attachment info for reference
            }

            logger.info(f"Retrieved message {msg_id}: {subject}")
            return result

        except HttpError as e:
            logger.error(f"Gmail API error getting message {msg_id}: {e}")
            return None

    def send_email(
        self, to: str, subject: str, body: str, attachments: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Send email with optional attachments.

        Args:
            to: Recipient email address(es) - comma-separated for multiple
            subject: Email subject
            body: Email body (plain text or HTML)
            attachments: Optional list of file paths to attach

        Returns:
            Dictionary with message_id and thread_id, or None if failed
        """
        try:
            # Create message
            if attachments:
                message = MIMEMultipart()
                message["to"] = to
                message["subject"] = subject

                # Add body
                # Detect if body is HTML
                if "<html" in body.lower() or "<body" in body.lower():
                    msg_body = MIMEText(body, "html")
                else:
                    msg_body = MIMEText(body, "plain")
                message.attach(msg_body)

                # Add attachments
                for file_path in attachments:
                    if os.path.exists(file_path):
                        with open(file_path, "rb") as f:
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                "Content-Disposition",
                                f'attachment; filename="{os.path.basename(file_path)}"',
                            )
                            message.attach(part)
            else:
                # Simple text message
                message = MIMEText(body)
                message["to"] = to
                message["subject"] = subject

            # Encode and send
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

            sent_message = (
                self.service.users()
                .messages()
                .send(userId="me", body={"raw": raw_message})
                .execute()
            )

            result = {
                "message_id": sent_message.get("id"),
                "thread_id": sent_message.get("threadId"),
            }

            logger.info(f"Sent email to {to}: {subject}")
            return result

        except HttpError as e:
            logger.error(f"Gmail API error sending email: {e}")
            return None

    def draft_email(
        self, to: str, subject: str, body: str, attachments: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Create email draft with optional attachments.

        Args:
            to: Recipient email address(es)
            subject: Email subject
            body: Email body
            attachments: Optional list of file paths to attach

        Returns:
            Draft ID or None if failed
        """
        try:
            # Create message (same as send_email)
            if attachments:
                message = MIMEMultipart()
                message["to"] = to
                message["subject"] = subject

                if "<html" in body.lower() or "<body" in body.lower():
                    msg_body = MIMEText(body, "html")
                else:
                    msg_body = MIMEText(body, "plain")
                message.attach(msg_body)

                for file_path in attachments:
                    if os.path.exists(file_path):
                        with open(file_path, "rb") as f:
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                "Content-Disposition",
                                f'attachment; filename="{os.path.basename(file_path)}"',
                            )
                            message.attach(part)
            else:
                message = MIMEText(body)
                message["to"] = to
                message["subject"] = subject

            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

            # Create draft
            draft = (
                self.service.users()
                .drafts()
                .create(userId="me", body={"message": {"raw": raw_message}})
                .execute()
            )

            draft_id = draft["id"]
            logger.info(f"Created draft {draft_id} to {to}: {subject}")
            return draft_id

        except HttpError as e:
            logger.error(f"Gmail API error creating draft: {e}")
            return None

    def reply_to_email(self, msg_id: str, body: str) -> Optional[Dict[str, Any]]:
        """
        Reply to an email message.

        Args:
            msg_id: Original message ID to reply to
            body: Reply body

        Returns:
            Dictionary with message_id and thread_id, or None if failed
        """
        try:
            # Get original message
            original = self.get_message(msg_id)
            if not original:
                logger.error(f"Original message {msg_id} not found")
                return None

            # Extract reply-to address (use From of original)
            from_addr = original.get("from", "")
            # Parse email address
            _, reply_to = parseaddr(from_addr)

            if not reply_to:
                logger.error(f"Could not extract reply-to address from: {from_addr}")
                return None

            # Get subject and add Re: prefix if not present
            subject = original.get("subject", "")
            if not subject.startswith("Re:"):
                subject = f"Re: {subject}"

            # Create reply message
            message = MIMEText(body)
            message["to"] = reply_to
            message["subject"] = subject
            message["In-Reply-To"] = msg_id

            # Get thread ID from original
            original_msg = (
                self.service.users()
                .messages()
                .get(userId="me", id=msg_id, format="metadata")
                .execute()
            )
            thread_id = original_msg.get("threadId")

            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

            # Send reply
            sent_message = (
                self.service.users()
                .messages()
                .send(userId="me", body={"raw": raw_message, "threadId": thread_id})
                .execute()
            )

            result = {
                "message_id": sent_message.get("id"),
                "thread_id": sent_message.get("threadId"),
            }

            logger.info(f"Replied to message {msg_id}")
            return result

        except HttpError as e:
            logger.error(f"Gmail API error replying to email: {e}")
            return None

    def forward_email(
        self, msg_id: str, to: str, body: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Forward an email message.

        Args:
            msg_id: Original message ID to forward
            to: Recipient email address(es)
            body: Optional forward message body

        Returns:
            Dictionary with message_id and thread_id, or None if failed
        """
        try:
            # Get original message
            original = self.get_message(msg_id)
            if not original:
                logger.error(f"Original message {msg_id} not found")
                return None

            # Get original subject and add Fwd: prefix if not present
            subject = original.get("subject", "")
            if not subject.startswith("Fwd:"):
                subject = f"Fwd: {subject}"

            # Build forward body
            forward_body = "\n\n---------- Forwarded message ----------\n"
            forward_body += f"From: {original.get('from', 'Unknown')}\n"
            forward_body += f"Date: {original.get('date', 'Unknown')}\n"
            forward_body += f"Subject: {original.get('subject', 'No subject')}\n"
            forward_body += f"To: {original.get('to', 'Unknown')}\n\n"

            # Add original body
            original_body = original.get("body_plain", original.get("body_html", ""))
            if original_body:
                forward_body += original_body

            # Add user's forward message if provided
            if body:
                forward_body = f"{body}\n\n{forward_body}"

            # Create forward message
            message = MIMEText(forward_body)
            message["to"] = to
            message["subject"] = subject

            # Get thread ID from original (optional, for threading)
            try:
                original_msg = (
                    self.service.users()
                    .messages()
                    .get(userId="me", id=msg_id, format="metadata")
                    .execute()
                )
                thread_id = original_msg.get("threadId")
            except Exception:
                thread_id = None

            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

            # Send forward
            send_body = {"raw": raw_message}
            if thread_id:
                send_body["threadId"] = thread_id

            sent_message = (
                self.service.users()
                .messages()
                .send(userId="me", body=send_body)
                .execute()
            )

            result = {
                "message_id": sent_message.get("id"),
                "thread_id": sent_message.get("threadId"),
            }

            logger.info(f"Forwarded message {msg_id} to {to}")
            return result

        except HttpError as e:
            logger.error(f"Gmail API error forwarding email: {e}")
            return None

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "EMA-INTE-002",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["adapter", "api", "auth", "client", "email-integration", "integration", "logging", "messaging", "streaming"],
    "keywords": ["client", "draft", "email", "extract", "filename", "forward", "gmail", "messages"],
    "business_value": "Implements GmailClient for gmail client functionality",
    "last_modified": "2026-01-14T16:23:18Z",
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
