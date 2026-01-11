"""
VitaFlow API - Google Secret Manager Integration.

Securely retrieves secrets from Google Cloud Secret Manager,
replacing environment variables for production deployments.
"""

import os
import logging
from typing import Optional, Dict, Any
from functools import lru_cache

logger = logging.getLogger(__name__)


class SecretManagerService:
    """
    Google Cloud Secret Manager integration.
    
    Retrieves secrets securely at runtime, avoiding hardcoded values
    or environment variables that could be leaked.
    
    Features:
    - Lazy loading of secrets
    - LRU caching to minimize API calls
    - Fallback to environment variables for local dev
    - Automatic version handling (latest by default)
    """
    
    def __init__(self, project_id: Optional[str] = None):
        """
        Initialize Secret Manager client.
        
        Args:
            project_id: GCP project ID. Defaults to GCP_PROJECT_ID env var.
        """
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID", "vitaflow-prod")
        self._client = None
        self._cache: Dict[str, str] = {}
    
    @property
    def client(self):
        """Lazy-load Secret Manager client."""
        if self._client is None:
            try:
                from google.cloud import secretmanager
                self._client = secretmanager.SecretManagerServiceClient()
                logger.info("Secret Manager client initialized")
            except ImportError:
                logger.warning("google-cloud-secret-manager not installed")
                self._client = "unavailable"
            except Exception as e:
                logger.warning(f"Secret Manager unavailable: {e}")
                self._client = "unavailable"
        return self._client
    
    def get_secret(
        self,
        secret_id: str,
        version: str = "latest",
        fallback: Optional[str] = None,
    ) -> Optional[str]:
        """
        Retrieve a secret from Secret Manager.
        
        Args:
            secret_id: The secret ID (not the full resource name).
            version: Secret version (default: "latest").
            fallback: Fallback value if secret not found.
        
        Returns:
            Secret value as string, or fallback if not found.
        """
        cache_key = f"{secret_id}:{version}"
        
        # Check cache first
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Check environment variable fallback (for local dev)
        env_value = os.getenv(secret_id.upper().replace("-", "_"))
        if env_value:
            logger.debug(f"Using environment variable for {secret_id}")
            self._cache[cache_key] = env_value
            return env_value
        
        # Try Secret Manager
        if self.client == "unavailable":
            logger.debug(f"Secret Manager unavailable, using fallback for {secret_id}")
            return fallback
        
        try:
            name = f"projects/{self.project_id}/secrets/{secret_id}/versions/{version}"
            response = self.client.access_secret_version(request={"name": name})
            secret_value = response.payload.data.decode("UTF-8")
            
            # Cache the value
            self._cache[cache_key] = secret_value
            logger.info(f"Retrieved secret: {secret_id}")
            
            return secret_value
            
        except Exception as e:
            logger.error(f"Failed to retrieve secret {secret_id}: {e}")
            return fallback
    
    def get_secret_json(
        self,
        secret_id: str,
        version: str = "latest",
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve a JSON secret from Secret Manager.
        
        Args:
            secret_id: The secret ID.
            version: Secret version (default: "latest").
        
        Returns:
            Parsed JSON as dictionary, or None if not found.
        """
        import json
        
        secret_value = self.get_secret(secret_id, version)
        if secret_value:
            try:
                return json.loads(secret_value)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON secret {secret_id}: {e}")
        return None
    
    def create_secret(
        self,
        secret_id: str,
        secret_value: str,
    ) -> bool:
        """
        Create a new secret (for setup scripts).
        
        Args:
            secret_id: The secret ID.
            secret_value: The secret value.
        
        Returns:
            True if created successfully.
        """
        if self.client == "unavailable":
            logger.error("Cannot create secret: Secret Manager unavailable")
            return False
        
        try:
            parent = f"projects/{self.project_id}"
            
            # Create the secret
            secret = self.client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": secret_id,
                    "secret": {"replication": {"automatic": {}}},
                }
            )
            
            # Add the first version
            self.client.add_secret_version(
                request={
                    "parent": secret.name,
                    "payload": {"data": secret_value.encode("UTF-8")},
                }
            )
            
            logger.info(f"Created secret: {secret_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create secret {secret_id}: {e}")
            return False
    
    def clear_cache(self):
        """Clear the secrets cache."""
        self._cache.clear()


# Global instance
_secret_manager: Optional[SecretManagerService] = None


def get_secret_manager() -> SecretManagerService:
    """Get or create global Secret Manager instance."""
    global _secret_manager
    if _secret_manager is None:
        _secret_manager = SecretManagerService()
    return _secret_manager


# Convenience functions
@lru_cache(maxsize=50)
def get_secret(secret_id: str, fallback: Optional[str] = None) -> Optional[str]:
    """Get a secret value (cached)."""
    return get_secret_manager().get_secret(secret_id, fallback=fallback)


def get_db_password() -> str:
    """Get database password from Secret Manager."""
    return get_secret("db-password", fallback=os.getenv("DB_PASSWORD", ""))


def get_gemini_api_key() -> str:
    """Get Gemini API key from Secret Manager."""
    return get_secret("gemini-api-key", fallback=os.getenv("GEMINI_API_KEY", ""))


def get_stripe_api_key() -> str:
    """Get Stripe API key from Secret Manager."""
    return get_secret("stripe-api-key", fallback=os.getenv("STRIPE_API_KEY", ""))


def get_jwt_secret() -> str:
    """Get JWT secret from Secret Manager."""
    return get_secret("jwt-secret", fallback=os.getenv("SECRET_KEY", "dev-secret"))


def get_fitbit_client_secret() -> str:
    """Get Fitbit client secret from Secret Manager."""
    return get_secret("fitbit-client-secret", fallback=os.getenv("FITBIT_CLIENT_SECRET", ""))


def get_garmin_consumer_secret() -> str:
    """Get Garmin consumer secret from Secret Manager."""
    return get_secret("garmin-consumer-secret", fallback=os.getenv("GARMIN_CONSUMER_SECRET", ""))
