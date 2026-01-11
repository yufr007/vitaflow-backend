"""
VitaFlow API - Google Cloud Configuration Package.

Provides unified access to all Google Cloud services:
- Cloud SQL (PostgreSQL)
- Secret Manager
- Cloud Storage
- BigQuery Analytics
"""

from app.config.cloud_sql_connector import (
    CloudSQLConnector,
    get_cloud_sql_connector,
    get_db_session,
    create_cloud_sql_connector,
)

from app.config.secret_manager import (
    SecretManagerService,
    get_secret_manager,
    get_secret,
    get_db_password,
    get_gemini_api_key,
    get_stripe_api_key,
    get_jwt_secret,
)

from app.config.cloud_storage import (
    CloudStorageService,
    get_storage_service,
)

from app.config.bigquery_service import (
    BigQueryService,
    get_bigquery_service,
    FormCheckEvent,
    WearableSyncEvent,
    RevenueEvent,
)

__all__ = [
    # Cloud SQL
    "CloudSQLConnector",
    "get_cloud_sql_connector",
    "get_db_session",
    "create_cloud_sql_connector",
    # Secrets
    "SecretManagerService",
    "get_secret_manager",
    "get_secret",
    "get_db_password",
    "get_gemini_api_key",
    "get_stripe_api_key",
    "get_jwt_secret",
    # Storage
    "CloudStorageService",
    "get_storage_service",
    # BigQuery
    "BigQueryService",
    "get_bigquery_service",
    "FormCheckEvent",
    "WearableSyncEvent",
    "RevenueEvent",
]
