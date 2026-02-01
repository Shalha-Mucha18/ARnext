from fastapi import APIRouter, Query, Depends
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.rfm_service import RFMService
router = APIRouter()
@router.get("/analysis")
async def get_rfm_analysis(
    unit_id: Optional[int] = Query(None, description="Business Unit ID filter"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db)
):
    """Get complete RFM analysis with customer segments"""
    service = RFMService(db)
    return await service.get_rfm_analysis(unit_id, start_date, end_date)