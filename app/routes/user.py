# app/routes/user.py
"""
VitaFlow API - User Routes (MongoDB).

User profile management endpoints.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime, timezone
import uuid

from app.models.mongodb import UserDocument
from app.dependencies import get_current_user_id

router = APIRouter()


@router.get("/profile")
async def get_profile(user_id: str = Depends(get_current_user_id)):
    """Get current user's profile."""
    user = await UserDocument.find_one(UserDocument.uid == uuid.UUID(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
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
        "tier": user.tier,
    }


@router.put("/profile")
async def update_profile(
    data: dict,
    user_id: str = Depends(get_current_user_id)
):
    """Update current user's profile."""
    user = await UserDocument.find_one(UserDocument.uid == uuid.UUID(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update fields
    for field in ['name', 'fitness_level', 'goal', 'equipment', 
                  'location_country', 'location_state', 'location_city',
                  'onboarding_completed']:
        if field in data:
            setattr(user, field, data[field])
    
    user.updated_at = datetime.now(timezone.utc)
    await user.save()
    
    return {"message": "Profile updated", "user_id": str(user.uid)}
