# app/middleware/db_middleware.py
"""
Lazy Database Connection Middleware.

Ensures MongoDB connection is established before processing requests.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import logging

from database import Database
from settings import settings

logger = logging.getLogger(__name__)


class LazyDatabaseMiddleware(BaseHTTPMiddleware):
    """Middleware to ensure database connection before handling requests."""
    
    async def dispatch(self, request: Request, call_next):
        """
        Ensure database is connected before processing request.
        
        This lazy initialization prevents Azure startup timeout issues
        while ensuring the database is ready for the first request.
        """
        # Skip for health check endpoints to allow fast startup validation
        if request.url.path in ["/health", "/health/detailed"]:
            return await call_next(request)
        
        # Initialize database if not already done
        if not Database._initialized:
            try:
                logger.info("Lazy initializing MongoDB connection...")
                await Database.connect_db(
                    database_url=settings.MONGODB_URL,
                    database_name=settings.DATABASE_NAME
                )
            except Exception as e:
                logger.error(f"Failed to initialize database: {e}")
                # Let the request proceed - individual routes will handle the error
        
        return await call_next(request)
