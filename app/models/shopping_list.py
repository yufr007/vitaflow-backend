"""
VitaFlow API - ShoppingList ORM Model.

ShoppingList model for meal plan ingredients with price comparison.
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class ShoppingList(Base):
    """
    ShoppingList model for storing shopping lists derived from meal plans.
    
    Contains ingredients from meal plans with store price comparisons.
    Supports location-based pricing and checkout tracking.
    
    Attributes:
        id: Unique identifier (UUID).
        user_id: Foreign key to User.
        meal_plan_id: Foreign key to MealPlan (optional).
        items: JSON array of shopping items with quantities.
        location_id: City/area identifier for price lookup.
        store_prices: JSON object with prices by store.
        created_at: List creation timestamp.
    """
    
    __tablename__ = "shopping_lists"
    __table_args__ = (
        Index("ix_shopping_lists_user_id", "user_id"),
    )
    
    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False
    )
    
    # Foreign keys
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    meal_plan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("meal_plans.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Shopping list data
    items = Column(
        JSON,
        nullable=True
    )  # [{name, quantity, unit, category}, ...]
    
    # Location and pricing
    location_id = Column(
        String(255),
        nullable=True
    )  # City or area identifier
    store_prices = Column(
        JSON,
        nullable=True
    )  # {store_name: {item: price}, ...}
    
    # Timestamp
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    user = relationship("User", back_populates="shopping_lists")
    meal_plan = relationship("MealPlan", back_populates="shopping_lists")
    
    def __repr__(self) -> str:
        """String representation of ShoppingList."""
        return f"<ShoppingList(id={self.id}, location={self.location_id})>"
