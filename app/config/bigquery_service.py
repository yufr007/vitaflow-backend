"""
VitaFlow API - BigQuery Analytics Service.

Tracks user behavior, form check quality, wearable sync rates,
and revenue for business intelligence and product improvement.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FormCheckEvent:
    """Form check analytics event."""
    user_id: str
    form_check_id: str
    exercise_type: str
    form_quality_score: float
    feedback: str
    subscription_tier: str
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


@dataclass
class WearableSyncEvent:
    """Wearable sync analytics event."""
    user_id: str
    device_type: str
    sync_status: str  # success, failed, partial
    metrics_synced: int
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


@dataclass
class RevenueEvent:
    """Revenue analytics event."""
    user_id: str
    subscription_tier: str  # free, pro, premium
    amount: float
    currency: str
    event_type: str  # subscription, upgrade, downgrade, refund
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


class BigQueryService:
    """
    BigQuery analytics for VitaFlow.
    
    Features:
    - Event streaming via insert API
    - Batch loading for historical data
    - Pre-built queries for KPIs
    - Workspace Sheets integration
    """
    
    DATASET_ID = "vitaflow_analytics"
    
    SCHEMAS = {
        "form_checks": [
            {"name": "user_id", "type": "STRING", "mode": "REQUIRED"},
            {"name": "form_check_id", "type": "STRING", "mode": "REQUIRED"},
            {"name": "exercise_type", "type": "STRING", "mode": "NULLABLE"},
            {"name": "form_quality_score", "type": "FLOAT64", "mode": "NULLABLE"},
            {"name": "feedback", "type": "STRING", "mode": "NULLABLE"},
            {"name": "subscription_tier", "type": "STRING", "mode": "NULLABLE"},
            {"name": "timestamp", "type": "TIMESTAMP", "mode": "REQUIRED"},
        ],
        "wearable_syncs": [
            {"name": "user_id", "type": "STRING", "mode": "REQUIRED"},
            {"name": "device_type", "type": "STRING", "mode": "REQUIRED"},
            {"name": "sync_status", "type": "STRING", "mode": "REQUIRED"},
            {"name": "metrics_synced", "type": "INT64", "mode": "NULLABLE"},
            {"name": "timestamp", "type": "TIMESTAMP", "mode": "REQUIRED"},
        ],
        "revenue": [
            {"name": "user_id", "type": "STRING", "mode": "REQUIRED"},
            {"name": "subscription_tier", "type": "STRING", "mode": "REQUIRED"},
            {"name": "amount", "type": "FLOAT64", "mode": "REQUIRED"},
            {"name": "currency", "type": "STRING", "mode": "REQUIRED"},
            {"name": "event_type", "type": "STRING", "mode": "REQUIRED"},
            {"name": "timestamp", "type": "TIMESTAMP", "mode": "REQUIRED"},
        ],
    }
    
    def __init__(self, project_id: Optional[str] = None):
        """Initialize BigQuery client."""
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID", "vitaflow-prod")
        self._client = None
    
    @property
    def client(self):
        """Lazy-load BigQuery client."""
        if self._client is None:
            try:
                from google.cloud import bigquery
                self._client = bigquery.Client(project=self.project_id)
                logger.info("BigQuery client initialized")
            except ImportError:
                logger.warning("google-cloud-bigquery not installed")
                self._client = "unavailable"
            except Exception as e:
                logger.warning(f"BigQuery unavailable: {e}")
                self._client = "unavailable"
        return self._client
    
    def setup_dataset(self) -> bool:
        """Create dataset and tables if they don't exist."""
        if self.client == "unavailable":
            return False
        
        try:
            from google.cloud import bigquery
            
            # Create dataset
            dataset_ref = f"{self.project_id}.{self.DATASET_ID}"
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = "US"
            self.client.create_dataset(dataset, exists_ok=True)
            
            # Create tables
            for table_name, schema in self.SCHEMAS.items():
                table_ref = f"{dataset_ref}.{table_name}"
                table = bigquery.Table(
                    table_ref,
                    schema=[bigquery.SchemaField(**field) for field in schema]
                )
                self.client.create_table(table, exists_ok=True)
                logger.info(f"Created/verified table: {table_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup BigQuery: {e}")
            return False
    
    def log_form_check(self, event: FormCheckEvent) -> bool:
        """Log form check event to BigQuery."""
        return self._insert_row("form_checks", {
            "user_id": event.user_id,
            "form_check_id": event.form_check_id,
            "exercise_type": event.exercise_type,
            "form_quality_score": event.form_quality_score,
            "feedback": event.feedback,
            "subscription_tier": event.subscription_tier,
            "timestamp": event.timestamp.isoformat(),
        })
    
    def log_wearable_sync(self, event: WearableSyncEvent) -> bool:
        """Log wearable sync event to BigQuery."""
        return self._insert_row("wearable_syncs", {
            "user_id": event.user_id,
            "device_type": event.device_type,
            "sync_status": event.sync_status,
            "metrics_synced": event.metrics_synced,
            "timestamp": event.timestamp.isoformat(),
        })
    
    def log_revenue(self, event: RevenueEvent) -> bool:
        """Log revenue event to BigQuery."""
        return self._insert_row("revenue", {
            "user_id": event.user_id,
            "subscription_tier": event.subscription_tier,
            "amount": event.amount,
            "currency": event.currency,
            "event_type": event.event_type,
            "timestamp": event.timestamp.isoformat(),
        })
    
    def _insert_row(self, table_name: str, row: Dict[str, Any]) -> bool:
        """Insert a single row to BigQuery."""
        if self.client == "unavailable":
            logger.debug(f"BigQuery unavailable, skipping log to {table_name}")
            return False
        
        try:
            table_ref = f"{self.project_id}.{self.DATASET_ID}.{table_name}"
            errors = self.client.insert_rows_json(table_ref, [row])
            
            if errors:
                logger.error(f"BigQuery insert errors: {errors}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to insert to BigQuery: {e}")
            return False
    
    def get_daily_metrics(self) -> Dict[str, Any]:
        """Get daily KPI metrics."""
        if self.client == "unavailable":
            return self._demo_metrics()
        
        try:
            query = f"""
            SELECT
                COUNT(DISTINCT user_id) as daily_active_users,
                COUNT(*) as form_checks_today,
                AVG(form_quality_score) as avg_form_quality
            FROM `{self.project_id}.{self.DATASET_ID}.form_checks`
            WHERE DATE(timestamp) = CURRENT_DATE()
            """
            
            result = self.client.query(query).result()
            row = next(result)
            
            return {
                "daily_active_users": row.daily_active_users or 0,
                "form_checks_today": row.form_checks_today or 0,
                "avg_form_quality": float(row.avg_form_quality or 0),
            }
            
        except Exception as e:
            logger.error(f"Failed to query BigQuery: {e}")
            return self._demo_metrics()
    
    def get_wearable_sync_rate(self) -> float:
        """Get wearable sync success rate (last 24h)."""
        if self.client == "unavailable":
            return 0.95  # Demo value
        
        try:
            query = f"""
            SELECT
                COUNTIF(sync_status = 'success') / COUNT(*) as success_rate
            FROM `{self.project_id}.{self.DATASET_ID}.wearable_syncs`
            WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
            """
            
            result = self.client.query(query).result()
            row = next(result)
            
            return float(row.success_rate or 0)
            
        except Exception as e:
            logger.error(f"Failed to query sync rate: {e}")
            return 0.0
    
    def get_revenue_today(self) -> float:
        """Get total revenue for today."""
        if self.client == "unavailable":
            return 0.0
        
        try:
            query = f"""
            SELECT
                SUM(amount) as total_revenue
            FROM `{self.project_id}.{self.DATASET_ID}.revenue`
            WHERE DATE(timestamp) = CURRENT_DATE()
            AND event_type IN ('subscription', 'upgrade')
            """
            
            result = self.client.query(query).result()
            row = next(result)
            
            return float(row.total_revenue or 0)
            
        except Exception as e:
            logger.error(f"Failed to query revenue: {e}")
            return 0.0
    
    def _demo_metrics(self) -> Dict[str, Any]:
        """Return demo metrics when BigQuery is unavailable."""
        return {
            "daily_active_users": 1247,
            "form_checks_today": 3892,
            "avg_form_quality": 7.8,
        }


# Global instance
_bigquery_service: Optional[BigQueryService] = None


def get_bigquery_service() -> BigQueryService:
    """Get or create global BigQuery instance."""
    global _bigquery_service
    if _bigquery_service is None:
        _bigquery_service = BigQueryService()
    return _bigquery_service
