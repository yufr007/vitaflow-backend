# app/routes/workout.py
"""VitaFlow API - Workout Routes (MongoDB)."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from app.dependencies import get_current_user_id
from app.middleware.auth import JWTBearer
from app.models.mongodb import UserDocument, WorkoutDocument
from app.schemas.workout import WorkoutRequest
from app.services.ai_router import get_ai_router

router = APIRouter()

@router.post("/generate")
async def generate_workout(
    request: WorkoutRequest,
    user_id: Optional[str] = Depends(JWTBearer(auto_error=False))
):
    """Generate personalized workout plan and save to MongoDB."""
    
    # GUEST MODE: If no user_id (unauthenticated), create a transient guest user context
    if not user_id:
        # Create a dummy user object for the logic below
        # We don't save this to the User collection to avoid pollution, 
        # but we need an ID for the Workout document.
        guest_id = uuid.uuid4()
        user = UserDocument(
            uid=guest_id,
            email=f"guest_{guest_id}@vitaflow.fitness",
            hashed_password="guest_mode_no_password",
            tier="pro", # Grant Pro tier for guests (Investors/Demo)
            fitness_level=request.fitness_level,
            goal=request.goal,
            equipment=[e.strip() for e in request.equipment.split(',')] if request.equipment else []
        )
        # Verify if we need to insert this user? 
        # If we don't, history won't work for them (which is fine for one-off demo).
        # But generate_workout logic below calls user.save(). We should skip that if guest.
    else:
        user = await UserDocument.find_one(UserDocument.uid == uuid.UUID(user_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update user profile with latest data from request
        user.fitness_level = request.fitness_level
        user.goal = request.goal
        user.equipment = [e.strip() for e in request.equipment.split(',')] if request.equipment else []
        await user.save()

    # Get AI router
    ai_router = await get_ai_router()
    result = await ai_router.generate_workout(
        user_profile={
            "fitness_level": request.fitness_level,
            "goal": request.goal,
            "equipment": request.equipment,
            "tier": user.tier,
            "time_available": request.time_available
        }
    )
    
    # Save to MongoDB
    workout_id = uuid.uuid4()
    workout = WorkoutDocument(
        uid=workout_id,
        user_id=user.uid,
        title=f"{(user.goal or 'General Fitness').replace('_', ' ').title()} Workout Plan",
        days=result.get("days", []),
        notes=result.get("weekly_summary"),
        difficulty=user.fitness_level or "beginner"
    )
    await workout.insert()
    
    return {
        "workout_id": str(workout_id),
        "plan_data": result,
        "created_at": workout.created_at
    }

@router.get("/history")
async def get_history(user_id: str = Depends(get_current_user_id)):
    """Get workout history."""
    workouts = await WorkoutDocument.find(
        WorkoutDocument.user_id == uuid.UUID(user_id)
    ).sort(-WorkoutDocument.created_at).limit(20).to_list()
    
    return {
        "workouts": [
            {
                "id": str(w.uid),
                "title": w.title,
                "difficulty": w.difficulty,
                "created_at": w.created_at,
                "day_count": len(w.days)
            }
            for w in workouts
        ]
    }