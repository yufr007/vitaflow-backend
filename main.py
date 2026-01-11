# main.py
"""
VitaFlow API - Main Application.

FastAPI app with MongoDB Atlas backend.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from database import Database
from settings import settings
from app.middleware.db_middleware import LazyDatabaseMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Sentry for error tracking
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        integrations=[
            FastApiIntegration(),
            LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR
            ),
        ],
    )
    logger.info(f"Sentry initialized ({settings.SENTRY_ENVIRONMENT})")
else:
    logger.warning("Sentry DSN not configured - error tracking disabled")

# Import routers
from app.routes import (
    auth,
    user,
    form_check,
    workout,
    meal_plan,
    shopping,
    coaching,
    subscription,
    voice_coaching,
    nutrition_scan
)
from app.routes import recovery


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting VitaFlow API...")
    # Initialize database connection at startup
    # This makes the /health/detailed endpoint ready to use immediately
    # If initialization fails, lazy initialization will be used as fallback
    try:
        await Database.connect_db(settings.DATABASE_URL, settings.DATABASE_NAME)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize database at startup: {e}")
        logger.warning("Database will be initialized lazily on first request")
    
    yield
    
    # Shutdown: Close MongoDB connection
    await Database.close_db()
    logger.info("VitaFlow API shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="VitaFlow API",
    version="1.0.0",
    description="AI-powered fitness and nutrition platform",
    lifespan=lifespan
)

# CORS middleware - Allow frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://vitaflow.fitness",
        "https://www.vitaflow.fitness",
        "https://vitaflow-xi.vercel.app",
        "https://vitaflow-668nm.ondigitalocean.app",
        "https://vitaflow-backend-bvfso.ondigitalocean.app",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:19006",  # Expo
        "http://localhost:8081",   # React Native Metro
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy database connection middleware
app.add_middleware(LazyDatabaseMiddleware)


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint - fast response without database dependency."""
    return {
        "status": "ok",
        "environment": settings.ENV,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0"
    }


@app.get("/health/detailed")
async def health_check_detailed():
    """Detailed health check with MongoDB connectivity test."""
    try:
        mongo_ok = await Database.ping()
        return {
            "status": "ok" if mongo_ok else "degraded",
            "database": "mongodb",
            "database_connected": mongo_ok,
            "environment": settings.ENV,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "error",
            "database": "mongodb",
            "database_connected": False,
            "environment": settings.ENV,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        }


@app.get("/health/redis")
async def redis_health_check():
    """Redis connectivity and statistics health check."""
    from app.services.cache import cache_service

    try:
        is_healthy = await cache_service.healthcheck()

        if not is_healthy:
            return {
                "status": "unhealthy",
                "redis_connected": False,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        # Get statistics
        stats = await cache_service.get_stats()

        # Calculate hit rate
        hits = stats.get("keyspace_hits", 0)
        misses = stats.get("keyspace_misses", 0)
        total = hits + misses
        hit_rate = (hits / total * 100) if total > 0 else 0

        return {
            "status": "healthy",
            "redis_connected": True,
            "memory_used": stats.get("used_memory_human"),
            "memory_used_bytes": stats.get("used_memory"),
            "memory_max_bytes": stats.get("maxmemory"),
            "connected_clients": stats.get("connected_clients"),
            "cache_hit_rate": f"{hit_rate:.2f}%",
            "cache_hits": hits,
            "cache_misses": misses,
            "total_operations": stats.get("total_commands_processed"),
            "evicted_keys": stats.get("evicted_keys"),
            "ops_per_sec": stats.get("instantaneous_ops_per_sec"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        return {
            "status": "error",
            "redis_connected": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(user.router, prefix="/user", tags=["User"])
app.include_router(form_check.router, prefix="/form-check", tags=["Form Check"])
app.include_router(workout.router, prefix="/workout", tags=["Workout"])
app.include_router(meal_plan.router, prefix="/meal-plan", tags=["Meal Plan"])
app.include_router(shopping.router, prefix="/shopping", tags=["Shopping"])
app.include_router(coaching.router, prefix="/coaching", tags=["Coaching"])
app.include_router(subscription.router, prefix="/subscription", tags=["Subscription"])
app.include_router(recovery.router, prefix="/recovery", tags=["Rest & Recovery"])
app.include_router(voice_coaching.router)  # Elite tier voice coaching
app.include_router(nutrition_scan.router)  # Pro/Elite nutrition scanning


# Root endpoint
@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "message": "VitaFlow API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }
