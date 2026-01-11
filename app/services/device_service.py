"""
VitaFlow API - Smart Device Service.

Handles BLE device registration, readings, and gym equipment (Peloton/Mirror) integration.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from urllib.parse import urlencode
import secrets

import httpx
from sqlalchemy.orm import Session

from app.models.smart_device import (
    SmartDevice, DeviceReading, 
    PelotonWorkout, MirrorWorkout, AccessibilitySettings
)
from app.services.cache import cache_service
from settings import settings

logger = logging.getLogger(__name__)


# ============ Smart Device Service ============

class SmartDeviceService:
    """Service for managing BLE smart devices and their readings."""
    
    SUPPORTED_TYPES = ["smart_scale", "hr_monitor", "bp_cuff", "glucose_monitor", "gym_equipment"]
    
    async def register_device(
        self,
        db: Session,
        user_id: str,
        device_type: str,
        device_name: str,
        ble_address: Optional[str] = None,
        manufacturer: Optional[str] = None,
        model: Optional[str] = None,
    ) -> SmartDevice:
        """
        Register a new smart device for a user.
        
        Args:
            db: Database session.
            user_id: Owner's user ID.
            device_type: Type of device.
            device_name: User-friendly name.
            ble_address: Bluetooth MAC/UUID.
            manufacturer: Device manufacturer.
            model: Device model.
        
        Returns:
            Created SmartDevice.
        """
        if device_type not in self.SUPPORTED_TYPES:
            raise ValueError(f"Unsupported device type: {device_type}")
        
        device = SmartDevice(
            user_id=user_id,
            device_type=device_type,
            device_name=device_name,
            ble_address=ble_address,
            manufacturer=manufacturer,
            model=model,
            is_connected=False,
        )
        db.add(device)
        db.commit()
        db.refresh(device)
        
        logger.info(f"Registered {device_type} '{device_name}' for user {user_id}")
        return device
    
    async def get_user_devices(
        self,
        db: Session,
        user_id: str,
        device_type: Optional[str] = None
    ) -> List[SmartDevice]:
        """Get all devices for a user, optionally filtered by type."""
        query = db.query(SmartDevice).filter(SmartDevice.user_id == user_id)
        if device_type:
            query = query.filter(SmartDevice.device_type == device_type)
        return query.order_by(SmartDevice.created_at.desc()).all()
    
    async def update_device(
        self,
        db: Session,
        device_id: str,
        user_id: str,
        **kwargs
    ) -> Optional[SmartDevice]:
        """Update device properties."""
        device = db.query(SmartDevice).filter(
            SmartDevice.id == device_id,
            SmartDevice.user_id == user_id
        ).first()
        
        if not device:
            return None
        
        for key, value in kwargs.items():
            if hasattr(device, key) and value is not None:
                setattr(device, key, value)
        
        db.commit()
        db.refresh(device)
        return device
    
    async def delete_device(
        self,
        db: Session,
        device_id: str,
        user_id: str
    ) -> bool:
        """Delete a device and all its readings."""
        device = db.query(SmartDevice).filter(
            SmartDevice.id == device_id,
            SmartDevice.user_id == user_id
        ).first()
        
        if not device:
            return False
        
        db.delete(device)
        db.commit()
        logger.info(f"Deleted device {device_id} for user {user_id}")
        return True
    
    async def add_reading(
        self,
        db: Session,
        device_id: str,
        user_id: str,
        reading_type: str,
        value: float,
        unit: str,
        timestamp: Optional[datetime] = None,
        notes: Optional[str] = None,
        raw_data: Optional[Dict] = None
    ) -> DeviceReading:
        """
        Add a new reading from a device.
        
        Args:
            db: Database session.
            device_id: Source device ID.
            user_id: Owner's user ID.
            reading_type: Type (weight, body_fat, hr, etc).
            value: Numeric value.
            unit: Unit of measurement.
            timestamp: When reading was taken (default: now).
            notes: Optional notes.
            raw_data: Raw sensor data.
        
        Returns:
            Created DeviceReading.
        """
        reading = DeviceReading(
            device_id=device_id,
            user_id=user_id,
            reading_type=reading_type,
            value=value,
            unit=unit,
            timestamp=timestamp or datetime.now(timezone.utc),
            notes=notes,
            raw_data=raw_data,
        )
        db.add(reading)
        
        # Update device last_reading
        device = db.query(SmartDevice).filter(SmartDevice.id == device_id).first()
        if device:
            device.last_reading = reading.timestamp
        
        db.commit()
        db.refresh(reading)
        
        logger.debug(f"Added {reading_type} reading: {value} {unit}")
        return reading
    
    async def get_readings(
        self,
        db: Session,
        user_id: str,
        device_id: Optional[str] = None,
        reading_type: Optional[str] = None,
        days: int = 30,
        limit: int = 100
    ) -> List[DeviceReading]:
        """Get device readings with filters."""
        since = datetime.now(timezone.utc) - timedelta(days=days)
        
        query = db.query(DeviceReading).filter(
            DeviceReading.user_id == user_id,
            DeviceReading.timestamp >= since
        )
        
        if device_id:
            query = query.filter(DeviceReading.device_id == device_id)
        if reading_type:
            query = query.filter(DeviceReading.reading_type == reading_type)
        
        return query.order_by(DeviceReading.timestamp.desc()).limit(limit).all()


# ============ Peloton Service ============

class PelotonService:
    """Service for Peloton OAuth and workout sync."""
    
    def __init__(self):
        self.client_id = getattr(settings, 'PELOTON_CLIENT_ID', None)
        self.client_secret = getattr(settings, 'PELOTON_CLIENT_SECRET', None)
        self.callback_url = f"{settings.API_BASE_URL}/equipment/peloton/callback"
        self.auth_url = "https://api.onepeloton.com/auth/login"
        self.api_url = "https://api.onepeloton.com/api"
    
    async def get_authorization_url(self, user_id: str) -> str:
        """Generate Peloton authorization URL."""
        state = secrets.token_urlsafe(32)
        await cache_service.set(f"peloton_state:{state}", user_id, ttl_seconds=600)
        
        # Peloton uses username/password auth, not OAuth
        # Return a custom login page URL
        return f"{settings.API_BASE_URL}/equipment/peloton/login?state={state}"
    
    async def authenticate(
        self,
        username: str,
        password: str,
        db: Session,
        user_id: str
    ) -> Dict[str, Any]:
        """Authenticate with Peloton using username/password."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.auth_url,
                json={"username_or_email": username, "password": password}
            )
            
            if response.status_code != 200:
                raise ValueError("Peloton authentication failed")
            
            data = response.json()
            
            # Store session in cache (Peloton uses session cookies)
            await cache_service.set(
                f"peloton_session:{user_id}",
                {
                    "session_id": data.get("session_id"),
                    "user_id": data.get("user_id"),
                },
                ttl_seconds=86400  # 24 hours
            )
            
            return {"status": "connected", "peloton_user_id": data.get("user_id")}
    
    async def sync_workouts(
        self,
        db: Session,
        user_id: str,
        days: int = 30
    ) -> int:
        """Sync recent workouts from Peloton."""
        session = await cache_service.get(f"peloton_session:{user_id}")
        if not session:
            raise ValueError("Not authenticated with Peloton")
        
        async with httpx.AsyncClient() as client:
            # Get workout history
            response = await client.get(
                f"{self.api_url}/user/{session['user_id']}/workouts",
                params={"limit": 50, "page": 0},
                cookies={"peloton_session_id": session["session_id"]}
            )
            
            if response.status_code != 200:
                logger.error(f"Peloton API error: {response.status_code}")
                return 0
            
            data = response.json()
            count = 0
            
            for workout in data.get("data", []):
                # Check if already synced
                existing = db.query(PelotonWorkout).filter(
                    PelotonWorkout.peloton_id == workout["id"]
                ).first()
                
                if existing:
                    continue
                
                # Create new workout record
                pw = PelotonWorkout(
                    user_id=user_id,
                    peloton_id=workout["id"],
                    workout_type=workout.get("fitness_discipline", "unknown"),
                    title=workout.get("title"),
                    instructor=workout.get("instructor_name"),
                    duration_seconds=workout.get("ride", {}).get("duration", 0),
                    calories_burned=workout.get("calories"),
                    avg_heart_rate=workout.get("avg_heart_rate"),
                    max_heart_rate=workout.get("max_heart_rate"),
                    total_output=workout.get("total_work"),
                    started_at=datetime.fromtimestamp(workout.get("start_time", 0), tz=timezone.utc),
                    raw_data=workout,
                )
                db.add(pw)
                count += 1
            
            db.commit()
            logger.info(f"Synced {count} Peloton workouts for user {user_id}")
            return count
    
    async def get_workouts(
        self,
        db: Session,
        user_id: str,
        limit: int = 20
    ) -> List[PelotonWorkout]:
        """Get synced Peloton workouts."""
        return db.query(PelotonWorkout).filter(
            PelotonWorkout.user_id == user_id
        ).order_by(PelotonWorkout.started_at.desc()).limit(limit).all()


