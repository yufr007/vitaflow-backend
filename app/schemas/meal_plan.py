"""
VitaFlow API - MealPlan Schemas.

Pydantic schemas for meal plan generation and logging.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, ConfigDict


class MealPlanRequest(BaseModel):
    """
    Schema for meal plan generation request.
    
    Attributes:
        dietary_restrictions: List of dietary restrictions.
        budget_per_week: Weekly food budget.
        calories_target: Daily calorie target.
        meals_per_day: Number of meals per day.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "dietary_restrictions": ["vegetarian", "gluten-free"],
                "budget_per_week": 150.00,
                "calories_target": 2000,
                "meals_per_day": 3
            }
        }
    )
    
    dietary_restrictions: Optional[List[str]] = Field(
        None,
        description="List of dietary restrictions"
    )
    budget_per_week: Optional[float] = Field(
        None,
        ge=0,
        description="Weekly food budget in USD"
    )
    calories_target: Optional[int] = Field(
        None,
        ge=1000,
        le=5000,
        description="Daily calorie target"
    )
    meals_per_day: int = Field(
        default=3,
        ge=1,
        le=6,
        description="Number of meals per day"
    )


class MealPlanResponse(BaseModel):
    """
    Schema for generated meal plan response.
    
    Attributes:
        meal_plan_id: Unique identifier for this meal plan.
        plan_data: JSON structure with 7-day meal plan.
        budget_per_week: Estimated weekly cost.
        created_at: Generation timestamp.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "meal_plan_id": "550e8400-e29b-41d4-a716-446655440000",
                "plan_data": {
                    "day_1": {
                        "breakfast": {"name": "Oatmeal with berries", "calories": 350},
                        "lunch": {"name": "Quinoa salad", "calories": 450},
                        "dinner": {"name": "Grilled salmon", "calories": 600}
                    }
                },
                "budget_per_week": 125.50,
                "created_at": "2024-01-15T10:30:00Z"
            }
        }
    )
    
    meal_plan_id: str = Field(..., description="Meal plan unique ID")
    plan_data: Dict[str, Any] = Field(..., description="7-day meal plan")
    budget_per_week: Optional[float] = Field(None, description="Estimated weekly cost")
    created_at: datetime = Field(..., description="Generation timestamp")


class MealLogRequest(BaseModel):
    """
    Schema for meal logging request.
    
    Attributes:
        meal_plan_id: ID of the meal plan.
        logged_meals: Dictionary of logged meals by day.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "meal_plan_id": "550e8400-e29b-41d4-a716-446655440000",
                "logged_meals": {
                    "day_1": {
                        "breakfast": True,
                        "lunch": True,
                        "dinner": False,
                        "notes": "Skipped dinner, had late lunch"
                    }
                }
            }
        }
    )
    
    meal_plan_id: str = Field(..., description="Meal plan ID")
    logged_meals: Dict[str, Any] = Field(..., description="Logged meals by day")
