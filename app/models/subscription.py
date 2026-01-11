"""
VitaFlow API - Subscription ORM Model.

Subscription model for managing user subscriptions with Stripe integration.
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Subscription(Base):
    """
    Subscription model for managing user subscriptions and billing.
    
    Stores subscription details, pricing tiers, and Stripe integration data.
    
    Attributes:
        id: Unique identifier (UUID).
        user_id: Reference to User.
        stripe_customer_id: Stripe customer ID for this user.
        stripe_subscription_id: Stripe subscription ID (for active subscriptions).
        plan_type: Type of plan ('free' or 'pro').
        billing_cycle: Billing cycle ('monthly' or 'annual').
        status: Subscription status ('active', 'canceled', 'past_due', 'incomplete').
        current_period_start: Start of current billing period.
        current_period_end: End of current billing period.
        cancel_at_period_end: Whether subscription cancels at period end.
        created_at: Subscription creation timestamp.
        updated_at: Last subscription update timestamp.
    """
    
    __tablename__ = "subscriptions"
    
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
        nullable=False,
        index=True
    )
    
    # Stripe Integration
    stripe_customer_id = Column(
        String(255),
        nullable=True,
        index=True,
        unique=True
    )
    stripe_subscription_id = Column(
        String(255),
        nullable=True,
        index=True
    )
    stripe_session_id = Column(
        String(255),
        nullable=True
    )
    
    # Plan Details
    plan_type = Column(
        String(50),
        nullable=False,
        default="free"
    )  # free, pro
    
    billing_cycle = Column(
        String(50),
        nullable=True
    )  # monthly, annual
    
    # Subscription Status
    status = Column(
        String(50),
        nullable=False,
        default="active"
    )  # active, canceled, past_due, incomplete, trialing
    
    # Billing Period
    current_period_start = Column(
        DateTime(timezone=True),
        nullable=True
    )
    current_period_end = Column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Cancellation
    cancel_at_period_end = Column(
        Boolean,
        default=False,
        nullable=False
    )
    
    canceled_at = Column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    
    # Relationship
    user = relationship("User", back_populates="subscriptions")
    
    def __repr__(self) -> str:
        """String representation of Subscription."""
        return f"<Subscription(user_id={self.user_id}, plan={self.plan_type}, status={self.status})>"
