"""
VitaFlow API - Workout Schemas.

Pydantic schemas for workout generation and tracking.
"""

from datetime import datetime
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field, ConfigDict


class WorkoutRequest(BaseModel):
    """
    Schema for workout generation request.
    
    Attributes:
        fitness_level: User's fitness level.
        goal: Workout goal.
        equipment: Available equipment.
        time_available: Available time in minutes.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "fitness_level": "intermediate",
                "goal": "muscle_gain",
                "equipment": "full_gym",
                "time_available": 60
            }
        }
    )
    
    fitness_level: str = Field(
        ...,
        description="Fitness level (beginner/intermediate/advanced)"
    )
    goal: str = Field(
        ...,
        description="Goal (weight_loss/muscle_gain/endurance/flexibility)"
    )
    equipment: str = Field(
        ...,
        description="Available equipment (none/minimal/home_gym/full_gym)"
    )
    time_available: int = Field(
        ...,
        ge=10,
        le=180,
        description="Available time in minutes (10-180)"
    )


class WorkoutResponse(BaseModel):
    """
    Schema for generated workout response.
    
    Attributes:
        workout_id: Unique identifier for this workout.
        plan_data: JSON structure with 7-day workout plan.
        created_at: Generation timestamp.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workout_id": "550e8400-e29b-41d4-a716-446655440000",
                "plan_data": {
                    "day_1": {
                        "focus": "Push",
                        "exercises": [
                            {"name": "Bench Press", "sets": 4, "reps": "8-10"},
                            {"name": "Overhead Press", "sets": 3, "reps": "10-12"}
                        ]
                    }
                },
                "created_at": "2024-01-15T10:30:00Z"
            }
        }
    )
    
    workout_id: str = Field(..., description="Workout unique ID")
    plan_data: Dict[str, Any] = Field(..., description="7-day workout plan")
    created_at: datetime = Field(..., description="Generation timestamp")


class WorkoutFeedbackRequest(BaseModel):
    """
    Schema for workout feedback submission.
    
    Attributes:
        workout_id: ID of the workout to provide feedback for.
        feedback: User's feedback text.
        completed: Whether the workout was completed.
        difficulty_rating: Perceived difficulty (1-5).
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workout_id": "550e8400-e29b-41d4-a716-446655440000",
                "feedback": "Great workout, felt challenging but doable.",
                "completed": True,
                "difficulty_rating": 4
            }
        }
    )
    
    workout_id: str = Field(..., description="Workout ID")
    feedback: str = Field(..., description="Feedback text")
    completed: bool = Field(default=True, description="Workout completed")
    difficulty_rating: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="Difficulty rating (1-5)"
    )
