# app/routes/devices.py
"""
VitaFlow API - Smart Devices, Equipment & Accessibility.
Modified to use MongoDB/Beanie.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid
import logging

from app.models.mongodb import (
    UserDocument,
    SmartDeviceDocument,
    DeviceReadingDocument,
    AccessibilitySettingsDocument
)
from app.dependencies import get_current_user_id
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ============ Schemas ============

class DeviceResponse(BaseModel):
    id: str
    device_type: str
    device_name: str
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    is_connected: bool = False
    battery_level: Optional[int] = None
    last_reading: Optional[datetime] = None

class DeviceListResponse(BaseModel):
    devices: List[DeviceResponse]

class DeviceConnectRequest(BaseModel):
    provider: str

class DeviceSyncResponse(BaseModel):
    status: str
    synced_count: int

class AccessibilitySettingsResponse(BaseModel):
    high_contrast_enabled: bool
    text_scale_percent: int
    font_family: str
    color_filter: str
    reduce_motion: bool
    screen_reader_enabled: bool
    captions_enabled: bool

# ============ Routers ============

router = APIRouter()

@router.get("/list", response_model=DeviceListResponse)
async def list_devices(user_id: str = Depends(get_current_user_id)):
    """List all registered smart devices for the user."""
    devices = await SmartDeviceDocument.find(
        SmartDeviceDocument.user_id == uuid.UUID(user_id)
    ).to_list()
    
    return DeviceListResponse(
        devices=[
            DeviceResponse(
                id=str(d.uid),
                device_type=d.device_type,
                device_name=d.device_name,
                manufacturer=d.manufacturer,
                model=d.model,
                is_connected=d.is_connected,
                battery_level=d.battery_level,
                last_reading=d.last_reading
            ) for d in devices
        ]
    )

@router.post("/connect")
async def connect_device(
    request: DeviceConnectRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Simulate connecting a device/provider."""
    # Create or update device record
    existing = await SmartDeviceDocument.find_one(
        SmartDeviceDocument.user_id == uuid.UUID(user_id),
        SmartDeviceDocument.device_type == request.provider
    )
    
    if not existing:
        new_device = SmartDeviceDocument(
            user_id=uuid.UUID(user_id),
            device_type=request.provider,
            device_name=f"{request.provider.capitalize()} Device",
            is_connected=True,
            battery_level=85
        )
        await new_device.insert()
        device_id = str(new_device.uid)
    else:
        existing.is_connected = True
        await existing.save()
        device_id = str(existing.uid)
        
    return {"status": "connected", "device_id": device_id}

@router.post("/disconnect")
async def disconnect_device(
    request: DeviceConnectRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Simulate disconnecting a device/provider."""
    device = await SmartDeviceDocument.find_one(
        SmartDeviceDocument.user_id == uuid.UUID(user_id),
        SmartDeviceDocument.device_type == request.provider
    )
    
    if device:
        device.is_connected = False
        await device.save()
        
    return {"status": "disconnected"}

@router.post("/sync", response_model=DeviceSyncResponse)
async def sync_device(
    request: DeviceConnectRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Simulate syncing data from a device/provider."""
    # Find device
    device = await SmartDeviceDocument.find_one(
        SmartDeviceDocument.user_id == uuid.UUID(user_id),
        SmartDeviceDocument.device_type == request.provider
    )
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not connected")
    
    # Simulate adding a reading
    if request.provider == "apple_watch" or request.provider == "garmin":
        reading = DeviceReadingDocument(
            user_id=uuid.UUID(user_id),
            device_id=device.uid,
            reading_type="hr",
            value=72.0,
            unit="bpm"
        )
        await reading.insert()
        device.last_reading = reading.timestamp
        await device.save()
        return DeviceSyncResponse(status="success", synced_count=1)
        
    return DeviceSyncResponse(status="success", synced_count=0)

# ============ Accessibility Routers ============

@router.get("/accessibility/settings", response_model=AccessibilitySettingsResponse)
async def get_a11y_settings(user_id: str = Depends(get_current_user_id)):
    """Get accessibility settings."""
    settings = await AccessibilitySettingsDocument.find_one(
        AccessibilitySettingsDocument.user_id == uuid.UUID(user_id)
    )
    
    if not settings:
        settings = AccessibilitySettingsDocument(user_id=uuid.UUID(user_id))
        await settings.insert()
        
    return AccessibilitySettingsResponse(
        high_contrast_enabled=settings.high_contrast_enabled,
        text_scale_percent=settings.text_scale_percent,
        font_family=settings.font_family,
        color_filter=settings.color_filter,
        reduce_motion=settings.reduce_motion,
        screen_reader_enabled=settings.screen_reader_enabled,
        captions_enabled=settings.captions_enabled
    )
