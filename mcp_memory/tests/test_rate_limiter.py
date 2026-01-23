import pytest
from src.rate_limiter import RateLimiter


@pytest.mark.asyncio
async def test_rate_limit_blocks_after_limit() -> None:
    limiter = RateLimiter(
        request_limit=2,
        request_window_seconds=60,
        failed_auth_limit=3,
        failed_auth_block_seconds=300,
    )
    now = 1000.0
    ip = "127.0.0.1"

    assert await limiter.is_rate_limited(ip, now=now) is False
    await limiter.record_request(ip, now=now)
    assert await limiter.is_rate_limited(ip, now=now) is False
    await limiter.record_request(ip, now=now + 1)
    assert await limiter.is_rate_limited(ip, now=now + 1) is True


@pytest.mark.asyncio
async def test_failed_auth_block_expires() -> None:
    limiter = RateLimiter(
        request_limit=10,
        request_window_seconds=60,
        failed_auth_limit=2,
        failed_auth_block_seconds=30,
    )
    now = 2000.0
    ip = "10.0.0.1"

    await limiter.record_failed_auth(ip, now=now)
    assert await limiter.is_auth_blocked(ip, now=now) is False
    await limiter.record_failed_auth(ip, now=now + 1)
    assert await limiter.is_auth_blocked(ip, now=now + 1) is True

    assert await limiter.is_auth_blocked(ip, now=now + 40) is False
