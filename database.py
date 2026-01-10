from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from config import settings
import logging

logger = logging.getLogger(__name__)

client = None
database = None

async def init_db():
    """Initialize MongoDB connection and Beanie ODM"""
    global client, database
    
    try:
        client = AsyncIOMotorClient(settings.get_mongodb_url())
        database = client[settings.DATABASE_NAME]
        
        # Import models
        from app.models.user import User
        from app.models.subscription import Subscription
        from app.models.formcheck import FormCheck
        from app.models.workout import Workout
        from app.models.mealplan import MealPlan
        from app.models.shoppinglist import ShoppingList
        from app.models.coaching import CoachingMessage
        
        await init_beanie(
            database=database,
            document_models=[
                User,
                Subscription,
                FormCheck,
                Workout,
                MealPlan,
                ShoppingList,
                CoachingMessage
            ]
        )
        logger.info("✅ Connected to MongoDB Atlas")
        
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {str(e)}")
        raise

async def close_db():
    """Close MongoDB connection"""
    if client:
        client.close()
        logger.info("❌ MongoDB connection closed")
