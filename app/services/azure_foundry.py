# app/services/azure_foundry.py
"""
VitaFlow - Azure OpenAI + Foundry Integration.

Handles complex multi-step AI workflows for:
- Shopping optimizer (price comparison, route optimization)
- Advanced coaching (personalized feedback, goal tracking)
- Meal plan optimization

Simple features (form check, basic generation) remain on Gemini.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)


@dataclass
class AzureOpenAIConfig:
    """Azure OpenAI configuration."""
    endpoint: str
    api_key: str
    api_version: str = "2024-02-01"
    deployment_gpt4: str = "gpt-4o"
    deployment_gpt4_turbo: str = "gpt-4-turbo"


@dataclass
class FoundryConfig:
    """Azure AI Foundry configuration."""
    project_id: str
    subscription_id: Optional[str] = None
    resource_group: Optional[str] = None


class AzureFoundryService:
    """
    Azure OpenAI + Foundry service for complex AI workflows.
    
    Usage:
        service = AzureFoundryService()
        await service.initialize()
        result = await service.optimize_shopping_list(items, location)
    """
    
    _instance: Optional['AzureFoundryService'] = None
    _initialized: bool = False
    
    def __init__(self):
        """Initialize Azure services configuration."""
        self.openai_config: Optional[AzureOpenAIConfig] = None
        self.foundry_config: Optional[FoundryConfig] = None
        self.client: Optional[AzureOpenAI] = None
    
    @classmethod
    def get_instance(cls) -> 'AzureFoundryService':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def initialize(self) -> bool:
        """
        Initialize Azure OpenAI and Foundry connections.
        
        Returns:
            bool: True if initialization successful.
        """
        if self._initialized:
            return True
        
        try:
            # Load configuration from environment
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            api_key = os.getenv("AZURE_OPENAI_KEY")
            
            if not endpoint or not api_key:
                logger.warning("Azure OpenAI not configured - using fallback mode")
                return False
            
            self.openai_config = AzureOpenAIConfig(
                endpoint=endpoint,
                api_key=api_key,
                deployment_gpt4=os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT4", "gpt-4o"),
                deployment_gpt4_turbo=os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT4_TURBO", "gpt-4-turbo"),
            )
            
            self.foundry_config = FoundryConfig(
                project_id=os.getenv("AZURE_FOUNDRY_PROJECT_ID", ""),
                subscription_id=os.getenv("AZURE_SUBSCRIPTION_ID"),
                resource_group=os.getenv("AZURE_RESOURCE_GROUP"),
            )
            
            # Initialize Azure OpenAI client
            self.client = AzureOpenAI(
                azure_endpoint=self.openai_config.endpoint,
                api_key=self.openai_config.api_key,
                api_version=self.openai_config.api_version,
            )
            
            # Test connection
            logger.info("Testing Azure OpenAI connection...")
            test_response = self.client.chat.completions.create(
                model=self.openai_config.deployment_gpt4,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5,
            )
            logger.info(f"Azure OpenAI connected: {test_response.model}")
            
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Azure services: {e}")
            return False
    
    @property
    def is_available(self) -> bool:
        """Check if Azure services are available."""
        return self._initialized and self.client is not None
    
    # =========================================================================
    # Shopping Optimizer
    # =========================================================================
    
    async def optimize_shopping_list(
        self,
        items: List[str],
        location: Dict[str, Any],
        budget: Optional[float] = None,
        preferences: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Optimize shopping list with price comparison and route optimization.
        
        Args:
            items: List of grocery items to buy
            location: User location (lat, lng, zip_code)
            budget: Optional weekly budget
            preferences: User preferences (organic, store preferences, etc.)
        
        Returns:
            Optimized shopping plan with stores, prices, and route
        """
        if not self.is_available:
            return self._fallback_shopping_response(items)
        
        try:
            system_prompt = """You are VitaFlow's Personal Chef shopping optimizer.
Your job is to create the most cost-effective shopping plan.

Given a list of grocery items and user location, you should:
1. Suggest which stores to visit for best prices
2. Group items by store for efficiency
3. Estimate total cost and potential savings
4. Suggest budget-friendly substitutions if needed

Respond in JSON format with this structure:
{
    "stores": [
        {
            "name": "Store Name",
            "items": ["item1", "item2"],
            "estimated_cost": 25.50,
            "address": "Optional address"
        }
    ],
    "total_estimated_cost": 75.00,
    "estimated_savings": 15.00,
    "substitutions": [
        {"original": "organic milk", "substitute": "regular milk", "savings": 2.50}
    ],
    "tips": ["Buy in bulk at Costco for...", "Check weekly flyer for..."]
}"""

            user_prompt = f"""Optimize this shopping list for a user in {location.get('city', 'Unknown')}, {location.get('state', 'Unknown')}:

Items: {', '.join(items)}
Budget: ${budget if budget else 'No limit'}
Preferences: {preferences if preferences else 'None specified'}

Consider major retailers in their area (Walmart, Kroger, Costco, Aldi, local stores).
"""

            response = self.client.chat.completions.create(
                model=self.openai_config.deployment_gpt4,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                max_tokens=1500,
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            result["ai_provider"] = "azure_openai"
            return result
            
        except Exception as e:
            logger.error(f"Shopping optimization failed: {e}")
            return self._fallback_shopping_response(items)
    
    def _fallback_shopping_response(self, items: List[str]) -> Dict[str, Any]:
        """Fallback response when Azure is unavailable."""
        return {
            "stores": [{"name": "Local Store", "items": items, "estimated_cost": 0}],
            "total_estimated_cost": 0,
            "estimated_savings": 0,
            "substitutions": [],
            "tips": ["Azure AI not configured - basic mode active"],
            "ai_provider": "fallback"
        }
    
    # =========================================================================
    # Advanced Coaching
    # =========================================================================
    
    async def generate_coaching_message(
        self,
        user_profile: Dict[str, Any],
        progress_data: Dict[str, Any],
        persona: str = "motivator",
    ) -> Dict[str, Any]:
        """
        Generate personalized coaching message based on user progress.
        
        Args:
            user_profile: User's profile data (goals, fitness level, etc.)
            progress_data: Recent progress (workouts, streaks, form scores)
            persona: Coaching persona (motivator, scientist, drill_sergeant, therapist, specialist)
        
        Returns:
            Personalized coaching message and action items
        """
        if not self.is_available:
            return self._fallback_coaching_response(persona)
        
        persona_prompts = {
            "motivator": "You are an enthusiastic, high-energy fitness coach. Use 🔥 emojis, celebrate wins, and inspire action.",
            "scientist": "You are a data-driven coach. Reference specific metrics, explain the science, use 🧪 emojis.",
            "drill_sergeant": "You are a no-nonsense coach. Be direct, push for more, use 💪 emojis. Tough love.",
            "therapist": "You are an empathetic coach. Focus on mental wellness, recovery, use 🧠 emojis. Be supportive.",
            "specialist": "You are a technical expert. Give advanced tips, periodization advice, use 🎯 emojis.",
        }
        
        try:
            system_prompt = f"""You are VitaFlow's AI Coach using the {persona.upper()} persona.

{persona_prompts.get(persona, persona_prompts['motivator'])}

Generate a personalized coaching message based on the user's recent progress.
Include specific references to their data and actionable next steps.

Respond in JSON:
{{
    "message": "Your personalized message here...",
    "action_items": ["Do X today", "Track Y"],
    "focus_area": "strength|cardio|nutrition|recovery",
    "motivation_score": 1-10
}}"""

            user_prompt = f"""User Profile:
- Name: {user_profile.get('name', 'Champion')}
- Goal: {user_profile.get('goal', 'General Fitness')}
- Fitness Level: {user_profile.get('fitness_level', 'Intermediate')}

Progress Data:
- Workout Streak: {progress_data.get('streak', 0)} days
- This Week: {progress_data.get('workouts_this_week', 0)} workouts
- Form Score Average: {progress_data.get('form_score_avg', 'N/A')}
- Last Workout: {progress_data.get('last_workout', 'Not recorded')}

Generate an encouraging, personalized message for today."""

            response = self.client.chat.completions.create(
                model=self.openai_config.deployment_gpt4_turbo,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                max_tokens=500,
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            result["persona"] = persona
            result["ai_provider"] = "azure_openai"
            return result
            
        except Exception as e:
            logger.error(f"Coaching message generation failed: {e}")
            return self._fallback_coaching_response(persona)
    
    def _fallback_coaching_response(self, persona: str) -> Dict[str, Any]:
        """Fallback coaching response."""
        messages = {
            "motivator": "🔥 You're doing amazing! Keep pushing forward!",
            "scientist": "🧪 Data shows consistency is key. One workout at a time.",
            "drill_sergeant": "💪 No excuses. Get after it today!",
            "therapist": "🧠 Remember to be kind to yourself. Progress takes time.",
            "specialist": "🎯 Focus on form first, intensity second.",
        }
        return {
            "message": messages.get(persona, messages["motivator"]),
            "action_items": ["Complete today's workout", "Log your progress"],
            "focus_area": "general",
            "motivation_score": 7,
            "persona": persona,
            "ai_provider": "fallback"
        }
    
    # =========================================================================
    # Meal Plan Optimization
    # =========================================================================
    
    async def optimize_meal_plan(
        self,
        user_profile: Dict[str, Any],
        dietary_restrictions: List[str],
        budget: float,
        days: int = 7,
    ) -> Dict[str, Any]:
        """
        Generate optimized meal plan with budget and nutrition balance.
        
        Args:
            user_profile: User's profile and goals
            dietary_restrictions: List of restrictions (vegetarian, gluten-free, etc.)
            budget: Weekly grocery budget
            days: Number of days to plan
        
        Returns:
            Optimized meal plan with costs and shopping list
        """
        if not self.is_available:
            return {"message": "Azure AI not configured", "ai_provider": "fallback"}
        
        # Implementation for meal plan optimization
        # (Similar pattern to shopping optimizer)
        pass


# Singleton instance
azure_foundry = AzureFoundryService.get_instance()
