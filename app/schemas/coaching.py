"""
VitaFlow API - Coaching Schemas.

Pydantic schemas for AI coaching messages and feedback.
"""

from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


class CoachingMessageResponse(BaseModel):
    """
    Schema for coaching message response.
    
    Attributes:
        message: The personalized coaching message.
        created_at: Message generation timestamp.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Great progress this week! You've completed 4 out of 5 planned workouts. Keep up the momentum - your consistency is paying off. For today, I recommend focusing on recovery with some light stretching.",
                "created_at": "2024-01-15T10:30:00Z"
            }
        }
    )
    
    message: str = Field(..., description="Personalized coaching message")
    created_at: datetime = Field(..., description="Message timestamp")


class CoachingFeedbackRequest(BaseModel):
    """
    Schema for coaching feedback submission.
    
    Attributes:
        feedback: User's feedback on the coaching message.
        helpful: Whether the message was helpful.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "feedback": "The recovery suggestion was very helpful!",
                "helpful": True
            }
        }
    )
    
    feedback: str = Field(..., description="Feedback text")
    helpful: bool = Field(default=True, description="Was message helpful")
