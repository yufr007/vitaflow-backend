# app/services/evolver.py
"""
VitaFlow API - AgentEvolver Service (MongoDB/Beanie Version).
Handles user-specific AI adaptation and progress tracking.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4

from app.models.mongodb import (
    UserDocument,
    UserExperienceDocument,
    ProgressAttributionDocument,
    ExperienceEventDocument,
    FormCheckDocument,
    WorkoutDocument,
    MealPlanDocument
)
from app.schemas.evolution import (
    ExperienceContext,
    ExperienceEventCreate,
    WorkoutSummary,
    MealSummary,
    FormCheckSummary,
    UserPreferences,
    Challenge,
    Attribution,
    EvolutionProfile,
    Insight,
)

logger = logging.getLogger(__name__)

class AgentEvolverService:
    """Manages AI adaptation using MongoDB/Beanie."""
    
    async def get_or_create_experience(self, user_id: str) -> UserExperienceDocument:
        """Get or create user experience document."""
        experience = await UserExperienceDocument.find_one(
            UserExperienceDocument.user_id == UUID(user_id)
        )
        
        if not experience:
            experience = UserExperienceDocument(
                user_id=UUID(user_id),
                workout_preferences={},
                meal_preferences={},
                exercise_performance={},
                coaching_feedback={},
                adaptation_params={}
            )
            await experience.insert()
            logger.info(f"Created new experience record for user {user_id}")
            
        return experience
    
    async def update_user_experience(
        self, 
        user_id: str, 
        event: ExperienceEventCreate
    ) -> None:
        """Update user experience from a new event."""
        # 1. Store raw event
        raw_event = ExperienceEventDocument(
            user_id=UUID(user_id),
            event_type=event.type,
            event_data=event.data
        )
        await raw_event.insert()
        
        # 2. Update aggregated experience
        experience = await self.get_or_create_experience(user_id)
        
        # Increment data points and update stage (simple logic from legacy model)
        experience.total_data_points += 1
        experience.preferences_confidence = min(0.95, experience.total_data_points / 100)
        
        if experience.total_data_points > 50:
            experience.learning_stage = "advanced"
        elif experience.total_data_points > 20:
            experience.learning_stage = "established"
        elif experience.total_data_points > 5:
            experience.learning_stage = "developing"
            
        # Update specific preference categories
        if event.type == "form_check":
            await self._update_exercise_performance(experience, event.data)
        elif event.type == "workout_completed":
            await self._update_workout_preferences(experience, event.data)
        elif event.type == "meal_logged":
            await self._update_meal_preferences(experience, event.data)
        elif event.type == "coaching_feedback":
            await self._update_coaching_feedback(experience, event.data)
            
        experience.updated_at = datetime.now(timezone.utc)
        await experience.save()
        logger.info(f"Updated experience for user {user_id}: {event.type}")

    async def _update_exercise_performance(self, experience: UserExperienceDocument, data: Dict[str, Any]):
        exercise = data.get("exercise", "unknown")
        score = data.get("score", 0)
        
        perf = experience.exercise_performance
        if exercise not in perf:
            perf[exercise] = {"avg_score": float(score), "total_checks": 1, "scores": [float(score)]}
        else:
            perf[exercise]["scores"].append(float(score))
            scores = perf[exercise]["scores"][-10:]
            perf[exercise]["total_checks"] = len(perf[exercise]["scores"])
            perf[exercise]["avg_score"] = sum(scores) / len(scores)
        experience.exercise_performance = perf

    async def _update_workout_preferences(self, experience: UserExperienceDocument, data: Dict[str, Any]):
        prefs = experience.workout_preferences
        completed = data.get("exercises_completed", [])
        freq = prefs.setdefault("exercise_frequency", {})
        for ex in completed:
            freq[ex] = freq.get(ex, 0) + 1
        experience.workout_preferences = prefs

    async def _update_meal_preferences(self, experience: UserExperienceDocument, data: Dict[str, Any]):
        prefs = experience.meal_preferences
        cuisine = data.get("cuisine")
        if cuisine and data.get("rating", 0) >= 4:
            liked = prefs.setdefault("liked_cuisines", [])
            if cuisine not in liked:
                liked.append(cuisine)
        experience.meal_preferences = prefs

    async def _update_coaching_feedback(self, experience: UserExperienceDocument, data: Dict[str, Any]):
        feedback = experience.coaching_feedback
        if data.get("helpful"):
            topics = feedback.setdefault("effective_topics", [])
            topic = data.get("topic", "general")
            if topic not in topics:
                topics.append(topic)
        experience.coaching_feedback = feedback

    async def get_experience_context(self, user_id: str, days_back: int = 30) -> ExperienceContext:
        """Build context for AI generation."""
        experience = await self.get_or_create_experience(user_id)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
        
        # Recent form checks
        form_checks = await FormCheckDocument.find(
            FormCheckDocument.user_id == UUID(user_id),
            FormCheckDocument.created_at >= cutoff
        ).sort(-FormCheckDocument.created_at).limit(10).to_list()
        
        form_history = [
            FormCheckSummary(
                check_id=str(fc.uid),
                exercise=fc.exercise_name,
                score=float(fc.score),
                date=fc.created_at,
                key_feedback=fc.tips[:100] if fc.tips else None
            ) for fc in form_checks
        ]
        
        # Build preferences
        wp = experience.workout_preferences
        mp = experience.meal_preferences
        
        preferences = UserPreferences(
            preferred_exercises=list((wp.get("exercise_frequency") or {}).keys())[:5],
            avoided_exercises=[],
            preferred_workout_duration=int(wp.get("preferred_duration", 45)),
            intensity_preference=wp.get("intensity_preference", "moderate"),
            dietary_restrictions=mp.get("dietary_restrictions", []),
            favorite_cuisines=mp.get("liked_cuisines", [])
        )
        
        return ExperienceContext(
            workout_history=[], # Simplified for now
            meal_history=[],
            form_check_history=form_history,
            preferences=preferences,
            attribution_scores={},
            learning_stage=experience.learning_stage,
            preferences_confidence=experience.preferences_confidence
        )

    async def generate_adaptive_challenges(self, user_id: str, count: int = 3) -> List[Challenge]:
        """Generate progressive challenges."""
        experience = await self.get_or_create_experience(user_id)
        challenges = []
        
        # Default consistency challenge
        challenges.append(Challenge(
            id=str(uuid4()),
            title=f"Consistency Kickstart",
            description=f"Complete 3 workouts this week to build your baseline.",
            difficulty=2,
            category="consistency",
            reward_xp=100,
            deadline=datetime.now(timezone.utc) + timedelta(days=7),
            success_criteria="3 workouts completed"
        ))
        
        return challenges[:count]

    async def get_evolution_profile(self, user_id: str) -> EvolutionProfile:
        """Get user's AI learning profile."""
        experience = await self.get_or_create_experience(user_id)
        
        insights = []
        perf = experience.exercise_performance
        if perf:
            best = max(perf.items(), key=lambda x: x[1].get("avg_score", 0))
            insights.append(f"Your best exercise is {best[0]} with {best[1].get('avg_score', 0):.0f}% avg score")
        
        return EvolutionProfile(
            user_id=user_id,
            learning_stage=experience.learning_stage,
            preferences_confidence=experience.preferences_confidence,
            total_data_points=experience.total_data_points,
            last_evolution=experience.updated_at,
            key_insights=insights[:5],
            effective_interventions=[],
            areas_for_growth=["Complete more workouts to improve recommendations"]
        )

evolver_service = AgentEvolverService()
