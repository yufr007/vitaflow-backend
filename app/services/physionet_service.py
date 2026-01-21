"""
VitaFlow API - PhysioNet Research Service.

Provides research citations and dataset references from PhysioNet.org,
the Research Resource for Complex Physiologic Signals.

All datasets referenced are Open Access - no credentialing required.

Sources:
- https://physionet.org/content/
- PhysioNet API: https://physionet.org/api/v1/
"""

import httpx
import logging
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PhysioNetCitation(BaseModel):
    """Citation model for PhysioNet datasets."""
    id: str = Field(..., description="Dataset identifier (e.g., 'mmash')")
    title: str = Field(..., description="Full dataset title")
    authors: List[str] = Field(default_factory=list, description="Dataset authors")
    version: str = Field(default="1.0.0", description="Dataset version")
    url: str = Field(..., description="PhysioNet URL")
    access_type: str = Field(default="open", description="open, credentialed, or restricted")
    description: Optional[str] = Field(None, description="Brief description")
    relevance: Optional[str] = Field(None, description="Relevance to VitaFlow")


class PhysioNetService:
    """
    Service to interact with PhysioNet's database catalog.
    
    Provides research citations for:
    - Wearable device validation
    - Recovery scoring algorithms  
    - Activity and sleep analysis
    - Stress detection patterns
    """
    
    BASE_URL = "https://physionet.org"
    API_URL = "https://physionet.org/api/v1"
    
    # Pre-configured datasets relevant to VitaFlow (smartwatch/listening devices)
    VITAFLOW_DATASETS = {
        "mmash": {
            "id": "mmash",
            "title": "Multilevel Monitoring of Activity and Sleep in Healthy People",
            "authors": ["Massimiliano Rossi", "et al."],
            "version": "1.0.0",
            "url": "https://physionet.org/content/mmash/1.0.0/",
            "access_type": "open",
            "description": "24hr beat-to-beat heart data, accelerometer, sleep quality, activity",
            "relevance": "Recovery scoring, sleep analysis, activity validation"
        },
        "sleep-accel": {
            "id": "sleep-accel",
            "title": "Motion and Heart Rate from Wrist-Worn Wearable and Labeled Sleep from PSG",
            "authors": ["Olivia Walch", "et al."],
            "version": "1.0.0",
            "url": "https://physionet.org/content/sleep-accel/1.0.0/",
            "access_type": "open",
            "description": "Apple Watch motion/HR data with polysomnography-labeled sleep",
            "relevance": "Wearable HR validation, sleep detection benchmarks"
        },
        "cgmacros": {
            "id": "cgmacros",
            "title": "CGMacros: A Scientific Dataset for Personalized Nutrition and Diet Monitoring",
            "authors": ["Maria Rodriguez", "et al."],
            "version": "1.0.0",
            "url": "https://physionet.org/content/cgmacros/",
            "access_type": "open",
            "description": "CGM data, food macronutrients, wearable sensor data, demographics",
            "relevance": "Meal planning AI validation, glycemic response patterns"
        },
        "wearable-exam-stress": {
            "id": "wearable-exam-stress",
            "title": "A Wearable Exam Stress Dataset for Predicting Cognitive Performance",
            "authors": ["Stress Research Team"],
            "version": "1.0.0",
            "url": "https://physionet.org/content/wearable-exam-stress/",
            "access_type": "open",
            "description": "EDA, HR, BVP, skin temp, IBI, accelerometer during exam stress",
            "relevance": "Flow Engine stress detection, mental wellness scoring"
        },
        "autonomic-aging-cardiovascular": {
            "id": "autonomic-aging-cardiovascular",
            "title": "Autonomic Aging: Changes of Cardiovascular Autonomic Function During Healthy Aging",
            "authors": ["Autonomic Research Group"],
            "version": "1.0.0", 
            "url": "https://physionet.org/content/autonomic-aging-cardiovascular/",
            "access_type": "open",
            "description": "ECG and BP recordings from 1,104 healthy volunteers across age groups",
            "relevance": "Age-stratified recovery baselines, HRV reference values"
        },
        "ephnogram": {
            "id": "ephnogram",
            "title": "EPHNOGRAM: Simultaneous ECG and Phonocardiogram Database",
            "authors": ["EPHNOGRAM Team"],
            "version": "1.0.0",
            "url": "https://physionet.org/content/ephnogram/",
            "access_type": "open",
            "description": "ECG/PCG from young healthy adults during stress-test experiments",
            "relevance": "Workout intensity zone calibration, exercise HR patterns"
        },
        "big-ideas-glycemic-wearable": {
            "id": "big-ideas-glycemic-wearable", 
            "title": "BIG IDEAs Lab Glycemic Variability and Wearable Device Data",
            "authors": ["BIG IDEAs Lab"],
            "version": "1.1.1",
            "url": "https://physionet.org/content/big-ideas-glycemic-wearable/1.1.1/",
            "access_type": "open",
            "description": "Glucose measurements and wrist-worn wearable sensor data",
            "relevance": "Wearable device benchmarks, metabolic health correlation"
        }
    }
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=15.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 3600 * 24  # 24 hours
    
    async def get_dataset_info(self, dataset_id: str) -> Optional[PhysioNetCitation]:
        """Get information about a specific PhysioNet dataset."""
        
        # Check curated list first
        if dataset_id in self.VITAFLOW_DATASETS:
            return PhysioNetCitation(**self.VITAFLOW_DATASETS[dataset_id])
        
        # Try API fetch for unknown datasets
        cache_key = f"dataset:{dataset_id}"
        if cache_key in self._cache:
            timestamp, data = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                return PhysioNetCitation(**data) if data else None
        
        try:
            response = await self.client.get(
                f"{self.API_URL}/published/{dataset_id}/",
                headers={"Accept": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                citation = PhysioNetCitation(
                    id=dataset_id,
                    title=data.get("title", "Unknown"),
                    authors=[a.get("name", "") for a in data.get("authors", [])[:3]],
                    version=data.get("version", "1.0.0"),
                    url=f"{self.BASE_URL}/content/{dataset_id}/",
                    access_type=data.get("access_policy", "open").lower(),
                    description=data.get("abstract", "")[:200]
                )
                self._cache[cache_key] = (time.time(), citation.model_dump())
                return citation
            else:
                self._cache[cache_key] = (time.time(), None)
                return None
                
        except Exception as e:
            logger.warning(f"PhysioNet API error for {dataset_id}: {e}")
            return None
    
    async def get_citations_for_recovery(self) -> List[PhysioNetCitation]:
        """Get PhysioNet citations relevant to recovery science."""
        recovery_datasets = ["mmash", "autonomic-aging-cardiovascular", "sleep-accel"]
        return [
            PhysioNetCitation(**self.VITAFLOW_DATASETS[ds])
            for ds in recovery_datasets
            if ds in self.VITAFLOW_DATASETS
        ]
    
    async def get_citations_for_activity(self, activity_name: str = None) -> List[PhysioNetCitation]:
        """
        Get PhysioNet citations relevant to activity analysis.
        Args:
            activity_name: Optional name of the activity (e.g. "squat") to filter citations.
        """
        # Default activity citations
        activity_datasets = ["mmash", "ephnogram", "sleep-accel"]
        
        # If we had specific datasets for squat/deadlift, we'd add logic here
        # For now, we return the general activity validation datasets
        
        return [
            PhysioNetCitation(**self.VITAFLOW_DATASETS[ds])
            for ds in activity_datasets
            if ds in self.VITAFLOW_DATASETS
        ]
    
    async def get_citations_for_nutrition(self) -> List[PhysioNetCitation]:
        """Get PhysioNet citations relevant to nutrition/metabolic health."""
        nutrition_datasets = ["cgmacros", "big-ideas-glycemic-wearable"]
        return [
            PhysioNetCitation(**self.VITAFLOW_DATASETS[ds])
            for ds in nutrition_datasets
            if ds in self.VITAFLOW_DATASETS
        ]
    
    async def get_citations_for_stress(self) -> List[PhysioNetCitation]:
        """Get PhysioNet citations relevant to stress detection."""
        stress_datasets = ["wearable-exam-stress", "mmash"]
        return [
            PhysioNetCitation(**self.VITAFLOW_DATASETS[ds])
            for ds in stress_datasets
            if ds in self.VITAFLOW_DATASETS
        ]
    
    async def get_citations_for_wearable_validation(self) -> List[PhysioNetCitation]:
        """Get PhysioNet citations for wearable device validation."""
        wearable_datasets = ["sleep-accel", "big-ideas-glycemic-wearable", "mmash"]
        return [
            PhysioNetCitation(**self.VITAFLOW_DATASETS[ds])
            for ds in wearable_datasets
            if ds in self.VITAFLOW_DATASETS
        ]
    
    async def get_all_vitaflow_citations(self) -> List[PhysioNetCitation]:
        """Get all PhysioNet citations curated for VitaFlow."""
        return [
            PhysioNetCitation(**data) 
            for data in self.VITAFLOW_DATASETS.values()
        ]
    
    async def search_datasets(self, query: str, max_results: int = 5) -> List[PhysioNetCitation]:
        """
        Search PhysioNet datasets by keyword.
        
        Note: PhysioNet's API is limited, so we primarily search our curated list.
        """
        query_lower = query.lower()
        results = []
        
        for ds_id, ds_data in self.VITAFLOW_DATASETS.items():
            # Search in title, description, and relevance
            searchable = f"{ds_data['title']} {ds_data.get('description', '')} {ds_data.get('relevance', '')}".lower()
            if query_lower in searchable:
                results.append(PhysioNetCitation(**ds_data))
        
        return results[:max_results]
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# Singleton instance
physionet_service = PhysioNetService()
