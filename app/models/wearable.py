"""
VitaFlow API - Wearable Device ORM Model.

Stores connected wearable devices (Apple Health, Google Fit, Fitbit, Garmin)
with encrypted OAuth tokens and sync status.
"""

from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional

from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Boolean, Integer, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class WearableDevice(Base):
    """
    Wearable device model for OAuth-connected health data sources.
    
    Attributes:
        id: Unique identifier (UUID).
        user_id: Owner user's ID.
        device_type: Type of wearable (apple_health, google_fit, fitbit, garmin).
        device_name: User-friendly name for the device.
        external_device_id: External platform's device/user ID.
        oauth_token: Encrypted refresh token for API access.
        sync_status: Current sync status (active/paused/error).
        last_sync: Last successful data sync timestamp.
        battery_level: Current battery level (if available).
        created_at: Connection timestamp.
        updated_at: Last update timestamp.
    """
    
    __tablename__ = "wearable_devices"
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False
    )
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    device_type = Column(
        String(50),
        nullable=False,
        index=True
    )  # apple_health, google_fit, fitbit, garmin, smart_scale
    
    device_name = Column(
        String(100),
        nullable=True
    )
    
    external_device_id = Column(
        String(255),
        nullable=True
    )
    
    oauth_token = Column(
        Text,
        nullable=True
    )  # Encrypted refresh token
    
    oauth_token_expires = Column(
        DateTime(timezone=True),
        nullable=True
    )
    
    sync_status = Column(
        String(20),
        default="active",
        nullable=False
    )  # active, paused, error, pending
    
    last_sync = Column(
        DateTime(timezone=True),
        nullable=True
    )
    
    battery_level = Column(
        Integer,
        nullable=True
    )
    
    metadata_json = Column(
        JSON,
        nullable=True
    )  # Additional device-specific data
    
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    
    # Relationships
    user = relationship("User", back_populates="wearable_devices")
    health_metrics = relationship("HealthMetric", back_populates="device", cascade="all, delete-orphan")


class HealthMetric(Base):
    """
    Health metric data points synced from wearable devices.
    
    Stores individual data points (heart rate, steps, sleep, calories)
    with timestamps for historical tracking and health score calculation.
    
    Attributes:
        id: Unique identifier (UUID).
        user_id: Owner user's ID.
        device_id: Source wearable device ID.
        metric_type: Type of metric (heart_rate, steps, sleep, calories, weight, etc).
        metric_value: Numeric value of the metric.
        metric_unit: Unit of measurement (bpm, steps, hours, kcal, kg, etc).
        timestamp: When the metric was recorded.
        raw_data: Original data from the wearable API (JSON).
    """
    
    __tablename__ = "health_metrics"
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False
    )
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    device_id = Column(
        UUID(as_uuid=True),
        ForeignKey("wearable_devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    metric_type = Column(
        String(50),
        nullable=False,
        index=True
    )  # heart_rate, steps, sleep, calories, weight, body_fat, etc
    
    metric_value = Column(
        String(50),  # Store as string to handle different formats
        nullable=False
    )
    
    metric_unit = Column(
        String(20),
        nullable=False
    )  # bpm, steps, hours, kcal, kg, %, etc
    
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    
    raw_data = Column(
        JSON,
        nullable=True
    )
    
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    
    # Relationships
    user = relationship("User", back_populates="health_metrics")
    device = relationship("WearableDevice", back_populates="health_metrics")