# ============ Mirror Service ============

class MirrorService:
    """Service for Mirror/Lululemon Studio OAuth and workout sync."""
    
    def __init__(self):
        self.client_id = getattr(settings, 'MIRROR_CLIENT_ID', None)
        self.client_secret = getattr(settings, 'MIRROR_CLIENT_SECRET', None)
        self.callback_url = f"{settings.API_BASE_URL}/equipment/mirror/callback"
        self.auth_url = "https://api.mirror.co/oauth/authorize"
        self.token_url = "https://api.mirror.co/oauth/token"
        self.api_url = "https://api.mirror.co/api/v1"
    
    async def get_authorization_url(self, user_id: str) -> str:
        """Generate Mirror authorization URL."""
        state = secrets.token_urlsafe(32)
        await cache_service.set(f"mirror_state:{state}", user_id, ttl_seconds=600)
        
        params = {
            "client_id": self.client_id or "vitaflow",
            "response_type": "code",
            "redirect_uri": self.callback_url,
            "state": state,
            "scope": "workouts:read profile:read",
        }
        return f"{self.auth_url}?{urlencode(params)}"
    
    async def exchange_code(
        self,
        code: str,
        db: Session,
        user_id: str
    ) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.callback_url,
                }
            )
            
            if response.status_code != 200:
                raise ValueError("Mirror token exchange failed")
            
            tokens = response.json()
            
            # Store tokens in cache
            await cache_service.set(
                f"mirror_tokens:{user_id}",
                tokens,
                ttl_seconds=tokens.get("expires_in", 3600)
            )
            
            return {"status": "connected"}
    
    async def sync_workouts(
        self,
        db: Session,
        user_id: str,
        days: int = 30
    ) -> int:
        """Sync recent workouts from Mirror."""
        tokens = await cache_service.get(f"mirror_tokens:{user_id}")
        if not tokens:
            raise ValueError("Not authenticated with Mirror")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/workouts",
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
                params={"limit": 50}
            )
            
            if response.status_code != 200:
                logger.error(f"Mirror API error: {response.status_code}")
                return 0
            
            data = response.json()
            count = 0
            
            for workout in data.get("workouts", []):
                existing = db.query(MirrorWorkout).filter(
                    MirrorWorkout.mirror_id == workout["id"]
                ).first()
                
                if existing:
                    continue
                
                mw = MirrorWorkout(
                    user_id=user_id,
                    mirror_id=workout["id"],
                    workout_type=workout.get("type", "unknown"),
                    title=workout.get("title"),
                    instructor=workout.get("instructor"),
                    duration_seconds=workout.get("duration", 0),
                    calories_burned=workout.get("calories"),
                    avg_heart_rate=workout.get("avg_heart_rate"),
                    started_at=datetime.fromisoformat(workout.get("started_at", "2025-01-01T00:00:00Z").replace("Z", "+00:00")),
                    raw_data=workout,
                )
                db.add(mw)
                count += 1
            
            db.commit()
            logger.info(f"Synced {count} Mirror workouts for user {user_id}")
            return count


