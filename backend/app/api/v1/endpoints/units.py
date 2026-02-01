"""
Business units endpoints.
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict
from app.repositories import units_repo
from core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.v1.deps import get_db
from app.repositories.units_repository import UnitsRepository
from app.schemas.common import StandardResponse
from app.utils.cache import cache_response

router = APIRouter()

@router.get("/", response_model=StandardResponse)
@cache_response(expire=3600) # Cache units for 1 hour as they rarely change
async def get_units(db: AsyncSession = Depends(get_db)):
    """
    Get list of all business units with their IDs and names.
    """
    try:
        repo = UnitsRepository(db)
        data = await repo.get_all_units()
        return StandardResponse(data=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
