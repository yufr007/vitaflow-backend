"""
VitaFlow API - MealPlan ORM Model.

MealPlan model for AI-generated meal plans with dietary preferences.
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, Index
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class MealPlan(Base):
    """
    MealPlan model for storing AI-generated meal plans.
    
    Stores 7-day meal plans with dietary restrictions and budget.
    Has relationship to ShoppingList for ingredient tracking.
    
    Attributes:
        id: Unique identifier (UUID).
        user_id: Foreign key to User.
        plan_data: JSON structure containing 7-day meal plan.
        dietary_restrictions: JSON array of dietary restrictions.
        budget_per_week: Weekly food budget.
        created_at: Plan generation timestamp.
    """
    
    __tablename__ = "meal_plans"
    __table_args__ = (
        Index("ix_meal_plans_user_id", "user_id"),
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
    
    # Meal plan data
    plan_data = Column(
        JSON,
        nullable=True
    )  # 7-day meal plan structure
    
    # Preferences
    dietary_restrictions = Column(
        JSON,
        nullable=True
    )  # Array of restrictions: ["vegetarian", "gluten-free", etc.]
    budget_per_week = Column(
        Numeric(10, 2),
        nullable=True
    )
    
    # Timestamp
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    user = relationship("User", back_populates="meal_plans")
    shopping_lists = relationship(
        "ShoppingList",
        back_populates="meal_plan",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        """String representation of MealPlan."""
        return f"<MealPlan(id={self.id}, budget={self.budget_per_week})>"
