from beanie import Document
from pydantic import Field
from datetime import datetime
from typing import Optional, Dict
from uuid import UUID, uuid4

class Workout(Document):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    plan_data: Optional[Dict] = None  # 7-day plan structure
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "workouts"
        indexes = ["user_id"]
