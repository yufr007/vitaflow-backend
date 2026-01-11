# app/routes/workout.py
"""VitaFlow API - Workout Routes (MongoDB)."""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from app.dependencies import get_current_user_id
from app.models.mongodb import UserDocument, WorkoutDocument
from app.services.ai_router import get_ai_router

router = APIRouter()

@router.post("/generate")
async def generate_workout(user_id: str = Depends(get_current_user_id)):
    """Generate personalized workout plan and save to MongoDB."""
    user = await UserDocument.find_one(UserDocument.uid == uuid.UUID(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get AI router
    ai_router = await get_ai_router()
    result = await ai_router.generate_workout(
        user_profile={
            "fitness_level": user.fitness_level or "beginner",
            "goal": user.goal or "general_fitness",
            "equipment": user.equipment or [],
            "tier": user.tier
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