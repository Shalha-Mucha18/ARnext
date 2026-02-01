from typing import Generic, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar('T')

class StandardResponse(BaseModel, Generic[T]):
    """Standard API response format"""
    status: str = "success"
    data: Optional[T] = None
    message: Optional[str] = None
    errors: Optional[dict] = None

class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response format"""
    status: str = "success"
    data: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
