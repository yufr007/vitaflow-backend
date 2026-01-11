"""
VitaFlow API - Profile Routes.

Endpoints for user profile management and onboarding sync.
"""

from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List

from app.models.mongodb import UserDocument, SubscriptionDocument
from app.dependencies import get_current_user_id


router = APIRouter()


class ProfileResponse(BaseModel):
    """Response model for profile data."""
    name: str
    fitness_level: Optional[str] = None
    goal: Optional[str] = None
    equipment: List[str] = []
    location_country: Optional[str] = None
    location_state: Optional[str] = None
    location_city: Optional[str] = None
    onboarding_completed: bool = False
    tier: str = "free"


class ProfileUpdateRequest(BaseModel):
    """Request model for updating profile."""
    name: Optional[str] = None
    fitness_level: Optional[str] = None
    goal: Optional[str] = None
    equipment: Optional[List[str]] = None
    location_country: Optional[str] = None
    location_state: Optional[str] = None
    location_city: Optional[str] = None
    onboarding_completed: Optional[bool] = None


@router.get("/me", response_model=ProfileResponse)
async def get_profile(
    user_id: str = Depends(get_current_user_id)
) -> ProfileResponse:
    """
    Get current user's profile.
    
    Args:
        user_id: Current user's ID from JWT.
    
    Returns:
        ProfileResponse with user profile data.
    
    Raises:
        HTTPException: 404 if user not found.
    """
    user = await UserDocument.find_one(UserDocument.uid == uuid.UUID(user_id))
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Equipment is already a list in MongoDB
    equipment_list = user.equipment or []
        
    # Determine tier from active subscriptions
    tier = user.tier or "free"
    subscriptions = await SubscriptionDocument.find(
        SubscriptionDocument.user_id == uuid.UUID(user_id)
    ).to_list()
    
    for sub in subscriptions:
        if sub.status == "active":
            tier = sub.tier
            break
    
    return ProfileResponse(
        name=user.name,
        fitness_level=user.fitness_level,
        goal=user.goal,
        equipment=equipment_list,
        location_country=user.location_country,
        location_state=user.location_state,
        location_city=user.location_city,
        onboarding_completed=user.onboarding_completed,
        tier=tier
    )


@router.put("/me", response_model=ProfileResponse)
async def update_profile(
    profile: ProfileUpdateRequest,
    user_id: str = Depends(get_current_user_id)
) -> ProfileResponse:
    """
    Update current user's profile.
    
    Args:
        profile: ProfileUpdateRequest with fields to update.
        user_id: Current user's ID from JWT.
    
    Returns:
        ProfileResponse with updated profile data.
    
    Raises:
        HTTPException: 404 if user not found.
    """
    user = await UserDocument.find_one(UserDocument.uid == uuid.UUID(user_id))
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields if provided
    if profile.name is not None:
        user.name = profile.name
    if profile.fitness_level is not None:
        user.fitness_level = profile.fitness_level
    if profile.goal is not None:
        user.goal = profile.goal
    if profile.equipment is not None:
        user.equipment = profile.equipment
    if profile.location_country is not None:
        user.location_country = profile.location_country
    if profile.location_state is not None:
        user.location_state = profile.location_state
    if profile.location_city is not None:
        user.location_city = profile.location_city
    if profile.onboarding_completed is not None:
        user.onboarding_completed = profile.onboarding_completed
    
    user.updated_at = datetime.now(timezone.utc)
    await user.save()
    
    # Equipment is already a list
    equipment_list = user.equipment or []
        
    # Determine tier from active subscriptions
    tier = user.tier or "free"
    subscriptions = await SubscriptionDocument.find(
        SubscriptionDocument.user_id == uuid.UUID(user_id)
    ).to_list()
    
    for sub in subscriptions:
        if sub.status == "active":
            tier = sub.tier
            break
    
    return ProfileResponse(
        name=user.name,
        fitness_level=user.fitness_level,
        goal=user.goal,
        equipment=equipment_list,
        location_country=user.location_country,
        location_state=user.location_state,
        location_city=user.location_city,
        onboarding_completed=user.onboarding_completed,
        tier=tier
    )