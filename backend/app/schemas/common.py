"""
Common Pydantic schemas used across the application.
"""
from pydantic import BaseModel
from typing import Optional, Any, Dict

class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str
    error_code: Optional[str] = None
    
class SuccessResponse(BaseModel):
    """Standard success response."""
    message: str
    data: Optional[Dict[str, Any]] = None

class MetricsBase(BaseModel):
    """Base metrics model."""
    total_orders: int
    total_quantity: float
    uom: str = "MT"
