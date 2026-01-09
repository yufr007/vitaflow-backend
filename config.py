from pydantic_settings import BaseSettings
from typing import Optional, List

class Settings(BaseSettings):
    # MongoDB
    MONGODB_URL: str
    DATABASE_NAME: str = "vitaflow"
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # APIs
    GEMINI_API_KEY: Optional[str] = None
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    
    # Google Cloud
    GCP_PROJECT_ID: Optional[str] = None
    GCS_BUCKET_NAME: Optional[str] = None
    
    # Email
    SUPPORT_EMAIL: str = "support@vitaflow.fitness"
    
    # Domain
    DOMAIN: str = "vitaflow.fitness"
    FRONTEND_URL: str = "https://vitaflow.fitness"
    
    # Environment
    ENV: str = "development"
    DEBUG: bool = True
    
    # CORS
    CORS_ORIGINS: str = "https://vitaflow.fitness,https://www.vitaflow.fitness,http://localhost:5173,http://localhost:3000"
    
    def get_cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
