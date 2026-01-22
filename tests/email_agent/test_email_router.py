"""
L9 Email Router Tests
=====================

Comprehensive tests for email routing with multi-account support and auth.
No external services required - uses mocks.

Version: 2.0.0

Test Coverage:
- Auth enforcement (401 without API key)
- Account routing (igor, l, invalid)
- Memory ingestion (pre/post events)
- Backward compatibility (legacy GmailClient)
- Request validation
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add project root to path FIRST - before any other imports
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Set test API key before importing anything
os.environ["L9_EXECUTOR_API_KEY"] = "test-api-key-12345"

# Now import the modules
from fastapi import FastAPI
from fastapi.testclient import TestClient

from email_agent.config import VALID_ACCOUNTS
from email_agent.router import GetRequest, QueryRequest, router

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def app():
    """Create FastAPI app with email router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Valid auth headers."""
    return {"Authorization": "Bearer test-api-key-12345"}


@pytest.fixture
def mock_gmail_client():
    """Mock GmailClient that returns empty results."""
    with patch("email_agent.gmail_client.GmailClient") as mock:
        mock_client = MagicMock()
        mock_client.list_messages.return_value = []
        mock_client.get_message.return_value = {
            "id": "test-id",
            "from": "test@example.com",
            "subject": "Test",
            "attachments": [],
        }
        mock_client.draft_email.return_value = "draft-123"
        mock_client.send_email.return_value = {
            "message_id": "msg-123",
            "thread_id": "thread-123",
        }
        mock_client.reply_to_email.return_value = {
            "message_id": "msg-456",
            "thread_id": "thread-123",
        }
        mock_client.forward_email.return_value = {
            "message_id": "msg-789",
            "thread_id": "thread-456",
        }
        mock.return_value = mock_client
        yield mock


@pytest.fixture
def mock_memory_ingest():
    """Mock memory ingestion."""
    with patch("email_agent.router.ingest_email_event", new_callable=AsyncMock) as mock:
        yield mock


# =============================================================================
# Test: Auth Enforcement
# =============================================================================


class TestAuthEnforcement:
    """All endpoints require API key."""

    @pytest.mark.parametrize(
        "endpoint",
        [
            "/email/igor/query",
            "/email/igor/get",
            "/email/igor/draft",
            "/email/igor/send",
            "/email/igor/reply",
            "/email/igor/forward",
            "/email/l/query",
            "/email/l/get",
        ],
    )
    def test_no_auth_returns_401(self, client, endpoint):
        """Request without API key returns 401."""
        response = client.post(endpoint, json={"query": "test"})
        assert (
            response.status_code == 401
        ), f"Expected 401 for {endpoint}, got {response.status_code}"

    @pytest.mark.parametrize(
        "endpoint",
        [
            "/email/igor/query",
            "/email/l/query",
        ],
    )
    def test_wrong_api_key_returns_401(self, client, endpoint):
        """Request with wrong API key returns 401."""
        response = client.post(
            endpoint,
            json={"query": "test"},
            headers={"Authorization": "Bearer wrong-key"},
        )
        assert response.status_code == 401

    def test_valid_api_key_passes_auth(
        self, client, auth_headers, mock_gmail_client, mock_memory_ingest
    ):
        """Request with valid API key passes auth check."""
        response = client.post(
            "/email/igor/query",
            json={"query": "test", "max_results": 5},
            headers=auth_headers,
        )
        # Should not be 401 - either 200 or some other error
        assert response.status_code != 401


# =============================================================================
# Test: Account Routing
# =============================================================================


class TestAccountRouting:
    """Account path parameter validation."""

    def test_igor_account_accepted(
        self, client, auth_headers, mock_gmail_client, mock_memory_ingest
    ):
        """Igor account is valid."""
        response = client.post(
            "/email/igor/query",
            json={"query": "is:unread", "max_results": 5},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["account"] == "igor"

    def test_l_account_accepted(
        self, client, auth_headers, mock_gmail_client, mock_memory_ingest
    ):
        """L account is valid."""
        response = client.post(
            "/email/l/query",
            json={"query": "is:unread", "max_results": 5},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["account"] == "l"

    def test_invalid_account_returns_422(self, client, auth_headers):
        """Invalid account name returns 422 (path validation fails)."""
        response = client.post(
            "/email/unknown/query",
            json={"query": "test"},
            headers=auth_headers,
        )
        # FastAPI path validation returns 422
        assert response.status_code == 422

    def test_gmail_client_receives_account(
        self, client, auth_headers, mock_gmail_client, mock_memory_ingest
    ):
        """GmailClient is initialized with correct account."""
        client.post(
            "/email/igor/query",
            json={"query": "test"},
            headers=auth_headers,
        )
        mock_gmail_client.assert_called_with(account="igor")

        client.post(
            "/email/l/query",
            json={"query": "test"},
            headers=auth_headers,
        )
        mock_gmail_client.assert_called_with(account="l")


# =============================================================================
# Test: Memory Ingestion
# =============================================================================


class TestMemoryIngestion:
    """Pre/post events ingested to memory."""

    @pytest.mark.asyncio
    async def test_query_ingests_pre_post(
        self, client, auth_headers, mock_gmail_client, mock_memory_ingest
    ):
        """Query endpoint ingests pre and post events."""
        response = client.post(
            "/email/igor/query",
            json={"query": "test", "max_results": 5},
            headers=auth_headers,
        )

        assert response.status_code == 200

        # Should have 2 calls: pre and post
        assert mock_memory_ingest.call_count == 2

        # Check pre-action call
        pre_call = mock_memory_ingest.call_args_list[0]
        assert pre_call.kwargs["phase"] == "pre"
        assert pre_call.kwargs["action"] == "email.igor.query"
        assert pre_call.kwargs["payload"]["account"] == "igor"

        # Check post-action call
        post_call = mock_memory_ingest.call_args_list[1]
        assert post_call.kwargs["phase"] == "post"
        assert post_call.kwargs["action"] == "email.igor.query"
        assert post_call.kwargs["payload"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_action_includes_account(
        self, client, auth_headers, mock_gmail_client, mock_memory_ingest
    ):
        """Action name includes account for tracing."""
        client.post(
            "/email/l/query",
            json={"query": "test"},
            headers=auth_headers,
        )

        pre_call = mock_memory_ingest.call_args_list[0]
        assert "email.l.query" in pre_call.kwargs["action"]


# =============================================================================
# Test: Endpoint Functionality
# =============================================================================


class TestEndpoints:
    """Test each endpoint's basic functionality."""

    def test_query_returns_messages(
        self, client, auth_headers, mock_gmail_client, mock_memory_ingest
    ):
        """Query endpoint returns messages array."""
        mock_gmail_client.return_value.list_messages.return_value = [
            {"id": "1", "subject": "Test 1"},
            {"id": "2", "subject": "Test 2"},
        ]

        response = client.post(
            "/email/igor/query",
            json={"query": "is:unread", "max_results": 10},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert "trace_id" in data
        assert len(data["messages"]) == 2

    def test_get_returns_message(
        self, client, auth_headers, mock_gmail_client, mock_memory_ingest
    ):
        """Get endpoint returns full message."""
        response = client.post(
            "/email/igor/get",
            json={"id": "msg-123"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "trace_id" in data

    def test_draft_returns_draft_id(
        self, client, auth_headers, mock_gmail_client, mock_memory_ingest
    ):
        """Draft endpoint returns draft ID."""
        response = client.post(
            "/email/igor/draft",
            json={"to": "test@example.com", "subject": "Test", "body": "Hello"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["draft_id"] == "draft-123"
        assert data["status"] == "success"

    def test_send_returns_message_id(
        self, client, auth_headers, mock_gmail_client, mock_memory_ingest
    ):
        """Send endpoint returns message ID."""
        response = client.post(
            "/email/igor/send",
            json={"to": "test@example.com", "subject": "Test", "body": "Hello"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "message_id" in data

    def test_send_requires_fields_for_direct(
        self, client, auth_headers, mock_gmail_client, mock_memory_ingest
    ):
        """Direct send requires to, subject, body."""
        response = client.post(
            "/email/igor/send",
            json={"to": "test@example.com"},  # Missing subject and body
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "required" in response.json()["detail"].lower()

    def test_reply_returns_success(
        self, client, auth_headers, mock_gmail_client, mock_memory_ingest
    ):
        """Reply endpoint returns success."""
        response = client.post(
            "/email/igor/reply",
            json={"id": "msg-123", "body": "Thanks!"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_forward_returns_success(
        self, client, auth_headers, mock_gmail_client, mock_memory_ingest
    ):
        """Forward endpoint returns success."""
        response = client.post(
            "/email/igor/forward",
            json={"id": "msg-123", "to": "other@example.com", "body": "FYI"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


# =============================================================================
# Test: Request Validation
# =============================================================================


class TestRequestValidation:
    """Request model validation."""

    def test_query_request_defaults(self):
        """QueryRequest has correct defaults."""
        request = QueryRequest()
        assert request.query == ""
        assert request.max_results == 10

    def test_query_request_custom(self):
        """QueryRequest accepts custom values."""
        request = QueryRequest(query="from:test@example.com", max_results=50)
        assert request.query == "from:test@example.com"
        assert request.max_results == 50

    def test_get_request_requires_id(self):
        """GetRequest requires id field."""
        with pytest.raises(Exception):  # Pydantic validation error
            GetRequest()


# =============================================================================
# Test: Backward Compatibility
# =============================================================================


class TestBackwardCompat:
    """Legacy GmailClient() still works."""

    def test_gmail_client_no_account_uses_legacy(self):
        """GmailClient with no account param uses legacy mode."""
        with patch("email_agent.gmail_client.load_tokens") as mock_load:
            mock_load.return_value = MagicMock()
            with patch("email_agent.gmail_client.build"):
                from email_agent.gmail_client import GmailClient

                client = GmailClient()  # No account param

        # Should call load_tokens with None (legacy mode)
        mock_load.assert_called_with(None)

    def test_gmail_client_with_account(self):
        """GmailClient with account param uses account-specific credentials."""
        with patch("email_agent.gmail_client.load_tokens") as mock_load:
            mock_load.return_value = MagicMock()
            with patch("email_agent.gmail_client.build"):
                from email_agent.gmail_client import GmailClient

                client = GmailClient(account="igor")

        mock_load.assert_called_with("igor")


# =============================================================================
# Test: Config
# =============================================================================


class TestConfig:
    """Config module tests."""

    def test_valid_accounts_defined(self):
        """VALID_ACCOUNTS contains expected accounts."""
        assert "igor" in VALID_ACCOUNTS
        assert "l" in VALID_ACCOUNTS

    def test_get_account_config_valid(self):
        """get_account_config returns config for valid accounts."""
        from email_agent.config import get_account_config

        config = get_account_config("igor")
        assert config.name == "igor"
        assert config.tokens_file.name == "tokens.json"

    def test_get_account_config_invalid(self):
        """get_account_config raises for invalid accounts."""
        from email_agent.config import get_account_config

        with pytest.raises(ValueError) as exc_info:
            get_account_config("invalid")

        assert "Unknown account" in str(exc_info.value)
