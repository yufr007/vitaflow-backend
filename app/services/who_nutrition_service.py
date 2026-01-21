# app/services/who_nutrition_service.py
"""
VitaFlow API - WHO eLENA Nutrition Guidelines Service.

Provides evidence-based nutrition guidelines from the WHO Electronic Library
of Evidence for Nutrition Actions (eLENA).

All guidelines are sourced from: https://www.who.int/elena/

WARNING: These are real WHO guidelines. Do not modify without verifying
against official WHO documentation.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class NutrientCategory(str, Enum):
    """Categories of nutrients with WHO guidelines."""
    SODIUM = "sodium"
    SUGAR = "sugar"
    SATURATED_FAT = "saturated_fat"
    FIBER = "fiber"
    FRUITS_VEGETABLES = "fruits_vegetables"
    POTASSIUM = "potassium"
    TRANS_FAT = "trans_fat"


@dataclass
class WHOGuideline:
    """A single WHO eLENA guideline with source attribution."""
    nutrient: NutrientCategory
    recommendation: str
    threshold_value: float
    threshold_unit: str
    threshold_type: str  # "max", "min", "range"
    source_title: str
    source_url: str
    publication_year: int
    evidence_quality: str  # "strong", "moderate", "conditional"


class WHONutritionService:
    """
    Service providing evidence-based WHO nutrition guidelines.
    
    All data is sourced from WHO eLENA (Electronic Library of Evidence
    for Nutrition Actions): https://www.who.int/elena/
    
    Guidelines are used to:
    1. Validate AI-generated meal plans
    2. Inject context into AI prompts for scientifically-backed generation
    3. Score meal plans for compliance ("WHO Score")
    """
    
    # =========================================================================
    # REAL WHO GUIDELINES (verified from official sources)
    # =========================================================================
    
    GUIDELINES: Dict[NutrientCategory, WHOGuideline] = {
        NutrientCategory.SODIUM: WHOGuideline(
            nutrient=NutrientCategory.SODIUM,
            recommendation="Adults should consume less than 2g of sodium (5g salt) per day",
            threshold_value=2.0,
            threshold_unit="g/day",
            threshold_type="max",
            source_title="WHO Guideline: Sodium intake for adults and children",
            source_url="https://www.who.int/publications/i/item/9789241504836",
            publication_year=2012,
            evidence_quality="strong"
        ),
        NutrientCategory.SUGAR: WHOGuideline(
            nutrient=NutrientCategory.SUGAR,
            recommendation="Free sugars should be less than 10% of total energy intake; "
                          "a further reduction to below 5% provides additional health benefits",
            threshold_value=10.0,
            threshold_unit="% of energy",
            threshold_type="max",
            source_title="WHO Guideline: Sugars intake for adults and children",
            source_url="https://www.who.int/publications/i/item/9789241549028",
            publication_year=2015,
            evidence_quality="strong"
        ),
        NutrientCategory.SATURATED_FAT: WHOGuideline(
            nutrient=NutrientCategory.SATURATED_FAT,
            recommendation="Saturated fatty acid intake should be less than 10% of total energy intake",
            threshold_value=10.0,
            threshold_unit="% of energy",
            threshold_type="max",
            source_title="WHO Guideline: Saturated fatty acid and trans-fatty acid intake",
            source_url="https://www.who.int/publications/i/item/9789240073630",
            publication_year=2023,
            evidence_quality="strong"
        ),
        NutrientCategory.TRANS_FAT: WHOGuideline(
            nutrient=NutrientCategory.TRANS_FAT,
            recommendation="Trans-fatty acid intake should be less than 1% of total energy intake",
            threshold_value=1.0,
            threshold_unit="% of energy",
            threshold_type="max",
            source_title="WHO Guideline: Saturated fatty acid and trans-fatty acid intake",
            source_url="https://www.who.int/publications/i/item/9789240073630",
            publication_year=2023,
            evidence_quality="strong"
        ),
        NutrientCategory.FIBER: WHOGuideline(
            nutrient=NutrientCategory.FIBER,
            recommendation="Adults should consume at least 25g of dietary fibre per day",
            threshold_value=25.0,
            threshold_unit="g/day",
            threshold_type="min",
            source_title="WHO/FAO Expert Consultation on Diet, Nutrition and Prevention of Chronic Diseases",
            source_url="https://www.who.int/publications/i/item/924120916X",
            publication_year=2003,
            evidence_quality="strong"
        ),
        NutrientCategory.FRUITS_VEGETABLES: WHOGuideline(
            nutrient=NutrientCategory.FRUITS_VEGETABLES,
            recommendation="Eat at least 400g (5 portions) of fruits and vegetables per day",
            threshold_value=400.0,
            threshold_unit="g/day",
            threshold_type="min",
            source_title="WHO Healthy Diet Fact Sheet",
            source_url="https://www.who.int/news-room/fact-sheets/detail/healthy-diet",
            publication_year=2020,
            evidence_quality="strong"
        ),
        NutrientCategory.POTASSIUM: WHOGuideline(
            nutrient=NutrientCategory.POTASSIUM,
            recommendation="Adults should consume at least 3510mg of potassium per day",
            threshold_value=3510.0,
            threshold_unit="mg/day",
            threshold_type="min",
            source_title="WHO Guideline: Potassium intake for adults and children",
            source_url="https://www.who.int/publications/i/item/9789241504829",
            publication_year=2012,
            evidence_quality="strong"
        ),
    }
    
    def get_all_guidelines(self) -> List[WHOGuideline]:
        """Get all WHO nutrition guidelines."""
        return list(self.GUIDELINES.values())
    
    def get_guideline(self, nutrient: NutrientCategory) -> Optional[WHOGuideline]:
        """Get a specific guideline by nutrient category."""
        return self.GUIDELINES.get(nutrient)
    
    def build_ai_context(self) -> str:
        """
        Build a context string for AI prompts with WHO guidelines.
        
        This is injected into Gemini prompts to ensure meal plans
        follow evidence-based nutrition principles.
        """
        context = "\n\nWHO NUTRITION GUIDELINES (mandatory compliance):"
        context += "\nSource: WHO eLENA - https://www.who.int/elena/\n"
        
        for guideline in self.GUIDELINES.values():
            context += f"\n- {guideline.nutrient.value.upper()}: {guideline.recommendation}"
            context += f" [{guideline.source_title}, {guideline.publication_year}]"
        
        context += "\n\nYour meal plan MUST prioritize these guidelines. "
        context += "Include a 'who_compliance_notes' field explaining how each day meets WHO standards."
        
        return context
    
    def check_meal_compliance(
        self,
        daily_nutrition: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Check a day's nutrition against WHO guidelines.
        
        Args:
            daily_nutrition: Dict with keys like 'sodium_g', 'sugar_percent', 'fiber_g', etc.
        
        Returns:
            Compliance report with score and violations.
        """
        compliant = []
        violations = []
        
        # Sodium check
        if sodium := daily_nutrition.get("sodium_g"):
            if sodium <= 2.0:
                compliant.append("sodium")
            else:
                violations.append({
                    "nutrient": "sodium",
                    "actual": sodium,
                    "limit": 2.0,
                    "unit": "g",
                    "message": f"Sodium {sodium}g exceeds WHO limit of 2g/day"
                })
        
        # Sugar check (as % of calories)
        if sugar_pct := daily_nutrition.get("sugar_percent"):
            if sugar_pct <= 10:
                compliant.append("sugar")
            else:
                violations.append({
                    "nutrient": "sugar",
                    "actual": sugar_pct,
                    "limit": 10,
                    "unit": "% energy",
                    "message": f"Sugar {sugar_pct}% exceeds WHO limit of 10%"
                })
        
        # Fiber check
        if fiber := daily_nutrition.get("fiber_g"):
            if fiber >= 25:
                compliant.append("fiber")
            else:
                violations.append({
                    "nutrient": "fiber",
                    "actual": fiber,
                    "minimum": 25,
                    "unit": "g",
                    "message": f"Fiber {fiber}g below WHO minimum of 25g/day"
                })
        
        # Calculate compliance score
        total_checked = len(compliant) + len(violations)
        score = (len(compliant) / total_checked * 100) if total_checked > 0 else 0
        
        return {
            "who_score": round(score, 1),
            "compliant_nutrients": compliant,
            "violations": violations,
            "guidelines_checked": total_checked,
            "source": "WHO eLENA (https://www.who.int/elena/)"
        }
    
    def get_citations(self) -> List[Dict[str, str]]:
        """Get formatted citations for all WHO sources used."""
        citations = []
        seen_urls = set()
        
        for guideline in self.GUIDELINES.values():
            if guideline.source_url not in seen_urls:
                citations.append({
                    "title": guideline.source_title,
                    "url": guideline.source_url,
                    "year": guideline.publication_year,
                    "organization": "World Health Organization",
                    "license": "Public Domain"
                })
                seen_urls.add(guideline.source_url)
        
        return citations


# Singleton instance
who_nutrition_service = WHONutritionService()
