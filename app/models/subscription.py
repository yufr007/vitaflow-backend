from beanie import Document
from pydantic import Field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from decimal import Decimal

class Subscription(Document):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    tier: str = "free"  # free/pro
    status: str = "active"  # active/canceled/past_due
    monthly_cost: Decimal = Decimal("9.99")
    renews_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    canceled_at: Optional[datetime] = None

    class Settings:
        name = "subscriptions"
        indexes = ["user_id", "stripe_customer_id"]
