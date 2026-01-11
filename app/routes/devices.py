"""
VitaFlow API - Smart Devices & Accessibility Routes.

Phase 3 API endpoints for BLE devices, gym equipment, and WCAG AA accessibility.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import logging

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.smart_device import (
    SmartDevice, DeviceReading, PelotonWorkout, MirrorWorkout, AccessibilitySettings
)
from app.services.device_service import (
    smart_device_service, peloton_service, mirror_service, accessibility_service
)

logger = logging.getLogger(__name__)


# ============ Pydantic Schemas ============

class DeviceRegisterRequest(BaseModel):
    device_type: str = Field(..., description="smart_scale, hr_monitor, bp_cuff, glucose_monitor")
    device_name: str
    ble_address: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None


class DeviceResponse(BaseModel):
    id: str
    device_type: str
    device_name: str
    manufacturer: Optional[str]
    model: Optional[str]
    is_connected: bool
    battery_level: Optional[int]
    last_reading: Optional[datetime]
    created_at: datetime


class ReadingRequest(BaseModel):
    reading_type: str = Field(..., description="weight, body_fat, hr, bp_systolic, bp_diastolic, glucose")
    value: float
    unit: str
    timestamp: Optional[datetime] = None
    notes: Optional[str] = None


class ReadingResponse(BaseModel):
    id: str
    reading_type: str
    value: float
    unit: str
    timestamp: datetime
    notes: Optional[str]


class PelotonLoginRequest(BaseModel):
    username: str
    password: str


class WorkoutResponse(BaseModel):
    id: str
    workout_type: str
    title: Optional[str]
    instructor: Optional[str]
    duration_seconds: int
    calories_burned: Optional[int]
    started_at: datetime


class AccessibilitySettingsRequest(BaseModel):
    high_contrast_enabled: Optional[bool] = None
    text_scale_percent: Optional[int] = Field(None, ge=80, le=200)
    font_family: Optional[str] = None
    color_filter: Optional[str] = None
    reduce_motion: Optional[bool] = None
    screen_reader_enabled: Optional[bool] = None
    captions_enabled: Optional[bool] = None
    audio_descriptions_enabled: Optional[bool] = None
    voice_commands_enabled: Optional[bool] = None
    haptic_feedback_enabled: Optional[bool] = None
    touch_target_size: Optional[str] = None


class AccessibilitySettingsResponse(BaseModel):
    high_contrast_enabled: bool
    text_scale_percent: int
    font_family: str
    color_filter: str
    reduce_motion: bool
    screen_reader_enabled: bool
    captions_enabled: bool
    audio_descriptions_enabled: bool
    voice_commands_enabled: bool
    haptic_feedback_enabled: bool
    touch_target_size: str


class VoiceCommandRequest(BaseModel):
    command: str


class VoiceCommandResponse(BaseModel):
    recognized: bool
    command: str
    action: Optional[str] = None
    target: Optional[str] = None
    message: Optional[str] = None


# ============ Smart Device Routes ============

devices_router = APIRouter(prefix="/devices", tags=["smart-devices"])


@devices_router.post("/register", response_model=DeviceResponse)
async def register_device(
    request: DeviceRegisterRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Register a new smart device (scale, HR monitor, etc)."""
    try:
        device = await smart_device_service.register_device(
            db=db,
            user_id=str(current_user.id),
            device_type=request.device_type,
            device_name=request.device_name,
            ble_address=request.ble_address,
            manufacturer=request.manufacturer,
            model=request.model,
        )
        return DeviceResponse(
            id=str(device.id),
            device_type=device.device_type,
            device_name=device.device_name,
            manufacturer=device.manufacturer,
            model=device.model,
            is_connected=device.is_connected,
            battery_level=device.battery_level,
            last_reading=device.last_reading,
            created_at=device.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@devices_router.get("/list", response_model=List[DeviceResponse])
async def list_devices(
    device_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all registered smart devices."""
    devices = await smart_device_service.get_user_devices(
        db=db,
        user_id=str(current_user.id),
        device_type=device_type,
    )
    return [
        DeviceResponse(
            id=str(d.id),
            device_type=d.device_type,
            device_name=d.device_name,
            manufacturer=d.manufacturer,
            model=d.model,
            is_connected=d.is_connected,
            battery_level=d.battery_level,
            last_reading=d.last_reading,
            created_at=d.created_at,
        )
        for d in devices
    ]


@devices_router.delete("/{device_id}")
async def delete_device(
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a smart device and all its readings."""
    success = await smart_device_service.delete_device(
        db=db,
        device_id=device_id,
        user_id=str(current_user.id),
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return {"status": "deleted", "device_id": device_id}


@devices_router.post("/{device_id}/reading", response_model=ReadingResponse)
async def add_reading(
    device_id: str,
    request: ReadingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a new reading from a device."""
    reading = await smart_device_service.add_reading(
        db=db,
        device_id=device_id,
        user_id=str(current_user.id),
        reading_type=request.reading_type,
        value=request.value,
        unit=request.unit,
        timestamp=request.timestamp,
        notes=request.notes,
    )
    return ReadingResponse(
        id=str(reading.id),
        reading_type=reading.reading_type,
        value=reading.value,
        unit=reading.unit,
        timestamp=reading.timestamp,
        notes=reading.notes,
    )


@devices_router.get("/{device_id}/readings", response_model=List[ReadingResponse])
async def get_readings(
    device_id: str,
    reading_type: Optional[str] = None,
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get readings from a specific device."""
    readings = await smart_device_service.get_readings(
        db=db,
        user_id=str(current_user.id),
        device_id=device_id,
        reading_type=reading_type,
        days=days,
    )
    return [
        ReadingResponse(
            id=str(r.id),
            reading_type=r.reading_type,
            value=r.value,
            unit=r.unit,
            timestamp=r.timestamp,
            notes=r.notes,
        )
        for r in readings
    ]


# ============ Equipment Routes (Peloton/Mirror) ============

equipment_router = APIRouter(prefix="/equipment", tags=["gym-equipment"])


@equipment_router.get("/peloton/connect")
async def connect_peloton(
    current_user: User = Depends(get_current_user),
):
    """Get Peloton connection URL."""
    auth_url = await peloton_service.get_authorization_url(str(current_user.id))
    return {"auth_url": auth_url, "status": "pending"}


@equipment_router.post("/peloton/login")
async def login_peloton(
    request: PelotonLoginRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Authenticate with Peloton using username/password."""
    try:
        result = await peloton_service.authenticate(
            username=request.username,
            password=request.password,
            db=db,
            user_id=str(current_user.id),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@equipment_router.post("/peloton/sync")
async def sync_peloton(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sync workouts from Peloton."""
    try:
        count = await peloton_service.sync_workouts(
            db=db,
            user_id=str(current_user.id),
        )
        return {"status": "synced", "workouts_synced": count}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@equipment_router.get("/peloton/workouts", response_model=List[WorkoutResponse])
async def get_peloton_workouts(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get synced Peloton workouts."""
    workouts = await peloton_service.get_workouts(
        db=db,
        user_id=str(current_user.id),
        limit=limit,
    )
    return [
        WorkoutResponse(
            id=str(w.id),
            workout_type=w.workout_type,
            title=w.title,
            instructor=w.instructor,
            duration_seconds=w.duration_seconds,
            calories_burned=w.calories_burned,
            started_at=w.started_at,
        )
        for w in workouts
    ]


@equipment_router.get("/mirror/connect")
async def connect_mirror(
    current_user: User = Depends(get_current_user),
):
    """Get Mirror connection URL."""
    auth_url = await mirror_service.get_authorization_url(str(current_user.id))
    return {"auth_url": auth_url, "status": "pending"}


@equipment_router.get("/mirror/callback")
async def mirror_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Handle Mirror OAuth callback."""
    if error:
        return HTMLResponse(f"<h1>Connection Failed</h1><p>{error}</p>")
    
    if not code or not state:
        return HTMLResponse("<h1>Invalid callback</h1>")
    
    from app.services.cache import cache_service
    user_id = await cache_service.get(f"mirror_state:{state}")
    
    if not user_id:
        return HTMLResponse("<h1>Session Expired</h1>")
    
    try:
        await mirror_service.exchange_code(code, db, user_id)
        return HTMLResponse("""
            <html>
                <body style="font-family: system-ui; padding: 40px; text-align: center;">
                    <h1>✅ Mirror Connected!</h1>
                    <p>You can close this window.</p>
                </body>
            </html>
        """)
    except Exception as e:
        return HTMLResponse(f"<h1>Error</h1><p>{str(e)}</p>")


@equipment_router.post("/mirror/sync")
async def sync_mirror(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sync workouts from Mirror."""
    try:
        count = await mirror_service.sync_workouts(
            db=db,
            user_id=str(current_user.id),
        )
        return {"status": "synced", "workouts_synced": count}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============ Accessibility Routes ============

a11y_router = APIRouter(prefix="/accessibility", tags=["accessibility"])


@a11y_router.get("/settings", response_model=AccessibilitySettingsResponse)
async def get_accessibility_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get WCAG AA accessibility settings."""
    settings = await accessibility_service.get_settings(
        db=db,
        user_id=str(current_user.id),
    )
    return AccessibilitySettingsResponse(
        high_contrast_enabled=settings.high_contrast_enabled,
        text_scale_percent=settings.text_scale_percent,
        font_family=settings.font_family,
        color_filter=settings.color_filter,
        reduce_motion=settings.reduce_motion,
        screen_reader_enabled=settings.screen_reader_enabled,
        captions_enabled=settings.captions_enabled,
        audio_descriptions_enabled=settings.audio_descriptions_enabled,
        voice_commands_enabled=settings.voice_commands_enabled,
        haptic_feedback_enabled=settings.haptic_feedback_enabled,
        touch_target_size=settings.touch_target_size,
    )


@a11y_router.put("/settings", response_model=AccessibilitySettingsResponse)
async def update_accessibility_settings(
    request: AccessibilitySettingsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update WCAG AA accessibility settings."""
    try:
        settings = await accessibility_service.update_settings(
            db=db,
            user_id=str(current_user.id),
            **request.model_dump(exclude_none=True),
        )
        return AccessibilitySettingsResponse(
            high_contrast_enabled=settings.high_contrast_enabled,
            text_scale_percent=settings.text_scale_percent,
            font_family=settings.font_family,
            color_filter=settings.color_filter,
            reduce_motion=settings.reduce_motion,
            screen_reader_enabled=settings.screen_reader_enabled,
            captions_enabled=settings.captions_enabled,
            audio_descriptions_enabled=settings.audio_descriptions_enabled,
            voice_commands_enabled=settings.voice_commands_enabled,
            haptic_feedback_enabled=settings.haptic_feedback_enabled,
            touch_target_size=settings.touch_target_size,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@a11y_router.post("/voice-command", response_model=VoiceCommandResponse)
async def process_voice_command(
    request: VoiceCommandRequest,
    current_user: User = Depends(get_current_user),
):
    """Process a voice command and return the action."""
    result = await accessibility_service.process_voice_command(
        command=request.command,
        user_id=str(current_user.id),
    )
    return VoiceCommandResponse(**result)
