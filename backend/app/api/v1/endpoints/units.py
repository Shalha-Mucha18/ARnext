"""
Business units endpoints.
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict
from app.repositories import units_repo
from core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/v1/units")
def get_units() -> List[Dict[str, str]]:
    """
    Get list of all business units with their IDs and names.
    
    Returns:
        List of dicts with unit_id and business_unit_name
        
    Raises:
        HTTPException: If database query fails
    """
    try:
        return units_repo.get_all_units()
    except Exception as e:
        logger.error(f"Error in get_units endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))
