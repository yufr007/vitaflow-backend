# database.py
"""
VitaFlow MongoDB Database Connection.

Uses Motor async driver with Beanie ODM.
"""

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class Database:
    """MongoDB database connection manager."""
    
    client: Optional[AsyncIOMotorClient] = None
    _initialized: bool = False
    
    @classmethod
    async def connect_db(cls, database_url: str, database_name: str):
        """
        Connect to MongoDB Atlas.
        
        Args:
            database_url: MongoDB connection string
            database_name: Database name to use
        """
        # Skip if already initialized (prevents multiple worker initialization)
        if cls._initialized:
            return
        
        try:
            # Create Motor client
            cls.client = AsyncIOMotorClient(
                database_url,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                maxPoolSize=50,  # Connection pool
                minPoolSize=10
            )
            
            # Get database
            db = cls.client[database_name]
            
            # Test connection with ping
            await cls.client.admin.command('ping')
            logger.info(f"Connected to MongoDB Atlas: {database_name}")
            
            # Initialize Beanie ODM with models
            from app.models.mongodb import (
                UserDocument,
                SubscriptionDocument,
                FormCheckDocument,
                WorkoutDocument,
                MealPlanDocument,
                ShoppingListDocument,
                CoachingMessageDocument,
                RecoveryAssessmentDocument
            )
            
            await init_beanie(
                database=db,
                document_models=[
                    UserDocument,
                    SubscriptionDocument,
                    FormCheckDocument,
                    WorkoutDocument,
                    MealPlanDocument,
                    ShoppingListDocument,
                    CoachingMessageDocument,
                    RecoveryAssessmentDocument
                ]
            )
            logger.info("Beanie ODM initialized with all models")
            cls._initialized = True
            
        except Exception as e:
            logger.error(f"Error connecting to MongoDB: {e}")
            raise
    
    @classmethod
    async def close_db(cls):
        """Close MongoDB connection."""
        if cls.client:
            cls.client.close()
            logger.info("MongoDB connection closed")
    
    @classmethod
    async def ping(cls) -> bool:
        """Test MongoDB connection."""
        if not cls.client:
            return False
        try:
            await cls.client.admin.command('ping')
            return True
        except Exception:
            return False


# Dependency for routes (if needed)
async def get_database():
    """Dependency to get database instance."""
    from settings import settings
    return Database.client[settings.DATABASE_NAME]
