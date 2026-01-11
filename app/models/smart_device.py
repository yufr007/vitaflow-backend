"""
VitaFlow API - Smart Device Models.

Database models for Bluetooth LE smart devices, readings, gym equipment,
and accessibility settings.
"""

from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Float, Text, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class SmartDevice(Base):
    """
    Smart device model for Bluetooth LE devices.
    
    Supports: Smart scales, heart rate monitors, blood pressure cuffs,
    glucose monitors, and gym equipment.
    """
    
    __tablename__ = "smart_devices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    device_type = Column(String(50), nullable=False, index=True)  # smart_scale, hr_monitor, bp_cuff, glucose_monitor
    device_name = Column(String(100), nullable=False)
    manufacturer = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    
    # Bluetooth
    ble_address = Column(String(50), nullable=True)  # MAC address or UUID
    ble_service_uuid = Column(String(50), nullable=True)
    
    # Status
    is_connected = Column(Boolean, default=False, nullable=False)
    battery_level = Column(Integer, nullable=True)
    firmware_version = Column(String(50), nullable=True)
    last_reading = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    settings_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="smart_devices")
    readings = relationship("DeviceReading", back_populates="device", cascade="all, delete-orphan")


class DeviceReading(Base):
    """
    Device reading model for sensor data.
    
    Stores individual readings from smart devices with timestamps.
    """
    
    __tablename__ = "device_readings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("smart_devices.id", ondelete="CASCADE"), nullable=False, index=True)
    
    reading_type = Column(String(50), nullable=False, index=True)  # weight, body_fat, bmi, hr, bp_systolic, bp_diastolic, glucose
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)  # kg, %, bpm, mmHg, mg/dL
    
    # Additional context
    notes = Column(Text, nullable=True)
    raw_data = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="device_readings")
    device = relationship("SmartDevice", back_populates="readings")


class PelotonWorkout(Base):
    """
    Peloton workout sync model.
    
    Stores workouts synced from Peloton API.
    """
    
    __tablename__ = "peloton_workouts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    peloton_id = Column(String(100), nullable=False, unique=True)  # Peloton's workout ID
    workout_type = Column(String(50), nullable=False)  # cycling, running, strength, yoga
    title = Column(String(200), nullable=True)
    instructor = Column(String(100), nullable=True)
    
    duration_seconds = Column(Integer, nullable=False)
    calories_burned = Column(Integer, nullable=True)
    avg_heart_rate = Column(Integer, nullable=True)
    max_heart_rate = Column(Integer, nullable=True)
    total_output = Column(Integer, nullable=True)  # kJ for cycling
    avg_cadence = Column(Integer, nullable=True)
    avg_resistance = Column(Integer, nullable=True)
    distance_miles = Column(Float, nullable=True)
    
    started_at = Column(DateTime(timezone=True), nullable=False)
    raw_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="peloton_workouts")


class MirrorWorkout(Base):
    """
    Mirror workout sync model.
    
    Stores workouts synced from Mirror API.
    """
    
    __tablename__ = "mirror_workouts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    mirror_id = Column(String(100), nullable=False, unique=True)
    workout_type = Column(String(50), nullable=False)  # strength, cardio, yoga, boxing
    title = Column(String(200), nullable=True)
    instructor = Column(String(100), nullable=True)
    
    duration_seconds = Column(Integer, nullable=False)
    calories_burned = Column(Integer, nullable=True)
    avg_heart_rate = Column(Integer, nullable=True)
    
    started_at = Column(DateTime(timezone=True), nullable=False)
    raw_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="mirror_workouts")


class AccessibilitySettings(Base):
    """
    User accessibility settings model.
    
    WCAG AA compliant settings for each user.
    """
    
    __tablename__ = "accessibility_settings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Visual
    high_contrast_enabled = Column(Boolean, default=False, nullable=False)
    text_scale_percent = Column(Integer, default=100, nullable=False)  # 80-200%
    font_family = Column(String(50), default="system", nullable=False)  # system, dyslexic-friendly, monospace
    color_filter = Column(String(50), default="none", nullable=False)  # none, protanopia, deuteranopia, tritanopia
    reduce_motion = Column(Boolean, default=False, nullable=False)
    
    # Audio
    screen_reader_enabled = Column(Boolean, default=False, nullable=False)
    captions_enabled = Column(Boolean, default=True, nullable=False)
    audio_descriptions_enabled = Column(Boolean, default=False, nullable=False)
    
    # Interaction
    voice_commands_enabled = Column(Boolean, default=False, nullable=False)
    haptic_feedback_enabled = Column(Boolean, default=True, nullable=False)
    touch_target_size = Column(String(20), default="normal", nullable=False)  # normal, large, extra-large
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="accessibility_settings")
