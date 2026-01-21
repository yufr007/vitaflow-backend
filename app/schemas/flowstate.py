from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class FlowMoment(BaseModel):
    timestamp: datetime
    score: int

class FlowstateSessionResponse(BaseModel):
    id: str
    user_id: str
    flow_score: int
    hrv: Optional[float] = None
    focus_score: Optional[int] = None
    energy_score: Optional[int] = None
    moments: List[FlowMoment] = []
    recommendations: List[str] = []
    created_at: datetime

class FlowstateLatestResponse(BaseModel):
    has_data: bool
    latest_session: Optional[FlowstateSessionResponse] = None
