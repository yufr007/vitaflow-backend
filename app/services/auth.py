"""
VitaFlow API - Authentication Service.

JWT token generation and password hashing utilities.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import logging

import bcrypt
from jose import jwt, JWTError

from settings import settings
from .cache import cache_service

logger = logging.getLogger(__name__)


# Maximum password length for bcrypt (72 bytes)
MAX_PASSWORD_BYTES = 72


def _prepare_password(password: str) -> bytes:
    """
    Prepare password for bcrypt hashing.
    
    Bcrypt only uses the first 72 bytes of any password.
    This function encodes and truncates to ensure consistent behavior.
    
    Args:
        password: Plain text password.
    
    Returns:
        bytes: UTF-8 encoded password, truncated to 72 bytes.
    """
    # Encode to UTF-8 bytes and truncate to 72 bytes
    return password.encode('utf-8')[:MAX_PASSWORD_BYTES]


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Note: Passwords are truncated to 72 bytes (bcrypt limit).
    
    Args:
        password: Plain text password to hash.
    
    Returns:
        str: Bcrypt hashed password.
    
    Example:
        >>> hashed = hash_password("mysecurepassword")
        >>> verify_password("mysecurepassword", hashed)
        True
    """
    password_bytes = _prepare_password(password)
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    
    Note: Passwords are truncated to 72 bytes before verification.
    
    Args:
        plain_password: Plain text password to verify.
        hashed_password: Bcrypt hashed password to check against.
    
    Returns:
        bool: True if password matches, False otherwise.
    
    Example:
        >>> hashed = hash_password("mysecurepassword")
        >>> verify_password("mysecurepassword", hashed)
        True
        >>> verify_password("wrongpassword", hashed)
        False
    """
    try:
        password_bytes = _prepare_password(plain_password)
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        logger.warning(f"Password verification failed: {e}")
        return False


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Dictionary containing token payload (must include 'sub' key).
        expires_delta: Optional custom expiration time.
    
    Returns:
        str: Encoded JWT access token.
    
    Example:
        >>> token = create_access_token({"sub": "user-uuid-here"})
        >>> len(token) > 0
        True
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode a JWT access token.
    
    Args:
        token: JWT access token to verify.
    
    Returns:
        Optional[Dict[str, Any]]: Token payload if valid, None otherwise.
    
    Raises:
        None: Returns None on invalid token instead of raising.
    
    Example:
        >>> token = create_access_token({"sub": "user-123"})
        >>> payload = verify_token(token)
        >>> payload["sub"]
        'user-123'
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def get_user_id_from_token(token: str) -> Optional[str]:
    """
    Extract user ID from a JWT token.

    Args:
        token: JWT access token.

    Returns:
        Optional[str]: User ID if token is valid, None otherwise.

    Example:
        >>> token = create_access_token({"sub": "user-123"})
        >>> get_user_id_from_token(token)
        'user-123'
    """
    payload = verify_token(token)
    if payload:
        return payload.get("sub")
    return None


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token with longer expiration.

    Args:
        data: Dictionary containing token payload (must include 'sub' key).
        expires_delta: Optional custom expiration time.

    Returns:
        str: Encoded JWT refresh token.

    Example:
        >>> refresh_token = create_refresh_token({"sub": "user-uuid-here"})
        >>> len(refresh_token) > 0
        True
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Refresh tokens last 7 days by default
        expire = datetime.now(timezone.utc) + timedelta(days=7)

    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh"  # Mark as refresh token
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def verify_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode a JWT refresh token.

    Args:
        token: JWT refresh token to verify.

    Returns:
        Optional[Dict[str, Any]]: Token payload if valid refresh token, None otherwise.

    Example:
        >>> token = create_refresh_token({"sub": "user-123"})
        >>> payload = verify_refresh_token(token)
        >>> payload["sub"]
        'user-123'
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        # Verify it's a refresh token
        if payload.get("type") != "refresh":
            logger.warning("Token is not a refresh token")
            return None

        return payload
    except JWTError as e:
        logger.warning(f"Refresh token verification failed: {e}")
        return None


async def blacklist_token(token: str, ttl_seconds: int) -> bool:
    """
    Add a token to the Redis blacklist for logout functionality.

    Args:
        token: JWT access token to blacklist.
        ttl_seconds: Time-to-live matching token expiry.

    Returns:
        bool: True if successfully blacklisted, False otherwise.

    Example:
        >>> await blacklist_token("token-string", 1800)
        True
    """
    try:
        # Use token itself as key for efficient lookup
        blacklist_key = f"blacklist:{token}"
        await cache_service.set(blacklist_key, {"blacklisted": True}, ttl_seconds)
        logger.info(f"Token blacklisted successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to blacklist token: {e}")
        return False


async def is_token_blacklisted(token: str) -> bool:
    """
    Check if a token is blacklisted.

    Args:
        token: JWT access token to check.

    Returns:
        bool: True if blacklisted, False otherwise.

    Example:
        >>> await is_token_blacklisted("token-string")
        False
    """
    try:
        blacklist_key = f"blacklist:{token}"
        result = await cache_service.get(blacklist_key)
        return result is not None
    except Exception as e:
        logger.error(f"Error checking token blacklist: {e}")
        # Fail open - allow request if Redis is down
        return False
