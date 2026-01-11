"""
VitaFlow API - Gemini AI Service.

Centralized Gemini API client for form analysis, workout generation,
meal planning, and adaptive coaching.
"""

import json
import logging
from typing import Optional, Dict, Any, List

from google import genai

from settings import settings
from app.services.cache import cache_service
from app.services.fixed_plans import get_fixed_workout_plan, get_fixed_meal_plan


logger = logging.getLogger(__name__)


class _ModelWrapper:
    """
    Compatibility wrapper to mirror the old GenerativeModel.generate_content API
    using the new google-genai client.
    """

    def __init__(self, client: genai.Client, model_name: str):
        self.client = client
        self.model_name = model_name

    def generate_content(self, contents):
        # Preserve existing call sites that pass a string or list for contents
        return self.client.models.generate_content(model=self.model_name, contents=contents)


class GeminiService:
    """
    Gemini API service for AI-powered features.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini client.
        """
        self.api_key = api_key or settings.GEMINI_API_KEY
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
            self.vision_model = _ModelWrapper(self.client, "gemini-1.5-flash")
            self.text_model = _ModelWrapper(self.client, "gemini-1.5-flash")
        else:
            self.client = None
            self.vision_model = None
            self.text_model = None
        self.logger = logging.getLogger(__name__)
        
    def _get_persona(self, tier: str, goal: str, user_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Get the AI Persona based on User Tier, Goal, and AgentEvolver learning.
        
        PERSONALIZATION LEVELS:
        - FREE: Generic, no adaptation
        - PRO: Personalized with AgentEvolver learning
        - ELITE: Deep personalization + proactive insights
        
        Args:
            tier: User's subscription tier (free/pro/elite)
            goal: User's fitness goal
            user_context: AgentEvolver experience data (preferences, history)
        """
        # FREE TIER: Generic responses, no personalization
        if tier == 'free':
            return "You are a standard fitness assistant. Provide generic advice without personalization."
        
        # Build base persona from goal
        goal_lower = goal.lower() if goal else "general"
        
        if "weight" in goal_lower and "loss" in goal_lower:
            base_persona = "You are an Accountability and Motivation Coach. Focus on consistency, discipline, high energy, and fat loss psychology."
        elif "muscle" in goal_lower:
            base_persona = "You are a Strength and Conditioning Coach. Focus on hypertrophy, technique, progressive overload, and recovery."
        elif "strength" in goal_lower or "power" in goal_lower:
            base_persona = "You are a Powerlifting Coach. Focus on compound lifts, mechanics, and nervous system adaptation."
        else:
            base_persona = "You are an Elite Personal Trainer designing a bespoke program for a high-performance client."
        
        # PRO TIER: Add AgentEvolver personalization
        if tier == 'pro':
            persona = base_persona + "\n\nPERSONALIZATION INSTRUCTIONS:"
            
            if user_context:
                # Add learned preferences
                if prefs := user_context.get('workout_preferences'):
                    persona += f"\n- User prefers: {prefs.get('preferred_time', 'any time')} workouts"
                    persona += f"\n- Motivation style: {prefs.get('motivation_style', 'balanced')}"
                
                if meal_prefs := user_context.get('meal_preferences'):
                    persona += f"\n- Food preferences: {meal_prefs.get('likes', 'varied')}"
                    persona += f"\n- Dislikes: {meal_prefs.get('dislikes', 'none specified')}"
                
                if history := user_context.get('exercise_performance'):
                    persona += f"\n- Exercise history: {len(history)} exercises tracked"
                    persona += "\n- Adapt difficulty based on this user's SPECIFIC progress patterns"
            
            persona += "\n\nRemember: This user has unique preferences. Tailor your advice to THEIR specific needs, not generic recommendations."
            return persona
        
        # ELITE TIER: Deep personalization + proactive insights
        if tier == 'elite':
            persona = base_persona + "\n\nELITE PERSONALIZATION INSTRUCTIONS:"
            
            if user_context:
                # More detailed context for Elite
                persona += "\n\nUSER PROFILE:"
                
                if prefs := user_context.get('workout_preferences'):
                    persona += f"\n- Optimal training time: {prefs.get('preferred_time', 'any')}"
                    persona += f"\n- Recovery pattern: {prefs.get('recovery_speed', 'normal')}"
                    persona += f"\n- Responds best to: {prefs.get('progression_style', 'progressive overload')}"
                
                if meal_prefs := user_context.get('meal_preferences'):
                    persona += f"\n- Meal timing preference: {meal_prefs.get('meal_timing', 'flexible')}"
                    persona += f"\n- Digestion speed: {meal_prefs.get('digestion', 'normal')}"
                    persona += f"\n- Favorite flavors: {meal_prefs.get('flavor_profile', 'varied')}"
                
                if biomechanics := user_context.get('biomechanics_insights'):
                    persona += f"\n- Mobility limitations: {biomechanics.get('limitations', 'none detected')}"
                    persona += f"\n- Injury risk areas: {biomechanics.get('risk_areas', 'none')}"
                
                persona += "\n\nADVANCED INSTRUCTIONS:"
                persona += "\n- Provide PROACTIVE insights (predict issues before they happen)"
                persona += "\n- Include biomechanics explanations (WHY this works for THIS user)"
                persona += "\n- Suggest progressive learning (teach at their current knowledge level)"
                persona += "\n- Reference their specific past performance (e.g., 'Last week your squat depth improved 15%')"
            
            persona += "\n\nYou are this user's PERSONAL coach. No two users receive identical advice. Make them feel like you know them intimately."
            return persona
        
        # Default (shouldn't reach here)
        return base_persona
    
    async def analyze_form_check(
        self,
        image_base64: str,
        exercise_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze exercise form using Gemini Vision API with persona.
        """
        if not self.vision_model:
            self.logger.error("Gemini API key not configured")
            return None
        
        try:
            # Persona: Form and Technique Analysis Specialist (Always Pro Quality for Demo)
            prompt = f"""You are a specialized Biomechanics and Form Analysis expert. 
Analyze this exercise form for {exercise_name}. 

Focus strictly on safety, joint alignment, and efficient force production.

Return ONLY a valid JSON object with these exact fields (no markdown, no code blocks):
{{
    "form_score": <integer 0-100>,
    "alignment_feedback": "<technical feedback on joint positioning>",
    "rom_feedback": "<feedback on range of motion>",
    "stability_feedback": "<feedback on balance/core control>",
    "corrections": ["<correction 1>", "<correction 2>"],
    "tips": ["<technical tip 1>", "<technical tip 2>"],
    "next_step": "<suggested regression/progression based on form>"
}}
"""

            response = self.vision_model.generate_content([
                {"mime_type": "image/jpeg", "data": image_base64},
                prompt
            ])
            
            result = self._extract_json(response.text)
            return result
        
        except Exception as e:
            self.logger.error(f"Form check analysis error: {str(e)}")
            return None
    
    async def generate_workout(
        self,
        user_profile: Dict[str, Any],
        use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Generate personalized 7-day workout plan.
        """
        tier = user_profile.get('tier', 'free')
        goal = user_profile.get('goal', 'general_fitness')
        equipment = user_profile.get('equipment', 'minimal')

        # FREE TIER Logic: Fixed Plans
        if tier == 'free':
            return get_fixed_workout_plan(goal, equipment)

        # PRO TIER Logic
        if not self.text_model:
            self.logger.error("Gemini API key not configured")
            return None
        
        # Check cache with deterministic key
        if use_cache:
            cache_params = {
                "fitness_level": user_profile.get('fitness_level', 'beginner'),
                "goal": goal,
                "equipment": equipment,
                "time_available": user_profile.get('time_available_minutes', 45)
            }
            cache_key = cache_service.generate_key("workout", cache_params)
            cached = await cache_service.get(cache_key)
            if cached:
                self.logger.info(f"Cache hit for workout generation: {cache_key}")
                cached["from_cache"] = True
                return cached
        
        try:
            persona = self._get_persona(tier, goal)

            prompt = f"""{persona}

Create a premium 7-day workout plan for:
- Fitness level: {user_profile.get('fitness_level', 'beginner')}
- Goal: {goal}
- Equipment: {equipment}
- Time per session: {user_profile.get('time_available_minutes', 45)} minutes

Your output MUST reflect your coaching persona in the "notes" and "weekly_summary".

Return ONLY valid JSON (no markdown):
{{
    "days": [
        {{
            "day": 1,
            "focus": "...",
            "exercises": [
                {{"name": "...", "sets": 3, "reps": "...", "duration_minutes": 5, "notes": "Persona-driven coaching cue"}}
            ],
            "rest_between_sets": "...",
            "warmup": "...",
            "cooldown": "..."
        }}
    ],
    "weekly_summary": "Persona-driven motivation/technical summary"
}}
"""

            response = self.text_model.generate_content(prompt)
            result = self._extract_json(response.text)

            if result:
                result["from_cache"] = False
                if use_cache:
                    # Use configured TTL for workout plans (24 hours)
                    await cache_service.set(cache_key, result, ttl_seconds=settings.CACHE_TTL_WORKOUT)
                    self.logger.info(f"Cached workout plan: {cache_key}")

            return result

        except Exception as e:
            self.logger.error(f"Workout generation error: {str(e)}")
            return None
    
    async def generate_meal_plan(
        self,
        user_profile: Dict[str, Any],
        use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Generate personalized 7-day meal plan.
        """
        tier = user_profile.get('tier', 'free')
        restrictions = ', '.join(user_profile.get('dietary_restrictions', [])) or 'none'

        if tier == 'free':
            return get_fixed_meal_plan(restrictions)

        if not self.text_model:
            self.logger.error("Gemini API key not configured")
            return None
        
        # Check cache with deterministic key
        if use_cache:
            cache_params = {
                "goal": user_profile.get('fitness_goal', 'balanced diet'),
                "restrictions": sorted(user_profile.get('dietary_restrictions', [])),
                "budget": user_profile.get('budget_per_week', 150)
            }
            cache_key = cache_service.generate_key("meal_plan", cache_params)
            cached = await cache_service.get(cache_key)
            if cached:
                self.logger.info(f"Cache hit for meal plan generation: {cache_key}")
                cached["from_cache"] = True
                return cached
        
        try:
            budget = user_profile.get('budget_per_week', 150)
            goal = user_profile.get('fitness_goal', 'balanced diet')
            
            prompt = f"""You are an expert Personal Chef and Nutritionist. Design a 7-day meal plan that feels curated and catered.

User Profile:
- Goal: {goal}
- Diet: {restrictions}
- Budget: ${budget}/week

Chef's Guidelines:
1. Flavor Profile: Varied but cohesive.
2. Efficiency: "Cook once, eat twice".
3. No generic "boiled chicken". Use spices, marinades, and gourmet textures.
4. Educational Value: Explain WHY each meal supports their goal (build muscle, burn fat, sustain energy).

Return ONLY valid JSON (no markdown):
{{
    "days": [
        {{
            "day": 1,
            "meals": [
                {{
                    "type": "Breakfast",
                    "name": "...",
                    "calories": 400,
                    "macros": {{ "protein": 20, "carbs": 45, "fat": 15 }},
                    "prep_time_minutes": 10,
                    "ingredients": ["...", "..."],
                    "chef_explanation": "Why this meal works: Explain how the macros support their goal. E.g., 'High protein from eggs builds muscle, complex carbs from oats provide sustained energy for your morning workout.'",
                    "macro_breakdown": "Protein: 20g (muscle repair), Carbs: 45g (energy), Fat: 15g (hormone production)",
                    "goal_alignment": "Perfect pre-workout fuel: protein for muscle synthesis, carbs for glycogen, healthy fats for satiety.",
                    "nutrition_lesson": "Fun fact or tip related to this meal, e.g., 'Oats contain beta-glucan fiber which helps regulate blood sugar and keeps you full longer.'"
                }}
            ],
            "daily_totals": {{ "calories": 2000, "protein": 150, "carbs": 200, "fat": 70 }},
            "daily_summary": "Why today's nutrition works: Explain how the daily macro distribution supports their specific goal (e.g., muscle gain, fat loss, endurance)."
        }}
    ],
    "chef_tips": ["Educational tips about nutrition, meal prep, or ingredient swaps", "..."],
    "total_estimated_cost": 120.00,
    "weekly_nutrition_strategy": "Overall explanation of how this week's meal plan progressively supports their fitness goal. E.g., 'Higher carbs on training days (Mon/Wed/Fri) for performance, moderate carbs on rest days for recovery without excess calories.'"
}}

CRITICAL: Include 'chef_explanation', 'macro_breakdown', 'goal_alignment', and 'nutrition_lesson' for EVERY meal. These educational insights are what make VitaFlow superior to competitors like MyFitnessPal.
"""

            response = self.text_model.generate_content(prompt)
            result = self._extract_json(response.text)

            if result:
                result["from_cache"] = False
                if use_cache:
                    # Use configured TTL for meal plans (6 hours)
                    await cache_service.set(cache_key, result, ttl_seconds=settings.CACHE_TTL_MEAL_PLAN)
                    self.logger.info(f"Cached meal plan: {cache_key}")

            return result
        
        except Exception as e:
            self.logger.error(f"Meal plan generation error: {str(e)}")
            return None
    
    async def generate_coaching_message(
        self,
        user_metrics: Dict[str, Any],
        use_cache: bool = True
    ) -> Optional[str]:
        """
        Generate personalized coaching message based on user metrics and FORM DATA.
        """
        if not self.text_model:
            self.logger.error("Gemini API key not configured")
            return None
        
        # Check cache
        if use_cache:
            cache_key = cache_service.generate_key("coaching", user_metrics)
            cached = await cache_service.get(cache_key)
            if cached:
                return cached.get("message")
        
        try:
            tier = user_metrics.get('tier', 'free')
            goal = user_metrics.get('goal', 'fitness')
            name = user_metrics.get('name', 'User')
            
            persona = self._get_persona(tier, goal)
            
            # Incorporate Form Data Pipeline
            form_context = ""
            recent_forms = user_metrics.get('recent_form_insights', [])
            if recent_forms:
                # Format: [{'exercise': 'Squat', 'score': 80, 'date': ...}]
                form_context = f"\nRecent Form Analysis Data: {json.dumps(recent_forms)}"
                form_context += "\nAnalyze this data. If scores are improving, praise specific exercises. If declining, suggest focus."

            prompt = f"""{persona}

Write a brief, personalized coaching message (2-3 sentences) for {name}.

Stats:
- Workouts this week: {user_metrics.get('workouts_this_week', 0)}
- Meals logged: {user_metrics.get('meals_logged', 0)}
- Active streak: {user_metrics.get('days_active_streak', 0)} days
{form_context}

Be encouraging but realistic. Speak in your persona's voice.
Plain text only."""

            response = self.text_model.generate_content(prompt)
            message = response.text.strip()
            
            if message and use_cache:
                await cache_service.set(
                    cache_key,
                    {"message": message},
                    ttl_seconds=900
                )
            
            return message
        
        except Exception as e:
            self.logger.error(f"Coaching message generation error: {str(e)}")
            return None
    
    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract and parse JSON from Gemini response.
        """
        try:
            if "```json" in text:
                start = text.find("```json") + 7
                end = text.find("```", start)
                text = text[start:end].strip()
            elif "```" in text:
                start = text.find("```") + 3
                end = text.find("```", start)
                text = text[start:end].strip()
            
            json_start = text.find("{")
            json_end = text.rfind("}") + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = text[json_start:json_end]
                return json.loads(json_str)
            
            return None
        
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing error: {str(e)}")
            return None

    async def generate_tasks_from_goal(self, goal: str) -> Optional[List[Dict[str, Any]]]:
        """
        Generate a list of tasks from a high-level goal.
        """
        if not self.text_model:
            self.logger.error("Gemini API key not configured")
            return None
        
        try:
            prompt = f"""Given the goal: "{goal}", break it down into tasks. Return JSON: {{ "tasks": [{{ "id": "1", "name": "...", "args": {{}} }}] }}"""
            response = self.text_model.generate_content(prompt)
            result = self._extract_json(response.text)
            return result.get("tasks") if result else None
        except Exception as e:
            self.logger.error(f"Task generation error: {str(e)}")
            return None

    async def generate_shopping_list_prices(
        self,
        items: List[Dict[str, Any]],
        stores: List[str],
        currency: str
    ) -> Optional[Dict[str, Any]]:
        """
        Estimate prices for a shopping list.
        """
        if not self.text_model:
            self.logger.error("Gemini API key not configured")
            return None
            
        try:
            items_str = ", ".join([f"{i.get('quantity')} {i.get('unit')} {i.get('name')}" for i in items])
            prompt = f"""Estimate grocery costs for: {items_str} at {', '.join(stores)} in {currency}. Return JSON: {{ "store_prices": {{ "Store": {{ "total": 0, "savings": 0 }} }} }}"""
            response = self.text_model.generate_content(prompt)
            result = self._extract_json(response.text)
            return result
        except Exception as e:
            self.logger.error(f"Price estimation error: {str(e)}")
            return None

    async def generate_recovery_assessment(
        self,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Generate AI-powered recovery assessment and recommendations.
        
        Analyzes sleep, stress, soreness, workout load, and form scores
        to produce personalized recovery protocol.
        """
        if not self.text_model:
            self.logger.error("Gemini API key not configured")
            return None
        
        try:
            user_metrics = context.get("user_metrics", {})
            training_data = context.get("training_data", {})
            user_profile = context.get("user_profile", {})
            
            prompt = f"""You are an elite Sports Recovery Scientist specializing in preventing overtraining and optimizing performance.

Analyze this athlete's recovery status and provide personalized recommendations.

USER METRICS:
- Sleep: {user_metrics.get('sleep_hours', 'N/A')} hours, quality {user_metrics.get('sleep_quality', 'N/A')}/10
- Stress Level: {user_metrics.get('stress_level', 'N/A')}/10
- Muscle Soreness: {user_metrics.get('soreness_level', 'N/A')}/10
- Energy Level: {user_metrics.get('energy_level', 'N/A')}/10

TRAINING DATA (Last 7 Days):
- Workouts completed: {training_data.get('workouts_7days', 0)}
- Training load: {training_data.get('workout_load', 'N/A')}
- Average form score: {training_data.get('avg_form_score', 'N/A')}
- Exercises with poor form: {training_data.get('poor_form_exercises', [])}

ATHLETE PROFILE:
- Fitness level: {user_profile.get('fitness_level', 'intermediate')}
- Goal: {user_profile.get('goal', 'general fitness')}
- Name: {user_profile.get('name', 'Athlete')}

Return ONLY valid JSON (no markdown):
{{
    "recovery_score": <0-100 integer>,
    "recovery_status": "<well_rested|moderate|fatigued|overtrained>",
    "recommendation_summary": "<2-3 personalized sentences>",
    "protocol": {{
        "rest_days_needed": <0-7>,
        "active_recovery": ["<activity 1>", "<activity 2>"],
        "mobility_exercises": ["<exercise 1>", "<exercise 2>", "<exercise 3>"],
        "next_workout_timing": "<specific timing recommendation>",
        "intensity_adjustment": "<specific intensity guidance>"
    }},
    "ai_provider": "gemini"
}}"""

            response = self.text_model.generate_content(prompt)
            result = self._extract_json(response.text)
            
            if result:
                result["ai_provider"] = "gemini"
            
            return result
        
        except Exception as e:
            self.logger.error(f"Recovery assessment generation error: {str(e)}")
            return None

# Global Gemini service instance
gemini_service = GeminiService()
