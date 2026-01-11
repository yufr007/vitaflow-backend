# app/workflows/coaching_agents.py
"""
VitaFlow Multi-Agent Coaching System - Gemini-Based.

4 specialized "agents" (prompts) collaborate to generate personalized coaching:
1. Form Analysis Coach - Analyzes form check trends
2. Workout Adherence Coach - Tracks workout consistency
3. Nutrition Coach - Assesses dietary alignment
4. Master Coach Synthesizer - Creates personalized message

Uses Gemini orchestration (Azure OpenAI not available on student accounts).
"""

import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from app.services.gemini_orchestrator import (
    GeminiOrchestrator,
    WorkflowStep,
    WorkflowResult,
    gemini_orchestrator
)

logger = logging.getLogger(__name__)


@dataclass
class CoachPersona:
    """Coaching persona configuration."""
    id: str
    name: str
    emoji: str
    color: str
    tone: str
    specialization: str


COACHING_PERSONAS: Dict[str, CoachPersona] = {
    "motivator": CoachPersona(
        id="motivator",
        name="The Motivator",
        emoji="🔥",
        color="#FF6B35",
        tone="High-energy, celebratory, enthusiastic",
        specialization="Celebrating wins, building momentum"
    ),
    "scientist": CoachPersona(
        id="scientist",
        name="The Scientist",
        emoji="🧪",
        color="#00D9FF",
        tone="Data-driven, analytical, precise",
        specialization="Metrics analysis, optimization"
    ),
    "drill_sergeant": CoachPersona(
        id="drill_sergeant",
        name="The Drill Sergeant",
        emoji="💪",
        color="#FF0040",
        tone="Direct, no-nonsense, challenging",
        specialization="Pushing limits, accountability"
    ),
    "therapist": CoachPersona(
        id="therapist",
        name="The Therapist",
        emoji="🧠",
        color="#9D4EDD",
        tone="Empathetic, supportive, holistic",
        specialization="Mental wellness, recovery, balance"
    ),
    "specialist": CoachPersona(
        id="specialist",
        name="The Specialist",
        emoji="🎯",
        color="#3A0CA3",
        tone="Technical, expert, advanced",
        specialization="Sport-specific, periodization"
    )
}


