"""
Slack File Handling Service
============================

Handles downloading, saving, and managing file attachments from Slack messages.

Features:
- Download files from Slack using Web API
- Save files to managed storage directory (~/.l9/slack_files/YYYY/MM/DD/)
- Create file artifact records for orchestrator
- Support for PDFs, images, audio, markdown, ZIP, DOCX

Version: 1.1.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Slack Files",
    "module_version": "1.1.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-14T12:48:58Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "services",
    "module_name": "slack_files",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API", "OpenAI API", "Slack API"],
        "memory_layers": [],
        "imported_by": ["_archived.legacy_slack.webhook_slack", "memory.slack_ingest"],
    },
}
# ============================================================================

import os
import structlog
import httpx
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = structlog.get_logger(__name__)

# Configuration
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")

# Import centralized config
try:
    from config.settings import get_slack_files_dir

    SLACK_FILES_BASE_DIR = get_slack_files_dir()
except ImportError:
    # Fallback if config not available
    SLACK_FILES_BASE_DIR = os.path.expanduser("~/.l9/slack_files")
    Path(SLACK_FILES_BASE_DIR).mkdir(parents=True, exist_ok=True)


def download_file(
    file_id: str, file_url_private: str, filename: str, mimetype: Optional[str] = None
) -> bytes:
    """
    Download a file from Slack using the private URL.

    Args:
        file_id: Slack file ID
        file_url_private: Private download URL from files.info
        filename: Original filename
        mimetype: MIME type of the file (optional)

    Returns:
        File contents as bytes

    Raises:
        httpx.HTTPError: If download fails
        ValueError: If SLACK_BOT_TOKEN is not configured
    """
    if not SLACK_BOT_TOKEN:
        raise ValueError("SLACK_BOT_TOKEN not configured")

    logger.info(
        "[SlackFiles] Downloading file: id=%s, name=%s, type=%s",
        file_id,
        filename,
        mimetype or "unknown",
    )

    headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(file_url_private, headers=headers)
            response.raise_for_status()

            logger.info(
                "[SlackFiles] Downloaded file: id=%s, size=%d bytes",
                file_id,
                len(response.content),
            )

            return response.content

    except httpx.HTTPError as e:
        logger.error("[SlackFiles] Failed to download file %s: %s", file_id, e)
        raise


def save_to_disk(
    file_bytes: bytes,
    file_id: str,
    filename: str,
    mimetype: Optional[str] = None,
    created_timestamp: Optional[int] = None,
) -> str:
    """
    Save file bytes to disk in managed storage directory with date-based subfolders.

    Storage structure: ~/.l9/slack_files/YYYY/MM/DD/<safe_filename>

    Args:
        file_bytes: File contents as bytes
        file_id: Slack file ID (used in filename)
        filename: Original filename
        mimetype: MIME type (optional, used for extension detection)
        created_timestamp: Unix timestamp for file creation date (optional, uses current time if not provided)

    Returns:
        Absolute path to saved file

    Raises:
        OSError: If file cannot be written
    """
    # Determine date for subfolder structure
    if created_timestamp:
        file_date = datetime.fromtimestamp(created_timestamp)
    else:
        file_date = datetime.now()

    # Build date-based subfolder: YYYY/MM/DD
    year = file_date.strftime("%Y")
    month = file_date.strftime("%m")  # %m for month (01-12), not %M (minutes)
    day = file_date.strftime("%d")
    date_subfolder = Path(year) / month / day

    # Sanitize filename: remove path components and special chars
    safe_filename = os.path.basename(filename)
    # Replace spaces and special characters, keep extension
    name_parts = safe_filename.rsplit(".", 1)
    if len(name_parts) == 2:
        base_name, ext = name_parts
        safe_base = "".join(c if c.isalnum() or c in "._-" else "_" for c in base_name)
        safe_filename = f"{safe_base}.{ext}"
    else:
        safe_filename = "".join(
            c if c.isalnum() or c in "._-" else "_" for c in safe_filename
        )

    # Build storage path: <base_dir>/YYYY/MM/DD/<file_id>_<safe_filename>
    storage_filename = f"{file_id}_{safe_filename}"
    file_path = Path(SLACK_FILES_BASE_DIR) / date_subfolder / storage_filename

    # Ensure directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Write file
    try:
        file_path.write_bytes(file_bytes)

        absolute_path = str(file_path.resolve())

        # Log confirmation
        logger.info("[L9 Storage] Saved Slack file to: %s", absolute_path)
        logger.debug(
            "[SlackFiles] Saved file: id=%s, path=%s, size=%d bytes",
            file_id,
            absolute_path,
            len(file_bytes),
        )

        return absolute_path

    except OSError as e:
        logger.error("[SlackFiles] Failed to save file %s: %s", file_id, e)
        raise


def build_artifact_record(
    file_id: str,
    filename: str,
    file_path: str,
    mimetype: str,
    slack_url_private: Optional[str] = None,
    size_bytes: Optional[int] = None,
    additional_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a file artifact record for orchestrator consumption.

    Uses storage_key convention:
    {
        "storage_backend": "local",
        "storage_key": "<absolute_path>",
        "source": "slack",
        "slack_file_id": "<id>"
    }

    Args:
        file_id: Slack file ID
        filename: Original filename
        file_path: Absolute path to saved file
        mimetype: MIME type
        slack_url_private: Private Slack URL (optional)
        size_bytes: File size in bytes (optional)
        additional_metadata: Additional metadata to include (optional)

    Returns:
        File artifact dictionary with standard structure
    """
    # Ensure absolute path
    absolute_path = os.path.abspath(file_path)

    artifact = {
        "storage_backend": "local",
        "storage_key": absolute_path,
        "source": "slack",
        "slack_file_id": file_id,
        "id": file_id,
        "name": filename,
        "path": absolute_path,
        "type": mimetype,
        "slack_url": slack_url_private,
    }

    if size_bytes is not None:
        artifact["size_bytes"] = size_bytes

    if additional_metadata:
        artifact.update(additional_metadata)

    return artifact


