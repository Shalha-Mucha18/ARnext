from pydantic import BaseModel
from typing import List, Optional

class SessionState(BaseModel):
    last_question: Optional[str] = None
    last_sql: Optional[str] = None
    last_result: Optional[str] = None
    last_descriptive: Optional[str] = None

    entity_type: str = "unknown"
    entities: List[str] = []
    metric: str = "unknown"
