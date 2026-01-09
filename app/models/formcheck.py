from beanie import Document
from pydantic import Field
from datetime import datetime
from typing import Optional, List, Dict
from uuid import UUID, uuid4

class FormCheck(Document):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    exercise_name: str
    image_url: Optional[str] = None
    form_score: Optional[int] = None  # 0-100
    alignment_feedback: Optional[str] = None
    rom_feedback: Optional[str] = None
    stability_feedback: Optional[str] = None
    corrections: Optional[List[str]] = None
    tips: Optional[str] = None
    next_step: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "formchecks"
        indexes = ["user_id"]
