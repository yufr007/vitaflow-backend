# app/services/azure_document_intelligence.py
"""
VitaFlow - Azure Document Intelligence (Form Recognizer) Integration.

Provides nutrition label OCR scanning (Pro tier feature).
Features:
- Extract nutrition facts from food labels
- Parse ingredient lists
- Calculate macros automatically
"""

import os
import logging
from typing import Optional, Dict, Any, List
from io import BytesIO

try:
    from azure.ai.formrecognizer import DocumentAnalysisClient
    from azure.core.credentials import AzureKeyCredential
    AZURE_FORM_RECOGNIZER_AVAILABLE = True
except ImportError:
    AZURE_FORM_RECOGNIZER_AVAILABLE = False
    DocumentAnalysisClient = None
    AzureKeyCredential = None

logger = logging.getLogger(__name__)


class AzureDocumentIntelligenceService:
    """
    Azure Document Intelligence for nutrition label scanning.
    
    Usage:
        service = AzureDocumentIntelligenceService()
        await service.initialize()
        nutrition_data = await service.analyze_nutrition_label(image_bytes)
    """
    
    _instance: Optional['AzureDocumentIntelligenceService'] = None
    _initialized: bool = False
    
    def __init__(self):
        """Initialize Azure Document Intelligence configuration."""
        self.client: Optional[DocumentAnalysisClient] = None
        self.endpoint: Optional[str] = None
        self.key: Optional[str] = None
        
    @classmethod
    def get_instance(cls) -> 'AzureDocumentIntelligenceService':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def initialize(self) -> bool:
        """
        Initialize Azure Document Intelligence connection.
        
        Returns:
            bool: True if initialization successful.
        """
        if self._initialized:
            return True
        
        if not AZURE_FORM_RECOGNIZER_AVAILABLE:
            logger.warning("Azure Form Recognizer SDK not installed - pip install azure-ai-formrecognizer")
            return False
        
        try:
            self.endpoint = os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT")
            self.key = os.getenv("AZURE_FORM_RECOGNIZER_KEY")
            
            if not self.endpoint or not self.key:
                logger.warning("Azure Document Intelligence not configured - using fallback mode")
                return False
            
            self.client = DocumentAnalysisClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.key)
            )
            
            logger.info("Azure Document Intelligence initialized")
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Azure Document Intelligence: {e}")
            return False
    
    @property
    def is_available(self) -> bool:
        """Check if Azure Document Intelligence is available."""
        return self._initialized and self.client is not None
    
    # =========================================================================
    # Nutrition Label Analysis
    # =========================================================================
    
    async def analyze_nutrition_label(
        self,
        image_data: bytes
    ) -> Optional[Dict[str, Any]]:
        """
        Extract nutrition facts from food label image.
        
        Args:
            image_data: Image bytes (JPEG, PNG)
        
        Returns:
            {
                "product_name": "Protein Bar",
                "serving_size": "60g",
                "servings_per_container": 12,
                "calories": 200,
                "total_fat": 8.0,
                "saturated_fat": 3.0,
                "trans_fat": 0.0,
                "cholesterol": 10,
                "sodium": 150,
                "total_carbohydrate": 22.0,
                "dietary_fiber": 3.0,
                "sugars": 12.0,
                "protein": 10.0,
                "ingredients": ["..."],
                "allergens": ["milk", "soy"],
                "confidence": 0.95
            }
        """
        if not self.is_available:
            logger.warning("Azure Document Intelligence not available - using fallback")
            return self._fallback_nutrition_response()
        
        try:
            # Analyze document using prebuilt nutrition model (if available)
            # Otherwise use general document model
            poller = self.client.begin_analyze_document(
                model_id="prebuilt-document",  # Use "prebuilt-nutrition" when available
                document=BytesIO(image_data)
            )
            
            result = poller.result()
            
            # Extract nutrition facts from detected fields
            nutrition_data = {
                "product_name": None,
                "serving_size": None,
                "servings_per_container": None,
                "calories": None,
                "total_fat": None,
                "saturated_fat": None,
                "trans_fat": None,
                "cholesterol": None,
                "sodium": None,
                "total_carbohydrate": None,
                "dietary_fiber": None,
                "sugars": None,
                "protein": None,
                "ingredients": [],
                "allergens": [],
                "confidence": 0.0
            }
            
            # Parse key-value pairs
            confidences = []
            for kv_pair in result.key_value_pairs:
                if kv_pair.key and kv_pair.value:
                    key_text = kv_pair.key.content.lower()
                    value_text = kv_pair.value.content
                    
                    # Match nutrition fields
                    if "calorie" in key_text:
                        nutrition_data["calories"] = self._parse_number(value_text)
                    elif "protein" in key_text:
                        nutrition_data["protein"] = self._parse_number(value_text)
                    elif "carb" in key_text or "carbohydrate" in key_text:
                        nutrition_data["total_carbohydrate"] = self._parse_number(value_text)
                    elif "fat" in key_text and "saturated" not in key_text and "trans" not in key_text:
                        nutrition_data["total_fat"] = self._parse_number(value_text)
                    elif "fiber" in key_text:
                        nutrition_data["dietary_fiber"] = self._parse_number(value_text)
                    elif "sugar" in key_text:
                        nutrition_data["sugars"] = self._parse_number(value_text)
                    elif "sodium" in key_text:
                        nutrition_data["sodium"] = self._parse_number(value_text)
                    elif "serving" in key_text:
                        nutrition_data["serving_size"] = value_text
                    
                    if kv_pair.confidence:
                        confidences.append(kv_pair.confidence)
            
            # Calculate average confidence
            if confidences:
                nutrition_data["confidence"] = sum(confidences) / len(confidences)
            
            # Extract text for ingredients (usually in a paragraph)
            all_text = []
            for page in result.pages:
                for line in page.lines:
                    all_text.append(line.content)
            
            # Simple ingredient detection (look for "ingredients:" section)
            full_text = " ".join(all_text).lower()
            if "ingredients:" in full_text:
                ing_start = full_text.index("ingredients:")
                ing_text = full_text[ing_start:ing_start+500]  # Get next 500 chars
                ingredients = self._parse_ingredients(ing_text)
                nutrition_data["ingredients"] = ingredients
            
            # Detect common allergens
            nutrition_data["allergens"] = self._detect_allergens(full_text)
            
            logger.info(f"Nutrition label analyzed: {nutrition_data.get('product_name', 'Unknown')}")
            return nutrition_data
            
        except Exception as e:
            logger.error(f"Failed to analyze nutrition label: {e}")
            return self._fallback_nutrition_response()
    
    def _parse_number(self, text: str) -> Optional[float]:
        """Extract numeric value from text (e.g., '200mg' -> 200)."""
        import re
        match = re.search(r'(\d+\.?\d*)', text)
        if match:
            return float(match.group(1))
        return None
    
    def _parse_ingredients(self, text: str) -> List[str]:
        """Parse comma-separated ingredient list."""
        # Remove 'ingredients:' prefix
        text = text.replace("ingredients:", "").strip()
        # Split by comma and clean
        ingredients = [ing.strip() for ing in text.split(",")]
        return [ing for ing in ingredients if ing and len(ing) > 2][:20]  # Limit to 20
    
    def _detect_allergens(self, text: str) -> List[str]:
        """Detect common allergens in text."""
        allergens = {
            "milk": ["milk", "dairy", "lactose", "whey", "casein"],
            "eggs": ["egg", "eggs"],
            "fish": ["fish"],
            "shellfish": ["shellfish", "shrimp", "crab", "lobster"],
            "tree_nuts": ["almond", "walnut", "cashew", "pecan", "pistachio"],
            "peanuts": ["peanut"],
            "wheat": ["wheat", "gluten"],
            "soy": ["soy", "soybean"]
        }
        
        detected = []
        for allergen, keywords in allergens.items():
            if any(keyword in text for keyword in keywords):
                detected.append(allergen)
        
        return detected
    
    def _fallback_nutrition_response(self) -> Dict[str, Any]:
        """Fallback response when Azure is unavailable."""
        return {
            "product_name": "Unknown",
            "message": "Azure Document Intelligence not configured - manual entry required",
            "calories": None,
            "protein": None,
            "total_carbohydrate": None,
            "total_fat": None,
            "confidence": 0.0,
            "ai_provider": "fallback"
        }
    
    # =========================================================================
    # Recipe Scanning (Future Feature)
    # =========================================================================
    
    async def analyze_recipe(
        self,
        image_data: bytes
    ) -> Optional[Dict[str, Any]]:
        """
        Extract recipe information from image (cookbook, screenshot).
        
        Returns:
            {
                "recipe_name": "Grilled Chicken",
                "ingredients": [...],
                "instructions": [...],
                "prep_time": "15 min",
                "cook_time": "30 min"
            }
        """
        # Similar to nutrition label analysis but with different field extraction
        # Implementation placeholder for Phase 2
        pass


# Singleton instance
azure_document_intelligence = AzureDocumentIntelligenceService.get_instance()
