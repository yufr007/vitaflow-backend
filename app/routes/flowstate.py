# app/routes/flowstate.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
import uuid
from datetime import datetime, timezone

from app.models.mongodb import FlowstateSessionDocument
from app.dependencies import get_current_user_id
from app.schemas.flowstate import FlowstateSessionResponse, FlowstateLatestResponse, FlowMoment

router = APIRouter()

@router.get("/latest", response_model=FlowstateLatestResponse)
async def get_latest_flowstate(user_id: str = Depends(get_current_user_id)):
    """Get the most recent flow state session."""
    session = await FlowstateSessionDocument.find_one(
        FlowstateSessionDocument.user_id == uuid.UUID(user_id)
    ).sort(-FlowstateSessionDocument.created_at)
    
    if not session:
        return FlowstateLatestResponse(has_data=False)
    
    return FlowstateLatestResponse(
        has_data=True,
        latest_session=FlowstateSessionResponse(
            id=str(session.uid),
            user_id=str(session.user_id),
            flow_score=session.flow_score,
            hrv=session.hrv,
            focus_score=session.focus_score,
            energy_score=session.energy_score,
            moments=[FlowMoment(timestamp=m["timestamp"], score=m["score"]) for m in session.moments],
            recommendations=session.recommendations,
            created_at=session.created_at
        )
    )

@router.post("/session")
async def create_flow_session(
    flow_score: int,
    user_id: str = Depends(get_current_user_id)
):
    """Log a new flow state session (mocked logic)."""
    session = FlowstateSessionDocument(
        user_id=uuid.UUID(user_id),
        flow_score=flow_score,
        moments=[
            {"timestamp": datetime.now(timezone.utc), "score": flow_score}
        ],
        recommendations=["Take a 5-minute breather", "Hydrate more"]
    )
    await session.insert()
    return {"status": "success", "session_id": str(session.uid)}
