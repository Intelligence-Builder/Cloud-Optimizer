"""Unit tests for Rate Limiter module.

Issue #162: Penetration testing preparation.
Tests rate limiting and DDoS protection functionality.
"""

from datetime import timedelta
from unittest.mock import MagicMock

import pytest

from cloud_optimizer.security.rate_limiter import (
    InMemoryRateLimiter,
    RateLimitConfig,
    RateLimitExceeded,
    get_client_identifier,
    get_rate_limit_key,
)


class TestInMemoryRateLimiter:
    """Test InMemoryRateLimiter class."""

    def test_allows_requests_under_limit(self) -> None:
        """Test that requests under the limit are allowed."""
        limiter = InMemoryRateLimiter()
        key = "test_key"
        limit = 5
        window = timedelta(minutes=1)

        # Make 5 requests (should all be allowed)
        for i in range(5):
            is_allowed, remaining = limiter.is_allowed(key, limit, window)
            assert is_allowed is True
            assert remaining == limit - i - 1

    def test_blocks_requests_over_limit(self) -> None:
        """Test that requests over the limit are blocked."""
        limiter = InMemoryRateLimiter()
        key = "test_key"
        limit = 3
        window = timedelta(minutes=1)

        # Make 3 requests (should all be allowed)
        for _ in range(3):
            is_allowed, _ = limiter.is_allowed(key, limit, window)
            assert is_allowed is True

        # 4th request should be blocked
        is_allowed, remaining = limiter.is_allowed(key, limit, window)
        assert is_allowed is False
        assert remaining == 0

    def test_different_keys_have_separate_limits(self) -> None:
        """Test that different keys have separate rate limits."""
        limiter = InMemoryRateLimiter()
        limit = 2
        window = timedelta(minutes=1)

        # Exhaust limit for key1
        for _ in range(2):
            limiter.is_allowed("key1", limit, window)

        # key2 should still be allowed
        is_allowed, _ = limiter.is_allowed("key2", limit, window)
        assert is_allowed is True

        # key1 should be blocked
        is_allowed, _ = limiter.is_allowed("key1", limit, window)
        assert is_allowed is False

    def test_remaining_count_decreases(self) -> None:
        """Test that remaining count decreases with each request."""
        limiter = InMemoryRateLimiter()
        key = "test_key"
        limit = 5
        window = timedelta(minutes=1)

        _, remaining = limiter.is_allowed(key, limit, window)
        assert remaining == 4

        _, remaining = limiter.is_allowed(key, limit, window)
        assert remaining == 3

        _, remaining = limiter.is_allowed(key, limit, window)
        assert remaining == 2


class TestRateLimitConfig:
    """Test RateLimitConfig class."""

    def test_auth_limit_is_restrictive(self) -> None:
        """Test that authentication endpoints have stricter limits."""
        assert RateLimitConfig.AUTH_LIMIT < RateLimitConfig.API_LIMIT
        assert RateLimitConfig.AUTH_LIMIT == 5

    def test_api_limit_is_reasonable(self) -> None:
        """Test that API limit is reasonable for normal usage."""
        assert RateLimitConfig.API_LIMIT == 100
        assert RateLimitConfig.API_WINDOW == timedelta(minutes=1)

    def test_global_limit_is_higher(self) -> None:
        """Test that global limit is higher than per-user limit."""
        assert RateLimitConfig.GLOBAL_LIMIT > RateLimitConfig.API_LIMIT
        assert RateLimitConfig.GLOBAL_LIMIT == 1000

    def test_health_limit_is_high(self) -> None:
        """Test that health check endpoints have very high limits."""
        assert RateLimitConfig.HEALTH_LIMIT > RateLimitConfig.GLOBAL_LIMIT


class TestRateLimitExceeded:
    """Test RateLimitExceeded exception."""

    def test_exception_has_correct_status_code(self) -> None:
        """Test that exception has 429 status code."""
        exc = RateLimitExceeded()
        assert exc.status_code == 429

    def test_exception_has_retry_after_header(self) -> None:
        """Test that exception includes Retry-After header."""
        exc = RateLimitExceeded(retry_after=120)
        assert exc.headers is not None
        assert exc.headers["Retry-After"] == "120"

    def test_exception_has_default_message(self) -> None:
        """Test that exception has default error message."""
        exc = RateLimitExceeded()
        assert exc.detail == "Rate limit exceeded"

    def test_exception_accepts_custom_message(self) -> None:
        """Test that exception accepts custom error message."""
        exc = RateLimitExceeded(detail="Custom rate limit message")
        assert exc.detail == "Custom rate limit message"


