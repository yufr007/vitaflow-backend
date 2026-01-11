"""
VitaFlow API - Progress Attribution Model.

Tracks causal relationships between AI interventions and user progress.
Implements AgentEvolver's "Self-Attributing" principle for credit assignment.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from sqlalchemy import Column, String, DateTime, Float, Text, ForeignKey, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class ProgressAttribution(Base):
    """
    Tracks which interventions (workouts, meals, coaching) led to measurable progress.
    
    This model implements the "Self-Attributing" principle from AgentEvolver:
    attribution-based credit assignment to identify effective interventions.
    """
    __tablename__ = "progress_attributions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Intervention Details
    intervention_type = Column(String, nullable=False)  # workout, meal_plan, coaching, form_check
    intervention_id = Column(String, nullable=True)  # Reference to specific workout/meal/message
    intervention_data = Column(JSON, default=dict)  # Summary of intervention content
    
    # Outcome Measurement
    outcome_metric = Column(String, nullable=False)  # form_score, strength_gain, weight_change, streak
    outcome_value = Column(Float, nullable=False)  # Measured value
    baseline_value = Column(Float, nullable=True)  # Value before intervention
    
    # Attribution Score (0-1) - confidence that intervention caused outcome
    # Calculated based on: timing, correlation, user feedback, control comparison
    attribution_score = Column(Float, default=0.5)
    
    # Time between intervention and outcome (hours)
    time_to_outcome = Column(Float, nullable=True)
    
    # User feedback on intervention effectiveness
    user_feedback = Column(String, nullable=True)  # helpful, not_helpful, neutral
    
    # Timestamps
    intervention_at = Column(DateTime(timezone=True), nullable=True)
    outcome_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationship
    user = relationship("User", back_populates="attributions")
    
    def __repr__(self) -> str:
        return f"<ProgressAttribution(user={self.user_id}, type={self.intervention_type}, score={self.attribution_score})>"
    
    def calculate_attribution_score(self) -> float:
        """
        Calculate attribution score based on available data.
        
        Factors:
        - Time proximity (closer = higher score)
        - User feedback (if helpful = +0.2, not_helpful = -0.2)
        - Outcome improvement (positive change = higher score)
        """
        base_score = 0.5
        
        # Time proximity factor (within 24h = +0.2, within 7d = +0.1)
        if self.time_to_outcome:
            if self.time_to_outcome <= 24:
                base_score += 0.2
            elif self.time_to_outcome <= 168:  # 7 days
                base_score += 0.1
        
        # User feedback factor
        if self.user_feedback == "helpful":
            base_score += 0.2
        elif self.user_feedback == "not_helpful":
            base_score -= 0.2
        
        # Outcome improvement factor
        if self.baseline_value and self.outcome_value:
            improvement = (self.outcome_value - self.baseline_value) / max(self.baseline_value, 1)
            base_score += min(0.2, improvement * 0.5)  # Cap at +0.2
        
        # Clamp to [0, 1]
        return max(0.0, min(1.0, base_score))


class ExperienceEvent(Base):
    """
    Raw event log for all user interactions that contribute to learning.
    
    This is the input data that feeds into UserExperience aggregations.
    """
    __tablename__ = "experience_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Event Details
    event_type = Column(String, nullable=False, index=True)  
    # Types: form_check, workout_started, workout_completed, meal_logged, 
    #        coaching_received, coaching_feedback, challenge_completed
    
    event_data = Column(JSON, nullable=False)  # Event-specific payload
    
    # Processed flag (for batch aggregation jobs)
    processed = Column(String, default="false")  # "true" or "false"
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationship
    user = relationship("User", back_populates="experience_events")
    
    def __repr__(self) -> str:
        return f"<ExperienceEvent(user={self.user_id}, type={self.event_type})>"
