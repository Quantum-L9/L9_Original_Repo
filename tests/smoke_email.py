#!/usr/bin/env python3
"""
L9 Email Routes Smoke Test
===========================

Verifies that email routes properly ingest events to memory.

This test:
1. Mocks the GmailClient to avoid real API calls
2. Calls email endpoints
3. Verifies memory ingestion was called with correct trace_id

Usage:
    python tests/smoke_email.py

Requirements:
    - Memory system must be importable (no DB connection needed)
    - Email agent router must be importable
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Smoke Email",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-14T12:23:43Z",
    "updated_at": "2026-01-07T13:35:58Z",
    "layer": "operations",
    "domain": "tests",
    "module_name": "smoke_email",
    "type": "test",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Gmail API", "PostgreSQL"],
        "memory_layers": ["working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import asyncio
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import structlog

# Ensure repo root is in path
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))


class MockGmailClient:
    """Mock Gmail client for testing."""

    def __init__(self):
        self.service = MagicMock()

    def list_messages(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        """Mock list_messages - returns fake results."""
        return [
            {"id": "msg_1", "subject": "Test Email 1", "from": "test@example.com"},
            {"id": "msg_2", "subject": "Test Email 2", "from": "test2@example.com"},
        ]

    def get_message(self, message_id: str) -> dict[str, Any]:
        """Mock get_message - returns fake message."""
        return {
            "id": message_id,
            "from": "test@example.com",
            "to": "me@example.com",
            "subject": "Test Subject",
            "date": "2025-01-01",
            "body_plain": "Test body content",
            "attachments": [],
        }

    def draft_email(self, to: str, subject: str, body: str, attachments=None) -> str:
        """Mock draft_email - returns fake draft ID."""
        return "draft_123"

    def send_email(
        self, to: str, subject: str, body: str, attachments=None
    ) -> dict[str, Any]:
        """Mock send_email - returns fake result."""
        return {"message_id": "sent_123", "thread_id": "thread_123"}

    def reply_to_email(self, message_id: str, body: str) -> dict[str, Any]:
        """Mock reply_to_email - returns fake result."""
        return {"message_id": "reply_123", "thread_id": "thread_123"}

    def forward_email(self, message_id: str, to: str, body: str = "") -> dict[str, Any]:
        """Mock forward_email - returns fake result."""
        return {"message_id": "forward_123", "thread_id": "thread_123"}


class IngestTracker:
    """Tracks calls to ingest_packet for verification."""

    def __init__(self):
        self.calls: list[dict[str, Any]] = []

    async def mock_ingest(self, packet_in):
        """Mock ingest_packet that records calls."""
        self.calls.append(
            {
                "packet_type": packet_in.packet_type,
                "payload": packet_in.payload,
                "metadata": packet_in.metadata,
            }
        )

    def find_by_trace_id(self, trace_id: str) -> list[dict[str, Any]]:
        """Find all ingested packets with a specific trace_id."""
        return [
            c
            for c in self.calls
            if c.get("payload", {}).get("trace_id") == trace_id
            or c.get("metadata", {}).get("trace_id") == trace_id
        ]

    def find_by_action(self, action: str) -> list[dict[str, Any]]:
        """Find all ingested packets with a specific action."""
        return [c for c in self.calls if c.get("payload", {}).get("action") == action]

    def clear(self):
        """Clear recorded calls."""
        self.calls = []


async def test_email_query_ingestion():
    """Test that /email/query ingests pre and post events."""
    try:
        from email_agent.router import QueryRequest, query_emails

        tracker = IngestTracker()

        with patch("memory.ingestion.ingest_packet", tracker.mock_ingest):
            with patch("email_agent.gmail_client.GmailClient", MockGmailClient):
                # Make request
                request = QueryRequest(query="from:test", max_results=5)
                result = await query_emails(request)

                # Verify response has trace_id
                assert "trace_id" in result, "Response missing trace_id"
                trace_id = result["trace_id"]

                # Verify ingestion calls
                action_calls = tracker.find_by_action("email.query")
                assert len(action_calls) == 2, (
                    f"Expected 2 ingestion calls, got {len(action_calls)}"
                )

                # Verify pre and post phases
                phases = [c["payload"]["phase"] for c in action_calls]
                assert "pre" in phases, "Missing pre-action ingestion"
                assert "post" in phases, "Missing post-action ingestion"

                # Verify trace_id consistency
                trace_calls = tracker.find_by_trace_id(trace_id)
                assert len(trace_calls) == 2, (
                    "Trace ID not consistent across ingestions"
                )

                return True, ""

        return False, "Test did not complete"
    except (ImportError, ModuleNotFoundError) as e:
        if "asyncpg" in str(e) or "psycopg" in str(e):
            return True, "skipped (DB drivers not installed)"
        raise


async def test_email_get_ingestion():
    """Test that /email/get ingests pre and post events."""
    try:
        from email_agent.router import GetRequest, get_email

        tracker = IngestTracker()

        with patch("memory.ingestion.ingest_packet", tracker.mock_ingest):
            with patch("email_agent.gmail_client.GmailClient", MockGmailClient):
                request = GetRequest(id="msg_test_123")
                result = await get_email(request)

                assert "trace_id" in result
                result["trace_id"]

                action_calls = tracker.find_by_action("email.get")
                assert len(action_calls) == 2

                phases = [c["payload"]["phase"] for c in action_calls]
                assert "pre" in phases
                assert "post" in phases

                # Verify message_id is in payload
                pre_call = next(
                    c for c in action_calls if c["payload"]["phase"] == "pre"
                )
                assert pre_call["payload"]["message_id"] == "msg_test_123"

                return True, ""

        return False, "Test did not complete"
    except (ImportError, ModuleNotFoundError) as e:
        if "asyncpg" in str(e) or "psycopg" in str(e):
            return True, "skipped (DB drivers not installed)"
        raise


async def test_email_draft_ingestion():
    """Test that /email/draft ingests pre and post events."""
    try:
        from email_agent.router import DraftRequest, draft_email

        tracker = IngestTracker()

        with patch("memory.ingestion.ingest_packet", tracker.mock_ingest):
            with patch("email_agent.gmail_client.GmailClient", MockGmailClient):
                request = DraftRequest(
                    to="recipient@example.com",
                    subject="Test Subject",
                    body="Test body content",
                )
                result = await draft_email(request)

                assert "trace_id" in result
                assert result["status"] == "success"
                assert "draft_id" in result

                action_calls = tracker.find_by_action("email.draft")
                assert len(action_calls) == 2

                # Verify sensitive content is NOT in payload (only length)
                pre_call = next(
                    c for c in action_calls if c["payload"]["phase"] == "pre"
                )
                assert "body" not in pre_call["payload"], (
                    "Body content should not be ingested"
                )
                assert "body_length" in pre_call["payload"], (
                    "Body length should be ingested"
                )

                return True, ""

        return False, "Test did not complete"
    except (ImportError, ModuleNotFoundError) as e:
        if "asyncpg" in str(e) or "psycopg" in str(e):
            return True, "skipped (DB drivers not installed)"
        raise


async def test_email_send_ingestion():
    """Test that /email/send ingests pre and post events."""
    try:
        from email_agent.router import SendRequest, send_email

        tracker = IngestTracker()

        with patch("memory.ingestion.ingest_packet", tracker.mock_ingest):
            with patch("email_agent.gmail_client.GmailClient", MockGmailClient):
                request = SendRequest(
                    to="recipient@example.com",
                    subject="Test Subject",
                    body="Test body content",
                )
                result = await send_email(request)

                assert "trace_id" in result
                assert result["status"] == "success"

                action_calls = tracker.find_by_action("email.send")
                assert len(action_calls) == 2

                post_call = next(
                    c for c in action_calls if c["payload"]["phase"] == "post"
                )
                assert post_call["payload"]["status"] == "success"
                assert post_call["payload"]["send_mode"] == "direct"

                return True, ""

        return False, "Test did not complete"
    except (ImportError, ModuleNotFoundError) as e:
        if "asyncpg" in str(e) or "psycopg" in str(e):
            return True, "skipped (DB drivers not installed)"
        raise


async def test_email_reply_ingestion():
    """Test that /email/reply ingests pre and post events."""
    try:
        from email_agent.router import ReplyRequest, reply_email

        tracker = IngestTracker()

        with patch("memory.ingestion.ingest_packet", tracker.mock_ingest):
            with patch("email_agent.gmail_client.GmailClient", MockGmailClient):
                request = ReplyRequest(id="msg_original", body="Reply content")
                result = await reply_email(request)

                assert "trace_id" in result
                assert result["status"] == "success"

                action_calls = tracker.find_by_action("email.reply")
                assert len(action_calls) == 2

                pre_call = next(
                    c for c in action_calls if c["payload"]["phase"] == "pre"
                )
                assert pre_call["payload"]["original_message_id"] == "msg_original"

                return True, ""

        return False, "Test did not complete"
    except (ImportError, ModuleNotFoundError) as e:
        if "asyncpg" in str(e) or "psycopg" in str(e):
            return True, "skipped (DB drivers not installed)"
        raise


async def test_email_forward_ingestion():
    """Test that /email/forward ingests pre and post events."""
    try:
        from email_agent.router import ForwardRequest, forward_email

        tracker = IngestTracker()

        with patch("memory.ingestion.ingest_packet", tracker.mock_ingest):
            with patch("email_agent.gmail_client.GmailClient", MockGmailClient):
                request = ForwardRequest(
                    id="msg_to_forward",
                    to="forward@example.com",
                    body="FYI",
                )
                result = await forward_email(request)

                assert "trace_id" in result
                assert result["status"] == "success"

                action_calls = tracker.find_by_action("email.forward")
                assert len(action_calls) == 2

                post_call = next(
                    c for c in action_calls if c["payload"]["phase"] == "post"
                )
                assert post_call["payload"]["to"] == "forward@example.com"

                return True, ""

        return False, "Test did not complete"
    except (ImportError, ModuleNotFoundError) as e:
        if "asyncpg" in str(e) or "psycopg" in str(e):
            return True, "skipped (DB drivers not installed)"
        raise


async def test_ingestion_fail_loud():
    """Test that ingestion failure causes HTTP 500."""
    try:
        from fastapi import HTTPException

        from email_agent.router import QueryRequest, query_emails

        async def failing_ingest(packet_in):
            raise Exception("Simulated ingestion failure")

        with patch("memory.ingestion.ingest_packet", failing_ingest):
            with patch("email_agent.gmail_client.GmailClient", MockGmailClient):
                request = QueryRequest(query="test", max_results=5)

                try:
                    await query_emails(request)
                    return False, "Should have raised HTTPException"
                except HTTPException as e:
                    assert e.status_code == 500
                    assert "Memory ingestion failed" in e.detail
                    assert "trace_id=" in e.detail
                    return True, ""
                except Exception as e:
                    return False, f"Wrong exception type: {type(e).__name__}: {e}"

        return False, "Test did not complete"
    except (ImportError, ModuleNotFoundError) as e:
        if "asyncpg" in str(e) or "psycopg" in str(e):
            return True, "skipped (DB drivers not installed)"
        raise


async def run_all_tests():
    """Run all email smoke tests."""
    import logging

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logger = structlog.get_logger(__name__)

    tests = [
        ("email_query_ingestion", test_email_query_ingestion),
        ("email_get_ingestion", test_email_get_ingestion),
        ("email_draft_ingestion", test_email_draft_ingestion),
        ("email_send_ingestion", test_email_send_ingestion),
        ("email_reply_ingestion", test_email_reply_ingestion),
        ("email_forward_ingestion", test_email_forward_ingestion),
        ("ingestion_fail_loud", test_ingestion_fail_loud),
    ]

    passed = 0
    failed = 0

    logger.info("=" * 60)
    logger.info("L9 EMAIL ROUTES SMOKE TEST")
    logger.info("=" * 60)

    for name, test_fn in tests:
        try:
            success, err = await test_fn()
            if success:
                logger.info(f"PASS: {name}")
                passed += 1
            else:
                logger.error(f"FAIL: {name} - {err}")
                failed += 1
        except Exception as e:
            logger.error(f"FAIL: {name} - {type(e).__name__}: {e}")
            failed += 1

    logger.info("=" * 60)
    logger.info(f"PASSED: {passed}")
    logger.info(f"FAILED: {failed}")

    if failed == 0:
        logger.info("\n" + "=" * 60)
        logger.info("ALL EMAIL SMOKE TESTS PASSED")
        logger.info("=" * 60)
        return 0
    logger.info("\n" + "=" * 60)
    logger.error("EMAIL SMOKE TESTS FAILED - SEE ERRORS ABOVE")
    logger.info("=" * 60)
    return 1


def main():
    return asyncio.run(run_all_tests())


if __name__ == "__main__":
    sys.exit(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TES-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "async",
        "client",
        "event-driven",
        "filesystem",
        "logging",
        "messaging",
        "mocking",
        "operations",
        "test",
    ],
    "keywords": [
        "action",
        "all",
        "clear",
        "client",
        "draft",
        "email",
        "fail",
        "failing",
    ],
    "business_value": "1. Mocks the GmailClient to avoid real API calls 2. Calls email endpoints 3. Verifies memory ingestion was called with correct trace_id python tests/smoke_email.py Memory system must be importable (no",
    "last_modified": "2026-01-07T13:35:58Z",
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
