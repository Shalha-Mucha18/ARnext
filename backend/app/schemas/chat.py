"""
Chat-related Pydantic schemas.
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any

class ChatRequest(BaseModel):
    """Chat request model."""
    message: str
    session_id: Optional[str] = None
    debug: bool = False

class ChatResponse(BaseModel):
    """Chat response model."""
    session_id: str
    mode: str
    answer: str
    used_question: Optional[str] = None
    sql: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
