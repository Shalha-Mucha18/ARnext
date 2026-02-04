from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from app.api.v1.deps import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.forecast_service import ForecastService
from app.schemas.common import StandardResponse
from app.utils.cache import cache_response

router = APIRouter()

async def get_forecast_service(db: AsyncSession = Depends(get_db)) -> ForecastService:
    return ForecastService(db)

@router.get("", response_model=StandardResponse)
# @cache_response(expire=300)
async def get_forecast(
    unit_id: Optional[str] = Query(None),
    service: ForecastService = Depends(get_forecast_service)
):
    try:
        data = await service.get_sales_forecast(unit_id)
        return StandardResponse(data=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from app.api.deps import get_core

@router.post("/insights", response_model=StandardResponse)
async def generate_forecast_insights(
    unit_id: Optional[str] = Query(None),
    service: ForecastService = Depends(get_forecast_service),
    core = Depends(get_core)
):
    """
    Generate AI strategic outlook for sales forecast.
    """
    try:
        insights = await service.generate_insights(unit_id, core)
        return StandardResponse(data=insights)
    except Exception as e:
        import logging
        logging.exception(f"Forecast AI Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
