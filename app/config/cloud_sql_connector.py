"""
VitaFlow API - Google Cloud SQL Connector.

Connects to Cloud SQL PostgreSQL using the Cloud SQL Python Connector
for secure, IAM-based authentication without public IP exposure.
"""

import os
import logging
from typing import Optional, Callable
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)


class CloudSQLConnector:
    """
    Google Cloud SQL Connector for PostgreSQL.
    
    Uses the Cloud SQL Python Connector for secure, private connections
    via Cloud SQL Auth Proxy built into the connector library.
    
    Features:
    - IAM authentication (no passwords in environment)
    - Private IP connection via VPC
    - Connection pooling with SQLAlchemy
    - Automatic reconnection on transient failures
    """
    
    def __init__(
        self,
        project_id: str,
        region: str,
        instance_name: str,
        database_name: str,
        db_user: Optional[str] = None,
        db_password: Optional[str] = None,
        use_iam_auth: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10,
    ):
        """
        Initialize Cloud SQL connector.
        
        Args:
            project_id: GCP project ID.
            region: Cloud SQL region (e.g., us-central1).
            instance_name: Cloud SQL instance name.
            database_name: PostgreSQL database name.
            db_user: Database user (or service account email for IAM).
            db_password: Database password (None for IAM auth).
            use_iam_auth: Whether to use IAM database authentication.
            pool_size: SQLAlchemy connection pool size.
            max_overflow: Maximum connections above pool_size.
        """
        self.project_id = project_id
        self.region = region
        self.instance_name = instance_name
        self.database_name = database_name
        self.db_user = db_user
        self.db_password = db_password
        self.use_iam_auth = use_iam_auth
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._connector = None
    
    @property
    def instance_connection_name(self) -> str:
        """Full Cloud SQL instance connection name."""
        return f"{self.project_id}:{self.region}:{self.instance_name}"
    
    def _get_conn(self):
        """Create connection using Cloud SQL Connector."""
        try:
            from google.cloud.sql.connector import Connector, IPTypes
            import pg8000
            
            if self._connector is None:
                self._connector = Connector()
            
            conn = self._connector.connect(
                self.instance_connection_name,
                "pg8000",
                user=self.db_user,
                password=self.db_password,
                db=self.database_name,
                enable_iam_auth=self.use_iam_auth,
                ip_type=IPTypes.PRIVATE,  # Use private IP via VPC
            )
            return conn
            
        except ImportError:
            # Fallback to standard connection for local development
            logger.warning("Cloud SQL Connector not available, using standard connection")
            import pg8000
            return pg8000.connect(
                user=self.db_user,
                password=self.db_password,
                database=self.database_name,
                host=os.getenv("DB_HOST", "localhost"),
                port=int(os.getenv("DB_PORT", "5432")),
            )
    
    def get_engine(self) -> Engine:
        """
        Get SQLAlchemy engine with connection pooling.
        
        Returns:
            Configured SQLAlchemy Engine.
        """
        if self._engine is None:
            self._engine = create_engine(
                "postgresql+pg8000://",
                creator=self._get_conn,
                poolclass=QueuePool,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_pre_ping=True,  # Check connection health
                pool_recycle=1800,   # Recycle connections every 30 min
            )
            
            # Add event listener for connection debugging
            @event.listens_for(self._engine, "connect")
            def on_connect(dbapi_conn, connection_record):
                logger.debug("New Cloud SQL connection established")
            
            @event.listens_for(self._engine, "checkout")
            def on_checkout(dbapi_conn, connection_record, connection_proxy):
                logger.debug("Connection checked out from pool")
        
        return self._engine
    
    def get_session_factory(self) -> sessionmaker:
        """
        Get SQLAlchemy session factory.
        
        Returns:
            Configured sessionmaker.
        """
        if self._session_factory is None:
            engine = self.get_engine()
            self._session_factory = sessionmaker(
                bind=engine,
                autocommit=False,
                autoflush=False,
            )
        return self._session_factory
    
    @contextmanager
    def get_session(self):
        """
        Context manager for database sessions.
        
        Usage:
            with connector.get_session() as session:
                session.query(User).all()
        """
        session = self.get_session_factory()()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def close(self):
        """Clean up connector resources."""
        if self._connector is not None:
            self._connector.close()
            self._connector = None
        
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None


# Factory function for creating connector from environment
def create_cloud_sql_connector() -> CloudSQLConnector:
    """
    Create Cloud SQL connector from environment variables.
    
    Required environment variables:
    - GCP_PROJECT_ID: Google Cloud project ID
    - CLOUD_SQL_REGION: Cloud SQL instance region
    - CLOUD_SQL_INSTANCE: Cloud SQL instance name
    - DB_NAME: PostgreSQL database name
    - DB_USER: Database username
    - DB_PASSWORD: Database password (or use IAM auth)
    
    Returns:
        Configured CloudSQLConnector instance.
    """
    return CloudSQLConnector(
        project_id=os.getenv("GCP_PROJECT_ID", "vitaflow-prod"),
        region=os.getenv("CLOUD_SQL_REGION", "us-central1"),
        instance_name=os.getenv("CLOUD_SQL_INSTANCE", "vitaflow-prod"),
        database_name=os.getenv("DB_NAME", "vitaflow"),
        db_user=os.getenv("DB_USER"),
        db_password=os.getenv("DB_PASSWORD"),
        use_iam_auth=os.getenv("USE_IAM_AUTH", "false").lower() == "true",
    )


# Global connector instance (initialized lazily)
_cloud_sql_connector: Optional[CloudSQLConnector] = None


def get_cloud_sql_connector() -> CloudSQLConnector:
    """Get or create global Cloud SQL connector."""
    global _cloud_sql_connector
    if _cloud_sql_connector is None:
        _cloud_sql_connector = create_cloud_sql_connector()
    return _cloud_sql_connector


def get_db_session() -> Session:
    """FastAPI dependency for database sessions."""
    connector = get_cloud_sql_connector()
    session = connector.get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
