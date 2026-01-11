"""
VitaFlow Backend - MongoDB Database Module.

Async MongoDB connection using Motor driver with Beanie ODM.
Replaces PostgreSQL/SQLAlchemy for flexible document storage.
"""

import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

logger = logging.getLogger(__name__)


class MongoDB:
    """
    MongoDB Atlas connection manager with Motor async driver.
    
    Uses lazy initialization pattern for Cloud Run deployment.
    Connection is established on first use, not at import time.
    
    Attributes:
        client: Motor async client instance.
        connected: Connection status flag.
    """
    
    client: Optional[AsyncIOMotorClient] = None
    connected: bool = False
    
    @classmethod
    async def connect(cls, database_url: str, database_name: str) -> None:
        """
        Connect to MongoDB Atlas and initialize Beanie ODM.
        
        Args:
            database_url: MongoDB connection string (mongodb+srv://...).
            database_name: Name of the database to use.
        
        Raises:
            Exception: If connection fails.
        """
        if cls.connected:
            logger.info("MongoDB already connected, skipping...")
            return
        
        try:
            logger.info("🔌 Connecting to MongoDB Atlas...")
            
            # Create Motor async client
            cls.client = AsyncIOMotorClient(
                database_url,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                maxPoolSize=50,                 # Connection pool
                minPoolSize=10,
            )
            
            # Get database reference
            db = cls.client[database_name]
            
            # Test connection with ping
            await cls.client.admin.command('ping')
            logger.info(f"✅ Connected to MongoDB Atlas: {database_name}")
            
            # Import all Beanie document models
            from app.models.mongodb import (
                UserDocument,
                SubscriptionDocument,
                FormCheckDocument,
                WorkoutDocument,
                MealPlanDocument,
                ShoppingListDocument,
                CoachingMessageDocument,
                RecoveryAssessmentDocument,
            )
            
            # Initialize Beanie ODM with all models
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
                    RecoveryAssessmentDocument,
                ]
            )
            
            cls.connected = True
            logger.info("✅ Beanie ODM initialized with all document models")
            
        except Exception as e:
            logger.error(f"❌ Error connecting to MongoDB: {e}")
            cls.connected = False
            raise
    
    @classmethod
    async def disconnect(cls) -> None:
        """Close MongoDB connection."""
        if cls.client:
            cls.client.close()
            cls.connected = False
            logger.info("❌ MongoDB connection closed")
    
    @classmethod
    async def ping(cls) -> bool:
        """
        Test MongoDB connection.
        
        Returns:
            bool: True if connected and responsive.
        """
        if not cls.client or not cls.connected:
            return False
        
        try:
            await cls.client.admin.command('ping')
            return True
        except Exception:
            return False
    
    @classmethod
    def get_database(cls, database_name: str):
        """
        Get database reference from client.
        
        Args:
            database_name: Name of the database.
        
        Returns:
            AsyncIOMotorDatabase: Database reference.
        
        Raises:
            RuntimeError: If not connected.
        """
        if not cls.client:
            raise RuntimeError("MongoDB not connected. Call connect() first.")
        return cls.client[database_name]


# Dependency injection for FastAPI routes
async def get_mongodb():
    """
    FastAPI dependency to get MongoDB database reference.
    
    Yields:
        Database reference for the current request.
    """
    from settings import settings
    return MongoDB.get_database(settings.DATABASE_NAME)
