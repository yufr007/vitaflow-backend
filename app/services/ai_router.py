# app/services/ai_router.py
"""
VitaFlow AI Service Router.

Routes AI requests to Gemini-based orchestration.
(Azure OpenAI not available on student accounts)

Features:
- Shopping optimizer with multi-step workflow
- Multi-agent coaching with persona support
- Form check with vision analysis
- Workout and meal plan generation
"""

import logging
from typing import Optional, Dict, Any

from settings import settings

logger = logging.getLogger(__name__)


class AIServiceRouter:
    """
    Routes AI requests to Gemini orchestration workflows.
    
    Usage:
        router = await get_ai_router()
        result = await router.generate_shopping_list(meal_plan, location)
    """
    
    def __init__(self):
        self._gemini_service = None
        self._shopping_workflow = None
        self._coaching_workflow = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize AI services lazily."""
        if self._initialized:
            return
        
        try:
            # Initialize Gemini service
            from app.services.gemini import GeminiService
            self._gemini_service = GeminiService()
            logger.info("Gemini service initialized")
        except Exception as e:
            logger.warning(f"Gemini service initialization failed: {e}")
        
        try:
            # Initialize shopping optimizer
            from app.workflows.shopping_optimizer import ShoppingOptimizerWorkflow
            self._shopping_workflow = ShoppingOptimizerWorkflow()
            logger.info("Shopping optimizer workflow initialized")
        except Exception as e:
            logger.warning(f"Shopping workflow initialization failed: {e}")
        
        try:
            # Initialize coaching workflow
            from app.workflows.coaching_agents import CoachingAgentsWorkflow
            self._coaching_workflow = CoachingAgentsWorkflow()
            logger.info("Coaching workflow initialized")
        except Exception as e:
            logger.warning(f"Coaching workflow initialization failed: {e}")
        
        self._initialized = True
    
    # =========================================================================
    # Shopping List Generation
    # =========================================================================
    
    async def generate_shopping_list(
        self,
        meal_plan_data: Dict[str, Any],
        user_id: str,
        location: Dict[str, Any],
        budget: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Generate optimized shopping list using Gemini orchestration.
        
        Multi-step workflow with retry logic and error recovery.
        """
        if not self._shopping_workflow:
            await self.initialize()
        
        if self._shopping_workflow:
            logger.info(f"Using Gemini orchestration for shopping (user: {user_id[:8]}...)")
            return await self._shopping_workflow.optimize(
                meal_plan_data, location, budget
            )
        else:
            # Basic fallback
            return {
                "success": False,
                "error": "Shopping workflow not available",
                "aiProvider": "error"
            }
    
    # =========================================================================
    # Coaching Message Generation
    # =========================================================================
    
    async def generate_coaching(
        self,
        user_id: str,
        user_profile: Dict[str, Any],
        metrics: Dict[str, Any],
        persona: str = "motivator"
    ) -> Dict[str, Any]:
        """
        Generate personalized coaching using multi-agent workflow.
        
        Uses 4 specialized "agents" (prompts) to analyze different aspects
        and synthesize into a personalized message.
        """
        if not self._coaching_workflow:
            await self.initialize()
        
        if self._coaching_workflow:
            logger.info(f"Using Gemini orchestration for coaching (user: {user_id[:8]}...)")
            return await self._coaching_workflow.generate_message(
                user_profile, metrics, persona
            )
        else:
            # Basic fallback
            return self._basic_coaching_response(user_profile, persona)
    
    def _basic_coaching_response(
        self,
        user_profile: Dict[str, Any],
        persona: str
    ) -> Dict[str, Any]:
        """Basic static coaching response when all AI fails."""
        name = user_profile.get("name", "Champion")
        messages = {
            "motivator": f"🔥 {name}, every workout counts! Keep pushing!",
            "scientist": f"🧪 {name}, consistency beats intensity. Stay focused.",
            "drill_sergeant": f"💪 {name}! No excuses today!",
            "therapist": f"🧠 {name}, be kind to yourself. Progress takes time.",
            "specialist": f"🎯 {name}, master the basics first.",
        }
        return {
            "message": messages.get(persona, messages["motivator"]),
            "actionItems": ["Complete your workout", "Log your progress"],
            "focusArea": "general",
            "motivationScore": 7,
            "aiProvider": "static_fallback"
        }
    
    # =========================================================================
    # Form Check (Gemini Vision)
    # =========================================================================
    
    async def analyze_form(
        self,
        image_data: bytes,
        exercise_name: str
    ) -> Dict[str, Any]:
        """
        Analyze exercise form from image.
        
        Uses Gemini Vision for image analysis.
        """
        if not self._gemini_service:
            await self.initialize()
        
        if self._gemini_service:
            return await self._gemini_service.analyze_form(image_data, exercise_name)
        
        return {"error": "Gemini service not available", "score": 0}
    
    # =========================================================================
    # Workout Generation
    # =========================================================================
    
    async def generate_workout(
        self,
        user_profile: Dict[str, Any],
        duration_minutes: int = 45
    ) -> Dict[str, Any]:
        """Generate personalized workout plan."""
        if not self._gemini_service:
            await self.initialize()
        
        if self._gemini_service:
            return await self._gemini_service.generate_workout(user_profile, duration_minutes)
        
        return {"error": "Gemini service not available"}
    
    # =========================================================================
    # Meal Plan Generation
    # =========================================================================
    
    async def generate_meal_plan(
        self,
        user_profile: Dict[str, Any],
        days: int = 7
    ) -> Dict[str, Any]:
        """Generate personalized meal plan."""
        if not self._gemini_service:
            await self.initialize()
        
        if self._gemini_service:
            return await self._gemini_service.generate_meal_plan(user_profile, days)
        
        return {"error": "Gemini service not available"}
    
    # =========================================================================
    # Recovery Assessment (Feature 6)
    # =========================================================================
    
    async def generate_recovery_assessment(
        self,
        user_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate AI-powered recovery assessment.
        
        Analyzes user metrics, workout load, and form scores to produce
        personalized recovery recommendations.
        """
        if not self._gemini_service:
            await self.initialize()
        
        if self._gemini_service:
            try:
                logger.info(f"Generating recovery assessment for user: {user_id[:8]}...")
                return await self._gemini_service.generate_recovery_assessment(context)
            except Exception as e:
                logger.error(f"Gemini recovery assessment failed: {e}")
                return self._fallback_recovery_assessment(context)
        
        return self._fallback_recovery_assessment(context)
    
    def _fallback_recovery_assessment(
        self,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fallback recovery assessment when AI is unavailable."""
        metrics = context.get("user_metrics", {})
        
        # Simple rule-based scoring
        sleep_score = (metrics.get("sleep_quality", 5) / 10) * 25
        energy_score = (metrics.get("energy_level", 5) / 10) * 25
        stress_penalty = (metrics.get("stress_level", 5) / 10) * 15
        soreness_penalty = (metrics.get("soreness_level", 5) / 10) * 15
        
        # Sleep hours bonus (7-9 is optimal)
        hours = metrics.get("sleep_hours", 7)
        if 7 <= hours <= 9:
            sleep_hours_bonus = 20
        elif 6 <= hours < 7 or 9 < hours <= 10:
            sleep_hours_bonus = 10
        else:
            sleep_hours_bonus = 0
        
        recovery_score = int(
            sleep_score + energy_score + sleep_hours_bonus - stress_penalty - soreness_penalty + 30
        )
        recovery_score = max(0, min(100, recovery_score))
        
        # Determine status
        if recovery_score >= 80:
            status = "well_rested"
            summary = "You're well-recovered and ready for intense training!"
        elif recovery_score >= 60:
            status = "moderate"
            summary = "You're moderately recovered. A regular workout is appropriate."
        elif recovery_score >= 40:
            status = "fatigued"
            summary = "You're showing signs of fatigue. Consider lighter activity today."
        else:
            status = "overtrained"
            summary = "Your body needs rest. Focus on recovery activities."
        
        return {
            "recovery_score": recovery_score,
            "recovery_status": status,
            "recommendation_summary": summary,
            "protocol": {
                "rest_days_needed": 2 if status == "overtrained" else 1 if status == "fatigued" else 0,
                "active_recovery": ["walking", "stretching"] if status in ["fatigued", "overtrained"] else [],
                "mobility_exercises": ["foam rolling", "hip stretches", "shoulder circles"],
                "next_workout_timing": "After 1-2 days rest" if status == "overtrained" else "Tomorrow" if status == "fatigued" else "Ready today",
                "intensity_adjustment": "Rest day" if status == "overtrained" else "Reduce by 30%" if status == "fatigued" else "Normal intensity"
            },
            "ai_provider": "fallback_rules"
        }


# Singleton instance
_router_instance: Optional[AIServiceRouter] = None


async def get_ai_router() -> AIServiceRouter:
    """Get or create the AI router singleton."""
    global _router_instance
    if _router_instance is None:
        _router_instance = AIServiceRouter()
        await _router_instance.initialize()
    return _router_instance
