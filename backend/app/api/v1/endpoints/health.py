"""
Health check endpoint.
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def health_check():
    """
    Health check endpoint.
    
    Returns:
        Status dict
    """
    return {"status": "ok"}
