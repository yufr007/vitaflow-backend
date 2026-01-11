"""
VitaFlow API - User Schemas.

Pydantic schemas for user profile operations.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserCreate(BaseModel):
    """
    Schema for creating a new user.
    
    Attributes:
        email: User's email address.
        password: User's password.
        name: User's display name.
    """
    
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(
        ...,
        min_length=8,
        description="User's password (minimum 8 characters)"
    )
    name: str = Field(..., min_length=1, description="User's display name")


class UserUpdate(BaseModel):
    """
    Schema for updating user profile.
    
    All fields are optional for partial updates.
    
    Attributes:
        name: User's display name.
        fitness_level: Fitness level (beginner/intermediate/advanced).
        goal: Primary fitness goal.
        location_country: Country.
        location_state: State/province.
        location_city: City.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "John Doe",
                "fitness_level": "intermediate",
                "goal": "muscle_gain",
                "location_country": "United States",
                "location_state": "California",
                "location_city": "Los Angeles"
            }
        }
    )
    
    name: Optional[str] = Field(None, min_length=1, description="Display name")
    fitness_level: Optional[str] = Field(
        None,
        description="Fitness level (beginner/intermediate/advanced)"
    )
    goal: Optional[str] = Field(
        None,
        description="Primary goal (weight_loss/muscle_gain/endurance/flexibility)"
    )
    location_country: Optional[str] = Field(None, description="Country")
    location_state: Optional[str] = Field(None, description="State/province")
    location_city: Optional[str] = Field(None, description="City")
    equipment: Optional[list[str]] = Field(None, description="Equipment list")
    onboarding_completed: Optional[bool] = Field(None, description="Onboarding status")


class UserResponse(BaseModel):
    """
    Schema for user response (minimal).
    
    Attributes:
        user_id: User's unique identifier.
        email: User's email address.
        name: User's display name.
        fitness_level: Current fitness level.
        goal: Primary fitness goal.
        created_at: Account creation timestamp.
    """
    
    model_config = ConfigDict(from_attributes=True)
    
    user_id: str = Field(..., description="User's unique ID")
    email: str = Field(..., description="User's email")
    name: str = Field(..., description="User's display name")
    fitness_level: Optional[str] = Field(None, description="Fitness level")
    goal: Optional[str] = Field(None, description="Primary goal")
    created_at: datetime = Field(..., description="Account creation time")


class UserProfile(BaseModel):
    """
    Schema for full user profile.
    
    Includes all user fields for detailed profile view.
    
    Attributes:
        user_id: User's unique identifier.
        email: User's email address.
        name: User's display name.
        fitness_level: Current fitness level.
        goal: Primary fitness goal.
        location_country: Country.
        location_state: State/province.
        location_city: City.
        created_at: Account creation timestamp.
        updated_at: Last profile update timestamp.
    """
    
    model_config = ConfigDict(from_attributes=True)
    
    user_id: str = Field(..., description="User's unique ID")
    email: str = Field(..., description="User's email")
    name: str = Field(..., description="User's display name")
    fitness_level: Optional[str] = Field(None, description="Fitness level")
    goal: Optional[str] = Field(None, description="Primary goal")
    location_country: Optional[str] = Field(None, description="Country")
    location_state: Optional[str] = Field(None, description="State/province")
    location_city: Optional[str] = Field(None, description="City")
    equipment: Optional[list[str]] = Field(None, description="Equipment list")
    onboarding_completed: Optional[bool] = Field(None, description="Onboarding status")
    created_at: datetime = Field(..., description="Account creation time")
    updated_at: datetime = Field(..., description="Last profile update time")