class TestGetClientIdentifier:
    """Test get_client_identifier function."""

    def test_uses_forwarded_for_header(self) -> None:
        """Test that X-Forwarded-For header is used when present."""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "1.2.3.4, 5.6.7.8"}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        result = get_client_identifier(request)
        assert result == "1.2.3.4"

    def test_uses_client_ip_when_no_forwarded_header(self) -> None:
        """Test that client IP is used when no X-Forwarded-For."""
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "192.168.1.100"

        result = get_client_identifier(request)
        assert result == "192.168.1.100"

    def test_returns_unknown_when_no_client(self) -> None:
        """Test that 'unknown' is returned when no client info."""
        request = MagicMock()
        request.headers = {}
        request.client = None

        result = get_client_identifier(request)
        assert result == "unknown"

    def test_strips_whitespace_from_forwarded_ip(self) -> None:
        """Test that whitespace is stripped from forwarded IP."""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "  10.0.0.1  , 10.0.0.2"}
        request.client = None

        result = get_client_identifier(request)
        assert result == "10.0.0.1"


class TestGetRateLimitKey:
    """Test get_rate_limit_key function."""

    def test_auth_endpoints_use_ip(self) -> None:
        """Test that auth endpoints use IP in the key."""
        request = MagicMock()
        request.url.path = "/api/v1/auth/login"
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "1.2.3.4"

        key = get_rate_limit_key(request)
        assert key.startswith("auth:")
        assert "1.2.3.4" in key

    def test_health_endpoints_use_ip(self) -> None:
        """Test that health endpoints use IP in the key."""
        request = MagicMock()
        request.url.path = "/health"
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "1.2.3.4"

        key = get_rate_limit_key(request)
        assert key.startswith("health:")

    def test_api_endpoints_use_user_id_when_provided(self) -> None:
        """Test that API endpoints use user ID when available."""
        request = MagicMock()
        request.url.path = "/api/v1/findings"
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "1.2.3.4"

        key = get_rate_limit_key(request, user_id="user-123")
        assert key == "api:user-123"

    def test_api_endpoints_use_ip_when_no_user(self) -> None:
        """Test that API endpoints use IP when no user ID."""
        request = MagicMock()
        request.url.path = "/api/v1/findings"
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "1.2.3.4"

        key = get_rate_limit_key(request)
        assert key == "api:1.2.3.4"


class TestRateLimitIntegration:
    """Integration tests for rate limiting."""

    def test_brute_force_protection(self) -> None:
        """Test that brute force attacks are blocked."""
        limiter = InMemoryRateLimiter()
        attacker_ip = "attacker.ip"
        window = timedelta(minutes=1)

        # Simulate 5 login attempts (auth limit)
        for i in range(5):
            is_allowed, _ = limiter.is_allowed(
                f"auth:{attacker_ip}",
                RateLimitConfig.AUTH_LIMIT,
                window,
            )
            assert is_allowed is True

        # 6th attempt should be blocked
        is_allowed, _ = limiter.is_allowed(
            f"auth:{attacker_ip}",
            RateLimitConfig.AUTH_LIMIT,
            window,
        )
        assert is_allowed is False

    def test_normal_user_not_affected(self) -> None:
        """Test that normal users are not rate limited."""
        limiter = InMemoryRateLimiter()
        user_id = "normal-user"
        window = timedelta(minutes=1)

        # Make 50 requests (half of API limit)
        for _ in range(50):
            is_allowed, remaining = limiter.is_allowed(
                f"api:{user_id}",
                RateLimitConfig.API_LIMIT,
                window,
            )
            assert is_allowed is True
            assert remaining >= 49

    def test_different_categories_independent(self) -> None:
        """Test that auth and API limits are independent."""
        limiter = InMemoryRateLimiter()
        ip = "test.ip"
        window = timedelta(minutes=1)

        # Exhaust auth limit
        for _ in range(RateLimitConfig.AUTH_LIMIT):
            limiter.is_allowed(f"auth:{ip}", RateLimitConfig.AUTH_LIMIT, window)

        # API requests should still work
        is_allowed, _ = limiter.is_allowed(
            f"api:{ip}",
            RateLimitConfig.API_LIMIT,
            window,
        )
        assert is_allowed is True
