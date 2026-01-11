"""
VitaFlow API - User Experience Model.

Stores user-specific learning data for AgentEvolver-style adaptive AI.
Tracks workout/meal preferences, performance history, and adaptation parameters.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class UserExperience(Base):
    """
    Stores cumulative learning data about each user for adaptive AI.
    
    This model implements the "Self-Navigating" principle from AgentEvolver:
    experience-guided exploration through summarized cross-task experiences.
    """
    __tablename__ = "user_experiences"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    
    # Workout Preferences (learned from feedback and completions)
    # Example: {"preferred_exercises": ["squats", "deadlifts"], "avoided_exercises": ["burpees"],
    #           "preferred_duration": 45, "intensity_preference": "moderate"}
    workout_preferences = Column(JSON, default=dict)
    
    # Meal Preferences (learned from ratings and patterns)
    # Example: {"dietary_restrictions": ["lactose"], "favorite_cuisines": ["mediterranean"],
    #           "meal_timing": "3_meals_2_snacks", "calorie_accuracy": 0.85}
    meal_preferences = Column(JSON, default=dict)
    
    # Exercise Performance History (rolling summary, not full history)
    # Example: {"squat": {"avg_score": 87, "improvement_rate": 2.5, "total_checks": 15},
    #           "deadlift": {"avg_score": 82, "improvement_rate": 1.8, "total_checks": 8}}
    exercise_performance = Column(JSON, default=dict)
    
    # Coaching Feedback History (what resonates with user)
    # Example: {"preferred_tone": "motivational", "effective_topics": ["form_tips", "recovery"],
    #           "message_length_preference": "concise", "feedback_response_rate": 0.72}
    coaching_feedback = Column(JSON, default=dict)
    
    # Adaptation Parameters (AI tuning for this user)
    # Example: {"progression_speed": 1.2, "variety_preference": 0.7, 
    #           "challenge_acceptance": 0.8, "consistency_score": 0.65}
    adaptation_params = Column(JSON, default=dict)
    
    # Learning Stage (beginner, developing, established, advanced)
    learning_stage = Column(String, default="beginner")
    
    # Confidence Score (0-1) - how confident AI is in its understanding of user
    preferences_confidence = Column(String, default="0.0")
    
    # Total data points collected (for confidence calculation)
    total_data_points = Column(String, default="0")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_updated = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), 
                          onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationship
    user = relationship("User", back_populates="experience")
    
    def __repr__(self) -> str:
        return f"<UserExperience(user_id={self.user_id}, stage={self.learning_stage})>"
    
    def to_context_dict(self) -> Dict[str, Any]:
        """
        Convert experience to context dictionary for Gemini prompts.
        """
        return {
            "workout_preferences": self.workout_preferences or {},
            "meal_preferences": self.meal_preferences or {},
            "exercise_performance": self.exercise_performance or {},
            "coaching_feedback": self.coaching_feedback or {},
            "learning_stage": self.learning_stage,
            "preferences_confidence": float(self.preferences_confidence or 0),
            "adaptation_params": self.adaptation_params or {},
        }
    
    def update_from_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """
        Update experience from a new event (form check, workout, meal, coaching).
        
        Args:
            event_type: Type of event (form_check, workout_completed, meal_logged, coaching_feedback)
            event_data: Event-specific data
        """
        # Increment data points
        current_points = int(self.total_data_points or 0)
        self.total_data_points = str(current_points + 1)
        
        # Update confidence (simple heuristic: more data = more confidence, caps at 0.95)
        new_confidence = min(0.95, current_points / 100)
        self.preferences_confidence = str(round(new_confidence, 2))
        
        # Update learning stage based on data points
        if current_points > 50:
            self.learning_stage = "advanced"
        elif current_points > 20:
            self.learning_stage = "established"
        elif current_points > 5:
            self.learning_stage = "developing"
        
        self.last_updated = datetime.now(timezone.utc)
