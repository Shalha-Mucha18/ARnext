"""
Health check endpoint.
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/v1/health")
def health_check():
    """
    Health check endpoint.
    
    Returns:
        Status dict
    """
    return {"status": "ok"}
