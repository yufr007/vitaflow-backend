"""
VitaFlow API - MongoDB Authentication Routes.

Endpoints for user registration, login, token refresh, logout, OTP verification, and OAuth.
Uses Beanie ODM for async MongoDB operations.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status, Request, Depends

from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    RegisterResponse,
    VerifyOTPRequest,
    ResendOTPRequest,
    ResendOTPResponse,
    GoogleOAuthRequest,
)
from app.models.mongodb import UserDocument, SubscriptionDocument
from app.services.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    blacklist_token,
    verify_token,
)
from app.services.email_service import email_service
from app.services.oauth_service import oauth_service
from app.services.recaptcha_service import recaptcha_service
from app.middleware.auth import get_current_user_id
from settings import settings


router = APIRouter()


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest) -> RegisterResponse:
    """
    Register a new user with email and password.
    
    Creates unverified user and sends OTP to email. User must verify OTP
    using /verify-otp endpoint to complete registration and receive tokens.
    
    Args:
        request: RegisterRequest with email, password, name.
    
    Returns:
        RegisterResponse with user_id and email for OTP verification.
    
    Raises:
        HTTPException: 400 if email already exists.
    """
    # Check if user exists (Beanie query)
    existing = await UserDocument.find_one(UserDocument.email == request.email)
    if existing:
        # If existing but not verified, allow re-registration
        if not existing.email_verified:
            # Generate new OTP and update
            otp_code = email_service.generate_otp()
            otp_expires = email_service.get_otp_expiry()
            existing.otp_code = otp_code
            existing.otp_expires_at = otp_expires
            existing.otp_attempts = 0
            existing.password_hash = hash_password(request.password)
            existing.name = request.name
            existing.updated_at = datetime.now(timezone.utc)
            await existing.save()
            
            # Send OTP email
            await email_service.send_otp_email(existing.email, existing.name, otp_code)
            
            return RegisterResponse(
                user_id=str(existing.uid),
                email=existing.email,
                message="Verification code sent to email"
            )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Generate OTP
    otp_code = email_service.generate_otp()
    otp_expires = email_service.get_otp_expiry()
    
    # Create user document (unverified)
    user = UserDocument(
        uid=uuid.uuid4(),
        email=request.email,
        password_hash=hash_password(request.password),
        name=request.name,
        email_verified=False,
        otp_code=otp_code,
        otp_expires_at=otp_expires,
        otp_attempts=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    # Insert into MongoDB
    await user.insert()
    
    # Send OTP email
    await email_service.send_otp_email(user.email, user.name, otp_code)

    return RegisterResponse(
        user_id=str(user.uid),
        email=user.email,
        message="Verification code sent to email"
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    """
    Login user with email and password.
    
    Args:
        request: LoginRequest with email, password.
    
    Returns:
        TokenResponse with access_token, token_type, user_id.
    
    Raises:
        HTTPException: 401 if credentials are invalid.
    """
    # Find user by email (Beanie query)
    user = await UserDocument.find_one(UserDocument.email == request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Update last login timestamp
    user.updated_at = datetime.now(timezone.utc)
    await user.save()
    
    # Create access and refresh tokens
    access_token = create_access_token({"sub": str(user.uid)})
    refresh_token = create_refresh_token({"sub": str(user.uid)})

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=str(user.uid),
        refresh_token=refresh_token
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest) -> TokenResponse:
    """
    Refresh access token using refresh token.

    Args:
        request: RefreshRequest with refresh_token.

    Returns:
        TokenResponse with new access_token and refresh_token.

    Raises:
        HTTPException: 401 if refresh token is invalid or expired.
    """
    # Verify refresh token
    payload = verify_refresh_token(request.refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    # Extract user ID
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    # Verify user still exists (Beanie query)
    user = await UserDocument.find_one(UserDocument.uid == uuid.UUID(user_id_str))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # Create new access and refresh tokens (token rotation)
    new_access_token = create_access_token({"sub": user_id_str})
    new_refresh_token = create_refresh_token({"sub": user_id_str})

    return TokenResponse(
        access_token=new_access_token,
        token_type="bearer",
        user_id=user_id_str,
        refresh_token=new_refresh_token
    )


@router.post("/logout")
async def logout(
    request: Request,
    user_id: str = Depends(get_current_user_id)
) -> dict:
    """
    Logout current user by blacklisting their access token.

    Args:
        request: FastAPI request object to extract authorization header.
        user_id: Current user ID from JWT token (validates authentication).

    Returns:
        dict: Logout confirmation message.

    Note:
        Requires valid JWT token in Authorization header.
        Token is blacklisted in Redis for remaining TTL to prevent reuse.
    """
    # Extract token from Authorization header
    authorization = request.headers.get("Authorization", "")
    token = None

    if authorization.startswith("Bearer "):
        token = authorization[7:]

    if not token:
        return {"message": "Logged out"}

    # Verify token to get expiry time
    payload = verify_token(token)
    if payload and "exp" in payload:
        exp_timestamp = payload["exp"]
        current_timestamp = datetime.now(timezone.utc).timestamp()
        ttl_seconds = int(exp_timestamp - current_timestamp)

        if ttl_seconds > 0:
            await blacklist_token(token, ttl_seconds)

    return {"message": "Logged out successfully"}


@router.get("/me")
async def get_current_user(
    user_id: str = Depends(get_current_user_id)
) -> dict:
    """
    Get current authenticated user's profile.
    
    Args:
        user_id: Current user ID from JWT token.
    
    Returns:
        dict: User profile information.
    
    Raises:
        HTTPException: 404 if user not found.
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
        "location_city": user.location_city,
        "location_state": user.location_state,
        "location_country": user.location_country,
        "equipment": user.equipment,
        "onboarding_completed": user.onboarding_completed,
        "subscription": {
            "tier": subscription.tier if subscription else "free",
            "status": subscription.status if subscription else "active",
        },
        "created_at": user.created_at.isoformat(),
    }


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(request: VerifyOTPRequest) -> TokenResponse:
    """
    Verify OTP code and activate user account.
    
    Args:
        request: VerifyOTPRequest with user_id and otp_code.
    
    Returns:
        TokenResponse with access_token and refresh_token on success.
    
    Raises:
        HTTPException: 400 if OTP invalid/expired, 429 if max attempts exceeded.
    """
    # Find user by uid
    user = await UserDocument.find_one(UserDocument.uid == uuid.UUID(request.user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if already verified
    if user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )
    
    # Check max attempts
    if user.otp_attempts >= settings.OTP_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Maximum OTP attempts exceeded. Please request a new code."
        )
    
    # Increment attempts
    user.otp_attempts += 1
    await user.save()
    
    # Check OTP expiry
    if not user.otp_expires_at or user.otp_expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP expired. Please request a new code."
        )
    
    # Verify OTP code
    if user.otp_code != request.otp_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP code"
        )
    
    # Success - activate user
    user.email_verified = True
    user.otp_code = None
    user.otp_expires_at = None
    user.otp_attempts = 0
    user.updated_at = datetime.now(timezone.utc)
    await user.save()
    
    # Create free subscription for verified user
    existing_sub = await SubscriptionDocument.find_one(
        SubscriptionDocument.user_id == user.uid
    )
    if not existing_sub:
        subscription = SubscriptionDocument(
            uid=uuid.uuid4(),
            user_id=user.uid,
            tier="free",
            status="active",
            created_at=datetime.now(timezone.utc)
        )
        await subscription.insert()
    
    # Create access and refresh tokens
    access_token = create_access_token({"sub": str(user.uid)})
    refresh_token = create_refresh_token({"sub": str(user.uid)})

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=str(user.uid),
        refresh_token=refresh_token
    )


