# app/routes/recovery.py
"""
VitaFlow API - Rest & Recovery Routes.

Feature 6: AI-powered recovery assessment and recommendations.
Uses workout load, form check scores, and self-reported metrics.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid
import logging

from app.models.mongodb import (
    RecoveryAssessmentDocument,
    UserDocument,
    FormCheckDocument,
    WorkoutDocument
)
from app.dependencies import get_current_user_id
from app.schemas.recovery import (
    RecoveryMetricsInput,
    RecoveryAssessmentResponse,
    RecoveryProtocol,
    RecoveryHistoryResponse,
    RecoveryHistoryItem,
    RecoveryQuickCheck
)
from app.services.ai_router import get_ai_router

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/assess", response_model=RecoveryAssessmentResponse)
async def create_recovery_assessment(
    metrics: RecoveryMetricsInput,
    user_id: str = Depends(get_current_user_id)
):
    """
    Create a new recovery assessment with AI-generated recommendations.
    
    Analyzes:
    - User-reported metrics (sleep, stress, soreness, energy)
    - Recent workout load (last 7 days)
    - Recent form check scores (last 7 days)
    
    Returns personalized recovery protocol.
    """
    try:
        # Get user profile
        user = await UserDocument.find_one(UserDocument.uid == uuid.UUID(user_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Calculate 7-day metrics
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        
        # Get recent form checks
        form_checks = await FormCheckDocument.find(
            FormCheckDocument.user_id == user.uid,
            FormCheckDocument.created_at >= seven_days_ago
        ).to_list()
        
        # Get recent workouts
        workouts = await WorkoutDocument.find(
            WorkoutDocument.user_id == user.uid,
            WorkoutDocument.created_at >= seven_days_ago
        ).to_list()
        
        # Calculate training load (simplified: number of workouts * avg intensity)
        workout_load = len(workouts) * 1.0  # Base load per workout
        
        # Calculate average form score
        avg_form_score = None
        if form_checks:
            avg_form_score = sum(fc.score for fc in form_checks) / len(form_checks)
        
        # Build context for AI
        context = {
            "user_metrics": {
                "sleep_hours": metrics.sleep_hours,
                "sleep_quality": metrics.sleep_quality,
                "stress_level": metrics.stress_level,
                "soreness_level": metrics.soreness_level,
                "energy_level": metrics.energy_level
            },
            "training_data": {
                "workouts_7days": len(workouts),
                "workout_load": workout_load,
                "avg_form_score": avg_form_score,
                "poor_form_exercises": [
                    fc.exercise_name for fc in form_checks if fc.score < 70
                ]
            },
            "user_profile": {
                "fitness_level": user.fitness_level,
                "goal": user.goal,
                "name": user.name
            }
        }
        
        # Generate AI recovery assessment
        ai_router = await get_ai_router()
        ai_result = await ai_router.generate_recovery_assessment(
            user_id=user_id,
            context=context
        )
        
        # Create assessment document
        assessment_id = uuid.uuid4()
        assessment = RecoveryAssessmentDocument(
            uid=assessment_id,
            user_id=user.uid,
            sleep_hours=metrics.sleep_hours,
            sleep_quality=metrics.sleep_quality,
            stress_level=metrics.stress_level,
            soreness_level=metrics.soreness_level,
            energy_level=metrics.energy_level,
            workout_load_7days=workout_load,
            avg_form_score_7days=avg_form_score,
            recovery_score=ai_result.get("recovery_score", 70),
            recovery_status=ai_result.get("recovery_status", "moderate"),
            recommendation_summary=ai_result.get("recommendation_summary", ""),
            protocol=ai_result.get("protocol", {})
        )
        await assessment.insert()
        
        # Build response
        protocol_data = ai_result.get("protocol", {})
        protocol = RecoveryProtocol(
            rest_days_needed=protocol_data.get("rest_days_needed", 0),
            active_recovery=protocol_data.get("active_recovery", []),
            mobility_exercises=protocol_data.get("mobility_exercises", []),
            next_workout_timing=protocol_data.get("next_workout_timing", "Ready to train"),
            intensity_adjustment=protocol_data.get("intensity_adjustment", "Normal intensity")
        )
        
        return RecoveryAssessmentResponse(
            assessment_id=str(assessment_id),
            recovery_score=ai_result.get("recovery_score", 70),
            recovery_status=ai_result.get("recovery_status", "moderate"),
            recommendation_summary=ai_result.get("recommendation_summary", ""),
            protocol=protocol,
            sleep_hours=metrics.sleep_hours,
            sleep_quality=metrics.sleep_quality,
            stress_level=metrics.stress_level,
            soreness_level=metrics.soreness_level,
            energy_level=metrics.energy_level,
            workout_load_7days=workout_load,
            avg_form_score_7days=avg_form_score,
            created_at=datetime.now(timezone.utc)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Recovery assessment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick-check")
async def quick_recovery_check(
    check: RecoveryQuickCheck,
    user_id: str = Depends(get_current_user_id)
):
    """
    Quick 2-question recovery check for daily use.
    
    Returns simplified recommendation without saving to database.
    Good for morning check-ins.
    """
    # Simple algorithm based on energy and soreness
    recovery_score = calculate_quick_recovery_score(
        check.energy_level,
        check.soreness_level
    )
    
    if recovery_score >= 80:
        status = "well_rested"
        recommendation = "You're feeling great! Ready for a challenging workout."
    elif recovery_score >= 60:
        status = "moderate"
        recommendation = "Good to go, but listen to your body. Consider moderate intensity."
    elif recovery_score >= 40:
        status = "fatigued"
        recommendation = "Your body needs recovery. Try light activity or active recovery."
    else:
        status = "overtrained"
        recommendation = "Rest day recommended. Focus on sleep and stress reduction."
    
    return {
        "recovery_score": recovery_score,
        "recovery_status": status,
        "recommendation": recommendation,
        "ready_to_train": recovery_score >= 60
    }


@router.get("/history", response_model=RecoveryHistoryResponse)
async def get_recovery_history(
    days: int = 30,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get recovery assessment history with trend analysis.
    
    Args:
        days: Number of days to look back (default 30)
    """
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    assessments = await RecoveryAssessmentDocument.find(
        RecoveryAssessmentDocument.user_id == uuid.UUID(user_id),
        RecoveryAssessmentDocument.created_at >= cutoff_date
    ).sort(-RecoveryAssessmentDocument.created_at).to_list()
    
    if not assessments:
        return RecoveryHistoryResponse(
            assessments=[],
            average_recovery_score=0.0,
            trend="stable",
            total_assessments=0
        )
    
    # Calculate average
    scores = [a.recovery_score for a in assessments if a.recovery_score]
    avg_score = sum(scores) / len(scores) if scores else 0.0
    
    # Calculate trend (compare first half vs second half)
    trend = calculate_trend(scores)
    
    # Build response
    history_items = [
        RecoveryHistoryItem(
            assessment_id=str(a.uid),
            recovery_score=a.recovery_score or 0,
            recovery_status=a.recovery_status or "unknown",
            recommendation_summary=a.recommendation_summary or "",
            created_at=a.created_at
        )
        for a in assessments
    ]
    
    return RecoveryHistoryResponse(
        assessments=history_items,
        average_recovery_score=round(avg_score, 1),
        trend=trend,
        total_assessments=len(assessments)
    )


