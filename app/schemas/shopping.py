"""
VitaFlow API - Shopping Schemas.

Pydantic schemas for shopping list and price comparison.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, ConfigDict


class ShoppingListRequest(BaseModel):
    """
    Schema for shopping list generation request.
    
    Attributes:
        meal_plan_id: ID of the meal plan to generate shopping list for.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "meal_plan_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }
    )
    
    meal_plan_id: str = Field(..., description="Meal plan ID to generate list from")


class ShoppingListResponse(BaseModel):
    """
    Schema for generated shopping list response.
    
    Attributes:
        shopping_list_id: Unique identifier for this shopping list.
        items: List of shopping items with quantities.
        store_prices: Prices by store for each item.
        total_estimated: Total estimated cost.
        created_at: Generation timestamp.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "shopping_list_id": "550e8400-e29b-41d4-a716-446655440000",
                "items": [
                    {"name": "Chicken breast", "quantity": 2, "unit": "lbs", "category": "Protein"},
                    {"name": "Brown rice", "quantity": 1, "unit": "bag", "category": "Grains"}
                ],
                "store_prices": {
                    "Walmart": {"total": 45.50},
                    "Whole Foods": {"total": 62.00},
                    "Trader Joes": {"total": 52.25}
                },
                "total_estimated": 45.50,
                "created_at": "2024-01-15T10:30:00Z"
            }
        }
    )
    
    shopping_list_id: str = Field(..., description="Shopping list unique ID")
    items: List[Dict[str, Any]] = Field(..., description="Shopping items")
    store_prices: Optional[Dict[str, Any]] = Field(None, description="Prices by store")
    total_estimated: Optional[float] = Field(None, description="Estimated total cost")
    created_at: datetime = Field(..., description="Generation timestamp")


class PriceCheckRequest(BaseModel):
    """
    Schema for price check request.
    
    Attributes:
        items: List of items to check prices for.
        location: Location for store lookup.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": ["chicken breast", "brown rice", "broccoli"],
                "location": "Los Angeles, CA"
            }
        }
    )
    
    items: List[str] = Field(..., description="Items to check prices for")
    location: str = Field(..., description="Location for store lookup")


class CheckoutRequest(BaseModel):
    """
    Schema for shopping list checkout request.
    
    Attributes:
        shopping_list_id: ID of the shopping list to mark as checked out.
        store_name: Store where items were purchased.
        actual_total: Actual total spent.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "shopping_list_id": "550e8400-e29b-41d4-a716-446655440000",
                "store_name": "Walmart",
                "actual_total": 47.23
            }
        }
    )
    
    shopping_list_id: str = Field(..., description="Shopping list ID")
    store_name: Optional[str] = Field(None, description="Store where purchased")
    actual_total: Optional[float] = Field(None, description="Actual total spent")