@router.post("/resend-otp", response_model=ResendOTPResponse)
async def resend_otp(request: ResendOTPRequest) -> ResendOTPResponse:
    """
    Resend OTP verification code to user's email.
    
    Rate limited: Cannot resend within 60 seconds of last OTP.
    
    Args:
        request: ResendOTPRequest with user_id.
    
    Returns:
        ResendOTPResponse indicating success or failure.
    """
    # Find user by uid
    user = await UserDocument.find_one(UserDocument.uid == uuid.UUID(request.user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if already verified
    if user.email_verified:
        return ResendOTPResponse(
            success=False,
            message="Email already verified"
        )
    
    # Generate new OTP
    otp_code = email_service.generate_otp()
    otp_expires = email_service.get_otp_expiry()
    
    # Update user with new OTP
    user.otp_code = otp_code
    user.otp_expires_at = otp_expires
    user.otp_attempts = 0  # Reset attempts
    user.updated_at = datetime.now(timezone.utc)
    await user.save()
    
    # Send OTP email
    sent = await email_service.send_otp_email(user.email, user.name, otp_code)
    
    if sent:
        return ResendOTPResponse(
            success=True,
            message="New verification code sent"
        )
    else:
        return ResendOTPResponse(
            success=False,
            message="Failed to send email. Please try again."
        )


@router.post("/google-oauth", response_model=TokenResponse)
async def google_oauth(request: GoogleOAuthRequest) -> TokenResponse:
    """
    Authenticate or register user via Google OAuth.
    
    If user exists with this Google account, logs them in.
    If email exists without OAuth, links the accounts.
    If new user, creates account (email auto-verified).
    
    Args:
        request: GoogleOAuthRequest with Google ID token.
    
    Returns:
        TokenResponse with access_token and refresh_token.
    
    Raises:
        HTTPException: 401 if token verification fails.
    """
    # Verify Google token
    profile = await oauth_service.verify_google_token(request.token)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token"
        )
    
    email = profile.get("email")
    google_id = profile.get("sub")
    name = profile.get("name", "User")
    
    # Look for existing user by Google ID
    user = await UserDocument.find_one(UserDocument.oauth_id == google_id)
    
    if not user:
        # Check if email exists (for account linking)
        user = await UserDocument.find_one(UserDocument.email == email)
        
        if user:
            # Link existing account to Google OAuth
            user.oauth_provider = "google"
            user.oauth_id = google_id
            user.email_verified = True  # Google verified
            user.updated_at = datetime.now(timezone.utc)
            await user.save()
        else:
            # Create new user (OAuth registration)
            user = UserDocument(
                uid=uuid.uuid4(),
                email=email,
                password_hash="",  # No password for OAuth users
                name=name,
                email_verified=True,  # Google verified
                oauth_provider="google",
                oauth_id=google_id,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            await user.insert()
            
            # Create free subscription
            subscription = SubscriptionDocument(
                uid=uuid.uuid4(),
                user_id=user.uid,
                tier="free",
                status="active",
                created_at=datetime.now(timezone.utc)
            )
            await subscription.insert()
    
    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    await user.save()
    
    # Create tokens
    access_token = create_access_token({"sub": str(user.uid)})
    refresh_token = create_refresh_token({"sub": str(user.uid)})

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=str(user.uid),
        refresh_token=refresh_token
    )