@router.get("/latest")
async def get_latest_assessment(
    user_id: str = Depends(get_current_user_id)
):
    """Get the most recent recovery assessment."""
    assessment = await RecoveryAssessmentDocument.find_one(
        RecoveryAssessmentDocument.user_id == uuid.UUID(user_id)
    )
    
    if not assessment:
        return {"message": "No assessments found", "has_assessment": False}
    
    return {
        "has_assessment": True,
        "assessment_id": str(assessment.uid),
        "recovery_score": assessment.recovery_score,
        "recovery_status": assessment.recovery_status,
        "recommendation_summary": assessment.recommendation_summary,
        "protocol": assessment.protocol,
        "created_at": assessment.created_at.isoformat()
    }


@router.get("/readiness")
async def get_workout_readiness(
    user_id: str = Depends(get_current_user_id)
):
    """
    Get current workout readiness score.
    
    Returns a 0-100 score indicating readiness for training.
    Factors in recent recovery assessments and workout history.
    """
    # Get most recent assessment (within last 24 hours)
    yesterday = datetime.now(timezone.utc) - timedelta(hours=24)
    
    recent_assessment = await RecoveryAssessmentDocument.find_one(
        RecoveryAssessmentDocument.user_id == uuid.UUID(user_id),
        RecoveryAssessmentDocument.created_at >= yesterday
    )
    
    if recent_assessment and recent_assessment.recovery_score:
        readiness = recent_assessment.recovery_score
        source = "recent_assessment"
    else:
        # Default to moderate readiness if no recent data
        readiness = 70
        source = "default"
    
    return {
        "readiness_score": readiness,
        "ready_to_train": readiness >= 60,
        "intensity_suggestion": get_intensity_suggestion(readiness),
        "source": source,
        "last_assessment": recent_assessment.created_at.isoformat() if recent_assessment else None
    }


# Helper functions
def calculate_quick_recovery_score(energy: int, soreness: int) -> int:
    """Calculate recovery score from quick check inputs."""
    # Energy contributes positively, soreness negatively
    # Scale: energy 1-10 (higher is better), soreness 1-10 (lower is better)
    energy_factor = energy * 6  # Max 60 points
    soreness_factor = (10 - soreness) * 4  # Max 40 points
    return min(100, max(0, energy_factor + soreness_factor))


def calculate_trend(scores: List[int]) -> str:
    """Calculate trend from a list of scores."""
    if len(scores) < 2:
        return "stable"
    
    mid = len(scores) // 2
    first_half = scores[mid:]  # Older scores (list is sorted recent-first)
    second_half = scores[:mid]  # Newer scores
    
    first_avg = sum(first_half) / len(first_half) if first_half else 0
    second_avg = sum(second_half) / len(second_half) if second_half else 0
    
    diff = second_avg - first_avg
    
    if diff > 5:
        return "improving"
    elif diff < -5:
        return "declining"
    return "stable"


def get_intensity_suggestion(readiness: int) -> str:
    """Get workout intensity suggestion based on readiness."""
    if readiness >= 85:
        return "high_intensity"
    elif readiness >= 70:
        return "normal_intensity"
    elif readiness >= 50:
        return "reduced_intensity"
    elif readiness >= 30:
        return "light_activity"
    return "rest_recommended"
