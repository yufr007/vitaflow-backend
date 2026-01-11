"""
VitaFlow API - FastAPI Dependencies.

Dependency injection helpers for routes (MongoDB version).
"""

from fastapi import Depends, HTTPException, status
import uuid

from app.middleware.auth import jwt_bearer
from app.models.mongodb import UserDocument, SubscriptionDocument


async def get_current_user_id(
    user_id: str = Depends(jwt_bearer)
) -> str:
    """
    Get current authenticated user ID from JWT token.
    
    Args:
        user_id: User ID extracted by jwt_bearer dependency.
    
    Returns:
        str: Authenticated user's ID.
    
    Raises:
        HTTPException: 401 if not authenticated.
    """
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user_id


async def get_current_user(
    user_id: str = Depends(get_current_user_id)
) -> UserDocument:
    """
    Get current authenticated user from database.
    
    Args:
        user_id: Current user's ID from token.
    
    Returns:
        UserDocument: Authenticated user object.
    
    Raises:
        HTTPException: 404 if user not found in database.
    """
    user = await UserDocument.find_one(UserDocument.uid == uuid.UUID(user_id))
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


def require_auth():
    """
    Dependency that ensures user is authenticated.
    
    Use this dependency to protect routes that require authentication.
    
    Returns:
        Depends: FastAPI Depends instance for get_current_user_id.
    
    Example:
        @router.get("/protected", dependencies=[Depends(require_auth())])
        async def protected_route():
            return {"message": "This is protected"}
    """
    return Depends(get_current_user_id)


async def require_pro_tier(
    user_id: str = Depends(get_current_user_id)
) -> SubscriptionDocument:
    """
    Dependency that requires active Pro subscription.
    
    Use for premium features like unlimited AI generations.
    
    Args:
        user_id: Current user's ID from token.
    
    Returns:
        SubscriptionDocument: Active Pro subscription.
    
    Raises:
        HTTPException: 403 if user doesn't have Pro subscription.
    
    Example:
        @router.get("/premium", dependencies=[Depends(require_pro_tier)])
        async def premium_feature():
            return {"message": "Pro feature"}
    """
    subscription = await SubscriptionDocument.find_one(
        SubscriptionDocument.user_id == uuid.UUID(user_id),
        SubscriptionDocument.status == "active",
        SubscriptionDocument.tier == "pro"
    )
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Pro subscription required for this feature"
        )
    
    return subscription
