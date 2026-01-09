from beanie import Document
from pydantic import Field
from datetime import datetime
from uuid import UUID, uuid4

class CoachingMessage(Document):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    message: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "coaching_messages"
        indexes = ["user_id"]
