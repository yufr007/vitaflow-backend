# app/routes/evolution.py
"""
VitaFlow API - Evolution Routes (MongoDB/Beanie Version).
"""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.dependencies import get_current_user_id
from app.services.evolver import evolver_service
from app.schemas.evolution import (
    ExperienceEventCreate,
    ExperienceContext,
    ChallengeListResponse,
    EvolutionProfile,
    InsightListResponse,
    Insight,
    EvolutionFeedback,
    EvolutionFeedbackResponse,
)

router = APIRouter()

@router.get("/profile", response_model=EvolutionProfile)
async def get_evolution_profile(user_id: str = Depends(get_current_user_id)):
    """Get user's AI learning profile."""
    return await evolver_service.get_evolution_profile(user_id)

@router.get("/context", response_model=ExperienceContext)
async def get_experience_context(
    user_id: str = Depends(get_current_user_id),
    days_back: int = 30
):
    """Get full experience context."""
    return await evolver_service.get_experience_context(user_id, days_back)

@router.get("/challenges", response_model=ChallengeListResponse)
async def get_adaptive_challenges(
    user_id: str = Depends(get_current_user_id),
    count: int = 3
):
    """Get personalized challenges."""
    challenges = await evolver_service.generate_adaptive_challenges(user_id, count)
    return ChallengeListResponse(
        challenges=challenges,
        total_xp_available=sum(c.reward_xp for c in challenges)
    )

@router.get("/insights", response_model=InsightListResponse)
async def get_ai_insights(user_id: str = Depends(get_current_user_id)):
    """Get AI-generated insights."""
    profile = await evolver_service.get_evolution_profile(user_id)
    
    insights = [
        Insight(
            id=str(uuid.uuid4()),
            category="performance",
            title=f"Insight #{i+1}",
            description=text,
            confidence=profile.preferences_confidence,
            created_at=datetime.now(timezone.utc)
        ) for i, text in enumerate(profile.key_insights)
    ]
    
    return InsightListResponse(
        insights=insights,
        updated_at=datetime.now(timezone.utc)
    )

@router.post("/event")
async def log_experience_event(
    event: ExperienceEventCreate,
    user_id: str = Depends(get_current_user_id)
):
    """Log an experience event."""
    await evolver_service.update_user_experience(user_id, event)
    return {"status": "success", "message": "Event recorded"}

@router.post("/feedback", response_model=EvolutionFeedbackResponse)
async def submit_evolution_feedback(
    feedback: EvolutionFeedback,
    user_id: str = Depends(get_current_user_id)
):
    """Submit feedback to improve AI."""
    await evolver_service.update_user_experience(
        user_id, 
        ExperienceEventCreate(
            type="feedback",
            data=feedback.model_dump()
        )
    )
    profile = await evolver_service.get_evolution_profile(user_id)
    return EvolutionFeedbackResponse(
        status="saved",
        message="Feedback received",
        learning_updated=True,
        new_confidence=profile.preferences_confidence
    )
