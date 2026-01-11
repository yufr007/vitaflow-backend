"""
VitaFlow API - Database Configuration.

SQLAlchemy engine, session factory, and declarative base for ORM models.
PostgreSQL connection with connection pooling and validation.
LAZY INITIALIZATION: Engine connects on first use, not at import time.
This enables Cloud Run containers to start quickly without blocking on DB.
"""

from typing import Generator, Optional
import logging

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import Session, sessionmaker, declarative_base

# Import settings from parent config
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from settings import settings

logger = logging.getLogger(__name__)

# Declarative base for ORM models
Base = declarative_base()

# Global engine and session factory (initialized lazily)
_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def get_engine() -> Engine:
    """
    Get or create the SQLAlchemy engine (lazy initialization).

    Creates engine with connection pooling, validation, and timeout settings
    optimized for Cloud Run deployment. Engine is created on first request,
    not at import time, allowing the app to start quickly.

    Returns:
        Engine: SQLAlchemy engine instance.
    """
    global _engine
    if _engine is None:
        logger.info("🔌 Creating database engine...")
        try:
            # Handle both PostgreSQL and SQLite URLs
            if settings.DATABASE_URL.startswith("sqlite"):
                _engine = create_engine(
                    settings.DATABASE_URL,
                    echo=False,
                    connect_args={"check_same_thread": False},  # SQLite specific
                )
            else:
                # PostgreSQL with connection pooling and validation
                _engine = create_engine(
                    settings.DATABASE_URL,
                    echo=False,
                    pool_size=5,
                    max_overflow=10,
                    pool_pre_ping=True,      # Validate connections before use
                    pool_recycle=3600,       # Recycle connections every hour
                    connect_args={
                        "connect_timeout": 10,           # 10 second connection timeout
                        "application_name": "vitaflow-backend",  # Identify in DB logs
                    },
                )
            logger.info("✅ Database engine created successfully")
        except Exception as e:
            logger.error(f"❌ Failed to create database engine: {e}")
            raise
    return _engine


def get_session_factory() -> sessionmaker:
    """
    Get or create the session factory (lazy initialization).

    Returns:
        sessionmaker: SQLAlchemy session factory.
    """
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(
            bind=engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI routes.

    Yields a database session and ensures proper cleanup after request.
    Uses lazy initialization - database connects on first request, not at startup.

    Yields:
        Session: SQLAlchemy database session.

    Example:
        @app.get("/users")
        async def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
