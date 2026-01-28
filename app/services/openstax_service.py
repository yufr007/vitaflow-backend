"""
OpenStax Educational Content Service.

Provides scientifically-backed citations from OpenStax textbooks
for AI-generated content in VitaFlow.
"""

import logging
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class OpenStaxCitation:
    """Represents a citation from an OpenStax textbook."""
    book_title: str
    chapter: str
    section: str = ""
    url: str = ""


class OpenStaxService:
    """
    Service for retrieving OpenStax educational citations.
    
    Provides evidence-based context from:
    - OpenStax Anatomy and Physiology (2e)
    - OpenStax Nutrition
    - OpenStax Psychology (2e)
    """
    
    # OpenStax textbook references
    ANATOMY_PHYSIOLOGY = "OpenStax Anatomy and Physiology 2e"
    NUTRITION = "OpenStax Nutrition"
    PSYCHOLOGY = "OpenStax Psychology 2e"
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def get_citations_for_workout(self, focus: str = "exercise") -> List[OpenStaxCitation]:
        """Get citations relevant to workout generation."""
        citations = []
        
        focus_lower = focus.lower()
        
        if "strength" in focus_lower or "muscle" in focus_lower:
            citations.append(OpenStaxCitation(
                book_title=self.ANATOMY_PHYSIOLOGY,
                chapter="Chapter 10: Muscle Tissue",
                section="10.3 Muscle Fiber Contraction and Relaxation"
            ))
            citations.append(OpenStaxCitation(
                book_title=self.ANATOMY_PHYSIOLOGY,
                chapter="Chapter 10: Muscle Tissue",
                section="10.6 Exercise and Muscle Performance"
            ))
        
        if "cardio" in focus_lower or "endurance" in focus_lower:
            citations.append(OpenStaxCitation(
                book_title=self.ANATOMY_PHYSIOLOGY,
                chapter="Chapter 19: The Cardiovascular System: The Heart",
                section="19.4 Cardiac Physiology"
            ))
        
        if "flexibility" in focus_lower or "mobility" in focus_lower:
            citations.append(OpenStaxCitation(
                book_title=self.ANATOMY_PHYSIOLOGY,
                chapter="Chapter 9: Joints",
                section="9.1 Classification of Joints"
            ))
        
        # Default exercise-related citations
        if not citations:
            citations.append(OpenStaxCitation(
                book_title=self.ANATOMY_PHYSIOLOGY,
                chapter="Chapter 10: Muscle Tissue",
                section="10.6 Exercise and Muscle Performance"
            ))
        
        return citations
    
    async def get_citations_for_nutrition(self, focus: str = "balanced") -> List[OpenStaxCitation]:
        """Get citations relevant to nutrition and meal planning."""
        citations = []
        
        focus_lower = focus.lower()
        
        # Macronutrient-focused citations
        if "protein" in focus_lower or "muscle" in focus_lower:
            citations.append(OpenStaxCitation(
                book_title=self.NUTRITION,
                chapter="Chapter 6: Proteins",
                section="Protein Metabolism and Athletic Performance"
            ))
        
        if "carb" in focus_lower or "energy" in focus_lower:
            citations.append(OpenStaxCitation(
                book_title=self.NUTRITION,
                chapter="Chapter 4: Carbohydrates",
                section="Carbohydrate Metabolism and Energy"
            ))
        
        if "fat" in focus_lower or "weight" in focus_lower:
            citations.append(OpenStaxCitation(
                book_title=self.NUTRITION,
                chapter="Chapter 5: Lipids",
                section="Fat Metabolism and Health"
            ))
        
        # Default nutrition citations
        if not citations:
            citations.append(OpenStaxCitation(
                book_title=self.NUTRITION,
                chapter="Chapter 1: Nutrition and You",
                section="Essential Nutrients and Balanced Diet"
            ))
            citations.append(OpenStaxCitation(
                book_title=self.NUTRITION,
                chapter="Chapter 10: Energy Balance and Body Composition",
                section="Energy Balance for Health"
            ))
        
        return citations
    
    async def get_citations_for_recovery(self) -> List[OpenStaxCitation]:
        """Get citations relevant to rest and recovery."""
        return [
            OpenStaxCitation(
                book_title=self.ANATOMY_PHYSIOLOGY,
                chapter="Chapter 10: Muscle Tissue",
                section="10.6 Exercise and Muscle Performance - Recovery"
            ),
            OpenStaxCitation(
                book_title=self.PSYCHOLOGY,
                chapter="Chapter 4: States of Consciousness",
                section="4.1 What Is Consciousness? - Sleep and Recovery"
            ),
        ]
    
    async def get_citations_for_mental_wellness(self) -> List[OpenStaxCitation]:
        """Get citations relevant to psychological aspects of fitness."""
        return [
            OpenStaxCitation(
                book_title=self.PSYCHOLOGY,
                chapter="Chapter 10: Emotion and Motivation",
                section="10.1 Emotion - Exercise and Mood"
            ),
            OpenStaxCitation(
                book_title=self.PSYCHOLOGY,
                chapter="Chapter 14: Stress, Lifestyle, and Health",
                section="14.2 Stressors - Physical Activity and Stress Management"
            ),
            OpenStaxCitation(
                book_title=self.PSYCHOLOGY,
                chapter="Chapter 7: Thinking and Intelligence",
                section="7.4 What Are Intelligence and Creativity?"
            ),
        ]


# Global service instance
openstax_service = OpenStaxService()