class CoachingAgentsWorkflow:
    """
    Multi-agent coaching workflow using Gemini orchestration.
    
    Simulates 4 specialized coaches analyzing different aspects
    of user performance, then synthesizes into personalized message.
    """
    
    def __init__(self, orchestrator: GeminiOrchestrator = None):
        self.orchestrator = orchestrator or gemini_orchestrator
    
    async def generate_message(
        self,
        user_profile: Dict[str, Any],
        metrics: Dict[str, Any],
        persona: str = "motivator"
    ) -> Dict[str, Any]:
        """
        Execute multi-agent coaching workflow.
        
        Args:
            user_profile: User profile (name, goals, fitness level)
            metrics: User metrics (form checks, workouts, streak)
            persona: Coaching persona to use
        
        Returns:
            Personalized coaching message with action items
        """
        workflow_id = f"coaching_{int(time.time())}"
        coach_persona = COACHING_PERSONAS.get(persona, COACHING_PERSONAS["motivator"])
        
        # Define workflow steps
        steps = [
            WorkflowStep(
                name="analyze_form",
                function=self._analyze_form,
                dependencies=[],
                max_retries=2,
                timeout=20
            ),
            WorkflowStep(
                name="analyze_workouts",
                function=self._analyze_workouts,
                dependencies=[],
                max_retries=2,
                timeout=20
            ),
            WorkflowStep(
                name="analyze_nutrition",
                function=self._analyze_nutrition,
                dependencies=[],
                max_retries=2,
                timeout=20
            ),
            WorkflowStep(
                name="synthesize_message",
                function=self._synthesize_message,
                dependencies=["analyze_form", "analyze_workouts", "analyze_nutrition"],
                max_retries=3,
                timeout=25
            )
        ]
        
        # Build context
        context = {
            "user_profile": user_profile,
            "metrics": metrics,
            "persona": coach_persona
        }
        
        # Execute workflow
        result = await self.orchestrator.execute_workflow(
            workflow_id, steps, context
        )
        
        if result.success:
            return self._format_success_response(result, coach_persona)
        else:
            return self._format_fallback_response(user_profile, coach_persona)
    
    # =========================================================================
    # Specialized Agent Steps
    # =========================================================================
    
    async def _analyze_form(
        self,
        orchestrator: GeminiOrchestrator,
        context: Dict[str, Any],
        previous: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Form Analysis Coach - analyze form check trends."""
        form_checks = context.get("metrics", {}).get("form_checks", [])
        
        if not form_checks:
            return {
                "status": "no_data",
                "message": "No form checks recorded yet",
                "strengths": [],
                "weaknesses": [],
                "trend": "unknown"
            }
        
        prompt = f"""You are a form analysis expert.

Analyze these recent form check results:
{form_checks}

Identify:
1. Strengths (exercises with good form)
2. Weaknesses (areas needing improvement)
3. Overall trend (improving/declining/stable)

Return ONLY valid JSON:
{{
  "status": "analyzed",
  "avgScore": 75,
  "checkCount": 5,
  "strengths": ["Good hip hinge on deadlifts"],
  "weaknesses": ["Knee cave on squats"],
  "trend": "improving",
  "priorityFocus": "Core bracing during heavy lifts"
}}"""

        return await orchestrator.generate_json(prompt)
    
    async def _analyze_workouts(
        self,
        orchestrator: GeminiOrchestrator,
        context: Dict[str, Any],
        previous: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Workout Adherence Coach - track consistency."""
        workouts = context.get("metrics", {}).get("workouts", [])
        streak = context.get("metrics", {}).get("streak", 0)
        
        if not workouts:
            return {
                "status": "no_data",
                "message": "No workouts logged yet",
                "adherenceRate": 0,
                "patterns": [],
                "recommendations": []
            }
        
        prompt = f"""You are a workout adherence specialist.

Analyze this workout history:
{workouts}
Current streak: {streak} days

Evaluate:
1. Adherence rate (workouts completed vs typical goal)
2. Patterns (consistent days, skipped days)
3. Recommendations for improvement

Return ONLY valid JSON:
{{
  "status": "analyzed",
  "adherenceRate": 0.85,
  "totalWorkouts": 12,
  "avgPerWeek": 4,
  "strongestDay": "Monday",
  "weakestDay": "Friday",
  "patterns": ["Tends to skip Friday workouts"],
  "recommendations": ["Front-load important workouts"]
}}"""

        return await orchestrator.generate_json(prompt)
    
    async def _analyze_nutrition(
        self,
        orchestrator: GeminiOrchestrator,
        context: Dict[str, Any],
        previous: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Nutrition Coach - assess dietary alignment."""
        nutrition = context.get("metrics", {}).get("nutrition", [])
        goal = context.get("user_profile", {}).get("goal", "general fitness")
        
        if not nutrition:
            return {
                "status": "no_data",
                "message": "No nutrition data yet",
                "macroAlignment": 0,
                "strengths": [],
                "gaps": []
            }
        
        prompt = f"""You are a sports nutrition expert.

Analyze this nutrition data for someone with goal "{goal}":
{nutrition}

Assess:
1. Macro alignment with fitness goals
2. Nutritional strengths
3. Nutritional gaps

Return ONLY valid JSON:
{{
  "status": "analyzed",
  "macroAlignment": 0.75,
  "avgProtein": "120g/day",
  "avgCalories": "2200kcal/day",
  "strengths": ["Good protein intake"],
  "gaps": ["Low fiber intake"],
  "priorityImprovement": "Add more vegetables"
}}"""

        return await orchestrator.generate_json(prompt)
    
    async def _synthesize_message(
        self,
        orchestrator: GeminiOrchestrator,
        context: Dict[str, Any],
        previous: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Master Coach - synthesize personalized message."""
        persona = context.get("persona")
        user_profile = context.get("user_profile", {})
        metrics = context.get("metrics", {})
        
        form_analysis = previous.get("analyze_form", {})
        workout_analysis = previous.get("analyze_workouts", {})
        nutrition_analysis = previous.get("analyze_nutrition", {})
        
        prompt = f"""You are VitaFlow's AI Coach using the {persona.name} persona.

PERSONA INSTRUCTIONS:
- Use emoji: {persona.emoji}
- Tone: {persona.tone}
- Specialization: {persona.specialization}

USER PROFILE:
- Name: {user_profile.get('name', 'Champion')}
- Goal: {user_profile.get('goal', 'General Fitness')}
- Fitness Level: {user_profile.get('fitness_level', 'Intermediate')}
- Current Streak: {metrics.get('streak', 0)} days

COACH ANALYSES:
Form Analysis: {form_analysis}
Workout Analysis: {workout_analysis}
Nutrition Analysis: {nutrition_analysis}

Create a personalized coaching message (2-3 sentences) that:
1. Uses your persona's tone and emoji
2. References SPECIFIC data from the analyses
3. Acknowledges progress (use actual numbers!)
4. Provides ONE clear, actionable next step

Return ONLY valid JSON:
{{
  "message": "{persona.emoji} Your personalized message here...",
  "actionItems": ["Primary action", "Secondary action"],
  "focusArea": "strength|cardio|nutrition|recovery|form",
  "motivationScore": 8,
  "dataInsights": ["Key insight 1", "Key insight 2"]
}}"""

        return await orchestrator.generate_json(prompt)
    
    # =========================================================================
    # Response Formatting
    # =========================================================================
    
    def _format_success_response(
        self,
        result: WorkflowResult,
        persona: CoachPersona
    ) -> Dict[str, Any]:
        """Format successful workflow result."""
        synthesis = result.results.get("synthesize_message", {})
        
        return {
            "success": True,
            "message": synthesis.get("message", f"{persona.emoji} Keep pushing forward!"),
            "persona": persona.id,
            "personaEmoji": persona.emoji,
            "personaName": persona.name,
            "actionItems": synthesis.get("actionItems", []),
            "focusArea": synthesis.get("focusArea", "general"),
            "motivationScore": synthesis.get("motivationScore", 7),
            "dataInsights": synthesis.get("dataInsights", []),
            "analyses": {
                "form": result.results.get("analyze_form", {}),
                "workout": result.results.get("analyze_workouts", {}),
                "nutrition": result.results.get("analyze_nutrition", {})
            },
            "workflowDurationMs": result.total_duration_ms,
            "aiProvider": "gemini_orchestration"
        }
    
    def _format_fallback_response(
        self,
        user_profile: Dict[str, Any],
        persona: CoachPersona
    ) -> Dict[str, Any]:
        """Format fallback response when workflow fails."""
        name = user_profile.get("name", "Champion")
        
        fallback_messages = {
            "motivator": f"🔥 {name}, you're doing amazing! Keep that momentum going!",
            "scientist": f"🧪 {name}, consistency beats intensity. One workout at a time.",
            "drill_sergeant": f"💪 {name}! No excuses - get after it today!",
            "therapist": f"🧠 {name}, be kind to yourself. Every step forward counts.",
            "specialist": f"🎯 {name}, master the basics before advancing.",
        }
        
        return {
            "success": False,
            "message": fallback_messages.get(persona.id, fallback_messages["motivator"]),
            "persona": persona.id,
            "personaEmoji": persona.emoji,
            "personaName": persona.name,
            "actionItems": ["Complete today's workout", "Log your progress"],
            "focusArea": "general",
            "motivationScore": 7,
            "aiProvider": "fallback"
        }


# Factory function
def create_coaching_workflow() -> CoachingAgentsWorkflow:
    """Create a coaching agents workflow instance."""
    return CoachingAgentsWorkflow()


# Default instance
coaching_workflow = CoachingAgentsWorkflow()
