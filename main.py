from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db, close_db
from config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="VitaFlow API",
    version="1.0.0",
    description="AI-powered fitness backend",
    contact={
        "name": "VitaFlow Support",
        "email": "support@vitaflow.fitness",
    },
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration using settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

@app.on_event("startup")
async def startup():
    """Initialize database on startup"""
    await init_db()
    logger.info("🚀 VitaFlow API started at vitaflow.fitness")

@app.on_event("shutdown")
async def shutdown():
    """Close database connection on shutdown"""
    await close_db()
    logger.info("👋 VitaFlow API shutdown")

# Import and register routes
from app.routes import auth, user, formcheck, workout, mealplan, shopping, coaching, subscription

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(user.router, prefix="/user", tags=["User"])
app.include_router(formcheck.router, prefix="/form-check", tags=["Form Check"])
app.include_router(workout.router, prefix="/workout", tags=["Workout"])
app.include_router(mealplan.router, prefix="/meal-plan", tags=["Meal Plan"])
app.include_router(shopping.router, prefix="/shopping", tags=["Shopping"])
app.include_router(coaching.router, prefix="/coaching", tags=["Coaching"])
app.include_router(subscription.router, prefix="/subscription", tags=["Subscription"])

@app.get("/")
async def root():
    return {
        "message": "VitaFlow API",
        "version": "1.0.0",
        "domain": "vitaflow.fitness",
        "docs": "https://vitaflow-backend-bvfso.ondigitalocean.app/docs",
        "support": "support@vitaflow.fitness",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "VitaFlow API",
        "domain": "vitaflow.fitness",
        "env": settings.ENV
    }
