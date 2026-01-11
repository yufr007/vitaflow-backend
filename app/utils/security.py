"""
VitaFlow API - Security Utilities.

Password validation and security helper functions.
"""

import re
from typing import Tuple


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Validate password strength requirements.
    
    Requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    
    Args:
        password: Password string to validate.
    
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
            - is_valid: True if password meets requirements
            - error_message: Empty if valid, description of issue if invalid
    
    Example:
        >>> validate_password_strength("Short1")
        (False, 'Password must be at least 8 characters')
        >>> validate_password_strength("ValidPass1")
        (True, '')
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit"
    
    return True, ""


def is_valid_email(email: str) -> bool:
    """
    Basic email format validation.
    
    Args:
        email: Email address to validate.
    
    Returns:
        bool: True if email format is valid.
    
    Example:
        >>> is_valid_email("user@example.com")
        True
        >>> is_valid_email("invalid-email")
        False
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def sanitize_string(value: str, max_length: int = 255) -> str:
    """
    Sanitize a string by stripping whitespace and limiting length.
    
    Args:
        value: String to sanitize.
        max_length: Maximum allowed length.
    
    Returns:
        str: Sanitized string.
    
    Example:
        >>> sanitize_string("  Hello World  ")
        'Hello World'
    """
    return value.strip()[:max_length]
