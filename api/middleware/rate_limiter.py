"""
Rate Limiting Middleware for L9 API
====================================

Implements token bucket rate limiting to prevent abuse and DDoS attacks.

Usage:
    from api.middleware.rate_limiter import RateLimiterMiddleware
    app.add_middleware(RateLimiterMiddleware, requests_per_minute=60)
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Rate Limiter Middleware",
    "module_version": "1.0.0",
    "created_by": "Manus AI",
    "created_at": "2026-01-21T18:30:00Z",
    "updated_at": "2026-01-21T18:30:00Z",
    "layer": "api",
    "domain": "middleware",
    "module_name": "rate_limiter",
    "type": "middleware",
    "status": "active",
    "integrates_with": {
        "api_endpoints": ["all"],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["api.server"],
    },
}
# ============================================================================

import time
from collections import defaultdict
from typing import Dict
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = structlog.get_logger(__name__)


class TokenBucket:
    """Token bucket algorithm for rate limiting."""

    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.

        Args:
            capacity: Maximum number of tokens (requests) in the bucket
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()

    def consume(self, tokens: int = 1) -> bool:
        """
        Attempt to consume tokens from the bucket.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed, False if rate limit exceeded
        """
        # Refill tokens based on time elapsed
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        # Try to consume tokens
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using token bucket algorithm.

    Limits requests per client IP address to prevent abuse.
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        burst_size: int = 10,
        enabled: bool = True,
    ):
        """
        Initialize rate limiter middleware.

        Args:
            app: FastAPI application
            requests_per_minute: Maximum requests per minute per IP
            burst_size: Maximum burst size (extra tokens beyond rate)
            enabled: Whether rate limiting is enabled
        """
        super().__init__(app)
        self.enabled = enabled
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.refill_rate = requests_per_minute / 60.0  # tokens per second
        self.capacity = requests_per_minute + burst_size
        self.buckets: Dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(self.capacity, self.refill_rate)
        )

        logger.info(
            "rate_limiter.initialized",
            enabled=enabled,
            requests_per_minute=requests_per_minute,
            burst_size=burst_size,
        )

    async def dispatch(self, request: Request, call_next):
        """
        Process request and apply rate limiting.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware in chain

        Returns:
            HTTP response (429 if rate limit exceeded, otherwise normal response)
        """
        # Skip rate limiting if disabled
        if not self.enabled:
            return await call_next(request)

        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)

        # Get client IP (handle proxies)
        client_ip = self._get_client_ip(request)

        # Get or create token bucket for this IP
        bucket = self.buckets[client_ip]

        # Try to consume a token
        if not bucket.consume():
            logger.warning(
                "rate_limiter.limit_exceeded",
                client_ip=client_ip,
                path=request.url.path,
                method=request.method,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.requests_per_minute} requests per minute",
                    "retry_after": 60,
                },
                headers={"Retry-After": "60"},
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))
        response.headers["X-RateLimit-Reset"] = str(
            int(time.time() + (self.capacity - bucket.tokens) / self.refill_rate)
        )

        return response

    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP address from request.

        Handles X-Forwarded-For header for proxied requests.

        Args:
            request: HTTP request

        Returns:
            Client IP address
        """
        # Check X-Forwarded-For header (for proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header (for nginx)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct client IP
        if request.client:
            return request.client.host

        return "unknown"


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "API-MW-002",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["starlette.middleware.base"],
    "tags": ["api", "middleware", "rate_limiting", "security", "ddos_prevention"],
    "keywords": [
        "rate",
        "limiter",
        "middleware",
        "token",
        "bucket",
        "ddos",
        "abuse",
        "prevention",
    ],
    "business_value": "Prevents API abuse and DDoS attacks by limiting requests per client IP address using token bucket algorithm.",
    "last_modified": "2026-01-21T18:30:00Z",
    "modified_by": "Manus_AI",
    "change_summary": "Initial implementation of rate limiting middleware",
}
# ============================================================================
