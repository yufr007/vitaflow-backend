"""
Biomechanics Dataset Downloader

Utilities for downloading and organizing biomechanics datasets
from the various sources indexed in mkjung99/biomechanics_dataset.

Some datasets require manual download due to access requirements.
This module handles automated downloads where possible and provides
instructions for manual downloads.
"""

import os
import requests
import zipfile
import tarfile
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import logging
import json
import hashlib

logger = logging.getLogger(__name__)


class DownloadStatus(Enum):
    """Status of dataset download"""
    NOT_STARTED = "not_started"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    REQUIRES_MANUAL = "requires_manual"
    FAILED = "failed"


@dataclass
class DatasetDownload:
    """Information about a dataset download"""
    dataset_id: str
    source_url: str
    local_path: Path
    status: DownloadStatus
    size_bytes: Optional[int] = None
    checksum: Optional[str] = None
    instructions: Optional[str] = None


# Default data directory
DEFAULT_DATA_DIR = Path(__file__).parent.parent.parent.parent / "research-data" / "datasets"


class DatasetDownloader:
    """
    Download and manage biomechanics datasets.
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize downloader.
        
        Args:
            data_dir: Directory to store downloaded datasets.
                      Defaults to research-data/datasets/
        """
        self.data_dir = data_dir or DEFAULT_DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Track download status
        self.status_file = self.data_dir / "download_status.json"
        self.status = self._load_status()
    
    def _load_status(self) -> Dict[str, Any]:
        """Load download status from disk"""
        if self.status_file.exists():
            with open(self.status_file, 'r') as f:
                return json.load(f)
        return {"datasets": {}}
    
    def _save_status(self):
        """Save download status to disk"""
        with open(self.status_file, 'w') as f:
            json.dump(self.status, f, indent=2)
    
    def download_figshare(
        self,
        dataset_id: str,
        collection_id: str,
        article_id: Optional[str] = None
    ) -> DatasetDownload:
        """
        Download dataset from Figshare.
        
        Many biomechanics datasets are hosted on Figshare.
        
        Args:
            dataset_id: VitaFlow dataset ID
            collection_id: Figshare collection ID (from URL)
            article_id: Optional specific article ID
        """
        dataset_dir = self.data_dir / dataset_id
        dataset_dir.mkdir(parents=True, exist_ok=True)
        
        # Figshare API base
        api_base = "https://api.figshare.com/v2"
        
        try:
            if article_id:
                # Download specific article
                url = f"{api_base}/articles/{article_id}"
            else:
                # Get collection info
                url = f"{api_base}/collections/{collection_id}/articles"
            
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            # Download files
            if isinstance(data, list):
                articles = data
            else:
                articles = [data]
            
            for article in articles:
                article_id = article.get('id')
                article_url = f"{api_base}/articles/{article_id}"
                article_resp = requests.get(article_url)
                article_data = article_resp.json()
                
                for file_info in article_data.get('files', []):
                    file_url = file_info['download_url']
                    file_name = file_info['name']
                    file_path = dataset_dir / file_name
                    
                    if not file_path.exists():
                        logger.info(f"Downloading {file_name}...")
                        self._download_file(file_url, file_path)
            
            return DatasetDownload(
                dataset_id=dataset_id,
                source_url=f"https://figshare.com/collections/{collection_id}",
                local_path=dataset_dir,
                status=DownloadStatus.COMPLETED
            )
            
        except Exception as e:
            logger.error(f"Failed to download {dataset_id}: {e}")
            return DatasetDownload(
                dataset_id=dataset_id,
                source_url=f"https://figshare.com/collections/{collection_id}",
                local_path=dataset_dir,
                status=DownloadStatus.FAILED,
                instructions=str(e)
            )
    
    def download_zenodo(
        self,
        dataset_id: str,
        record_id: str
    ) -> DatasetDownload:
        """
        Download dataset from Zenodo.
        
        Args:
            dataset_id: VitaFlow dataset ID
            record_id: Zenodo record ID
        """
        dataset_dir = self.data_dir / dataset_id
        dataset_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Zenodo API
            url = f"https://zenodo.org/api/records/{record_id}"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            for file_info in data.get('files', []):
                file_url = file_info['links']['self']
                file_name = file_info['key']
                file_path = dataset_dir / file_name
                
                if not file_path.exists():
                    logger.info(f"Downloading {file_name}...")
                    self._download_file(file_url, file_path)
            
            return DatasetDownload(
                dataset_id=dataset_id,
                source_url=f"https://zenodo.org/record/{record_id}",
                local_path=dataset_dir,
                status=DownloadStatus.COMPLETED
            )
            
        except Exception as e:
            logger.error(f"Failed to download {dataset_id}: {e}")
            return DatasetDownload(
                dataset_id=dataset_id,
                source_url=f"https://zenodo.org/record/{record_id}",
                local_path=dataset_dir,
                status=DownloadStatus.FAILED,
                instructions=str(e)
            )
    
    def download_mendeley(
        self,
        dataset_id: str,
        doi: str
    ) -> DatasetDownload:
        """
        Mendeley Data requires manual download.
        Returns instructions for manual download.
        """
        dataset_dir = self.data_dir / dataset_id
        dataset_dir.mkdir(parents=True, exist_ok=True)
        
        return DatasetDownload(
            dataset_id=dataset_id,
            source_url=f"https://data.mendeley.com/datasets/{doi}",
            local_path=dataset_dir,
            status=DownloadStatus.REQUIRES_MANUAL,
            instructions=f"""
Mendeley Data requires manual download:
1. Visit: https://data.mendeley.com/datasets/{doi}
2. Click "Download" and accept any terms
3. Download all files to: {dataset_dir}
4. Run verify_dataset('{dataset_id}') after download
"""
        )
    
    def _download_file(
        self,
        url: str,
        filepath: Path,
        chunk_size: int = 8192
    ):
        """Download a file with progress"""
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size:
                        progress = (downloaded / total_size) * 100
                        print(f"\r  Progress: {progress:.1f}%", end='')
        
        print()  # New line after progress
    
    def extract_archive(self, filepath: Path, extract_to: Optional[Path] = None):
        """Extract zip or tar archive"""
        if extract_to is None:
            extract_to = filepath.parent
        
        if filepath.suffix == '.zip':
            with zipfile.ZipFile(filepath, 'r') as zf:
                zf.extractall(extract_to)
        elif filepath.suffix in ['.tar', '.gz', '.tgz']:
            with tarfile.open(filepath, 'r:*') as tf:
                tf.extractall(extract_to)
        else:
            logger.warning(f"Unknown archive format: {filepath.suffix}")
    
    def list_c3d_files(self, dataset_id: str) -> List[Path]:
        """List all C3D files in a downloaded dataset"""
        dataset_dir = self.data_dir / dataset_id
        if not dataset_dir.exists():
            return []
        
        return list(dataset_dir.glob("**/*.c3d")) + list(dataset_dir.glob("**/*.C3D"))
    
    def get_download_instructions(self, dataset_id: str) -> str:
        """Get download instructions for a dataset"""
        from . import PRIORITY_DATASETS
        
        dataset = next((d for d in PRIORITY_DATASETS if d.id == dataset_id), None)
        if not dataset:
            return f"Unknown dataset: {dataset_id}"
        
        return f"""
Dataset: {dataset.name}
URL: {dataset.data_url}
DOI: {dataset.doi}

To download:
1. Visit the URL above
2. Follow site-specific download instructions
3. Place files in: {self.data_dir / dataset_id}
4. Run: downloader.verify_dataset('{dataset_id}')
"""
    
    def verify_dataset(self, dataset_id: str) -> Dict[str, Any]:
        """Verify a downloaded dataset"""
        dataset_dir = self.data_dir / dataset_id
        
        if not dataset_dir.exists():
            return {"status": "not_found", "path": str(dataset_dir)}
        
        c3d_files = self.list_c3d_files(dataset_id)
        all_files = list(dataset_dir.glob("**/*"))
        
        return {
            "status": "found" if c3d_files else "no_c3d_files",
            "path": str(dataset_dir),
            "total_files": len([f for f in all_files if f.is_file()]),
            "c3d_files": len(c3d_files),
            "size_mb": sum(f.stat().st_size for f in all_files if f.is_file()) / (1024 * 1024)
        }


