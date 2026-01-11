"""
VitaFlow API - Wearable Services.

OAuth integration services for Apple Health, Google Fit, Fitbit, and Garmin.
Handles authorization flows, token management, and health data synchronization.
"""

import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from settings import settings
from app.models.wearable import WearableDevice, HealthMetric
from app.services.cache import cache_service

logger = logging.getLogger(__name__)


# Token encryption
def get_cipher() -> Fernet:
    """Get Fernet cipher for token encryption."""
    key = settings.SECRET_KEY[:32].encode().ljust(32, b'=')
    return Fernet(key)


def encrypt_token(token: str) -> str:
    """Encrypt OAuth token for storage."""
    cipher = get_cipher()
    return cipher.encrypt(token.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    """Decrypt stored OAuth token."""
    cipher = get_cipher()
    return cipher.decrypt(encrypted.encode()).decode()


def generate_state() -> str:
    """Generate random state for OAuth CSRF protection."""
    return secrets.token_urlsafe(32)


class WearableServiceBase:
    """Base class for wearable OAuth services."""
    
    device_type: str = ""
    
    async def store_state(self, state: str, user_id: str) -> None:
        """Store OAuth state in cache for verification."""
        await cache_service.set(
            f"oauth_state:{state}",
            user_id,
            ttl_seconds=600  # 10 minutes
        )
    
    async def verify_state(self, state: str) -> Optional[str]:
        """Verify OAuth state and return user_id."""
        return await cache_service.get(f"oauth_state:{state}")
    
    async def save_device(
        self,
        db: Session,
        user_id: str,
        device_name: str,
        external_id: Optional[str],
        refresh_token: str
    ) -> WearableDevice:
        """Save connected device to database."""
        device = WearableDevice(
            user_id=user_id,
            device_type=self.device_type,
            device_name=device_name,
            external_device_id=external_id,
            oauth_token=encrypt_token(refresh_token),
            sync_status="active",
            last_sync=datetime.now(timezone.utc)
        )
        db.add(device)
        db.commit()
        db.refresh(device)
        return device
    
    async def save_metrics(
        self,
        db: Session,
        user_id: str,
        device_id: str,
        metrics: List[Dict[str, Any]]
    ) -> int:
        """Save health metrics to database."""
        count = 0
        for m in metrics:
            metric = HealthMetric(
                user_id=user_id,
                device_id=device_id,
                metric_type=m["type"],
                metric_value=str(m["value"]),
                metric_unit=m["unit"],
                timestamp=m["timestamp"],
                raw_data=m.get("raw")
            )
            db.add(metric)
            count += 1
        db.commit()
        return count


class AppleHealthService(WearableServiceBase):
    """Apple Health OAuth integration service."""
    
    device_type = "apple_health"
    
    def __init__(self):
        self.client_id = settings.APPLE_HEALTH_CLIENT_ID
        self.client_secret = settings.APPLE_HEALTH_CLIENT_SECRET
        self.callback_url = f"{settings.API_BASE_URL}/wearables/callback/apple"
        self.auth_url = "https://appleid.apple.com/auth/authorize"
        self.token_url = "https://appleid.apple.com/auth/token"
    
    async def get_authorization_url(self, user_id: str) -> str:
        """Generate Apple Health authorization URL."""
        state = generate_state()
        await self.store_state(state, user_id)
        
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "scope": "name email",  # Apple specific scopes
            "redirect_uri": self.callback_url,
            "state": state,
            "response_mode": "form_post"
        }
        return f"{self.auth_url}?{urlencode(params)}"
    
    async def exchange_code(
        self,
        code: str,
        db: Session,
        user_id: str
    ) -> WearableDevice:
        """Exchange authorization code for tokens and save device."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.callback_url
                }
            )
            response.raise_for_status()
            tokens = response.json()
        
        return await self.save_device(
            db=db,
            user_id=user_id,
            device_name="Apple Health",
            external_id=tokens.get("sub"),
            refresh_token=tokens.get("refresh_token", tokens.get("access_token"))
        )
    
    async def sync_health_data(self, db: Session, device: WearableDevice) -> int:
        """Sync health data from Apple Health (requires native SDK)."""
        # Note: Apple HealthKit requires native iOS SDK
        # Server-side sync is limited - most data comes from mobile app
        logger.info(f"Apple Health sync requested for device {device.id}")
        
        # Return demo data for development
        demo_metrics = [
            {"type": "steps", "value": 8234, "unit": "steps", "timestamp": datetime.now(timezone.utc)},
            {"type": "heart_rate", "value": 72, "unit": "bpm", "timestamp": datetime.now(timezone.utc)},
        ]
        
        return await self.save_metrics(db, str(device.user_id), str(device.id), demo_metrics)


class GoogleFitService(WearableServiceBase):
    """Google Fit OAuth integration service."""
    
    device_type = "google_fit"
    
    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.callback_url = f"{settings.API_BASE_URL}/wearables/callback/google"
        self.auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
        self.fitness_url = "https://www.googleapis.com/fitness/v1/users/me"
    
    async def get_authorization_url(self, user_id: str) -> str:
        """Generate Google Fit authorization URL."""
        state = generate_state()
        await self.store_state(state, user_id)
        
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "scope": " ".join([
                "https://www.googleapis.com/auth/fitness.heart_rate.read",
                "https://www.googleapis.com/auth/fitness.activity.read",
                "https://www.googleapis.com/auth/fitness.sleep.read",
                "https://www.googleapis.com/auth/fitness.body.read"
            ]),
            "redirect_uri": self.callback_url,
            "state": state,
            "access_type": "offline",
            "prompt": "consent"
        }
        return f"{self.auth_url}?{urlencode(params)}"
    
    async def exchange_code(
        self,
        code: str,
        db: Session,
        user_id: str
    ) -> WearableDevice:
        """Exchange authorization code for tokens."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.callback_url
                }
            )
            response.raise_for_status()
            tokens = response.json()
        
        return await self.save_device(
            db=db,
            user_id=user_id,
            device_name="Google Fit",
            external_id=None,
            refresh_token=tokens.get("refresh_token")
        )
    
    async def refresh_access_token(self, refresh_token: str) -> str:
        """Get fresh access token using refresh token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token"
                }
            )
            response.raise_for_status()
            return response.json()["access_token"]
    
    async def sync_health_data(self, db: Session, device: WearableDevice) -> int:
        """Sync health data from Google Fit."""
        try:
            refresh_token = decrypt_token(device.oauth_token)
            access_token = await self.refresh_access_token(refresh_token)
            
            # Fetch data from last 7 days
            now = datetime.now(timezone.utc)
            start = now - timedelta(days=7)
            
            async with httpx.AsyncClient() as client:
                # Fetch steps
                steps_response = await client.post(
                    f"{self.fitness_url}/dataset:aggregate",
                    headers={"Authorization": f"Bearer {access_token}"},
                    json={
                        "aggregateBy": [{"dataTypeName": "com.google.step_count.delta"}],
                        "bucketByTime": {"durationMillis": 86400000},  # 1 day
                        "startTimeMillis": int(start.timestamp() * 1000),
                        "endTimeMillis": int(now.timestamp() * 1000)
                    }
                )
                
                metrics = []
                if steps_response.status_code == 200:
                    data = steps_response.json()
                    for bucket in data.get("bucket", []):
                        for dataset in bucket.get("dataset", []):
                            for point in dataset.get("point", []):
                                value = point.get("value", [{}])[0].get("intVal", 0)
                                timestamp = datetime.fromtimestamp(
                                    int(point.get("endTimeNanos", 0)) / 1e9,
                                    tz=timezone.utc
                                )
                                metrics.append({
                                    "type": "steps",
                                    "value": value,
                                    "unit": "steps",
                                    "timestamp": timestamp,
                                    "raw": point
                                })
                
                # Update last sync
                device.last_sync = now
                db.commit()
                
                return await self.save_metrics(db, str(device.user_id), str(device.id), metrics)
                
        except Exception as e:
            logger.error(f"Google Fit sync error: {e}")
            device.sync_status = "error"
            db.commit()
            return 0


class FitbitService(WearableServiceBase):
    """Fitbit OAuth integration service."""
    
    device_type = "fitbit"
    
    def __init__(self):
        self.client_id = settings.FITBIT_CLIENT_ID
        self.client_secret = settings.FITBIT_CLIENT_SECRET
        self.callback_url = f"{settings.API_BASE_URL}/wearables/callback/fitbit"
        self.auth_url = "https://www.fitbit.com/oauth2/authorize"
        self.token_url = "https://api.fitbit.com/oauth2/token"
        self.api_url = "https://api.fitbit.com/1/user"
    
    async def get_authorization_url(self, user_id: str) -> str:
        """Generate Fitbit authorization URL."""
        state = generate_state()
        await self.store_state(state, user_id)
        
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "scope": "heartrate activity sleep weight",
            "redirect_uri": self.callback_url,
            "state": state,
        }
        return f"{self.auth_url}?{urlencode(params)}"
    
    async def exchange_code(
        self,
        code: str,
        db: Session,
        user_id: str
    ) -> WearableDevice:
        """Exchange authorization code for tokens."""
        import base64
        auth_header = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data={
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.callback_url
                }
            )
            response.raise_for_status()
            tokens = response.json()
        
        return await self.save_device(
            db=db,
            user_id=user_id,
            device_name="Fitbit",
            external_id=tokens.get("user_id"),
            refresh_token=tokens.get("refresh_token")
        )
    
    async def refresh_access_token(self, device: WearableDevice, db: Session) -> str:
        """Get fresh access token and update stored refresh token."""
        import base64
        auth_header = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        
        refresh_token = decrypt_token(device.oauth_token)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data={
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token"
                }
            )
            response.raise_for_status()
            tokens = response.json()
        
        # Update stored refresh token
        device.oauth_token = encrypt_token(tokens["refresh_token"])
        db.commit()
        
        return tokens["access_token"]
    
    async def sync_health_data(self, db: Session, device: WearableDevice) -> int:
        """Sync health data from Fitbit."""
        try:
            access_token = await self.refresh_access_token(device, db)
            user_id = device.external_device_id or "-"
            
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            metrics = []
            
            async with httpx.AsyncClient() as client:
                # Fetch steps
                steps_response = await client.get(
                    f"{self.api_url}/{user_id}/activities/date/{today}.json",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                
                if steps_response.status_code == 200:
                    data = steps_response.json()
                    summary = data.get("summary", {})
                    metrics.append({
                        "type": "steps",
                        "value": summary.get("steps", 0),
                        "unit": "steps",
                        "timestamp": datetime.now(timezone.utc),
                        "raw": summary
                    })
                    metrics.append({
                        "type": "calories",
                        "value": summary.get("caloriesOut", 0),
                        "unit": "kcal",
                        "timestamp": datetime.now(timezone.utc)
                    })
                
                # Fetch heart rate
                hr_response = await client.get(
                    f"{self.api_url}/{user_id}/activities/heart/date/{today}/1d.json",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                
                if hr_response.status_code == 200:
                    data = hr_response.json()
                    hr_data = data.get("activities-heart", [{}])[0].get("value", {})
                    resting_hr = hr_data.get("restingHeartRate")
                    if resting_hr:
                        metrics.append({
                            "type": "heart_rate",
                            "value": resting_hr,
                            "unit": "bpm",
                            "timestamp": datetime.now(timezone.utc)
                        })
            
            device.last_sync = datetime.now(timezone.utc)
            db.commit()
            
            return await self.save_metrics(db, str(device.user_id), str(device.id), metrics)
            
        except Exception as e:
            logger.error(f"Fitbit sync error: {e}")
            device.sync_status = "error"
            db.commit()
            return 0


class GarminService(WearableServiceBase):
    """Garmin Connect OAuth integration service."""
    
    device_type = "garmin"
    
    def __init__(self):
        self.consumer_key = settings.GARMIN_CONSUMER_KEY
        self.consumer_secret = settings.GARMIN_CONSUMER_SECRET
        self.callback_url = f"{settings.API_BASE_URL}/wearables/callback/garmin"
        self.request_token_url = "https://connectapi.garmin.com/oauth-service/oauth/request_token"
        self.auth_url = "https://connect.garmin.com/oauthConfirm"
        self.access_token_url = "https://connectapi.garmin.com/oauth-service/oauth/access_token"
    
    async def get_authorization_url(self, user_id: str) -> str:
        """Generate Garmin authorization URL (OAuth 1.0a)."""
        # Garmin uses OAuth 1.0a which requires request token first
        # For simplicity, returning the confirm URL with placeholder
        state = generate_state()
        await self.store_state(state, user_id)
        
        # In production: Implement full OAuth 1.0a flow
        params = {
            "oauth_callback": self.callback_url,
            "state": state
        }
        return f"{self.auth_url}?{urlencode(params)}"
    
    async def exchange_code(
        self,
        code: str,
        db: Session,
        user_id: str
    ) -> WearableDevice:
        """Exchange OAuth verifier for access token."""
        # Garmin uses OAuth 1.0a - simplified for demo
        return await self.save_device(
            db=db,
            user_id=user_id,
            device_name="Garmin Connect",
            external_id=None,
            refresh_token=code  # Would be actual token in production
        )
    
    async def sync_health_data(self, db: Session, device: WearableDevice) -> int:
        """Sync health data from Garmin."""
        logger.info(f"Garmin sync requested for device {device.id}")
        
        # Demo data - Garmin API requires OAuth 1.0a signatures
        demo_metrics = [
            {"type": "steps", "value": 9500, "unit": "steps", "timestamp": datetime.now(timezone.utc)},
            {"type": "heart_rate", "value": 68, "unit": "bpm", "timestamp": datetime.now(timezone.utc)},
            {"type": "calories", "value": 2100, "unit": "kcal", "timestamp": datetime.now(timezone.utc)},
        ]
        
        device.last_sync = datetime.now(timezone.utc)
        db.commit()
        
        return await self.save_metrics(db, str(device.user_id), str(device.id), demo_metrics)


# Service factory
def get_wearable_service(device_type: str) -> WearableServiceBase:
    """Get the appropriate wearable service for a device type."""
    services = {
        "apple_health": AppleHealthService,
        "google_fit": GoogleFitService,
        "fitbit": FitbitService,
        "garmin": GarminService,
    }
    service_class = services.get(device_type)
    if not service_class:
        raise ValueError(f"Unknown device type: {device_type}")
    return service_class()
