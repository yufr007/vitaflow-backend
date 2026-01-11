# app/routes/coaching.py
"""
VitaFlow API - Coaching Routes (MongoDB + Azure Foundry).

Multi-agent coaching system with personalized messages.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
import uuid
import logging

from app.models.mongodb import CoachingMessageDocument, UserDocument, FormCheckDocument, WorkoutDocument
from app.dependencies import get_current_user_id
from app.services.ai_router import get_ai_router

logger = logging.getLogger(__name__)
router = APIRouter()


class CoachingMessageResponse(BaseModel):
    """Coaching message response."""
    id: str
    message: str
    persona: str
    persona_emoji: Optional[str] = None
    action_items: Optional[list] = None
    focus_area: Optional[str] = None
    motivation_score: Optional[int] = None
    ai_provider: str
    created_at: str


class SetPersonaRequest(BaseModel):
    """Request to set coaching persona."""
    persona: str  # motivator, scientist, drill_sergeant, therapist, specialist


@router.get("/message", response_model=CoachingMessageResponse)
async def get_daily_coaching_message(
    persona: str = "motivator",
    user_id: str = Depends(get_current_user_id)
):
    """
    Get personalized daily coaching message.
    
    Uses Azure Foundry 4-agent workflow:
    - Form Analysis Coach
    - Workout Adherence Coach
    - Nutrition Coach
    - Master Coach Synthesizer
    
    Falls back to Gemini if Azure unavailable.
    """
    try:
        # Get user profile
        user = await UserDocument.find_one(UserDocument.uid == uuid.UUID(user_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_profile = {
            "name": user.name,
            "goal": user.goal,
            "fitness_level": user.fitness_level,
        }
        
        # Gather metrics for the last 30 days
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        
        # Form checks
        form_checks = await FormCheckDocument.find(
            FormCheckDocument.user_id == user.uid,
            FormCheckDocument.created_at >= thirty_days_ago
        ).to_list()
        
        # Workouts
        workouts = await WorkoutDocument.find(
            WorkoutDocument.user_id == user.uid,
            WorkoutDocument.created_at >= thirty_days_ago
        ).to_list()
        
        # Calculate streak (simplified)
        streak = len([w for w in workouts if w.created_at >= datetime.now(timezone.utc) - timedelta(days=7)])
        
        metrics = {
            "form_checks": [
                {"score": fc.score, "exercise": fc.exercise_name, "date": fc.created_at.isoformat()}
                for fc in form_checks
            ],
            "workouts": [
                {"title": w.title, "date": w.created_at.isoformat()}
                for w in workouts
            ],
            "nutrition": [],  # Add nutrition data when available
            "streak": streak
        }
        
        # Get AI router and generate coaching
        ai_router = await get_ai_router()
        result = await ai_router.generate_coaching(
            user_id=user_id,
            user_profile=user_profile,
            metrics=metrics,
            persona=persona
        )
        
        # Save to database
        message_id = uuid.uuid4()
        coaching_msg = CoachingMessageDocument(
            uid=message_id,
            user_id=user.uid,
            persona=persona,
            message=result.get("message", ""),
            context=result.get("analyses"),
            read=True,
            favorited=False
        )
        await coaching_msg.insert()
        
        return CoachingMessageResponse(
            id=str(message_id),
            message=result.get("message", "Keep up the great work!"),
            persona=persona,
            persona_emoji=result.get("persona_emoji"),
            action_items=result.get("action_items", []),
            focus_area=result.get("focus_area"),
            motivation_score=result.get("motivation_score"),
            ai_provider=result.get("ai_provider", "unknown"),
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Coaching message generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_coaching_history(
    limit: int = 20,
    user_id: str = Depends(get_current_user_id)
):
    """Get coaching message history."""
    messages = await CoachingMessageDocument.find(
        CoachingMessageDocument.user_id == uuid.UUID(user_id)
    ).sort(-CoachingMessageDocument.created_at).limit(limit).to_list()
    
    return {
        "messages": [
            {
                "id": str(msg.uid),
                "message": msg.message,
                "persona": msg.persona,
                "favorited": msg.favorited,
                "created_at": msg.created_at.isoformat()
            }
            for msg in messages
        ]
    }


@router.post("/{message_id}/favorite")
async def toggle_favorite(
    message_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Toggle favorite status on a coaching message."""
    message = await CoachingMessageDocument.find_one(
        CoachingMessageDocument.uid == uuid.UUID(message_id),
        CoachingMessageDocument.user_id == uuid.UUID(user_id)
    )
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    message.favorited = not message.favorited
    await message.save()
    
    return {"id": str(message.uid), "favorited": message.favorited}


@router.post("/persona")
async def set_preferred_persona(
    request: SetPersonaRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Set preferred coaching persona for user."""
    valid_personas = ["motivator", "scientist", "drill_sergeant", "therapist", "specialist"]
    
    if request.persona not in valid_personas:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid persona. Choose from: {valid_personas}"
        )
    
    # Could save to user preferences in DB here
    return {"message": f"Persona set to {request.persona}", "persona": request.persona}