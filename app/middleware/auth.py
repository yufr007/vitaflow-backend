"""
VitaFlow API - Authentication Middleware.

JWT verification middleware for protected routes.
"""

from typing import Optional

from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.services.auth import verify_token, is_token_blacklisted


class JWTBearer(HTTPBearer):
    """
    JWT Bearer token authentication.
    
    Custom HTTPBearer that validates JWT tokens on protected routes.
    
    Attributes:
        auto_error: Whether to automatically raise errors.
    """
    
    def __init__(self, auto_error: bool = True):
        """
        Initialize JWTBearer.
        
        Args:
            auto_error: Whether to raise HTTPException on auth failure.
        """
        super().__init__(auto_error=auto_error)
    
    async def __call__(self, request: Request) -> Optional[str]:
        """
        Verify JWT token from Authorization header.
        
        Args:
            request: FastAPI request object.
        
        Returns:
            Optional[str]: User ID from token if valid.
        
        Raises:
            HTTPException: 403 if token is invalid or missing.
        """
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        
        if not credentials:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid authorization credentials"
                )
            return None
        
        if credentials.scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid authentication scheme"
                )
            return None
        
        # Check if token is blacklisted (logout)
        if await is_token_blacklisted(credentials.credentials):
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked"
                )
            return None

        # Verify the JWT token
        payload = verify_token(credentials.credentials)

        if not payload:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid or expired token"
                )
            return None
        
        # Return user ID from token
        user_id = payload.get("sub")
        if not user_id:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid token payload"
                )
            return None
        
        return user_id


# Global JWT bearer instance for dependency injection
jwt_bearer = JWTBearer()


async def get_current_user_id(user_id: str = Depends(jwt_bearer)) -> str:
    """
    Dependency to get current authenticated user ID.

    Args:
        user_id: User ID from JWT token (injected by jwt_bearer).

    Returns:
        str: Authenticated user's ID.

    Raises:
        HTTPException: 401/403 if authentication fails.

    Usage:
        @router.get("/protected")
        async def protected_route(user_id: str = Depends(get_current_user_id)):
            return {"user_id": user_id}
    """
    return user_id
