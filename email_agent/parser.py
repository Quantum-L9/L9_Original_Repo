"""
Email Parser
============

Helpers for parsing Gmail message payloads, extracting headers, body, and attachments.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Parser",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-14T12:48:58Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "integration",
    "domain": "email_integration",
    "module_name": "parser",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["email_agent.gmail_client"],
    },
}
# ============================================================================

import base64
import re
from email.header import decode_header
from typing import Any

import structlog

try:
    import html  # noqa: F401 — used conditionally (html.unescape)
    from html.parser import HTMLParser

    HTML_AVAILABLE = True
except ImportError:
    HTML_AVAILABLE = False

logger = structlog.get_logger(__name__)


def parse_headers(payload: dict[str, Any]) -> dict[str, str]:
    """
    Parse email headers from Gmail payload.

    Args:
        payload: Gmail message payload dictionary

    Returns:
        Dictionary of header name -> decoded value
    """
    headers = {}
    header_list = payload.get("headers", [])

    for header in header_list:
        name = header.get("name", "").lower()
        value = header.get("value", "")

        # Decode header value if encoded
        try:
            decoded_parts = decode_header(value)
            decoded_value = ""
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        decoded_value += part.decode(encoding)
                    else:
                        decoded_value += part.decode("utf-8", errors="ignore")
                else:
                    decoded_value += part
            headers[name] = decoded_value
        except Exception as e:
            logger.warning(f"Failed to decode header {name}: {e}")
            headers[name] = value

    return headers


def parse_body(payload: dict[str, Any]) -> dict[str, str]:
    """
    Parse email body from Gmail payload.
    Extracts both plain text and HTML versions.

    Args:
        payload: Gmail message payload dictionary

    Returns:
        Dictionary with 'text' and 'html' keys
    """
    text_body = ""
    html_body = ""

    def extract_from_part(part: dict[str, Any]) -> None:
        """Recursively extract body from message parts."""
        nonlocal text_body, html_body

        mime_type = part.get("mimeType", "")
        body_data = part.get("body", {})
        data = body_data.get("data")

        if data:
            try:
                decoded = base64.urlsafe_b64decode(data).decode(
                    "utf-8", errors="ignore"
                )

                if mime_type == "text/plain":
                    if not text_body:  # Prefer first plain text part
                        text_body = decoded
                elif mime_type == "text/html":
                    if not html_body:  # Prefer first HTML part
                        html_body = decoded
            except Exception as e:
                logger.warning(f"Failed to decode body part: {e}")

        # Recursively process nested parts
        for nested_part in part.get("parts", []):
            extract_from_part(nested_part)

    # Process payload
    if "parts" in payload:
        for part in payload["parts"]:
            extract_from_part(part)
    else:
        # Single part message
        extract_from_part(payload)

    return {"text": text_body, "html": html_body}


def parse_attachments(
    payload: dict[str, Any], msg_id: str, attachments_dir
) -> list[dict[str, Any]]:
    """
    Parse attachments from Gmail payload.

    Args:
        payload: Gmail message payload dictionary
        msg_id: Message ID for filename prefix
        attachments_dir: Directory to save attachments

    Returns:
        List of attachment dictionaries with name, path, size, mime_type
    """
    attachments = []

    def extract_from_part(part: dict[str, Any], parent_path: str = "") -> None:
        """Recursively extract attachments from message parts."""
        mime_type = part.get("mimeType", "")
        body_data = part.get("body", {})
        attachment_id = body_data.get("attachmentId")

        # Check if this is an attachment
        is_attachment = False
        filename = None

        # Check headers for attachment info
        for header in part.get("headers", []):
            header_name = header.get("name", "").lower()
            header_value = header.get("value", "")

            if header_name == "content-disposition":
                if "attachment" in header_value.lower():
                    is_attachment = True
                    # Extract filename
                    filename_match = re.search(
                        r'filename="?([^"]+)"?', header_value, re.IGNORECASE
                    )
                    if filename_match:
                        filename = filename_match.group(1)

            elif header_name == "content-type" and not is_attachment:
                # Check if it's an attachment by MIME type
                if (
                    mime_type.startswith("application/")
                    or mime_type.startswith("image/")
                    or mime_type.startswith("video/")
                    or mime_type.startswith("audio/")
                ):
                    is_attachment = True
                    # Try to extract filename from Content-Type
                    filename_match = re.search(
                        r'name="?([^"]+)"?', header_value, re.IGNORECASE
                    )
                    if filename_match:
                        filename = filename_match.group(1)

        # If attachment found and has ID
        if is_attachment and attachment_id and filename:
            attachments.append(
                {
                    "attachment_id": attachment_id,
                    "filename": filename,
                    "mime_type": mime_type,
                    "size": body_data.get("size", 0),
                }
            )

        # Recursively process nested parts
        for nested_part in part.get("parts", []):
            extract_from_part(nested_part, parent_path)

    # Process payload
    if "parts" in payload:
        for part in payload["parts"]:
            extract_from_part(part)
    else:
        # Single part message
        extract_from_part(payload)

    return attachments


def html_to_text(html: str) -> str:
    """
    Convert HTML email body to plain text.

    Args:
        html: HTML string

    Returns:
        Plain text version
    """
    if not HTML_AVAILABLE:
        # Simple regex-based extraction
        # Remove script and style tags
        html = re.sub(
            r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE
        )
        html = re.sub(
            r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE
        )

        # Replace common HTML entities
        html = html.replace("&nbsp;", " ")
        html = html.replace("&amp;", "&")
        html = html.replace("&lt;", "<")
        html = html.replace("&gt;", ">")
        html = html.replace("&quot;", '"')

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", html)

        # Decode HTML entities
        try:
            import html as html_module

            text = html_module.unescape(text)
        except Exception:
            logger.debug("email_parser.html_unescape_failed")

        # Clean up whitespace
        text = re.sub(r"\n\s*\n", "\n\n", text)
        return text.strip()

    try:
        # Use html.parser for better extraction
        class HTMLToTextParser(HTMLParser):
            """
            Parses HTML content to extract plain text, handling script and style tags appropriately for email payload processing.


            Returns:
                The extracted plain text from the HTML content.
            """

            def __init__(self) -> None:
                """Initialize parser state."""
                super().__init__()
                self.text = []
                self.in_script = False
                self.in_style = False

            def handle_starttag(self, tag, attrs) -> None:
                """Handle opening HTML tags."""
                if tag.lower() in ["script", "style"]:
                    if tag.lower() == "script":
                        self.in_script = True
                    else:
                        self.in_style = True
                elif tag.lower() == "br":
                    self.text.append("\n")
                elif tag.lower() in ["p", "div", "li"]:
                    if self.text and not self.text[-1].endswith("\n"):
                        self.text.append("\n")

            def handle_endtag(self, tag) -> None:
                """Handle closing HTML tags."""
                if tag.lower() in ["script", "style"]:
                    if tag.lower() == "script":
                        self.in_script = False
                    else:
                        self.in_style = False
                elif tag.lower() in ["p", "div", "li"]:
                    if self.text and not self.text[-1].endswith("\n"):
                        self.text.append("\n")

            def handle_data(self, data) -> None:
                """Handle text content between tags."""
                if not self.in_script and not self.in_style:
                    self.text.append(data)

            def get_text(self) -> str:
                """Return extracted plain text."""
                text = "".join(self.text)
                # Clean up whitespace
                text = re.sub(r"\n\s*\n", "\n\n", text)
                return text.strip()

        parser = HTMLToTextParser()
        parser.feed(html)
        return parser.get_text()

    except Exception as e:
        logger.warning(f"Failed to parse HTML: {e}")
        # Fallback to simple extraction
        text = re.sub(r"<[^>]+>", "", html)
        text = html.unescape(text) if HTML_AVAILABLE else text
        return text.strip()


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "EMA-INTE-004",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "email-integration",
        "integration",
        "logging",
        "messaging",
        "parser",
        "utility",
    ],
    "keywords": [
        "attachments",
        "endtag",
        "extract",
        "handle",
        "headers",
        "html",
        "parse",
        "parser",
    ],
    "business_value": "Implements HTMLToTextParser for parser functionality",
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
