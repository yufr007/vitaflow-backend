"""
VitaFlow Session Management Service.

Redis-backed session storage for enhanced JWT functionality:
- Session metadata (login time, device, IP)
- Active session tracking
- Multi-device session management
- Session revocation (logout from all devices)
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import logging
from .cache import cache_service

logger = logging.getLogger(__name__)


class SessionService:
    """Manage user sessions in Redis."""

    def __init__(self):
        self.cache = cache_service
        self.session_ttl = 7 * 24 * 3600  # 7 days (matches refresh token)

    async def create_session(
        self,
        user_id: str,
        token_jti: str,  # JWT ID from token
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Create new session.

        Args:
            user_id: User UUID
            token_jti: Unique JWT token ID
            metadata: Device info, IP address, user agent, login time

        Returns:
            True if session was created successfully
        """
        session_key = f"session:{user_id}:{token_jti}"

        # Store session data
        session_data = {
            **metadata,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_activity": datetime.now(timezone.utc).isoformat()
        }

        try:
            # Store session
            success = await self.cache.set(session_key, session_data, self.session_ttl)

            if success:
                logger.info(f"Created session for user {user_id}: {token_jti}")

            return success

        except Exception as e:
            logger.error(f"Failed to create session: {str(e)}")
            return False

    async def get_session(self, user_id: str, token_jti: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve session metadata.

        Args:
            user_id: User UUID
            token_jti: JWT token ID

        Returns:
            Session data dict or None if not found
        """
        session_key = f"session:{user_id}:{token_jti}"

        try:
            session = await self.cache.get(session_key)
            return session
        except Exception as e:
            logger.error(f"Failed to get session: {str(e)}")
            return None

    async def update_activity(self, user_id: str, token_jti: str) -> bool:
        """
        Update last activity timestamp for session.

        Args:
            user_id: User UUID
            token_jti: JWT token ID

        Returns:
            True if updated successfully
        """
        try:
            # Get existing session
            session = await self.get_session(user_id, token_jti)

            if not session:
                return False

            # Update last activity
            session["last_activity"] = datetime.now(timezone.utc).isoformat()

            # Save back to cache
            session_key = f"session:{user_id}:{token_jti}"
            success = await self.cache.set(session_key, session, self.session_ttl)

            return success

        except Exception as e:
            logger.error(f"Failed to update session activity: {str(e)}")
            return False

    async def revoke_session(self, user_id: str, token_jti: str) -> bool:
        """
        Revoke specific session (single device logout).

        Args:
            user_id: User UUID
            token_jti: JWT token ID

        Returns:
            True if session was revoked
        """
        session_key = f"session:{user_id}:{token_jti}"

        try:
            success = await self.cache.delete(session_key)

            if success:
                logger.info(f"Revoked session for user {user_id}: {token_jti}")

            return success

        except Exception as e:
            logger.error(f"Failed to revoke session: {str(e)}")
            return False

    async def revoke_all_sessions(self, user_id: str) -> int:
        """
        Revoke all sessions for user (logout from all devices).

        Args:
            user_id: User UUID

        Returns:
            Number of sessions revoked
        """
        pattern = f"session:{user_id}:*"

        try:
            deleted_count = await self.cache.delete_pattern(pattern)
            logger.info(f"Revoked {deleted_count} sessions for user {user_id}")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to revoke all sessions: {str(e)}")
            return 0

    async def list_active_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List all active sessions for user (for account security page).

        Args:
            user_id: User UUID

        Returns:
            List of session metadata dicts
        """
        try:
            # This is a simplified implementation
            # In production, you might want to maintain a separate set of session IDs
            # for more efficient retrieval
            pattern = f"session:{user_id}:*"

            # Note: This requires scanning which can be slow
            # Consider maintaining a user_sessions:{user_id} SET for production
            sessions = []

            # Get all keys matching pattern
            if self.cache.client:
                async for key in self.cache.client.scan_iter(match=pattern):
                    session = await self.cache.get(key)
                    if session:
                        # Add the token JTI from the key
                        token_jti = key.split(":")[-1]
                        session["token_jti"] = token_jti
                        sessions.append(session)

            return sessions

        except Exception as e:
            logger.error(f"Failed to list active sessions: {str(e)}")
            return []

    async def extend_session(self, user_id: str, token_jti: str, additional_seconds: int = None) -> bool:
        """
        Extend session TTL.

        Args:
            user_id: User UUID
            token_jti: JWT token ID
            additional_seconds: Additional time to add (default: reset to full session_ttl)

        Returns:
            True if session was extended
        """
        session_key = f"session:{user_id}:{token_jti}"

        try:
            if additional_seconds:
                success = await self.cache.extend_ttl(session_key, additional_seconds)
            else:
                # Reset to full session TTL
                session = await self.get_session(user_id, token_jti)
                if session:
                    success = await self.cache.set(session_key, session, self.session_ttl)
                else:
                    success = False

            return success

        except Exception as e:
            logger.error(f"Failed to extend session: {str(e)}")
            return False


# Global instance
session_service = SessionService()
