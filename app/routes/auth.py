from fastapi import APIRouter, HTTPException, status
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.services.auth import hash_password, verify_password, create_access_token
from uuid import uuid4
from datetime import datetime

router = APIRouter()

@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest):
    """Register new user"""
    # Check if user exists
    existing_user = await User.find_one(User.email == request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = User(
        id=uuid4(),
        email=request.email,
        password_hash=hash_password(request.password),
        name=request.name,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    await user.insert()
    
    # Generate token
    token = create_access_token({"sub": str(user.id)})
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=str(user.id)
    )

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Login user"""
    user = await User.find_one(User.email == request.email)
    
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    token = create_access_token({"sub": str(user.id)})
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=str(user.id)
    )

@router.post("/logout")
async def logout():
    """Logout user (client-side token removal)"""
    return {"message": "Logged out successfully"}
