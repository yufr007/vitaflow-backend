# app/routes/meal_plan.py
"""VitaFlow API - Meal Plan Routes (MongoDB)."""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from app.dependencies import get_current_user_id
from app.models.mongodb import UserDocument, MealPlanDocument
from app.services.ai_router import get_ai_router

router = APIRouter()

@router.post("/generate")
async def generate_meal_plan(user_id: str = Depends(get_current_user_id)):
    """Generate personalized meal plan and save to MongoDB."""
    user = await UserDocument.find_one(UserDocument.uid == uuid.UUID(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get AI router
    ai_router = await get_ai_router()
    result = await ai_router.generate_meal_plan(
        user_profile={
            "fitness_level": user.fitness_level or "beginner",
            "goal": user.goal or "general_fitness",
            "location": {
                "city": user.location_city or "Sydney",
                "state": user.location_state or "NSW",
                "country": user.location_country or "Australia"
            },
            "tier": user.tier
        }
    )
    
    # Save to MongoDB
    meal_id = uuid.uuid4()
    meal_plan = MealPlanDocument(
        uid=meal_id,
        user_id=user.uid,
        title=f"7-Day {(user.goal or 'Balanced').replace('_', ' ').title()} Meal Plan",
        days=result.get("days", []),
        total_weekly_cost=result.get("total_weekly_cost"),
        dietary_restrictions=result.get("dietary_restrictions", [])
    )
    await meal_plan.insert()
    
    return {
        "meal_plan_id": str(meal_id),
        "plan_data": result,
        "created_at": meal_plan.created_at
    }

@router.get("/history")
async def get_history(user_id: str = Depends(get_current_user_id)):
    """Get meal plan history."""
    plans = await MealPlanDocument.find(
        MealPlanDocument.user_id == uuid.UUID(user_id)
    ).sort(-MealPlanDocument.created_at).limit(20).to_list()
    
    return {
        "meal_plans": [
            {
                "id": str(p.uid),
                "title": p.title,
                "total_weekly_cost": p.total_weekly_cost,
                "created_at": p.created_at,
                "day_count": len(p.days)
            }
            for p in plans
        ]
    }
