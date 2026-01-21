"""
VitaFlow API - Real-Time WebSocket Sync Service.

Handles real-time health data synchronization with connected wearable devices.
Uses Socket.IO for bidirectional communication with mobile/web clients.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.wearable import WearableDevice
from app.models.wearable import WearableDevice
from app.services.wearable_services import get_wearable_service
from app.websockets.connection_manager import manager

logger = logging.getLogger(__name__)


class RealtimeSyncService:
    """
    Real-time health data sync service using polling and WebSocket notifications.
    
    Manages background sync tasks for connected wearable devices and emits
    updates to clients via Socket.IO when new data is available.
    """
    
    # Sync intervals per device type (in seconds)
    SYNC_INTERVALS = {
        "apple_health": 5 * 60,      # 5 minutes
        "google_fit": 5 * 60,        # 5 minutes
        "fitbit": 15 * 60,           # 15 minutes (API rate limit)
        "garmin": 30 * 60,           # 30 minutes
        "smart_scale": 24 * 60 * 60, # Once per day
    }
    
    def __init__(self):
        """
        Initialize the real-time sync service.
        """
        self.active_syncs: Dict[str, asyncio.Task] = {}
        self.logger = logging.getLogger(__name__)
    
    def get_polling_interval(self, device_type: str) -> int:
        """Get sync interval in seconds for a device type."""
        return self.SYNC_INTERVALS.get(device_type, 60 * 60)  # Default 1 hour
    
    async def start_device_sync(
        self,
        device: WearableDevice,
        db_session_factory
    ) -> None:
        """
        Start background sync for a single device.
        
        Args:
            device: WearableDevice instance to sync.
            db_session_factory: Callable that returns a new DB session.
        """
        device_id = str(device.id)
        
        if device_id in self.active_syncs:
            self.logger.info(f"Sync already active for device {device_id}")
            return
        
        async def sync_loop():
            interval = self.get_polling_interval(device.device_type)
            
            while True:
                try:
                    # Get fresh DB session
                    db = db_session_factory()
                    
                    # Refresh device from DB
                    current_device = db.query(WearableDevice).filter(
                        WearableDevice.id == device.id
                    ).first()
                    
                    if not current_device or current_device.sync_status != "active":
                        self.logger.info(f"Device {device_id} no longer active, stopping sync")
                        break
                    
                    # Sync data
                    service = get_wearable_service(current_device.device_type)
                    metrics_count = await service.sync_health_data(db, current_device)
                    
                    # Emit update to client
                    if metrics_count > 0:
                        await self.emit_update(
                            str(current_device.user_id),
                            {
                                "event": "health_metrics_updated",
                                "data": {
                                    "device_id": device_id,
                                    "device_type": current_device.device_type,
                                    "metrics_synced": metrics_count,
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                }
                            }
                        )
                    
                    db.close()
                    
                except Exception as e:
                    self.logger.error(f"Sync error for device {device_id}: {e}")
                
                # Wait for next sync interval
                await asyncio.sleep(interval)
        
        # Start background task
        task = asyncio.create_task(sync_loop())
        self.active_syncs[device_id] = task
        self.logger.info(f"Started sync for device {device_id} ({device.device_type})")
    
    async def stop_device_sync(self, device_id: str) -> None:
        """Stop background sync for a device."""
        if device_id in self.active_syncs:
            self.active_syncs[device_id].cancel()
            del self.active_syncs[device_id]
            self.logger.info(f"Stopped sync for device {device_id}")
    
    async def start_user_syncs(
        self,
        user_id: str,
        db: Session,
        db_session_factory
    ) -> int:
        """
        Start syncs for all active devices of a user.
        
        Args:
            user_id: User ID to start syncs for.
            db: Database session.
            db_session_factory: Callable for creating new sessions.
        
        Returns:
            Number of sync tasks started.
        """
        devices = db.query(WearableDevice).filter(
            WearableDevice.user_id == user_id,
            WearableDevice.sync_status == "active"
        ).all()
        
        count = 0
        for device in devices:
            await self.start_device_sync(device, db_session_factory)
            count += 1
        
        self.logger.info(f"Started {count} sync tasks for user {user_id}")
        return count
    
    async def stop_user_syncs(self, user_id: str, db: Session) -> None:
        """Stop all syncs for a user."""
        devices = db.query(WearableDevice).filter(
            WearableDevice.user_id == user_id
        ).all()
        
        for device in devices:
            await self.stop_device_sync(str(device.id))
    
    async def emit_update(self, user_id: str, data: Dict[str, Any]) -> None:
        """
        Emit health metrics update to user's connected clients.
        
        Args:
            user_id: Target user ID.
            data: Update payload.
        """
        try:
            # Emit to user via ConnectionManager
            await manager.send_personal_message(data, user_id)
            self.logger.debug(f"Emitted update to user {user_id}")
        except Exception as e:
            self.logger.error(f"Failed to emit update: {e}")
    
    async def manual_sync(
        self,
        device: WearableDevice,
        db: Session
    ) -> Dict[str, Any]:
        """
        Trigger manual sync for a device.
        
        Args:
            device: Device to sync.
            db: Database session.
        
        Returns:
            Sync result with metrics count.
        """
        try:
            service = get_wearable_service(device.device_type)
            metrics_count = await service.sync_health_data(db, device)
            
            # Emit update
            await self.emit_update(
                str(device.user_id),
                {
                    "event": "health_metrics_updated",
                    "data": {
                        "device_id": str(device.id),
                        "device_type": device.device_type,
                        "metrics_synced": metrics_count,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "manual": True,
                    }
                }
            )
            
            return {
                "status": "success",
                "metrics_synced": metrics_count,
                "last_sync": datetime.now(timezone.utc).isoformat(),
            }
            
        except Exception as e:
            self.logger.error(f"Manual sync failed: {e}")
            return {
                "status": "error",
                "error": str(e),
            }
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status for all active syncs."""
        return {
            "active_syncs": len(self.active_syncs),
            "device_ids": list(self.active_syncs.keys()),
        }


# Global instance (initialized without socketio, set later)
realtime_sync_service = RealtimeSyncService()
