"""
VitaFlow API - Rate Limiting Middleware.

Prevents API abuse with configurable per-route rate limits.
Uses SlowAPI with Redis backend for distributed rate limiting.
"""

import logging
from typing import Callable, Optional

from fastapi import Request, HTTPException, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from settings import settings


logger = logging.getLogger(__name__)


def get_user_identifier(request: Request) -> str:
    """
    Get rate limit key identifier from request.
    
    Uses user ID from JWT if authenticated, otherwise IP address.
    
    Args:
        request: FastAPI request object.
    
    Returns:
        str: User ID or IP address for rate limiting.
    """
    # Try to get user ID from request state (set by auth middleware)
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    
    # Fall back to IP address
    return get_remote_address(request)


# Create limiter with Redis storage
limiter = Limiter(
    key_func=get_user_identifier,
    storage_uri=settings.REDIS_URL,
    default_limits=["60/minute"],
    enabled=settings.ENV != "testing"  # Disable rate limiting in test environment
)


# Rate limit decorators for different tiers
def auth_limit() -> str:
    """Rate limit for auth endpoints (login/register)."""
    return "5/minute"


def ai_free_limit() -> str:
    """Rate limit for AI endpoints on free tier."""
    # Higher limit in testing/development for easier testing
    if settings.ENV in ("testing", "development"):
        return "1000/hour"
    return "10/hour"


def ai_pro_limit() -> str:
    """Rate limit for AI endpoints on pro tier."""
    return "100/hour"


def general_limit() -> str:
    """Default rate limit for general API endpoints."""
    return "60/minute"


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> None:
    """
    Custom handler for rate limit exceeded errors.
    
    Args:
        request: FastAPI request object.
        exc: RateLimitExceeded exception.
    
    Raises:
        HTTPException: 429 Too Many Requests.
    """
    retry_after = getattr(exc, "retry_after", 60)
    logger.warning(f"Rate limit exceeded for {get_user_identifier(request)}")
    
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "error": "Rate limit exceeded",
            "retry_after_seconds": retry_after,
            "message": "Please slow down your requests"
        },
        headers={"Retry-After": str(retry_after)}
    )
