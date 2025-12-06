"""Security module for Cloud Optimizer.

Issue #162: Penetration testing preparation.
Contains security-related components including rate limiting and DDoS protection.
"""

from cloud_optimizer.security.rate_limiter import (
    InMemoryRateLimiter,
    RateLimitConfig,
    RateLimitExceeded,
    RateLimitMiddleware,
    get_client_identifier,
    get_rate_limit_key,
    get_rate_limiter,
    rate_limit,
)

__all__ = [
    "InMemoryRateLimiter",
    "RateLimitConfig",
    "RateLimitExceeded",
    "RateLimitMiddleware",
    "get_client_identifier",
    "get_rate_limit_key",
    "get_rate_limiter",
    "rate_limit",
]
