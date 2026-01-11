"""
VitaFlow API - Evolution Routes.

API endpoints for AgentEvolver-powered adaptive AI features.
Exposes user learning profiles, AI insights, challenges, and feedback.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from database import get_db
from app.dependencies import get_current_user_id, get_current_user
from app.models.user import User
from app.services.evolver import evolver_service
from app.middleware.rate_limit import limiter
from app.schemas.evolution import (
    ExperienceEventCreate,
    ExperienceEventResponse,
    ExperienceContext,
    Challenge,
    ChallengeListResponse,
    Attribution,
    AttributionCreateRequest,
    EvolutionProfile,
    Insight,
    InsightListResponse,
    EvolutionFeedback,
    EvolutionFeedbackResponse,
)


router = APIRouter()


# =========================================
# EVOLUTION PROFILE
# =========================================

@router.get("/profile", response_model=EvolutionProfile)
async def get_evolution_profile(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> EvolutionProfile:
    """
    Get user's AI learning profile and adaptation state.
    
    Shows:
    - Learning stage (beginner → advanced)
    - Preferences confidence (how well AI knows you)
    - Key insights about your fitness patterns
    - Effective interventions that worked for you
    - Areas for growth to unlock more personalization
    """
    try:
        profile = await evolver_service.get_evolution_profile(user_id, db)
        return profile
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get evolution profile: {str(e)}"
        )


@router.get("/context", response_model=ExperienceContext)
async def get_experience_context(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    days_back: int = 30
) -> ExperienceContext:
    """
    Get full experience context used for AI personalization.
    
    This is the data that Gemini sees when generating your recommendations.
    Includes workout history, meal history, form check results, and preferences.
    """
    try:
        context = await evolver_service.get_experience_context(user_id, db, days_back)
        return context
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get experience context: {str(e)}"
        )


# =========================================
# CHALLENGES (Self-Questioning)
# =========================================

@router.get("/challenges", response_model=ChallengeListResponse)
async def get_adaptive_challenges(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    count: int = 3
) -> ChallengeListResponse:
    """
    Get AI-generated progressive challenges.
    
    Challenges are personalized based on:
    - Your current performance levels
    - Areas that need improvement
    - Your learning stage
    - Activities you haven't tried yet
    
    Implementing AgentEvolver's "Self-Questioning" principle.
    """
    try:
        challenges = await evolver_service.generate_adaptive_challenges(user_id, db, count)
        total_xp = sum(c.reward_xp for c in challenges)
        return ChallengeListResponse(
            challenges=challenges,
            total_xp_available=total_xp
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate challenges: {str(e)}"
        )


@router.post("/challenges/{challenge_id}/complete")
async def complete_challenge(
    challenge_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> dict:
    """
    Mark a challenge as completed and award XP.
    """
    # TODO: Validate challenge completion criteria
    # For now, just record the completion
    await evolver_service.update_user_experience(
        user_id,
        ExperienceEventCreate(
            type="challenge_completed",
            data={"challenge_id": challenge_id, "completed_at": datetime.now(timezone.utc).isoformat()}
        ),
        db
    )
    
    return {
        "status": "completed",
        "challenge_id": challenge_id,
        "xp_earned": 100,  # TODO: Get from actual challenge
        "message": "Challenge completed! Your progress is being tracked."
    }


# =========================================
# INSIGHTS
# =========================================

@router.get("/insights", response_model=InsightListResponse)
async def get_ai_insights(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> InsightListResponse:
    """
    Get AI-generated insights about your progress patterns.
    
    Insights include:
    - Performance trends over time
    - Consistency patterns
    - Nutrition correlations
    - Recovery observations
    """
    # Get evolution profile which contains key insights
    profile = await evolver_service.get_evolution_profile(user_id, db)
    
    insights = []
    for i, insight_text in enumerate(profile.key_insights):
        insights.append(Insight(
            id=str(uuid.uuid4()),
            category="performance",
            title=f"Insight #{i+1}",
            description=insight_text,
            confidence=profile.preferences_confidence,
            action_suggestion=None,
            related_data={},
            created_at=datetime.now(timezone.utc)
        ))
    
    # Add growth area insights
    for area in profile.areas_for_growth:
        insights.append(Insight(
            id=str(uuid.uuid4()),
            category="growth",
            title="Growth Opportunity",
            description=area,
            confidence=1.0,
            action_suggestion="Take action to unlock more personalization",
            related_data={},
            created_at=datetime.now(timezone.utc)
        ))
    
    return InsightListResponse(
        insights=insights,
        updated_at=datetime.now(timezone.utc)
    )


# =========================================
# ATTRIBUTIONS (Self-Attributing)
# =========================================

@router.post("/attribution", response_model=Attribution)
async def create_attribution(
    request: AttributionCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> Attribution:
    """
    Create a progress attribution linking an intervention to an outcome.
    
    This helps the AI understand what works for you:
    - Which workouts led to strength gains
    - Which meals improved your energy
    - Which coaching tips you followed and benefited from
    
    Implementing AgentEvolver's "Self-Attributing" principle.
    """
    try:
        attribution = await evolver_service.attribute_progress(
            user_id=user_id,
            intervention_type=request.intervention_type,
            intervention_id=request.intervention_id,
            outcome_metric=request.outcome_metric,
            outcome_value=request.outcome_value,
            baseline_value=request.baseline_value,
            db=db
        )
        return attribution
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create attribution: {str(e)}"
        )


@router.get("/attributions", response_model=list[Attribution])
async def get_effective_interventions(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    min_score: float = 0.6
) -> list[Attribution]:
    """
    Get interventions that have proven effective for you.
    
    Higher attribution scores = more confidence that intervention caused progress.
    """
    try:
        attributions = await evolver_service.get_effective_interventions(user_id, db, min_score)
        return attributions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get attributions: {str(e)}"
        )


# =========================================
# EXPERIENCE EVENTS
# =========================================

@router.post("/event", response_model=dict)
async def log_experience_event(
    event: ExperienceEventCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> dict:
    """
    Log an experience event for AI learning.
    
    Events are automatically collected from form checks, workouts, etc.
    This endpoint allows manual event logging for custom tracking.
    
    Event types:
    - form_check: Exercise form analysis completed
    - workout_completed: Workout session finished
    - meal_logged: Meal was logged
    - coaching_feedback: Feedback on coaching message
    - challenge_completed: Challenge was achieved
    """
    try:
        await evolver_service.update_user_experience(user_id, event, db)
        return {
            "status": "logged",
            "event_type": event.type,
            "message": "Experience event recorded. AI learning updated."
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to log event: {str(e)}"
        )


# =========================================
# FEEDBACK
# =========================================

@router.post("/feedback", response_model=EvolutionFeedbackResponse)
async def submit_evolution_feedback(
    feedback: EvolutionFeedback,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> EvolutionFeedbackResponse:
    """
    Submit feedback to improve AI recommendations.
    
    Feedback helps the AI learn your preferences faster:
    - Rate workouts, meals, coaching messages
    - Specify what you liked/disliked
    - Update your preferences directly
    """
    try:
        # Log as experience event
        await evolver_service.update_user_experience(
            user_id,
            ExperienceEventCreate(
                type=f"{feedback.feedback_type}_feedback",
                data={
                    "item_id": feedback.item_id,
                    "rating": feedback.rating,
                    "helpful": feedback.helpful,
                    "specific_feedback": feedback.specific_feedback,
                    "preferences_update": feedback.preferences_update
                }
            ),
            db
        )
        
        # Get updated confidence
        profile = await evolver_service.get_evolution_profile(user_id, db)
        
        return EvolutionFeedbackResponse(
            status="saved",
            message="Thank you for your feedback! AI recommendations will improve.",
            learning_updated=True,
            new_confidence=profile.preferences_confidence
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}"
        )
