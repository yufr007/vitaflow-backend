# app/routes/auth.py
"""
VitaFlow API - Authentication Routes.

Register, login, logout endpoints with MongoDB/Beanie.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request
from datetime import datetime, timezone
import uuid
import logging

from app.models.mongodb import UserDocument, SubscriptionDocument
from app.schemas.auth import RegisterRequest, LoginRequest, RefreshRequest, TokenResponse
from app.services.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    blacklist_token
)
from app.dependencies import get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    """
    Register a new user.
    
    Args:
        request: RegisterRequest with email, password, name
    
    Returns:
        TokenResponse with user_id, email, access_token, refresh_token
    
    Raises:
        HTTPException 400: Email already registered
    """
    # Check if email exists (Beanie query)
    existing_user = await UserDocument.find_one(UserDocument.email == request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = UserDocument(
        uid=uuid.uuid4(),
        email=request.email,
        password_hash=hash_password(request.password),
        name=request.name,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    # Insert into MongoDB
    await user.insert()
    logger.info(f"New user registered: {user.email}")
    
    # Create free subscription for new user
    subscription = SubscriptionDocument(
        uid=uuid.uuid4(),
        user_id=user.uid,
        tier="free",
        status="active",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    await subscription.insert()
    
    # Generate JWT tokens
    access_token = create_access_token(data={"sub": str(user.uid)})
    refresh_token = create_refresh_token(data={"sub": str(user.uid)})
    
    return TokenResponse(
        user_id=str(user.uid),
        email=user.email,
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    Login user and return JWT tokens.
    
    Args:
        request: LoginRequest with email, password
    
    Returns:
        TokenResponse with access and refresh tokens
    
    Raises:
        HTTPException 401: Invalid credentials
    """
    # Find user by email
    user = await UserDocument.find_one(UserDocument.email == request.email)
    
    # Verify credentials
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    user.updated_at = datetime.now(timezone.utc)
    await user.save()
    
    logger.info(f"User logged in: {user.email}")
    
    # Generate JWT tokens
    access_token = create_access_token(data={"sub": str(user.uid)})
    refresh_token = create_refresh_token(data={"sub": str(user.uid)})
    
    return TokenResponse(
        user_id=str(user.uid),
        email=user.email,
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest):
    """
    Refresh access token using refresh token.
    
    Args:
        request: RefreshRequest with refresh_token
    
    Returns:
        TokenResponse with new access and refresh tokens
    
    Raises:
        HTTPException 401: Invalid or expired refresh token
    """
    # Verify refresh token
    payload = verify_refresh_token(request.refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Find user
    user = await UserDocument.find_one(UserDocument.uid == uuid.UUID(user_id_str))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Generate new tokens
    access_token = create_access_token(data={"sub": str(user.uid)})
    new_refresh_token = create_refresh_token(data={"sub": str(user.uid)})
    
    return TokenResponse(
        user_id=str(user.uid),
        email=user.email,
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer"
    )


@router.post("/logout")
async def logout(
    request: Request,
    user_id: str = Depends(get_current_user_id)
):
    """
    Logout user by blacklisting their token.
    
    Args:
        request: FastAPI request object
        user_id: Current user ID from token
    
    Returns:
        Success message
    """
    # Get token from header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        # Blacklist token for 30 minutes (token expiry time)
        await blacklist_token(token, ttl_seconds=1800)
    
    logger.info(f"User logged out: {user_id}")
    return {"message": "Successfully logged out"}


@router.get("/me")
async def get_current_user(user_id: str = Depends(get_current_user_id)):
    """
    Get current user profile.
    
    Args:
        user_id: Current user ID from token
    
    Returns:
        User profile data
    """
    user = await UserDocument.find_one(UserDocument.uid == uuid.UUID(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get subscription
    subscription = await SubscriptionDocument.find_one(
        SubscriptionDocument.user_id == user.uid
    )
    
    return {
        "user_id": str(user.uid),
        "email": user.email,
        "name": user.name,
        "fitness_level": user.fitness_level,
        "goal": user.goal,
        "equipment": user.equipment or [],
        "location_country": user.location_country,
        "location_state": user.location_state,
        "location_city": user.location_city,
        "onboarding_completed": user.onboarding_completed,
        "tier": subscription.tier if subscription else "free",
        "subscription_status": subscription.status if subscription else "active",
        "created_at": user.created_at.isoformat(),
    }
