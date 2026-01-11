# app/schemas/recovery.py
"""
VitaFlow Rest & Recovery Schemas.

Pydantic schemas for recovery assessment input/output.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class RecoveryMetricsInput(BaseModel):
    """User inputs for recovery assessment."""
    
    sleep_hours: Optional[float] = Field(None, ge=0, le=24, description="Hours of sleep (0-24)")
    sleep_quality: Optional[int] = Field(None, ge=1, le=10, description="Sleep quality (1-10)")
    stress_level: Optional[int] = Field(None, ge=1, le=10, description="Stress level (1-10)")
    soreness_level: Optional[int] = Field(None, ge=1, le=10, description="Muscle soreness (1-10)")
    energy_level: Optional[int] = Field(None, ge=1, le=10, description="Energy level (1-10)")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "sleep_hours": 7.5,
            "sleep_quality": 8,
            "stress_level": 4,
            "soreness_level": 6,
            "energy_level": 7
        }
    })


class RecoveryProtocol(BaseModel):
    """AI-generated recovery protocol."""
    
    rest_days_needed: int = Field(..., ge=0, le=7, description="Days of rest recommended")
    active_recovery: List[str] = Field(default_factory=list, description="Active recovery activities")
    mobility_exercises: List[str] = Field(default_factory=list, description="Recommended mobility work")
    next_workout_timing: str = Field(..., description="When to workout next")
    intensity_adjustment: str = Field(..., description="Intensity modification suggestion")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "rest_days_needed": 1,
            "active_recovery": ["light yoga", "walking", "swimming"],
            "mobility_exercises": ["hip flexor stretch", "shoulder mobility", "foam rolling"],
            "next_workout_timing": "Tomorrow afternoon",
            "intensity_adjustment": "Reduce intensity by 20%"
        }
    })


class RecoveryAssessmentResponse(BaseModel):
    """Response with recovery assessment and AI recommendations."""
    
    assessment_id: str
    recovery_score: int = Field(..., ge=0, le=100, description="Overall recovery score 0-100")
    recovery_status: str  # well_rested, moderate, fatigued, overtrained
    recommendation_summary: str
    protocol: RecoveryProtocol
    
    # User-reported metrics
    sleep_hours: Optional[float] = None
    sleep_quality: Optional[int] = None
    stress_level: Optional[int] = None
    soreness_level: Optional[int] = None
    energy_level: Optional[int] = None
    
    # Calculated metrics
    workout_load_7days: Optional[float] = None
    avg_form_score_7days: Optional[float] = None
    
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class RecoveryHistoryItem(BaseModel):
    """Single recovery assessment in history."""
    
    assessment_id: str
    recovery_score: int
    recovery_status: str
    recommendation_summary: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class RecoveryHistoryResponse(BaseModel):
    """List of past recovery assessments with trends."""
    
    assessments: List[RecoveryHistoryItem]
    average_recovery_score: float = Field(..., description="Average score over period")
    trend: str = Field(..., description="Trend: improving, stable, or declining")
    total_assessments: int
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "assessments": [],
            "average_recovery_score": 72.5,
            "trend": "improving",
            "total_assessments": 14
        }
    })


class RecoveryQuickCheck(BaseModel):
    """Quick recovery status check - minimal input."""
    
    energy_level: int = Field(..., ge=1, le=10, description="How energized do you feel? (1-10)")
    soreness_level: int = Field(..., ge=1, le=10, description="How sore are you? (1-10)")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "energy_level": 7,
            "soreness_level": 4
        }
    })