# Priority dataset download mappings
DATASET_SOURCES = {
    "ferber_2024": {
        "type": "figshare",
        "article_id": "24255795"
    },
    "gaitrec": {
        "type": "figshare",
        "collection_id": "4788012"
    },
    "mohr_squat": {
        "type": "mendeley",
        "doi": "37wyv32y8j"
    },
    "van_criekinge_2023": {
        "type": "figshare",
        "collection_id": "6503791"
    },
    "ozkaya_throwing": {
        "type": "figshare",
        "collection_id": "4017808"
    },
    "szcz_karate": {
        "type": "figshare",
        "collection_id": "4981073"
    },
    "mohr_knee_injury": {
        "type": "mendeley",
        "doi": "f2fv7gb577"
    },
    "toronto_elderly": {
        "type": "figshare",
        "collection_id": "5515953"
    }
}


def download_priority_datasets(min_priority: int = 8) -> List[DatasetDownload]:
    """
    Download all high-priority datasets.
    
    Args:
        min_priority: Minimum priority level to download
        
    Returns:
        List of DatasetDownload objects with status
    """
    from . import get_high_priority_datasets
    
    downloader = DatasetDownloader()
    results = []
    
    for dataset in get_high_priority_datasets(min_priority):
        if dataset.id not in DATASET_SOURCES:
            logger.warning(f"No source mapping for {dataset.id}")
            continue
        
        source = DATASET_SOURCES[dataset.id]
        
        if source["type"] == "figshare":
            if "collection_id" in source:
                result = downloader.download_figshare(
                    dataset.id,
                    collection_id=source["collection_id"]
                )
            else:
                result = downloader.download_figshare(
                    dataset.id,
                    collection_id="",
                    article_id=source["article_id"]
                )
        elif source["type"] == "zenodo":
            result = downloader.download_zenodo(
                dataset.id,
                record_id=source["record_id"]
            )
        elif source["type"] == "mendeley":
            result = downloader.download_mendeley(
                dataset.id,
                doi=source["doi"]
            )
        else:
            continue
        
        results.append(result)
        
        # Update status
        downloader.status["datasets"][dataset.id] = {
            "status": result.status.value,
            "path": str(result.local_path)
        }
        downloader._save_status()
    
    return results


if __name__ == "__main__":
    # Demo
    print("VitaFlow Dataset Downloader")
    print("=" * 50)
    
    downloader = DatasetDownloader()
    
    print(f"\nData directory: {downloader.data_dir}")
    print("\nDataset download instructions:")
    
    for ds_id in ["ferber_2024", "mohr_squat"]:
        print(downloader.get_download_instructions(ds_id))
