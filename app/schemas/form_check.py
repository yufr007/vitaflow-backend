"""
VitaFlow API - FormCheck Schemas.

Pydantic schemas for form check requests and responses.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, ConfigDict


class FormCheckRequest(BaseModel):
    """
    Schema for form check upload request.
    
    Attributes:
        exercise_name: Name of the exercise to analyze.
        image_url: URL to the uploaded image/video (optional).
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "exercise_name": "squat",
                "image_url": "https://storage.example.com/images/squat_001.jpg"
            }
        }
    )
    
    exercise_name: str = Field(..., description="Name of the exercise")
    image_url: Optional[str] = Field(None, description="URL to uploaded image/video")


class FormCheckResponse(BaseModel):
    """
    Schema for form check analysis response.
    
    Attributes:
        form_check_id: Unique identifier for this form check.
        form_score: Overall form score (0-100).
        alignment_feedback: Feedback on body alignment.
        rom_feedback: Feedback on range of motion.
        stability_feedback: Feedback on stability.
        corrections: List of specific corrections needed.
        tips: General improvement tips.
        next_step: Suggested next exercise or progression.
        created_at: Analysis timestamp.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "form_check_id": "550e8400-e29b-41d4-a716-446655440000",
                "form_score": 85,
                "alignment_feedback": "Good spinal alignment throughout the movement.",
                "rom_feedback": "Full depth achieved on the squat.",
                "stability_feedback": "Minor knee wobble detected at the bottom position.",
                "corrections": [
                    {"issue": "Knee valgus", "suggestion": "Focus on pushing knees out over toes"}
                ],
                "tips": "Consider using a resistance band around knees for proprioceptive feedback.",
                "next_step": "Try goblet squats to reinforce proper form.",
                "created_at": "2024-01-15T10:30:00Z"
            }
        }
    )
    
    form_check_id: str = Field(..., description="Form check unique ID")
    form_score: int = Field(..., ge=0, le=100, description="Form score (0-100)")
    alignment_feedback: str = Field(..., description="Alignment feedback")
    rom_feedback: str = Field(..., description="Range of motion feedback")
    stability_feedback: str = Field(..., description="Stability feedback")
    corrections: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="List of corrections"
    )
    tips: str = Field(..., description="Improvement tips")
    next_step: Optional[str] = Field(None, description="Suggested next step")
    created_at: datetime = Field(..., description="Analysis timestamp")
