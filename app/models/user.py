"""
VitaFlow API - User ORM Model.

User model with profile information and relationships to all user-owned entities.
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    """
    User model representing application users.
    
    Stores authentication credentials, profile information, and fitness preferences.
    Has relationships to all user-owned entities (subscriptions, workouts, etc.).
    
    Attributes:
        id: Unique identifier (UUID).
        email: User's email address (unique, indexed).
        password_hash: Bcrypt-hashed password.
        name: User's display name.
        fitness_level: Current fitness level (beginner/intermediate/advanced).
        goal: Primary fitness goal (weight_loss/muscle_gain/endurance/flexibility).
        location_country: Country for localized content.
        location_state: State/province for localized content.
        location_city: City for localized content and shopping.
        created_at: Account creation timestamp.
        updated_at: Last profile update timestamp.
    """
    
    __tablename__ = "users"
    
    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False
    )
    
    # Authentication
    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )
    password_hash = Column(
        String(255),
        nullable=False
    )
    
    # Profile
    name = Column(
        String(255),
        nullable=False
    )
    fitness_level = Column(
        String(50),
        nullable=True
    )  # beginner, intermediate, advanced
    goal = Column(
        String(50),
        nullable=True
    )  # weight_loss, muscle_gain, endurance, flexibility
    
    # Location
    location_country = Column(String(100), nullable=True)
    location_state = Column(String(100), nullable=True)
    location_city = Column(String(100), nullable=True)
    
    # Equipment (stored as JSON array)
    equipment = Column(String(500), nullable=True)  # Comma-separated list
    
    # Onboarding completion flag
    onboarding_completed = Column(
        String(10),
        nullable=True,
        default="false"
    )  # "true" or "false"
    
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
    
    # Relationships
    subscriptions = relationship(
        "Subscription",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    form_checks = relationship(
        "FormCheck",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    workouts = relationship(
        "Workout",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    meal_plans = relationship(
        "MealPlan",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    shopping_lists = relationship(
        "ShoppingList",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    coaching_messages = relationship(
        "CoachingMessage",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    wearable_devices = relationship(
        "WearableDevice",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    health_metrics = relationship(
        "HealthMetric",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    # Phase 3: Smart devices and accessibility
    smart_devices = relationship(
        "SmartDevice",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    device_readings = relationship(
        "DeviceReading",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    peloton_workouts = relationship(
        "PelotonWorkout",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    mirror_workouts = relationship(
        "MirrorWorkout",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    accessibility_settings = relationship(
        "AccessibilitySettings",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    # AgentEvolver: Adaptive AI Learning
    experience = relationship(
        "UserExperience",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
    attributions = relationship(
        "ProgressAttribution",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    experience_events = relationship(
        "ExperienceEvent",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        """String representation of User."""
        return f"<User(id={self.id}, email={self.email})>"
