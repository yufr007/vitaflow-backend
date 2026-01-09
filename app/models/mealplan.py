from beanie import Document
from pydantic import Field
from datetime import datetime
from typing import Optional, List, Dict
from uuid import UUID, uuid4
from decimal import Decimal

class MealPlan(Document):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    plan_data: Optional[Dict] = None  # 7-day meal structure
    dietary_restrictions: Optional[List[str]] = None
    budget_per_week: Optional[Decimal] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "mealplans"
        indexes = ["user_id"]
