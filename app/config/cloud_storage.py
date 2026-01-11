"""
VitaFlow API - Google Cloud Storage Service.

Handles file uploads for form check images, user avatars,
and other media assets using Cloud Storage.
"""

import os
import logging
from typing import Optional, BinaryIO
from datetime import datetime, timezone, timedelta
from uuid import uuid4

logger = logging.getLogger(__name__)


class CloudStorageService:
    """
    Google Cloud Storage integration for media files.
    
    Features:
    - Signed URLs for secure uploads/downloads
    - Automatic content type detection
    - Organized folder structure by user/content type
    - Image optimization support
    """
    
    def __init__(
        self,
        bucket_name: Optional[str] = None,
        project_id: Optional[str] = None,
    ):
        """
        Initialize Cloud Storage client.
        
        Args:
            bucket_name: GCS bucket name. Defaults to STORAGE_BUCKET env var.
            project_id: GCP project ID. Defaults to GCP_PROJECT_ID env var.
        """
        self.bucket_name = bucket_name or os.getenv("STORAGE_BUCKET", "vitaflow-media")
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID", "vitaflow-prod")
        self._client = None
        self._bucket = None
    
    @property
    def client(self):
        """Lazy-load storage client."""
        if self._client is None:
            try:
                from google.cloud import storage
                self._client = storage.Client(project=self.project_id)
                logger.info("Cloud Storage client initialized")
            except ImportError:
                logger.warning("google-cloud-storage not installed")
                self._client = "unavailable"
            except Exception as e:
                logger.warning(f"Cloud Storage unavailable: {e}")
                self._client = "unavailable"
        return self._client
    
    @property
    def bucket(self):
        """Get storage bucket."""
        if self._bucket is None and self.client != "unavailable":
            self._bucket = self.client.bucket(self.bucket_name)
        return self._bucket
    
    def upload_file(
        self,
        file_data: BinaryIO,
        file_name: str,
        folder: str,
        content_type: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Upload a file to Cloud Storage.
        
        Args:
            file_data: File binary data.
            file_name: Original filename.
            folder: Storage folder (form-checks, avatars, etc).
            content_type: MIME type (auto-detected if not provided).
            user_id: Optional user ID for path organization.
        
        Returns:
            Public URL or signed URL of uploaded file.
        """
        if self.bucket is None:
            logger.error("Cloud Storage bucket not available")
            return None
        
        # Generate unique filename
        ext = file_name.split(".")[-1] if "." in file_name else "bin"
        unique_name = f"{uuid4().hex}.{ext}"
        
        # Build path: folder/user_id/date/filename
        date_path = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        if user_id:
            blob_path = f"{folder}/{user_id}/{date_path}/{unique_name}"
        else:
            blob_path = f"{folder}/{date_path}/{unique_name}"
        
        try:
            blob = self.bucket.blob(blob_path)
            
            # Detect content type
            if content_type is None:
                content_type = self._detect_content_type(file_name)
            
            blob.upload_from_file(file_data, content_type=content_type)
            
            logger.info(f"Uploaded file: {blob_path}")
            
            # Return public URL if bucket is public, else signed URL
            return self.get_signed_url(blob_path)
            
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            return None
    
    def upload_form_check_image(
        self,
        image_data: BinaryIO,
        user_id: str,
        exercise_type: str,
    ) -> Optional[str]:
        """Upload form check image with metadata."""
        filename = f"{exercise_type}_{uuid4().hex[:8]}.jpg"
        return self.upload_file(
            file_data=image_data,
            file_name=filename,
            folder="form-checks",
            content_type="image/jpeg",
            user_id=user_id,
        )
    
    def get_signed_url(
        self,
        blob_path: str,
        expiration_minutes: int = 60,
    ) -> Optional[str]:
        """
        Generate a signed URL for private file access.
        
        Args:
            blob_path: Path to the blob in the bucket.
            expiration_minutes: URL validity duration.
        
        Returns:
            Signed URL string.
        """
        if self.bucket is None:
            return None
        
        try:
            blob = self.bucket.blob(blob_path)
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=expiration_minutes),
                method="GET",
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate signed URL: {e}")
            return None
    
    def get_upload_signed_url(
        self,
        blob_path: str,
        content_type: str,
        expiration_minutes: int = 30,
    ) -> Optional[str]:
        """
        Generate a signed URL for direct browser uploads.
        
        Allows frontend to upload directly to Cloud Storage
        without proxying through the backend.
        """
        if self.bucket is None:
            return None
        
        try:
            blob = self.bucket.blob(blob_path)
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=expiration_minutes),
                method="PUT",
                content_type=content_type,
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate upload URL: {e}")
            return None
    
    def delete_file(self, blob_path: str) -> bool:
        """Delete a file from storage."""
        if self.bucket is None:
            return False
        
        try:
            blob = self.bucket.blob(blob_path)
            blob.delete()
            logger.info(f"Deleted file: {blob_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            return False
    
    def _detect_content_type(self, filename: str) -> str:
        """Detect MIME type from filename."""
        ext = filename.lower().split(".")[-1] if "." in filename else ""
        types = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "webp": "image/webp",
            "mp4": "video/mp4",
            "mov": "video/quicktime",
            "pdf": "application/pdf",
            "json": "application/json",
        }
        return types.get(ext, "application/octet-stream")


# Global instance
_storage_service: Optional[CloudStorageService] = None


def get_storage_service() -> CloudStorageService:
    """Get or create global Cloud Storage instance."""
    global _storage_service
    if _storage_service is None:
        _storage_service = CloudStorageService()
    return _storage_service
