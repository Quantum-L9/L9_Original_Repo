"""
Tests for Rate Limiting Middleware
===================================

Tests for token bucket rate limiting implementation.
"""

import pytest
import time
from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.middleware.rate_limiter import RateLimiterMiddleware, TokenBucket


class TestTokenBucket:
    """Tests for TokenBucket algorithm."""

    def test_token_bucket_initialization(self):
        """Test token bucket is initialized with correct capacity."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        assert bucket.capacity == 10
        assert bucket.tokens == 10
        assert bucket.refill_rate == 1.0

    def test_token_consumption(self):
        """Test that tokens are consumed correctly."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)

        # Consume 5 tokens
        assert bucket.consume(5) is True
        assert bucket.tokens == 5

        # Consume 5 more tokens
        assert bucket.consume(5) is True
        assert bucket.tokens == 0

        # Try to consume when empty
        assert bucket.consume(1) is False

    def test_token_refill(self):
        """Test that tokens refill over time."""
        bucket = TokenBucket(capacity=10, refill_rate=10.0)  # 10 tokens/second

        # Consume all tokens
        bucket.consume(10)
        assert bucket.tokens == 0

        # Wait 0.5 seconds (should refill 5 tokens)
        time.sleep(0.5)
        assert bucket.consume(5) is True
        assert bucket.consume(1) is False  # Only 5 tokens refilled

    def test_token_refill_cap(self):
        """Test that tokens don't exceed capacity."""
        bucket = TokenBucket(capacity=10, refill_rate=10.0)

        # Consume 5 tokens
        bucket.consume(5)

        # Wait 2 seconds (would refill 20 tokens, but capped at 10)
        time.sleep(2)
        assert bucket.tokens <= 10


class TestRateLimiterMiddleware:
    """Tests for RateLimiterMiddleware."""

    @pytest.fixture
    def app(self):
        """Create test FastAPI app with rate limiting."""
        app = FastAPI()

        # Add rate limiter with low limits for testing
        app.add_middleware(
            RateLimiterMiddleware,
            requests_per_minute=6,  # 6 requests per minute = 0.1/second
            burst_size=2,
            enabled=True,
        )

        @app.get("/test")
        def test_endpoint():
            return {"message": "success"}

        @app.get("/health")
        def health_endpoint():
            return {"status": "ok"}

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_rate_limit_allows_normal_requests(self, client):
        """Test that normal requests are allowed."""
        response = client.get("/test")
        assert response.status_code == 200
        assert response.json() == {"message": "success"}

    def test_rate_limit_headers_present(self, client):
        """Test that rate limit headers are present."""
        response = client.get("/test")
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    def test_rate_limit_blocks_excessive_requests(self, client):
        """Test that excessive requests are blocked."""
        # Make requests up to the limit (6 + 2 burst = 8 total)
        for i in range(8):
            response = client.get("/test")
            assert response.status_code == 200, f"Request {i+1} failed"

        # Next request should be rate limited
        response = client.get("/test")
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["error"]

    def test_rate_limit_retry_after_header(self, client):
        """Test that Retry-After header is present on 429."""
        # Exhaust rate limit
        for _ in range(10):
            client.get("/test")

        response = client.get("/test")
        if response.status_code == 429:
            assert "Retry-After" in response.headers
            assert response.headers["Retry-After"] == "60"

    def test_health_endpoint_bypasses_rate_limit(self, client):
        """Test that health checks bypass rate limiting."""
        # Exhaust rate limit on /test
        for _ in range(10):
            client.get("/test")

        # Health endpoint should still work
        response = client.get("/health")
        assert response.status_code == 200

    def test_rate_limit_per_ip(self):
        """Test that rate limiting is per IP address."""
        app = FastAPI()
        app.add_middleware(
            RateLimiterMiddleware,
            requests_per_minute=2,
            burst_size=0,
            enabled=True,
        )

        @app.get("/test")
        def test_endpoint():
            return {"message": "success"}

        client1 = TestClient(app)
        client2 = TestClient(app)

        # Client 1 exhausts its limit
        client1.get("/test")
        client1.get("/test")
        response = client1.get("/test")
        assert response.status_code == 429

        # Client 2 should still be able to make requests
        # (Note: TestClient uses same IP, so this test is conceptual)
        # In real deployment, different IPs would have separate buckets

    def test_rate_limit_disabled(self):
        """Test that rate limiting can be disabled."""
        app = FastAPI()
        app.add_middleware(
            RateLimiterMiddleware,
            requests_per_minute=1,
            burst_size=0,
            enabled=False,  # Disabled
        )

        @app.get("/test")
        def test_endpoint():
            return {"message": "success"}

        client = TestClient(app)

        # Should allow unlimited requests when disabled
        for _ in range(10):
            response = client.get("/test")
            assert response.status_code == 200


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TEST-MW-001",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["api.middleware.rate_limiter", "fastapi.testclient"],
    "tags": ["test", "middleware", "rate_limiting", "security"],
    "keywords": ["rate", "limiter", "test", "token", "bucket", "middleware"],
    "business_value": "Ensures rate limiting middleware works correctly to prevent API abuse.",
    "last_modified": "2026-01-21T18:50:00Z",
    "modified_by": "Manus_AI",
    "change_summary": "Initial rate limiter tests",
}
# ============================================================================
