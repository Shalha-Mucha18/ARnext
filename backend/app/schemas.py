from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    session_id: str
    message: str
    debug: bool = False

class ChatResponse(BaseModel):
    session_id: str
    mode: str
    answer: str
    used_question: Optional[str] = None
    sql: Optional[str] = None
    meta: Optional[dict] = None

class RegionalInsight(BaseModel):
    region: str
    order_count: int
    total_delivery_qty: float
    total_delivery_value: float
    share_percentage: float

class RegionalInsightsResponse(BaseModel):
    regional_data: List[RegionalInsight]
    ai_insights: dict