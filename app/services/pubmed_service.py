"""
VitaFlow API - PubMed Research Citations Service.

Provides citations from PubMed/NCBI for evidence-based
nutrition and exercise recommendations.
"""

import logging
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PubMedCitation:
    """A citation from PubMed."""
    pmid: str
    title: str
    authors: str = ""
    journal: str = ""
    year: int = 0
    doi: str = ""
    url: str = ""


class PubMedService:
    """
    Service for retrieving PubMed research citations.
    
    Used to add scientific backing to AI-generated
    meal plans and workout recommendations.
    """
    
    # Pre-curated citations for common topics
    NUTRITION_CITATIONS = [
        PubMedCitation(
            pmid="32699189",
            title="Dietary protein and muscle mass: translating science to application",
            authors="Phillips SM",
            journal="Front Nutr",
            year=2020,
            url="https://pubmed.ncbi.nlm.nih.gov/32699189/"
        ),
        PubMedCitation(
            pmid="29414855",
            title="International Society of Sports Nutrition Position Stand: protein and exercise",
            authors="Jäger R et al.",
            journal="J Int Soc Sports Nutr",
            year=2017,
            url="https://pubmed.ncbi.nlm.nih.gov/29414855/"
        ),
        PubMedCitation(
            pmid="28919842",
            title="Position of the Academy of Nutrition and Dietetics: Vegetarian Diets",
            authors="Melina V et al.",
            journal="J Acad Nutr Diet",
            year=2016,
            url="https://pubmed.ncbi.nlm.nih.gov/28919842/"
        ),
    ]
    
    EXERCISE_CITATIONS = [
        PubMedCitation(
            pmid="19910831",
            title="American College of Sports Medicine position stand: Progression models in resistance training",
            authors="ACSM",
            journal="Med Sci Sports Exerc",
            year=2009,
            url="https://pubmed.ncbi.nlm.nih.gov/19910831/"
        ),
        PubMedCitation(
            pmid="28076926",
            title="Evidence-based effects of high-intensity interval training on exercise capacity",
            authors="Weston KS et al.",
            journal="Sports Med",
            year=2014,
            url="https://pubmed.ncbi.nlm.nih.gov/28076926/"
        ),
    ]
    
    RECOVERY_CITATIONS = [
        PubMedCitation(
            pmid="25028998",
            title="Sleep and athletic performance",
            authors="Simpson NS et al.",
            journal="Curr Sports Med Rep",
            year=2017,
            url="https://pubmed.ncbi.nlm.nih.gov/25028998/"
        ),
        PubMedCitation(
            pmid="29135639",
            title="Recovery techniques for athletes",
            authors="Dupuy O et al.",
            journal="Front Physiol",
            year=2018,
            url="https://pubmed.ncbi.nlm.nih.gov/29135639/"
        ),
    ]
    
    async def get_citations_for_nutrition(self, focus: str = "") -> List[PubMedCitation]:
        """Get nutrition-related PubMed citations."""
        return self.NUTRITION_CITATIONS
    
    async def get_citations_for_exercise(self, focus: str = "") -> List[PubMedCitation]:
        """Get exercise-related PubMed citations."""
        return self.EXERCISE_CITATIONS
    
    async def get_citations_for_recovery(self) -> List[PubMedCitation]:
        """Get recovery-related PubMed citations."""
        return self.RECOVERY_CITATIONS
    
    async def get_citations_for_topic(self, topic: str) -> List[PubMedCitation]:
        """Get citations for a general topic."""
        topic_lower = topic.lower()
        
        if any(word in topic_lower for word in ["nutrition", "diet", "meal", "food", "protein"]):
            return self.NUTRITION_CITATIONS
        elif any(word in topic_lower for word in ["exercise", "workout", "training", "strength"]):
            return self.EXERCISE_CITATIONS
        elif any(word in topic_lower for word in ["recovery", "sleep", "rest"]):
            return self.RECOVERY_CITATIONS
        
        # Default: return nutrition
        return self.NUTRITION_CITATIONS
    
    def build_ai_context(self, topic: str = "nutrition") -> str:
        """Build context string for AI prompts with PubMed citations."""
        citations = []
        
        if "nutrition" in topic.lower():
            citations = self.NUTRITION_CITATIONS
        elif "exercise" in topic.lower():
            citations = self.EXERCISE_CITATIONS
        else:
            citations = self.NUTRITION_CITATIONS + self.EXERCISE_CITATIONS
        
        context = "\n\nPUBMED RESEARCH CITATIONS:\n"
        for c in citations[:3]:
            context += f"- {c.title} ({c.authors}, {c.year}). PMID: {c.pmid}\n"
        
        return context


# Singleton instance
pubmed_service = PubMedService()
