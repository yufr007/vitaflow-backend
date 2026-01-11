"""
VitaFlow reCAPTCHA Service.

Verifies Google reCAPTCHA v3 tokens with configurable score threshold.
"""

import aiohttp
from typing import Tuple
from settings import settings


class RecaptchaService:
    """Google reCAPTCHA v3 verification service."""

    def __init__(self):
        """Initialize with reCAPTCHA secret key."""
        self.secret_key = settings.RECAPTCHA_SECRET_KEY
        self.verify_url = "https://www.google.com/recaptcha/api/siteverify"
        self.score_threshold = 0.5  # Configurable minimum score

    async def verify_token(self, token: str, action: str = "register") -> Tuple[bool, float]:
        """
        Verify reCAPTCHA v3 token.

        Args:
            token: reCAPTCHA token from frontend
            action: Action name (e.g., "register", "login")

        Returns:
            Tuple of (success: bool, score: float)
            - success: True if verification passes threshold
            - score: reCAPTCHA score (0.0 to 1.0)
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.verify_url,
                    data={
                        "secret": self.secret_key,
                        "response": token
                    }
                ) as response:
                    result = await response.json()

                    if not result.get("success"):
                        return False, 0.0

                    score = result.get("score", 0.0)
                    action_matches = result.get("action") == action

                    # Verification passes if score meets threshold and action matches
                    success = score >= self.score_threshold and action_matches

                    return success, score

        except Exception as e:
            print(f"reCAPTCHA verification error: {str(e)}")
            return False, 0.0


# Singleton instance
recaptcha_service = RecaptchaService()
