from beanie import Document
from pydantic import EmailStr, Field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

class User(Document):
    id: UUID = Field(default_factory=uuid4)
    email: EmailStr
    password_hash: str
    name: str
    fitness_level: Optional[str] = None  # beginner/intermediate/advanced
    goal: Optional[str] = None  # weight_loss/muscle_gain/endurance/flexibility
    location_country: Optional[str] = None
    location_state: Optional[str] = None
    location_city: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"
        indexes = ["email"]

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "name": "John Doe",
                "fitness_level": "beginner",
                "goal": "weight_loss"
            }
        }
