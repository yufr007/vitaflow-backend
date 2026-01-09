from beanie import Document
from pydantic import Field
from datetime import datetime
from typing import Optional, Dict
from uuid import UUID, uuid4

class ShoppingList(Document):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    mealplan_id: Optional[UUID] = None
    items: Optional[Dict] = None  # ingredients with quantities
    location_id: Optional[str] = None  # city/store location
    store_prices: Optional[Dict] = None  # prices by store
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "shoppinglists"
        indexes = ["user_id"]
