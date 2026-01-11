"""
Google Cloud Secret Manager Integration

Provides secure access to secrets stored in Google Cloud Secret Manager.
Used in production to avoid hardcoding sensitive credentials.
"""

import os
from typing import Optional
from google.cloud import secretmanager
from functools import lru_cache


class SecretManager:
    """Wrapper for Google Cloud Secret Manager operations."""

    def __init__(self, project_id: Optional[str] = None):
        """
        Initialize Secret Manager client.

        Args:
            project_id: GCP project ID. If not provided, uses GCP_PROJECT_ID env var.
        """
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID", "vitaflow-fitness")
        self.client = secretmanager.SecretManagerServiceClient()

    @lru_cache(maxsize=128)
    def get_secret(self, secret_id: str, version: str = "latest") -> str:
        """
        Retrieve a secret from Google Cloud Secret Manager.

        Args:
            secret_id: The ID of the secret (e.g., "gemini-api-key")
            version: Version of the secret to retrieve (default: "latest")

        Returns:
            The secret value as a string

        Raises:
            Exception: If secret cannot be retrieved
        """
        try:
            name = f"projects/{self.project_id}/secrets/{secret_id}/versions/{version}"
            response = self.client.access_secret_version(request={"name": name})
            secret_value = response.payload.data.decode("UTF-8")
            return secret_value
        except Exception as e:
            raise Exception(f"Failed to retrieve secret '{secret_id}': {str(e)}")


# Global instance for application use
_secret_manager: Optional[SecretManager] = None


def get_secret_manager() -> SecretManager:
    """Get or create the global SecretManager instance."""
    global _secret_manager
    if _secret_manager is None:
        _secret_manager = SecretManager()
    return _secret_manager


def get_secret(secret_id: str, fallback: Optional[str] = None) -> str:
    """
    Get a secret from Secret Manager with environment fallback.

    In development (ENV=development), falls back to environment variables.
    In production (ENV=production), requires Secret Manager.

    Args:
        secret_id: The secret identifier (e.g., "gemini-api-key")
        fallback: Optional fallback value if secret not found (dev only)

    Returns:
        The secret value

    Raises:
        Exception: If secret not found in production
    """
    env = os.getenv("ENV", "development")

    # In development, use environment variables
    if env == "development":
        # Convert secret_id to env var format (gemini-api-key -> GEMINI_API_KEY)
        env_var = secret_id.upper().replace("-", "_")
        value = os.getenv(env_var, fallback)
        if value is None:
            raise Exception(f"Secret '{secret_id}' not found in environment (ENV={env})")
        return value

    # In production, use Secret Manager
    try:
        sm = get_secret_manager()
        return sm.get_secret(secret_id)
    except Exception as e:
        if fallback is not None:
            return fallback
        raise e