# ============ Accessibility Service ============

class AccessibilityService:
    """Service for WCAG AA accessibility settings."""
    
    VALID_TEXT_SCALES = range(80, 201)  # 80% to 200%
    VALID_FONTS = ["system", "dyslexic-friendly", "monospace", "serif", "sans-serif"]
    VALID_COLOR_FILTERS = ["none", "protanopia", "deuteranopia", "tritanopia", "achromatopsia"]
    VALID_TOUCH_SIZES = ["normal", "large", "extra-large"]
    
    async def get_settings(
        self,
        db: Session,
        user_id: str
    ) -> AccessibilitySettings:
        """Get or create accessibility settings for a user."""
        settings = db.query(AccessibilitySettings).filter(
            AccessibilitySettings.user_id == user_id
        ).first()
        
        if not settings:
            # Create default settings
            settings = AccessibilitySettings(user_id=user_id)
            db.add(settings)
            db.commit()
            db.refresh(settings)
        
        return settings
    
    async def update_settings(
        self,
        db: Session,
        user_id: str,
        **kwargs
    ) -> AccessibilitySettings:
        """Update accessibility settings with validation."""
        settings = await self.get_settings(db, user_id)
        
        # Validate inputs
        if "text_scale_percent" in kwargs:
            scale = kwargs["text_scale_percent"]
            if scale not in self.VALID_TEXT_SCALES:
                raise ValueError(f"Text scale must be 80-200%, got {scale}")
        
        if "font_family" in kwargs:
            font = kwargs["font_family"]
            if font not in self.VALID_FONTS:
                raise ValueError(f"Invalid font: {font}")
        
        if "color_filter" in kwargs:
            filter_type = kwargs["color_filter"]
            if filter_type not in self.VALID_COLOR_FILTERS:
                raise ValueError(f"Invalid color filter: {filter_type}")
        
        if "touch_target_size" in kwargs:
            size = kwargs["touch_target_size"]
            if size not in self.VALID_TOUCH_SIZES:
                raise ValueError(f"Invalid touch size: {size}")
        
        # Apply updates
        for key, value in kwargs.items():
            if hasattr(settings, key) and value is not None:
                setattr(settings, key, value)
        
        db.commit()
        db.refresh(settings)
        
        logger.info(f"Updated accessibility settings for user {user_id}")
        return settings
    
    async def process_voice_command(
        self,
        command: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Process a voice command and return the action.
        
        Supported commands:
        - "start workout" / "begin exercise"
        - "stop" / "pause"
        - "next exercise" / "skip"
        - "show form check"
        - "go to dashboard"
        - "increase text size" / "decrease text size"
        """
        command = command.lower().strip()
        
        command_actions = {
            "start workout": {"action": "navigate", "target": "workouts", "params": {"auto_start": True}},
            "begin exercise": {"action": "navigate", "target": "workouts", "params": {"auto_start": True}},
            "stop": {"action": "control", "command": "stop"},
            "pause": {"action": "control", "command": "pause"},
            "resume": {"action": "control", "command": "resume"},
            "next exercise": {"action": "control", "command": "next"},
            "skip": {"action": "control", "command": "next"},
            "previous": {"action": "control", "command": "previous"},
            "show form check": {"action": "navigate", "target": "form_check"},
            "go to dashboard": {"action": "navigate", "target": "dashboard"},
            "open profile": {"action": "navigate", "target": "profile"},
            "increase text size": {"action": "accessibility", "setting": "text_scale_percent", "change": 10},
            "decrease text size": {"action": "accessibility", "setting": "text_scale_percent", "change": -10},
            "enable high contrast": {"action": "accessibility", "setting": "high_contrast_enabled", "value": True},
            "disable high contrast": {"action": "accessibility", "setting": "high_contrast_enabled", "value": False},
        }
        
        for pattern, action in command_actions.items():
            if pattern in command:
                return {"recognized": True, "command": pattern, **action}
        
        return {"recognized": False, "command": command, "message": "Command not recognized"}


# Service instances
smart_device_service = SmartDeviceService()
peloton_service = PelotonService()
mirror_service = MirrorService()
accessibility_service = AccessibilityService()
