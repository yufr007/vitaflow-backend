# app/routes/voice_coaching.py
"""
VitaFlow API - Voice Coaching Routes (Elite Tier).

Provides real-time voice coaching during workouts.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import logging

from app.services.azure_speech import azure_speech
from app.models.mongodb import UserDocument
from app.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice-coaching", tags=["voice-coaching"])


class VoiceCoachingRequest(BaseModel):
    """Request model for voice coaching cue."""
    exercise: str = Field(..., description="Current exercise name")
    feedback: str = Field(..., description="Coaching feedback text")
    voice_style: Optional[str] = Field("motivator", description="Voice coaching style")
    speaking_rate: Optional[float] = Field(1.0, ge=0.5, le=2.0, description="Speech speed")


class VoiceCommandRequest(BaseModel):
    """Request model for voice command recognition."""
    audio_data: str = Field(..., description="Base64-encoded audio data")
    language: Optional[str] = Field("en-US", description="Language code")


@router.post("/synthesize-cue")
async def synthesize_coaching_cue(
    request: VoiceCoachingRequest,
    user: UserDocument = Depends(get_current_user)
):
    """
    Generate voice coaching cue audio (Elite tier only).
    
    Returns audio/wav stream.
    """
    # Check tier (Elite only)
    if user.subscription_tier != "elite":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Voice coaching is an Elite tier feature"
        )
    
    # Initialize Azure Speech if needed
    if not azure_speech.is_available:
        await azure_speech.initialize()
    
    if not azure_speech.is_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voice coaching temporarily unavailable"
        )
    
    # Get voice name from style
    voices = azure_speech.get_available_voices()
    voice_name = voices.get(request.voice_style, voices["motivator"])
    
    # Synthesize personalized cue
    audio_data = await azure_speech.synthesize_personalized_cue(
        user_name=user.name.split()[0] if user.name else "there",
        exercise=request.exercise,
        feedback=request.feedback,
        user_context=None  # TODO: Get from AgentEvolver
    )
    
    if not audio_data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate voice coaching"
        )
    
    # Return audio stream
    return StreamingResponse(
        iter([audio_data]),
        media_type="audio/wav",
        headers={
            "Content-Disposition": f"attachment; filename=coaching_cue.wav"
        }
    )


@router.post("/recognize-command")
async def recognize_voice_command(
    request: VoiceCommandRequest,
    user: UserDocument = Depends(get_current_user)
):
    """
    Recognize voice command from audio (Elite tier only).
    
    Returns recognized text.
    """
    # Check tier (Elite only)
    if user.subscription_tier != "elite":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Voice commands are an Elite tier feature"
        )
    
    # Initialize Azure Speech if needed
    if not azure_speech.is_available:
        await azure_speech.initialize()
    
    if not azure_speech.is_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voice recognition temporarily unavailable"
        )
    
    # Decode base64 audio
    import base64
    try:
        audio_bytes = base64.b64decode(request.audio_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid audio data: {str(e)}"
        )
    
    # Recognize command
    result = await azure_speech.recognize_voice_command(
        audio_data=audio_bytes,
        language=request.language
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to recognize voice command"
        )
    
    return result


@router.get("/available-voices")
async def get_available_voices(
    user: UserDocument = Depends(get_current_user)
):
    """
    Get available voice styles for coaching (Elite tier only).
    """
    # Check tier (Elite only)
    if user.subscription_tier != "elite":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Voice coaching is an Elite tier feature"
        )
    
    return {
        "voices": azure_speech.get_available_voices(),
        "default": "motivator"
    }