def process_slack_file(file_id: str, file_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a Slack file: download, save, and create artifact record.

    This is the main entry point for processing a single file attachment.

    Args:
        file_id: Slack file ID
        file_info: File info dictionary from Slack API (files.info response)

    Returns:
        File artifact record dictionary

    Raises:
        ValueError: If required fields are missing
        httpx.HTTPError: If download fails
        OSError: If save fails
    """
    # Extract file metadata
    filename = file_info.get("name", f"file_{file_id}")
    mimetype = file_info.get("mimetype", "application/octet-stream")
    url_private = file_info.get("url_private")
    size_bytes = file_info.get("size")
    created_timestamp = file_info.get("created")  # Unix timestamp

    if not url_private:
        raise ValueError(f"Missing url_private for file {file_id}")

    # Download file
    file_bytes = download_file(
        file_id=file_id,
        file_url_private=url_private,
        filename=filename,
        mimetype=mimetype,
    )

    # Save to disk with date-based subfolder
    file_path = save_to_disk(
        file_bytes=file_bytes,
        file_id=file_id,
        filename=filename,
        mimetype=mimetype,
        created_timestamp=created_timestamp,
    )

    # Build artifact record
    artifact = build_artifact_record(
        file_id=file_id,
        filename=filename,
        file_path=file_path,
        mimetype=mimetype,
        slack_url_private=url_private,
        size_bytes=size_bytes or len(file_bytes),
        additional_metadata={
            "created_at": file_info.get("created"),
            "user_id": file_info.get("user"),
            "filetype": file_info.get("filetype"),
        },
    )

    # Enrich artifact based on mimetype
    try:
        # OCR for images
        if mimetype.startswith("image/"):
            try:
                from services.ocr_engine import ocr_image

                ocr_result = ocr_image(file_path)
                artifact["ocr"] = ocr_result
                logger.info(
                    f"[SlackFiles] OCR extracted {len(ocr_result.get('tokens', []))} tokens from {filename}"
                )
            except Exception as e:
                logger.warning(f"[SlackFiles] OCR failed for {filename}: {e}")

        # PDF extraction
        elif mimetype == "application/pdf":
            try:
                from services.pdf_engine import extract_pdf

                pdf_result = extract_pdf(file_path)
                artifact["pdf"] = pdf_result
                logger.info(
                    f"[SlackFiles] PDF extracted {len(pdf_result.get('pages', []))} pages from {filename}"
                )
            except Exception as e:
                logger.warning(
                    f"[SlackFiles] PDF extraction failed for {filename}: {e}"
                )

        # Audio transcription
        elif mimetype.startswith("audio/"):
            try:
                from openai import OpenAI

                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

                with open(file_path, "rb") as audio_file:
                    transcription = client.audio.transcriptions.create(
                        model="whisper-1", file=audio_file, response_format="text"
                    )

                artifact["transcription"] = {
                    "text": transcription,
                    "engine": "whisper-1",
                }
                logger.info(
                    f"[SlackFiles] Transcribed audio {filename} ({len(transcription)} chars)"
                )
            except Exception as e:
                logger.warning(
                    f"[SlackFiles] Audio transcription failed for {filename}: {e}"
                )

    except Exception as e:
        logger.error(f"[SlackFiles] Error enriching artifact: {e}", exc_info=True)
        # Continue even if enrichment fails

    logger.info(
        "[SlackFiles] Processed file artifact: id=%s, path=%s", file_id, file_path
    )

    return artifact


async def get_file_info(file_id: str) -> Dict[str, Any]:
    """
    Retrieve file metadata from Slack API using files.info (async).

    Args:
        file_id: Slack file ID

    Returns:
        File info dictionary from Slack API

    Raises:
        ValueError: If SLACK_BOT_TOKEN is not configured
        httpx.HTTPError: If API call fails
    """
    if not SLACK_BOT_TOKEN:
        raise ValueError("SLACK_BOT_TOKEN not configured")

    import httpx
    from api.slack_client import SlackAPIClient

    # Create async client for this call
    http_client = httpx.AsyncClient()
    slack_client = SlackAPIClient(bot_token=SLACK_BOT_TOKEN, http_client=http_client)

    try:
        response = await slack_client.get_file_info(file_id)
        file_info = response.get("file", {})
        logger.info(
            "[SlackFiles] Retrieved file info: id=%s, name=%s",
            file_id,
            file_info.get("name"),
        )
        return file_info
    except Exception as e:
        logger.error("[SlackFiles] Slack API error for file %s: %s", file_id, e)
        raise
    finally:
        await http_client.aclose()


async def process_file_attachments(files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Process multiple file attachments from a Slack message (async).

    Args:
        files: List of file dictionaries from Slack event (event["files"])

    Returns:
        List of file artifact records

    Note:
        Files that fail to process are logged but don't stop processing
        of other files. Returns partial results if some files fail.
    """
    artifacts = []

    for file_data in files:
        file_id = file_data.get("id")
        if not file_id:
            logger.warning("[SlackFiles] File missing ID, skipping")
            continue

        try:
            # Get full file info from Slack API (async)
            file_info = await get_file_info(file_id)

            # Process file: download, save, create artifact
            artifact = process_slack_file(file_id, file_info)
            artifacts.append(artifact)

        except Exception as e:
            logger.error(
                "[SlackFiles] Failed to process file %s: %s", file_id, e, exc_info=True
            )
            # Continue processing other files

    logger.info(
        "[SlackFiles] Processed %d/%d file attachments", len(artifacts), len(files)
    )

    return artifacts


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    # === IDENTITY ===
    "component_id": "SER-OPER-001",
    # === GOVERNANCE ===
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "security_classification": "internal",
    # === DEPENDENCIES ===
    "dependencies": ["api.slack_client"],
    # === OPERATIONAL ===
    "execution_mode": "on-demand",
    "timeout_seconds": 30,
    "performance_tier": "realtime",
    "retry_policy": "exponential",
    "circuit_breaker_enabled": True,
    "circuit_breaker_threshold": 5,
    # === OBSERVABILITY ===
    "monitoring_required": True,
    "logging_level": "info",
    "success_metrics": {
        "latency_p95_ms": 50,
        "throughput_ops_per_sec": 1000,
        "availability_percent": 99.99,
        "error_rate_percent": 0.01,
    },
    # === DISCOVERY ===
    "tags": [
        "api",
        "async",
        "auth",
        "debugging",
        "event-driven",
        "filesystem",
        "http-client",
        "llm",
        "logging",
        "messaging",
    ],
    "keywords": [
        "artifact",
        "attachments",
        "build",
        "disk",
        "download",
        "files",
        "orchestrator",
        "process",
    ],
    "business_value": "Handles downloading, saving, and managing file attachments from Slack messages. Download files from Slack using Web API Save files to managed storage directory (~/.l9/slack_files/YYYY/MM/DD/) Create f",
    # === CHANGE TRACKING ===
    "last_modified": "2026-01-17T23:47:56Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================

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
