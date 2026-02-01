from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class ChatRequest(BaseModel):
    message: str    
    session_id: Optional[str] = None
    debug: bool = False

class ChatResponse(BaseModel):
    session_id: str
    mode: str
    answer: str
    used_question: Optional[str] = None
    sql: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

class SessionState(BaseModel):
    """
    Serializable session state for Chat history.
    """
    last_question: Optional[str] = None
    last_sql: Optional[str] = None
    last_result: Optional[str] = None
    last_descriptive: Optional[str] = None
    entity_type: Optional[str] = "unknown"
    entities: List[str] = []
    metric: Optional[str] = "unknown"
