"""
VitaFlow API - AgentEvolver Service.

Implements self-evolving AI principles for adaptive fitness coaching.
Uses Gemini API with experience context instead of full RL training.

Three Core Mechanisms:
1. Self-Questioning - Curiosity-driven challenge generation
2. Self-Navigating - Experience-guided recommendations
3. Self-Attributing - Credit assignment for effective interventions
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.user import User
from app.models.user_experience import UserExperience
from app.models.progress_attribution import ProgressAttribution, ExperienceEvent
from app.models.form_check import FormCheck
from app.models.workout import Workout
from app.models.meal_plan import MealPlan
from app.models.coaching_message import CoachingMessage
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
    """
    VitaFlow implementation of AgentEvolver principles.
    
    Manages user-specific AI adaptation without full RL training.
    Uses Gemini API with rich context for personalized generation.
    """
    
    def __init__(self):
        """Initialize the evolver service."""
        self.logger = logging.getLogger(__name__)
    
    # =========================================
    # SELF-NAVIGATING: Experience Management
    # =========================================
    
    async def get_or_create_experience(self, user_id: str, db: Session) -> UserExperience:
        """
        Get user's experience record, creating if not exists.
        
        Args:
            user_id: User's unique identifier
            db: Database session
            
        Returns:
            UserExperience model instance
        """
        experience = db.query(UserExperience).filter(
            UserExperience.user_id == user_id
        ).first()
        
        if not experience:
            experience = UserExperience(
                id=uuid.uuid4(),
                user_id=user_id,
                workout_preferences={},
                meal_preferences={},
                exercise_performance={},
                coaching_feedback={},
                adaptation_params={},
                learning_stage="beginner",
                preferences_confidence="0.0",
                total_data_points="0"
            )
            db.add(experience)
            db.commit()
            db.refresh(experience)
            self.logger.info(f"Created new experience record for user {user_id}")
        
        return experience
    
    async def update_user_experience(
        self, 
        user_id: str, 
        event: ExperienceEventCreate,
        db: Session
    ) -> None:
        """
        Update user experience from a new event.
        
        This is the main entry point for experience collection.
        Called after form checks, workout completions, meal ratings, etc.
        
        Args:
            user_id: User's unique identifier
            event: The experience event to process
            db: Database session
        """
        # 1. Store raw event for batch processing
        raw_event = ExperienceEvent(
            id=uuid.uuid4(),
            user_id=user_id,
            event_type=event.type,
            event_data=event.data,
            processed="false"
        )
        db.add(raw_event)
        
        # 2. Update aggregated experience
        experience = await self.get_or_create_experience(user_id, db)
        experience.update_from_event(event.type, event.data)
        
        # 3. Update specific preference categories based on event type
        if event.type == "form_check":
            await self._update_exercise_performance(experience, event.data)
        elif event.type == "workout_completed":
            await self._update_workout_preferences(experience, event.data)
        elif event.type == "meal_logged":
            await self._update_meal_preferences(experience, event.data)
        elif event.type == "coaching_feedback":
            await self._update_coaching_feedback(experience, event.data)
        
        db.commit()
        self.logger.info(f"Updated experience for user {user_id}: {event.type}")
    
    async def _update_exercise_performance(
        self, 
        experience: UserExperience, 
        data: Dict[str, Any]
    ) -> None:
        """Update exercise performance from form check data."""
        exercise = data.get("exercise", "unknown")
        score = data.get("score", 0)
        
        perf = experience.exercise_performance or {}
        if exercise not in perf:
            perf[exercise] = {
                "avg_score": score,
                "total_checks": 1,
                "scores": [score],
                "improvement_rate": 0
            }
        else:
            perf[exercise]["scores"].append(score)
            perf[exercise]["total_checks"] += 1
            scores = perf[exercise]["scores"][-10:]  # Keep last 10
            perf[exercise]["avg_score"] = sum(scores) / len(scores)
            
            # Calculate improvement rate
            if len(scores) >= 2:
                perf[exercise]["improvement_rate"] = scores[-1] - scores[0]
        
        experience.exercise_performance = perf
    
    async def _update_workout_preferences(
        self, 
        experience: UserExperience, 
        data: Dict[str, Any]
    ) -> None:
        """Update workout preferences from completion data."""
        prefs = experience.workout_preferences or {}
        
        # Track preferred exercises
        completed = data.get("exercises_completed", [])
        prefs.setdefault("exercise_frequency", {})
        for ex in completed:
            prefs["exercise_frequency"][ex] = prefs["exercise_frequency"].get(ex, 0) + 1
        
        # Track preferred duration
        duration = data.get("duration_minutes")
        if duration:
            durations = prefs.setdefault("durations", [])
            durations.append(duration)
            prefs["preferred_duration"] = sum(durations[-5:]) / min(len(durations), 5)
        
        # Track difficulty preference
        difficulty = data.get("difficulty_rating")
        if difficulty:
            ratings = prefs.setdefault("difficulty_ratings", [])
            ratings.append(difficulty)
            prefs["intensity_preference"] = (
                "light" if sum(ratings[-5:]) / min(len(ratings), 5) < 3 
                else "intense" if sum(ratings[-5:]) / min(len(ratings), 5) > 4 
                else "moderate"
            )
        
        experience.workout_preferences = prefs
    
    async def _update_meal_preferences(
        self, 
        experience: UserExperience, 
        data: Dict[str, Any]
    ) -> None:
        """Update meal preferences from rating data."""
        prefs = experience.meal_preferences or {}
        
        rating = data.get("rating", 3)
        meal_type = data.get("meal_type", "unknown")
        cuisine = data.get("cuisine")
        
        # Track cuisine preferences
        if cuisine and rating >= 4:
            cuisines = prefs.setdefault("liked_cuisines", [])
            if cuisine not in cuisines:
                cuisines.append(cuisine)
        
        # Track meal timing preferences
        prefs.setdefault("meal_ratings", {}).setdefault(meal_type, []).append(rating)
        
        experience.meal_preferences = prefs
    
    async def _update_coaching_feedback(
        self, 
        experience: UserExperience, 
        data: Dict[str, Any]
    ) -> None:
        """Update coaching feedback preferences."""
        feedback = experience.coaching_feedback or {}
        
        helpful = data.get("helpful", True)
        topic = data.get("topic", "general")
        
        # Track helpful topics
        if helpful:
            feedback.setdefault("effective_topics", [])
            if topic not in feedback["effective_topics"]:
                feedback["effective_topics"].append(topic)
        
        # Track response rate
        total = feedback.get("total_messages", 0) + 1
        responded = feedback.get("responded_count", 0) + (1 if helpful is not None else 0)
        feedback["total_messages"] = total
        feedback["responded_count"] = responded
        feedback["feedback_response_rate"] = responded / total if total > 0 else 0
        
        experience.coaching_feedback = feedback
    
    async def get_experience_context(
        self, 
        user_id: str, 
        db: Session,
        days_back: int = 30
    ) -> ExperienceContext:
        """
        Build full experience context for Gemini generation.
        
        This context enables "Self-Navigating" - using past experience
        to guide better recommendations.
        
        Args:
            user_id: User's unique identifier
            db: Database session
            days_back: How many days of history to include
            
        Returns:
            ExperienceContext with full user learning data
        """
        experience = await self.get_or_create_experience(user_id, db)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
        
        # Get recent form checks
        form_checks = db.query(FormCheck).filter(
            FormCheck.user_id == user_id,
            FormCheck.created_at >= cutoff
        ).order_by(desc(FormCheck.created_at)).limit(10).all()
        
        form_history = [
            FormCheckSummary(
                check_id=str(fc.id),
                exercise=fc.exercise_name or "unknown",
                score=float(fc.form_score or 0),
                date=fc.created_at,
                key_feedback=fc.analysis_feedback[:100] if fc.analysis_feedback else None
            )
            for fc in form_checks
        ]
        
        # Get recent workouts
        workouts = db.query(Workout).filter(
            Workout.user_id == user_id,
            Workout.created_at >= cutoff
        ).order_by(desc(Workout.created_at)).limit(10).all()
        
        workout_history = [
            WorkoutSummary(
                workout_id=str(w.id),
                date=w.created_at,
                exercises_completed=len(w.exercises.split(",")) if w.exercises else 0,
                difficulty_rating=None,
                duration_minutes=w.duration_minutes if hasattr(w, "duration_minutes") else None
            )
            for w in workouts
        ]
        
        # Get recent meals
        meals = db.query(MealPlan).filter(
            MealPlan.user_id == user_id,
            MealPlan.created_at >= cutoff
        ).order_by(desc(MealPlan.created_at)).limit(10).all()
        
        meal_history = [
            MealSummary(
                meal_id=str(m.id),
                date=m.created_at,
                meal_type="meal_plan",
                calories=m.daily_calories if hasattr(m, "daily_calories") else None,
                adherence_score=None
            )
            for m in meals
        ]
        
        # Build preferences from experience
        wp = experience.workout_preferences or {}
        mp = experience.meal_preferences or {}
        
        preferences = UserPreferences(
            preferred_exercises=list((wp.get("exercise_frequency") or {}).keys())[:5],
            avoided_exercises=[],
            preferred_workout_duration=int(wp.get("preferred_duration", 45)),
            intensity_preference=wp.get("intensity_preference", "moderate"),
            dietary_restrictions=mp.get("dietary_restrictions", []),
            favorite_cuisines=mp.get("liked_cuisines", [])
        )
        
        # Get attribution scores
        attributions = db.query(ProgressAttribution).filter(
            ProgressAttribution.user_id == user_id,
            ProgressAttribution.attribution_score >= 0.6
        ).order_by(desc(ProgressAttribution.attribution_score)).limit(5).all()
        
        attribution_scores = {
            f"{a.intervention_type}:{a.outcome_metric}": a.attribution_score
            for a in attributions
        }
        
        return ExperienceContext(
            workout_history=workout_history,
            meal_history=meal_history,
            form_check_history=form_history,
            preferences=preferences,
            attribution_scores=attribution_scores,
            similar_user_insights=None,  # TODO: collaborative filtering
            learning_stage=experience.learning_stage,
            preferences_confidence=float(experience.preferences_confidence or 0)
        )
    
    # =========================================
    # SELF-QUESTIONING: Challenge Generation
    # =========================================
    
    async def generate_adaptive_challenges(
        self, 
        user_id: str, 
        db: Session,
        count: int = 3
    ) -> List[Challenge]:
        """
        Generate progressive challenges based on user's current abilities.
        
        Implements "Self-Questioning" - curiosity-driven task generation
        to help users grow and explore new fitness areas.
        
        Args:
            user_id: User's unique identifier
            db: Database session
            count: Number of challenges to generate
            
        Returns:
            List of personalized Challenge objects
        """
        experience = await self.get_or_create_experience(user_id, db)
        context = await self.get_experience_context(user_id, db)
        
        challenges = []
        
        # Challenge 1: Exercise Improvement (based on lowest performing exercise)
        perf = experience.exercise_performance or {}
        if perf:
            lowest = min(perf.items(), key=lambda x: x[1].get("avg_score", 100))
            challenges.append(Challenge(
                id=str(uuid.uuid4()),
                title=f"Master Your {lowest[0].title()}",
                description=f"Improve your {lowest[0]} form score from {lowest[1].get('avg_score', 0):.0f}% to {min(100, lowest[1].get('avg_score', 0) + 10):.0f}%",
                difficulty=max(1, min(10, 11 - int(lowest[1].get('avg_score', 50) / 10))),
                category="strength",
                reward_xp=150,
                deadline=datetime.now(timezone.utc) + timedelta(days=7),
                prerequisites=[],
                success_criteria=f"Achieve {min(100, lowest[1].get('avg_score', 0) + 10):.0f}% or higher on a {lowest[0]} form check"
            ))
        
        # Challenge 2: Consistency (based on learning stage)
        streak_target = {"beginner": 3, "developing": 5, "established": 7, "advanced": 14}
        target = streak_target.get(experience.learning_stage, 3)
        challenges.append(Challenge(
            id=str(uuid.uuid4()),
            title=f"Build a {target}-Day Streak",
            description=f"Complete at least one workout for {target} consecutive days",
            difficulty=min(10, target),
            category="consistency",
            reward_xp=target * 50,
            deadline=datetime.now(timezone.utc) + timedelta(days=target + 3),
            prerequisites=[],
            success_criteria=f"Log {target} workouts on consecutive days"
        ))
        
        # Challenge 3: Try Something New (explore avoided areas)
        if len(context.workout_history) > 0:
            challenges.append(Challenge(
                id=str(uuid.uuid4()),
                title="Flexibility Explorer",
                description="Complete a dedicated stretching or yoga session",
                difficulty=3,
                category="flexibility",
                reward_xp=100,
                deadline=datetime.now(timezone.utc) + timedelta(days=14),
                prerequisites=[],
                success_criteria="Complete a 15+ minute stretching/yoga workout"
            ))
        
        return challenges[:count]
    
    # =========================================
    # SELF-ATTRIBUTING: Credit Assignment
    # =========================================
    
    async def attribute_progress(
        self,
        user_id: str,
        intervention_type: str,
        intervention_id: Optional[str],
        outcome_metric: str,
        outcome_value: float,
        baseline_value: Optional[float],
        db: Session
    ) -> Attribution:
        """
        Create a progress attribution linking intervention to outcome.
        
        Implements "Self-Attributing" - tracking which interventions
        (workouts, meals, coaching) lead to actual progress.
        
        Args:
            user_id: User's unique identifier
            intervention_type: Type of intervention (workout, meal_plan, coaching)
            intervention_id: Specific intervention ID
            outcome_metric: What was measured (form_score, weight, strength)
            outcome_value: The measured value
            baseline_value: Previous value for comparison
            db: Database session
            
        Returns:
            Attribution with calculated score
        """
        attribution = ProgressAttribution(
            id=uuid.uuid4(),
            user_id=user_id,
            intervention_type=intervention_type,
            intervention_id=intervention_id,
            outcome_metric=outcome_metric,
            outcome_value=outcome_value,
            baseline_value=baseline_value,
            outcome_at=datetime.now(timezone.utc)
        )
        
        # Calculate attribution score
        attribution.attribution_score = attribution.calculate_attribution_score()
        
        db.add(attribution)
        db.commit()
        db.refresh(attribution)
        
        self.logger.info(
            f"Created attribution for user {user_id}: "
            f"{intervention_type} -> {outcome_metric} (score: {attribution.attribution_score:.2f})"
        )
        
        return Attribution(
            intervention_type=attribution.intervention_type,
            intervention_id=attribution.intervention_id,
            outcome_metric=attribution.outcome_metric,
            outcome_value=attribution.outcome_value,
            attribution_score=attribution.attribution_score,
            time_to_outcome_hours=attribution.time_to_outcome
        )
    
    async def get_effective_interventions(
        self, 
        user_id: str, 
        db: Session,
        min_score: float = 0.6
    ) -> List[Attribution]:
        """
        Get interventions that have proven effective for this user.
        
        Used to prioritize similar interventions in future recommendations.
        """
        attributions = db.query(ProgressAttribution).filter(
            ProgressAttribution.user_id == user_id,
            ProgressAttribution.attribution_score >= min_score
        ).order_by(desc(ProgressAttribution.attribution_score)).limit(10).all()
        
        return [
            Attribution(
                intervention_type=a.intervention_type,
                intervention_id=a.intervention_id,
                outcome_metric=a.outcome_metric,
                outcome_value=a.outcome_value,
                attribution_score=a.attribution_score,
                time_to_outcome_hours=a.time_to_outcome
            )
            for a in attributions
        ]
    
    # =========================================
    # EVOLUTION PROFILE
    # =========================================
    
    async def get_evolution_profile(
        self, 
        user_id: str, 
        db: Session
    ) -> EvolutionProfile:
        """
        Get user's AI learning profile and adaptation state.
        
        Shows how well the AI understands this user.
        """
        experience = await self.get_or_create_experience(user_id, db)
        context = await self.get_experience_context(user_id, db)
        
        # Generate key insights
        insights = []
        perf = experience.exercise_performance or {}
        if perf:
            best_exercise = max(perf.items(), key=lambda x: x[1].get("avg_score", 0))
            insights.append(f"Your best exercise is {best_exercise[0]} with {best_exercise[1].get('avg_score', 0):.0f}% avg score")
        
        if context.preferences.preferred_workout_duration:
            insights.append(f"You prefer {context.preferences.preferred_workout_duration}-minute workouts")
        
        # Get effective interventions
        effective = await self.get_effective_interventions(user_id, db)
        effective_types = list(set(e.intervention_type for e in effective))
        
        # Areas for growth
        growth_areas = []
        if not perf:
            growth_areas.append("Try your first form check to unlock personalized feedback")
        if len(context.workout_history) < 5:
            growth_areas.append("Complete more workouts to improve recommendations")
        
        return EvolutionProfile(
            user_id=user_id,
            learning_stage=experience.learning_stage,
            preferences_confidence=float(experience.preferences_confidence or 0),
            total_data_points=int(experience.total_data_points or 0),
            last_evolution=experience.last_updated,
            key_insights=insights[:5],
            effective_interventions=effective_types[:3],
            areas_for_growth=growth_areas[:3]
        )


# Global evolver service instance
evolver_service = AgentEvolverService()
