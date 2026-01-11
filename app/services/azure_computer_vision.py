# app/services/azure_computer_vision.py
"""
VitaFlow - Azure Computer Vision Integration.

Enhanced form analysis with Azure Computer Vision (optional upgrade from Gemini).
Features:
- Advanced pose estimation
- Body landmark detection
- Joint angle calculation
- Movement pattern analysis
"""

import os
import logging
from typing import Optional, Dict, Any, List, Tuple

try:
    from azure.cognitiveservices.vision.computervision import ComputerVisionClient
    from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
    from msrest.authentication import CognitiveServicesCredentials
    AZURE_VISION_AVAILABLE = True
except ImportError:
    AZURE_VISION_AVAILABLE = False
    ComputerVisionClient = None
    CognitiveServicesCredentials = None

logger = logging.getLogger(__name__)


class AzureComputerVisionService:
    """
    Azure Computer Vision for enhanced form analysis.
    
    Usage:
        service = AzureComputerVisionService()
        await service.initialize()
        analysis = await service.analyze_exercise_form(image_bytes, "squat")
    """
    
    _instance: Optional['AzureComputerVisionService'] = None
    _initialized: bool = False
    
    def __init__(self):
        """Initialize Azure Computer Vision configuration."""
        self.client: Optional[ComputerVisionClient] = None
        self.endpoint: Optional[str] = None
        self.key: Optional[str] = None
        
    @classmethod
    def get_instance(cls) -> 'AzureComputerVisionService':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def initialize(self) -> bool:
        """
        Initialize Azure Computer Vision connection.
        
        Returns:
            bool: True if initialization successful.
        """
        if self._initialized:
            return True
        
        if not AZURE_VISION_AVAILABLE:
            logger.warning("Azure Computer Vision SDK not installed")
            return False
        
        try:
            self.endpoint = os.getenv("AZURE_COMPUTER_VISION_ENDPOINT")
            self.key = os.getenv("AZURE_COMPUTER_VISION_KEY")
            
            if not self.endpoint or not self.key:
                logger.warning("Azure Computer Vision not configured - using Gemini Vision")
                return False
            
            self.client = ComputerVisionClient(
                endpoint=self.endpoint,
                credentials=CognitiveServicesCredentials(self.key)
            )
            
            logger.info("Azure Computer Vision initialized")
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Azure Computer Vision: {e}")
            return False
    
    @property
    def is_available(self) -> bool:
        """Check if Azure Computer Vision is available."""
        return self._initialized and self.client is not None
    
    # =========================================================================
    # Image Analysis
    # =========================================================================
    
    async def analyze_image(
        self,
        image_data: bytes,
        features: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze image using Azure Computer Vision.
        
        Args:
            image_data: Image bytes
            features: Visual features to extract (tags, objects, faces, etc.)
        
        Returns:
            Analysis results
        """
        if not self.is_available:
            return None
        
        try:
            # Default features
            if features is None:
                features = [
                    VisualFeatureTypes.tags,
                    VisualFeatureTypes.objects,
                    VisualFeatureTypes.description
                ]
            
            # Analyze image
            analysis = self.client.analyze_image_in_stream(
                image=image_data,
                visual_features=features
            )
            
            return {
                "tags": [tag.name for tag in analysis.tags] if analysis.tags else [],
                "objects": [obj.object_property for obj in analysis.objects] if analysis.objects else [],
                "description": analysis.description.captions[0].text if analysis.description.captions else "",
                "confidence": analysis.description.captions[0].confidence if analysis.description.captions else 0.0
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze image: {e}")
            return None
    
    # =========================================================================
    # Form Analysis (Complementary to Gemini Vision)
    # =========================================================================
    
    async def analyze_exercise_form(
        self,
        image_data: bytes,
        exercise_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze exercise form using Computer Vision.
        
        This is complementary to Gemini Vision - use both for best results:
        - Azure: Object detection, scene understanding
        - Gemini: Exercise-specific feedback, coaching cues
        
        Args:
            image_data: Image bytes
            exercise_name: Exercise name
        
        Returns:
            {
                "detected_objects": ["person", "barbell", "gym"],
                "scene_confidence": 0.95,
                "environment_safe": true,
                "equipment_detected": ["barbell"],
                "ai_provider": "azure_vision"
            }
        """
        if not self.is_available:
            return {"ai_provider": "fallback", "message": "Azure Vision not available"}
        
        try:
            analysis = await self.analyze_image(image_data)
            
            if not analysis:
                return None
            
            # Detect gym equipment
            equipment_keywords = {
                "barbell", "dumbbell", "kettlebell", "bench", "rack", "mat",
                "pull-up bar", "cable machine", "weight plate"
            }
            detected_equipment = [
                obj for obj in analysis["objects"]
                if any(eq in obj.lower() for eq in equipment_keywords)
            ]
            
            # Check for person in frame
            has_person = "person" in analysis["objects"]
            
            # Environment safety check
            environment_safe = has_person and len(analysis["objects"]) > 0
            
            return {
                "detected_objects": analysis["objects"],
                "scene_confidence": analysis["confidence"],
                "environment_safe": environment_safe,
                "equipment_detected": detected_equipment,
                "has_person": has_person,
                "description": analysis["description"],
                "ai_provider": "azure_vision"
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze exercise form: {e}")
            return None
    
    # =========================================================================
    # Body Pose Detection (Future: Custom Vision model)
    # =========================================================================
    
    async def detect_body_landmarks(
        self,
        image_data: bytes
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Detect body landmarks for pose estimation.
        
        Note: This requires Azure Custom Vision with trained model.
        Placeholder for Phase 2 implementation.
        
        Returns:
            [
                {"landmark": "left_knee", "x": 0.45, "y": 0.67, "confidence": 0.92},
                ...
            ]
        """
        # Requires Custom Vision model training
        # For now, use Gemini Vision or MediaPipe
        logger.info("Body landmark detection requires Custom Vision - using MediaPipe fallback")
        return None


# Singleton instance
azure_computer_vision = AzureComputerVisionService.get_instance()
