# app/models/mongodb.py
"""
VitaFlow MongoDB Document Models.

Beanie ODM models for MongoDB Atlas.
"""

from beanie import Document, Indexed
from pydantic import EmailStr, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4


class UserDocument(Document):
    """User model for MongoDB."""

    uid: UUID = Field(default_factory=uuid4)
    email: Indexed(EmailStr, unique=True)  # Indexed and unique
    password_hash: str
    name: str

    # Email verification
    email_verified: bool = False
    otp_code: Optional[str] = None
    otp_expires_at: Optional[datetime] = None
    otp_attempts: int = 0

    # OAuth integration
    oauth_provider: Optional[str] = None  # "google"
    oauth_id: Optional[str] = None

    # Profile fields
    fitness_level: Optional[str] = None  # beginner/intermediate/advanced
    goal: Optional[str] = None  # weight_loss/muscle_gain/endurance/flexibility
    equipment: Optional[List[str]] = None
    location_country: Optional[str] = None
    location_state: Optional[str] = None
    location_city: Optional[str] = None
    onboarding_completed: bool = False
    tier: str = "free"  # free or pro

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login_at: Optional[datetime] = None
    
    class Settings:
        name = "users"  # Collection name in MongoDB
        indexes = [
            "email",
            "uid",
        ]
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "john@vitaflow.fitness",
                "name": "John Doe",
                "fitness_level": "intermediate",
                "goal": "muscle_gain",
                "location_city": "Sydney",
                "location_state": "NSW",
                "location_country": "Australia"
            }
        }


class SubscriptionDocument(Document):
    """Subscription model for MongoDB."""
    
    uid: UUID = Field(default_factory=uuid4)
    user_id: UUID
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    tier: str = "free"
    status: str = "active"  # active, cancelled, past_due
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "subscriptions"
        indexes = [
            "user_id",
            "stripe_customer_id",
        ]


class FormCheckDocument(Document):
    """Form check analysis model for MongoDB."""
    
    uid: UUID = Field(default_factory=uuid4)
    user_id: UUID
    exercise_name: str
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    score: int = 0  # 0-100
    alignment_feedback: Optional[str] = None
    rom_feedback: Optional[str] = None
    stability_feedback: Optional[str] = None
    corrections: List[str] = Field(default_factory=list)
    tips: Optional[str] = None
    next_step: Optional[str] = None
    analysis_raw: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "formchecks"
        indexes = [
            "user_id",
        ]


class WorkoutDocument(Document):
    """Workout plan model for MongoDB."""
    
    uid: UUID = Field(default_factory=uuid4)
    user_id: UUID
    title: str
    description: Optional[str] = None
    days: List[Dict[str, Any]] = Field(default_factory=list)
    notes: Optional[str] = None
    difficulty: Optional[str] = None
    duration_weeks: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "workouts"
        indexes = [
            "user_id",
        ]


class MealPlanDocument(Document):
    """Meal plan model for MongoDB."""
    
    uid: UUID = Field(default_factory=uuid4)
    user_id: UUID
    title: str
    description: Optional[str] = None
    days: List[Dict[str, Any]] = Field(default_factory=list)
    total_weekly_cost: Optional[str] = None
    currency: str = "USD"
    dietary_restrictions: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "mealplans"
        indexes = [
            "user_id",
        ]


class ShoppingListDocument(Document):
    """Shopping list model for MongoDB."""
    
    uid: UUID = Field(default_factory=uuid4)
    user_id: UUID
    meal_plan_id: Optional[UUID] = None
    sections: List[Dict[str, Any]] = Field(default_factory=list)
    total_costs: Optional[List[Dict[str, Any]]] = None
    best_route: Optional[str] = None
    savings_potential: Optional[str] = None
    currency: str = "USD"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "shoppinglists"
        indexes = [
            "user_id",
        ]


class CoachingMessageDocument(Document):
    """Coaching message model for MongoDB."""
    
    uid: UUID = Field(default_factory=uuid4)
    user_id: UUID
    persona: str = "motivator"  # motivator, scientist, drill_sergeant, therapist, specialist
    message: str
    context: Optional[Dict[str, Any]] = None
    read: bool = False
    favorited: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "coachingmessages"
        indexes = [
            "user_id",
            "persona",
        ]


class RecoveryAssessmentDocument(Document):
    """Recovery assessment model for MongoDB - VitaFlow Feature 6."""
    
    uid: UUID = Field(default_factory=uuid4)
    user_id: UUID
    
    # User-reported metrics
    sleep_hours: Optional[float] = None  # Hours of sleep (0-24)
    sleep_quality: Optional[int] = None  # 1-10 scale
    stress_level: Optional[int] = None  # 1-10 scale
    soreness_level: Optional[int] = None  # 1-10 scale
    energy_level: Optional[int] = None  # 1-10 scale
    
    # Calculated metrics (from AI analysis)
    workout_load_7days: Optional[float] = None  # Training load last 7 days
    avg_form_score_7days: Optional[float] = None  # Avg form check score
    recovery_score: Optional[int] = None  # 0-100 overall recovery score
    
    # AI-generated recommendations
    recovery_status: Optional[str] = None  # well_rested, moderate, fatigued, overtrained
    recommendation_summary: Optional[str] = None  # 2-3 sentence summary
    protocol: Optional[Dict[str, Any]] = None  # Detailed recovery protocol
    # protocol structure: {
    #   "rest_days_needed": 1,
    #   "active_recovery": ["light yoga", "walking"],
    #   "mobility_exercises": ["hip flexor stretch", "shoulder mobility"],
    #   "next_workout_timing": "2 days",
    #   "intensity_adjustment": "reduce by 20%"
    # }
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "recovery_assessments"
        indexes = [
            "user_id",
            "created_at",
        ]
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "sleep_hours": 7.5,
                "sleep_quality": 8,
                "stress_level": 4,
                "soreness_level": 6,
                "energy_level": 7,
                "recovery_score": 75,
                "recovery_status": "moderate",
                "recommendation_summary": "You're moderately recovered. Consider light activity today."
            }
        }
