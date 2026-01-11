"""
VitaFlow OAuth Service.

Handles Google OAuth 2.0 token verification and user profile extraction.
"""

from google.auth.transport import requests
from google.oauth2 import id_token
from typing import Optional, Dict
from settings import settings


class OAuthService:
    """Google OAuth 2.0 integration service."""

    def __init__(self):
        """Initialize with Google Client ID."""
        self.google_client_id = settings.GOOGLE_CLIENT_ID

    async def verify_google_token(self, token: str) -> Optional[Dict[str, str]]:
        """
        Verify Google ID token and extract user profile.

        Args:
            token: Google ID token from frontend

        Returns:
            Dictionary with user profile:
            {
                "email": "user@gmail.com",
                "name": "John Doe",
                "picture": "https://...",
                "sub": "google_user_id"
            }
            Returns None if verification fails.
        """
        try:
            # Verify the token
            idinfo = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                self.google_client_id
            )

            # Verify the issuer
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                return None

            # Extract user profile
            return {
                "email": idinfo.get("email"),
                "name": idinfo.get("name"),
                "picture": idinfo.get("picture"),
                "sub": idinfo.get("sub"),  # Google user ID
                "email_verified": idinfo.get("email_verified", False)
            }

        except Exception as e:
            print(f"Google OAuth verification error: {str(e)}")
            return None


# Singleton instance
oauth_service = OAuthService()
