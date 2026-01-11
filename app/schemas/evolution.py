"""
VitaFlow API - Evolution Schemas.

Pydantic models for AgentEvolver-powered adaptive AI features.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


# ============================================
# Experience Event Schemas
# ============================================

class ExperienceEventCreate(BaseModel):
    """Schema for creating a new experience event."""
    type: str = Field(..., description="Event type: form_check, workout_completed, meal_logged, coaching_feedback")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event-specific payload")


class ExperienceEventResponse(BaseModel):
    """Response schema for experience event."""
    id: str
    type: str
    data: Dict[str, Any]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================
# Experience Context Schemas
# ============================================

class WorkoutSummary(BaseModel):
    """Summary of a workout for context."""
    workout_id: str
    date: datetime
    exercises_completed: int
    difficulty_rating: Optional[float] = None
    duration_minutes: Optional[int] = None


class MealSummary(BaseModel):
    """Summary of a meal for context."""
    meal_id: str
    date: datetime
    meal_type: str  # breakfast, lunch, dinner, snack
    calories: Optional[int] = None
    adherence_score: Optional[float] = None


class FormCheckSummary(BaseModel):
    """Summary of a form check for context."""
    check_id: str
    exercise: str
    score: float
    date: datetime
    key_feedback: Optional[str] = None


class UserPreferences(BaseModel):
    """Aggregated user preferences from learning."""
    preferred_exercises: List[str] = []
    avoided_exercises: List[str] = []
    preferred_workout_duration: Optional[int] = None
    intensity_preference: str = "moderate"  # light, moderate, intense
    dietary_restrictions: List[str] = []
    favorite_cuisines: List[str] = []


class ExperienceContext(BaseModel):
    """
    Full experience context passed to Gemini for personalized generation.
    
    This is the "Self-Navigating" memory that guides AI recommendations.
    """
    workout_history: List[WorkoutSummary] = []
    meal_history: List[MealSummary] = []
    form_check_history: List[FormCheckSummary] = []
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    attribution_scores: Dict[str, float] = Field(default_factory=dict)
    similar_user_insights: Optional[List[str]] = None
    learning_stage: str = "beginner"
    preferences_confidence: float = 0.0


# ============================================
# Evolved Plan Schemas
# ============================================

class EvolvedPlan(BaseModel):
    """AI-generated plan informed by user experience."""
    workout_plan: Dict[str, Any] = Field(default_factory=dict)
    meal_plan: Dict[str, Any] = Field(default_factory=dict)
    coaching_focus: str = ""
    progression_notes: List[str] = []
    confidence_score: float = 0.5
    personalization_level: str = "basic"  # basic, moderate, high, personalized


# ============================================
# Challenge Schemas (Self-Questioning)
# ============================================

class Challenge(BaseModel):
    """
    AI-generated progressive challenge for user growth.
    
    Implements "Self-Questioning" - curiosity-driven task generation.
    """
    id: str
    title: str
    description: str
    difficulty: int = Field(..., ge=1, le=10, description="Difficulty level 1-10")
    category: str = Field(..., description="strength, endurance, flexibility, nutrition, consistency")
    reward_xp: int = Field(default=100, description="Experience points for completion")
    deadline: Optional[datetime] = None
    prerequisites: List[str] = []
    success_criteria: str = ""


class ChallengeListResponse(BaseModel):
    """Response with list of challenges."""
    challenges: List[Challenge]
    total_xp_available: int


# ============================================
# Attribution Schemas (Self-Attributing)
# ============================================

class Attribution(BaseModel):
    """
    Tracks intervention effectiveness.
    
    Implements "Self-Attributing" - credit assignment for progress.
    """
    intervention_type: str
    intervention_id: Optional[str] = None
    outcome_metric: str
    outcome_value: float
    attribution_score: float = Field(..., ge=0, le=1)
    time_to_outcome_hours: Optional[float] = None


class AttributionCreateRequest(BaseModel):
    """Request to create a progress attribution."""
    intervention_type: str
    intervention_id: Optional[str] = None
    intervention_data: Dict[str, Any] = Field(default_factory=dict)
    outcome_metric: str
    outcome_value: float
    baseline_value: Optional[float] = None


# ============================================
# Evolution Profile Schemas
# ============================================

class EvolutionProfile(BaseModel):
    """
    User's AI learning profile showing adaptation state.
    """
    user_id: str
    learning_stage: str = "beginner"  # beginner, developing, established, advanced
    preferences_confidence: float = Field(default=0.0, ge=0, le=1)
    total_data_points: int = 0
    last_evolution: Optional[datetime] = None
    key_insights: List[str] = []
    effective_interventions: List[str] = []
    areas_for_growth: List[str] = []


class Insight(BaseModel):
    """AI-generated insight about user's progress."""
    id: str
    category: str  # performance, consistency, nutrition, recovery
    title: str
    description: str
    confidence: float = Field(..., ge=0, le=1)
    action_suggestion: Optional[str] = None
    related_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class InsightListResponse(BaseModel):
    """Response with list of insights."""
    insights: List[Insight]
    updated_at: datetime


# ============================================
# Feedback Schemas
# ============================================

class EvolutionFeedback(BaseModel):
    """User feedback to improve AI recommendations."""
    feedback_type: str = Field(..., description="workout, meal, coaching, challenge")
    item_id: str
    rating: int = Field(..., ge=1, le=5, description="1-5 star rating")
    helpful: bool = True
    specific_feedback: Optional[str] = None
    preferences_update: Optional[Dict[str, Any]] = None


class EvolutionFeedbackResponse(BaseModel):
    """Response after submitting feedback."""
    status: str = "saved"
    message: str
    learning_updated: bool = False
    new_confidence: Optional[float] = None
