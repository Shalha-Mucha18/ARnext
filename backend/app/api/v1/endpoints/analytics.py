from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from app.api.v1.deps import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.analytics_service import AnalyticsService
from app.schemas.common import StandardResponse
from app.api.deps import get_core # Legacy dependency for AI Core
from app.utils.cache import cache_response

router = APIRouter()

async def get_analytics_service(db: AsyncSession = Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(db)

@router.get("/available-months", response_model=StandardResponse)
@cache_response(expire=300)
async def get_available_months(
    unit_id: Optional[str] = Query(None),
    service: AnalyticsService = Depends(get_analytics_service)
):
    try:
        data = await service.get_available_months(unit_id)
        return StandardResponse(data={"months": data})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/top-customers", response_model=StandardResponse)
@cache_response(expire=300)
async def get_top_customers(
    unit_id: Optional[int] = Query(None),
    month: Optional[int] = Query(None, description="Month in YYYY-MM format"),
    year: Optional[int] = Query(None, description="Year (YYYY)"),
    service: AnalyticsService = Depends(get_analytics_service)
):
    try:
        data = await service.get_top_customers_by_month(unit_id, month, year)
        return StandardResponse(data={"top_customers": data})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/credit-ratio", response_model=StandardResponse)
async def get_credit_sales_ratio(
    unit_id: Optional[int] = Query(None),
    month: Optional[str] = Query(None, description="YYYY-MM"),
    year: Optional[int] = Query(None),
    generate_insights: bool = False,
    service: AnalyticsService = Depends(get_analytics_service),
    core = Depends(get_core) # Inject AI Core
):
    try:
        data = await service.get_credit_ratio(unit_id, month, year, generate_insights, core)
        return StandardResponse(data=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/concentration-risk", response_model=StandardResponse)
@cache_response(expire=300)
async def get_concentration_risk(
    unit_id: Optional[str] = Query(None),
    month: Optional[str] = Query(None),
    service: AnalyticsService = Depends(get_analytics_service)
):
    try:
        data = await service.get_concentration_risk(unit_id, month)
        return StandardResponse(data=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/concentration-risk-insights", response_model=StandardResponse)
async def get_concentration_risk_insights(
    unit_id: Optional[str] = Query(None),
    month: Optional[str] = Query(None),
    service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Generate AI insights for customer concentration risk.
    Analyzes top customer dependencies and provides strategic recommendations.
    """
    try:
        from llm.chain import SalesGPTCore
        from llm.client import get_llm
        
        # Get concentration risk data
        risk_data = await service.get_concentration_risk(unit_id, month)
        
        top10_pct = risk_data.get("top_10_percentage", 0)
        top_customers = risk_data.get("top_10_customers", [])
        
        # Get top customer data
        top1_data = {
            "name": top_customers[0]["name"] if top_customers else "N/A",
            "pct": top_customers[0]["percentage"] if top_customers else 0
        }
        
        # Generate AI insights using LLM
        llm = get_llm()
        gpt = SalesGPTCore(llm)
        insights = gpt.analyze_concentration_risk(
            top10_pct=top10_pct,
            top1_data=top1_data
        )
        
        return StandardResponse(
            data={"insights": insights.get("analysis", "No insights available")},
            message="Concentration risk insights generated successfully"
        )
    except Exception as e:
        import logging
        logging.exception(f"Failed to generate concentration risk insights: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate insights: {str(e)}")

