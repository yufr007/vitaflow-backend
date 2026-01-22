# app/routes/meal_plan.py
"""VitaFlow API - Meal Plan Routes (MongoDB)."""

import uuid
import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from app.dependencies import get_current_user_id
from app.middleware.auth import JWTBearer
from app.models.mongodb import UserDocument, MealPlanDocument
from app.services.ai_router import get_ai_router
from app.services.pubmed_service import pubmed_service
from app.services.openstax_service import openstax_service
from app.services.vita_points_service import vita_points_service
from app.services.who_nutrition_service import who_nutrition_service

from app.schemas.meal_plan import MealPlanRequest

router = APIRouter()

@router.post("/generate")
async def generate_meal_plan(
    request: MealPlanRequest,
    user_id: Optional[str] = Depends(JWTBearer(auto_error=False))
):
    """Generate personalized meal plan and save to MongoDB."""
    
    if not user_id:
        # GUEST MODE: Create dummy user for demo/investor access
        guest_id = uuid.uuid4()
        user = UserDocument(
            uid=guest_id,
            email=f"guest_{guest_id}@vitaflow.fitness",
            hashed_password="guest",
            name="Guest User",
            fitness_level="intermediate", # Default for guest
            goal="balanced_diet", # Default for guest
            location_city="Sydney",
            location_state="NSW",
            location_country="Australia",
            tier="pro",
            dietary_restrictions=request.dietary_restrictions or []
        )
    else:
        user = await UserDocument.find_one(UserDocument.uid == uuid.UUID(user_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update user dietary restrictions if provided
        if request.dietary_restrictions:
            user.dietary_restrictions = request.dietary_restrictions
            await user.save()

    # Get AI router
    ai_router = await get_ai_router()
    
    # Build diet query for research lookup
    diet_query = " ".join(request.dietary_restrictions or []) + " nutrition diet"
    
    # Parallel Execution: AI, PubMed, and OpenStax
    ai_task = ai_router.generate_meal_plan(
        user_profile={
            "fitness_level": user.fitness_level or "beginner",
            "goal": user.goal or "general_fitness",
            "location": {
                "city": user.location_city or "Sydney",
                "state": user.location_state or "NSW",
                "country": user.location_country or "Australia"
            },
            "tier": user.tier,
            "dietary_restrictions": request.dietary_restrictions,
            "budget_per_week": request.budget_per_week,
            "meals_per_day": request.meals_per_day
        }
    )
    
    pubmed_task = pubmed_service.get_citations_for_nutrition(diet_query.strip())
    openstax_task = openstax_service.get_citations_for_nutrition(diet_query.strip())
    
    result, pubmed_citations, openstax_citations = await asyncio.gather(
        ai_task, pubmed_task, openstax_task
    )
    
    # Calculate Vita Points for the meal plan
    vita_points = None
    if result and result.get("days"):
        vita_points = vita_points_service.calculate_plan_points(result)
    
    # Get WHO guideline citations
    who_citations = who_nutrition_service.get_citations()
    
    # Save to MongoDB
    meal_id = uuid.uuid4()
    pubmed_dicts = [c.model_dump() for c in pubmed_citations]
    openstax_dicts = [c.model_dump() for c in openstax_citations]

    meal_plan = MealPlanDocument(
        uid=meal_id,
        user_id=user.uid,
        title=f"7-Day {(user.goal or 'Balanced').replace('_', ' ').title()} Meal Plan",
        days=result.get("days", []) if result else [],
        total_weekly_cost=result.get("total_weekly_cost") if result else None,
        dietary_restrictions=result.get("dietary_restrictions", []) if result else [],
        research_citations=pubmed_dicts
    )
    await meal_plan.insert()
    
    return {
        "meal_plan_id": str(meal_id),
        "plan_data": result,
        "research_citations": {
            "pubmed": pubmed_dicts,
            "openstax": openstax_dicts,
            "who_elena": who_citations
        },
        "vita_points": vita_points,
        "scientific_sources": {
            "pubmed": "https://pubmed.ncbi.nlm.nih.gov/",
            "openstax": "https://openstax.org/ (CC BY 4.0)",
            "who_elena": "https://www.who.int/elena/"
        },
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
