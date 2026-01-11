# settings.py
"""
VitaFlow API Settings.

Pydantic settings management with environment variable support.
"""

from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional
from urllib.parse import urlparse, urlunparse


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # MongoDB - REQUIRED from environment
    DATABASE_URL: str = Field(..., env="DATABASE_URL", description="MongoDB connection string (required)")
    DATABASE_NAME: str = Field(default="vitaflow_prod", env="DATABASE_NAME")
    
    # JWT - REQUIRED from environment
    SECRET_KEY: str = Field(..., env="SECRET_KEY", description="JWT signing secret (required)")
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # Environment
    ENV: str = Field(default="development", env="ENV")
    DEBUG: bool = Field(default=True, env="DEBUG")
    
    # Gemini AI (for simple features: form check, basic generation)
    GEMINI_API_KEY: str = Field(..., env="GEMINI_API_KEY", description="Google Gemini API key (required)")
    
    # Azure OpenAI (for complex workflows: shopping optimizer, advanced coaching)
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_KEY: Optional[str] = None
    AZURE_OPENAI_DEPLOYMENT_GPT4: str = "gpt-4o-mini"
    AZURE_OPENAI_DEPLOYMENT_GPT4_TURBO: str = "gpt-4o-mini"
    
    # Azure AI Foundry
    AZURE_FOUNDRY_PROJECT_ID: Optional[str] = None
    AZURE_SUBSCRIPTION_ID: Optional[str] = None
    AZURE_RESOURCE_GROUP: str = "vitaflow-prod"
    
    # Azure Cognitive Services
    AZURE_SPEECH_KEY: Optional[str] = None
    AZURE_SPEECH_REGION: str = "australiaeast"
    AZURE_FORM_RECOGNIZER_ENDPOINT: Optional[str] = None
    AZURE_FORM_RECOGNIZER_KEY: Optional[str] = None
    AZURE_COMPUTER_VISION_ENDPOINT: Optional[str] = None
    AZURE_COMPUTER_VISION_KEY: Optional[str] = None
    
    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Email Service (Resend)
    RESEND_API_KEY: Optional[str] = None

    # reCAPTCHA
    RECAPTCHA_SECRET_KEY: Optional[str] = None
    RECAPTCHA_SITE_KEY: Optional[str] = None

    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None

    # OTP Configuration
    OTP_EXPIRY_MINUTES: int = 10
    OTP_MAX_ATTEMPTS: int = 3

    # Google Cloud (for storage)
    GCP_PROJECT_ID: Optional[str] = None
    GCS_BUCKET_NAME: Optional[str] = None

    # Redis Configuration
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL",
        description="Redis connection URL (redis://[:password@]host:port/db)"
    )
    REDIS_PASSWORD: Optional[str] = Field(
        default=None,
        env="REDIS_PASSWORD",
        description="Redis password for authentication"
    )
    REDIS_MAX_CONNECTIONS: int = Field(
        default=50,
        env="REDIS_MAX_CONNECTIONS",
        description="Redis connection pool size"
    )
    REDIS_SOCKET_TIMEOUT: int = Field(
        default=5,
        env="REDIS_SOCKET_TIMEOUT",
        description="Redis socket timeout in seconds"
    )
    REDIS_SOCKET_CONNECT_TIMEOUT: int = Field(
        default=5,
        env="REDIS_SOCKET_CONNECT_TIMEOUT",
        description="Redis connection timeout in seconds"
    )

    # Cache TTL Defaults (in seconds)
    CACHE_TTL_WORKOUT: int = Field(
        default=86400,
        env="CACHE_TTL_WORKOUT",
        description="Workout plan cache TTL (24 hours)"
    )
    CACHE_TTL_MEAL_PLAN: int = Field(
        default=21600,
        env="CACHE_TTL_MEAL_PLAN",
        description="Meal plan cache TTL (6 hours)"
    )
    CACHE_TTL_SHOPPING: int = Field(
        default=7200,
        env="CACHE_TTL_SHOPPING",
        description="Shopping list cache TTL (2 hours)"
    )
    CACHE_TTL_COACHING: int = Field(
        default=3600,
        env="CACHE_TTL_COACHING",
        description="Coaching message cache TTL (1 hour)"
    )

    # Feature Flags - Azure vs Gemini routing
    USE_AZURE_SHOPPING: bool = True  # Use Azure for shopping optimizer
    USE_AZURE_COACHING: bool = True  # Use Azure for multi-agent coaching
    AZURE_ROLLOUT_PERCENTAGE: int = 100  # % of users on Azure (0-100)
    
    # Azure App Service specific
    AZURE_DEPLOYMENT: bool = False  # Set True when deploying to Azure App Service
    WEBSITES_PORT: int = 8000  # Azure App Service default port
    
    # Sentry Error Tracking
    SENTRY_DSN: Optional[str] = None
    SENTRY_ENVIRONMENT: str = "production"
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1
    
    @property
    def is_mongodb(self) -> bool:
        """Check if using MongoDB (vs PostgreSQL)."""
        return self.DATABASE_URL.startswith("mongodb")
    
    @property
    def azure_openai_configured(self) -> bool:
        """Check if Azure OpenAI is configured."""
        return bool(self.AZURE_OPENAI_ENDPOINT and self.AZURE_OPENAI_KEY)

    @property
    def redis_url_with_auth(self) -> str:
        """Build Redis URL with authentication if password is provided."""
        if self.REDIS_PASSWORD:
            parsed = urlparse(self.REDIS_URL)
            netloc_with_auth = f":{self.REDIS_PASSWORD}@{parsed.netloc}"
            return urlunparse((
                parsed.scheme,
                netloc_with_auth,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
        return self.REDIS_URL
    
    def validate_required_settings(self) -> None:
        """Validate that required settings are configured."""
        if not self.DATABASE_URL:
            raise ValueError("DATABASE_URL must be set")
        if not self.SECRET_KEY:
            raise ValueError("SECRET_KEY must be changed from default in production")
        if not self.GEMINI_API_KEY and not self.AZURE_OPENAI_KEY:
            raise ValueError("Either GEMINI_API_KEY or AZURE_OPENAI_KEY must be set")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

# Validate in production
if settings.ENV == "production":
    settings.validate_required_settings()
