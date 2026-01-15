# app/routes/shopping.py
"""
VitaFlow API - Shopping Routes (MongoDB + Azure Foundry).

Shopping list generation with multi-agent optimization.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, Dict, Any
from pydantic import BaseModel
import uuid
import logging

from app.models.mongodb import ShoppingListDocument, MealPlanDocument
from app.dependencies import get_current_user_id
from app.services.ai_router import get_ai_router

logger = logging.getLogger(__name__)
router = APIRouter()


class GenerateShoppingRequest(BaseModel):
    """Request to generate shopping list."""
    meal_plan_id: Optional[str] = None
    location: Optional[Dict[str, Any]] = None
    budget: Optional[float] = None


class ShoppingListResponse(BaseModel):
    """Shopping list response."""
    shopping_list_id: str
    items: list
    store_prices: Optional[Dict] = None
    total_cost: Optional[float] = None
    recommendation: Optional[str] = None
    tips: Optional[list] = None
    ai_provider: str


@router.post("/generate", response_model=ShoppingListResponse)
async def generate_shopping_list(
    request: GenerateShoppingRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Generate optimized shopping list from meal plan.
    
    Uses Azure Foundry multi-agent workflow for:
    - Ingredient extraction
    - Price comparison across stores
    - Route optimization
    
    Falls back to Gemini if Azure unavailable.
    """
    try:
        # Get meal plan data
        meal_plan_data = {}
        if request.meal_plan_id:
            meal_plan = await MealPlanDocument.find_one(
                MealPlanDocument.uid == uuid.UUID(request.meal_plan_id)
            )
            if meal_plan:
                meal_plan_data = {
                    "days": meal_plan.days,
                    "dietary_restrictions": meal_plan.dietary_restrictions
                }
        
        # Default location if not provided
        location = request.location or {
            "city": "Sydney",
            "state": "NSW",
            "country": "Australia"
        }
        
        # Get AI router and generate shopping list
        ai_router = await get_ai_router()
        result = await ai_router.generate_shopping_list(
            meal_plan_data=meal_plan_data,
            user_id=user_id,
            location=location,
            budget=request.budget
        )
        
        # Save to database
        shopping_id = uuid.uuid4()
        shopping_list = ShoppingListDocument(
            uid=shopping_id,
            user_id=uuid.UUID(user_id),
            meal_plan_id=uuid.UUID(request.meal_plan_id) if request.meal_plan_id else None,
            sections=[{"section_name": "All Items", "items": result.get("items", [])}],
            total_costs=result.get("store_prices"),
            best_route=result.get("recommendation"),
            savings_potential=str(result.get("estimated_savings", 0)),
            currency=location.get("currency", "AUD")
        )
        await shopping_list.insert()
        
        return ShoppingListResponse(
            shopping_list_id=str(shopping_id),
            items=result.get("items", result.get("primary_store", {}).get("items", [])),
            store_prices=result.get("store_prices"),
            total_cost=result.get("total_cost"),
            recommendation=result.get("recommendation"),
            tips=result.get("tips", []),
            ai_provider=result.get("ai_provider", "unknown")
        )
        
    except Exception as e:
        logger.error(f"Shopping list generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_shopping_history(
    limit: int = 10,
    user_id: str = Depends(get_current_user_id)
):
    """Get user's shopping list history."""
    lists = await ShoppingListDocument.find(
        ShoppingListDocument.user_id == uuid.UUID(user_id)
    ).sort(-ShoppingListDocument.created_at).limit(limit).to_list()
    
    return {
        "lists": [
            {
                "id": str(sl.uid),
                "created_at": sl.created_at.isoformat(),
                "sections": sl.sections,
                "total_costs": sl.total_costs,
                "currency": sl.currency
            }
            for sl in lists
        ]
    }


@router.get("/{list_id}")
async def get_shopping_list(
    list_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get a specific shopping list."""
    shopping_list = await ShoppingListDocument.find_one(
        ShoppingListDocument.uid == uuid.UUID(list_id),
        ShoppingListDocument.user_id == uuid.UUID(user_id)
    )
    
    if not shopping_list:
        raise HTTPException(status_code=404, detail="Shopping list not found")
    
    return {
        "id": str(shopping_list.uid),
        "created_at": shopping_list.created_at.isoformat(),
        "sections": shopping_list.sections,
        "total_costs": shopping_list.total_costs,
        "best_route": shopping_list.best_route,
        "savings_potential": shopping_list.savings_potential,
        "currency": shopping_list.currency
    }