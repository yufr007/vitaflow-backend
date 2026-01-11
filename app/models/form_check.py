"""
VitaFlow API - FormCheck ORM Model.

FormCheck model for AI-powered exercise form analysis results.
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class FormCheck(Base):
    """
    FormCheck model for storing exercise form analysis results.
    
    Stores results from Gemini Vision API analysis of exercise form.
    Includes scoring, feedback categories, and improvement suggestions.
    
    Attributes:
        id: Unique identifier (UUID).
        user_id: Foreign key to User.
        exercise_name: Name of the exercise analyzed.
        image_url: URL to the uploaded form image/video.
        form_score: Overall form score (0-100).
        alignment_feedback: Feedback on body alignment.
        rom_feedback: Feedback on range of motion.
        stability_feedback: Feedback on stability.
        corrections: JSON array of specific corrections.
        tips: General improvement tips.
        next_step: Suggested next exercise or progression.
        created_at: Analysis timestamp.
    """
    
    __tablename__ = "form_checks"
    __table_args__ = (
        Index("ix_form_checks_user_id", "user_id"),
    )
    
    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False
    )
    
    # Foreign key
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Exercise info
    exercise_name = Column(
        String(255),
        nullable=False
    )
    image_url = Column(
        String(500),
        nullable=True
    )
    
    # Scoring
    form_score = Column(
        Integer,
        nullable=True
    )  # 0-100
    
    # Feedback categories
    alignment_feedback = Column(Text, nullable=True)
    rom_feedback = Column(Text, nullable=True)
    stability_feedback = Column(Text, nullable=True)
    
    # Corrections and tips
    corrections = Column(
        JSON,
        nullable=True
    )  # Array of correction objects
    tips = Column(Text, nullable=True)
    next_step = Column(Text, nullable=True)
    
    # Timestamp
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    
    # Relationship
    user = relationship("User", back_populates="form_checks")
    
    def __repr__(self) -> str:
        """String representation of FormCheck."""
        return f"<FormCheck(id={self.id}, exercise={self.exercise_name}, score={self.form_score})>"
