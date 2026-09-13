
import os
from collections.abc import Sequence
from dataclasses import dataclass

from fastapi import Header, HTTPException, Request

from core.decorators import must_stay_async

# Rate limiting for auth
from runtime.auth_rate_limiter import get_auth_rate_limiter

EXECUTOR_API_KEY_L = os.environ.get("L9_EXECUTOR_API_KEY_L")
EXECUTOR_API_KEY_C = os.environ.get("L9_EXECUTOR_API_KEY_C") or os.environ.get(
    "L9_EXECUTOR_API_KEY"
)


@dataclass(frozen=True)
class CallerIdentity:
    """
    Represents the identity of a caller in the authentication system, including their scope and source information.

    Args:
        caller_id: Unique identifier of the caller.
        allowed_scopes: List of scopes permitted for the caller.
        creator: Entity that created the caller identity.
        source: Origin of the caller request.

    Returns:
        An instance of CallerIdentity containing caller details.

    Raises:
        None
    """

    caller_id: str
    allowed_scopes: Sequence[str]
    creator: str
    source: str


def verify_api_key(authorization: str = Header(None)) -> CallerIdentity:
    """
    Verify API key and return caller identity.

    Note: This is a sync function for FastAPI dependency injection.
    For rate-limited auth, use verify_api_key_with_rate_limit instead.
    """
    if not EXECUTOR_API_KEY_L and not EXECUTOR_API_KEY_C:
        raise HTTPException(
            status_code=500,
            detail="Executor key not configured",
        )
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization.replace("Bearer ", "")
    if EXECUTOR_API_KEY_L and token == EXECUTOR_API_KEY_L:
        return CallerIdentity(
            caller_id="L",
            allowed_scopes=("developer", "global", "l-private"),
            creator="L-CTO",
            source="l9-api",
        )
    if EXECUTOR_API_KEY_C and token == EXECUTOR_API_KEY_C:
        return CallerIdentity(
            caller_id="C",
            allowed_scopes=("developer", "global"),
            creator="Cursor-IDE",
            source="cursor",
        )
    raise HTTPException(status_code=401, detail="Unauthorized")


@must_stay_async("callers use await")
async def verify_api_key_with_rate_limit(
    request: Request,
    authorization: str = Header(None),
) -> CallerIdentity:
    """
    Verify API key with rate limiting protection.

    Prevents brute force attacks by:
    - Tracking failed attempts per IP
    - Locking out after 5 failed attempts for 15 minutes
    - Logging all auth attempts for audit

    Use this for sensitive endpoints instead of verify_api_key.
    """
    # Get client IP
    client_ip = _get_client_ip(request)

    # Get rate limiter
    limiter = get_auth_rate_limiter()

    # Check if allowed before attempting auth
    result = await limiter.check_allowed(ip_address=client_ip)

    if not result.allowed:
        raise HTTPException(
            status_code=429,
            detail=result.reason or "Too many requests",
            headers={"Retry-After": str(result.retry_after_seconds or 900)},
        )

    # Check key configuration
    if not EXECUTOR_API_KEY_L and not EXECUTOR_API_KEY_C:
        raise HTTPException(
            status_code=500,
            detail="Executor key not configured",
        )

    # Check authorization header
    if not authorization or not authorization.startswith("Bearer "):
        await limiter.record_failure(ip_address=client_ip)
        raise HTTPException(status_code=401, detail="Unauthorized")

    token = authorization.replace("Bearer ", "")

    # Verify token
    if EXECUTOR_API_KEY_L and token == EXECUTOR_API_KEY_L:
        await limiter.record_success(ip_address=client_ip, username="L")
        return CallerIdentity(
            caller_id="L",
            allowed_scopes=("developer", "global", "l-private"),
            creator="L-CTO",
            source="l9-api",
        )

    if EXECUTOR_API_KEY_C and token == EXECUTOR_API_KEY_C:
        await limiter.record_success(ip_address=client_ip, username="C")
        return CallerIdentity(
            caller_id="C",
            allowed_scopes=("developer", "global"),
            creator="Cursor-IDE",
            source="cursor",
        )

    # Invalid token - record failure
    await limiter.record_failure(ip_address=client_ip)
    raise HTTPException(status_code=401, detail="Unauthorized")


def _get_client_ip(request: Request) -> str:
    """
    Extract client IP from request, handling proxies.

    Checks X-Forwarded-For and X-Real-IP headers for proxied requests.
    """
    # Check forwarded headers (reverse proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take first IP (client) from comma-separated list
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Direct connection
    if request.client:
        return request.client.host

    return "unknown"


# Runtime execution trace - updated automatically on every execution
