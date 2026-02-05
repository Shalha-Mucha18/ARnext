from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Optional
from app.api.v1.deps import get_regional_service
from app.services.regional_service import RegionalService
from app.schemas.regional import RegionalResponse
from app.schemas.common import StandardResponse
from app.utils.cache import cache_response

router = APIRouter()

@router.get(
    "/territories",
    response_model=StandardResponse[RegionalResponse],
    summary="Get Top/Bottom Territories"
)
@cache_response(expire=300)
async def get_top_territories(
    unit_id: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    service: RegionalService = Depends(get_regional_service)
):
    """
    Get territory performance ranking (Top 10 and Bottom 10).
    """
    try:
        data = await service.get_territory_performance(unit_id, year, month)
        return StandardResponse(data=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/regions", response_model=StandardResponse)
@cache_response(expire=300)
async def get_regions(
    unit_id: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    service: RegionalService = Depends(get_regional_service)
):
    try:
        data = await service.get_regional_contribution(unit_id, year, month)
        return StandardResponse(data=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/areas", response_model=StandardResponse)
@cache_response(expire=300)
async def get_areas(
    unit_id: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    service: RegionalService = Depends(get_regional_service)
):
    try:
        data = await service.get_area_performance(unit_id, year, month)
        return StandardResponse(data=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/insights", response_model=StandardResponse)
async def generate_regional_insights(
    unit_id: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    service: RegionalService = Depends(get_regional_service)
):
    try:
        from llm.chain import SalesGPTCore
        from llm.client import get_llm
        
        regional_data = await service.get_regional_contribution(unit_id, year, month)
        
        top_regions = regional_data.get("top_regions", [])
        bottom_regions = regional_data.get("bottom_regions", [])
        total_volume = regional_data.get("total_volume", 0)
        
        # Generate AI insights using LLM
        llm = get_llm()
        gpt = SalesGPTCore(llm)
        insights = gpt.analyze_regional_performance(
            top_regions=top_regions,
            bottom_regions=bottom_regions,
            total_volume=total_volume
        )
        
        return StandardResponse(
            data={"analysis": insights.get("analysis", "No insights available")},
            message="Regional insights generated successfully"
        )
    except Exception as e:
        import logging
        logging.exception(f"Failed to generate regional insights: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate insights: {str(e)}")

@router.post("/area-insights", response_model=StandardResponse)
async def generate_area_insights(
    unit_id: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    service: RegionalService = Depends(get_regional_service)
):
    """
    Generate AI insights for area sales performance.
    Analyzes top and bottom areas to provide strategic recommendations.
    """
    try:
        from llm.chain import SalesGPTCore
        from llm.client import get_llm
        
        # Get area performance data
        area_data = await service.get_area_performance(unit_id, year, month)
        
        top_areas = area_data.get("top_areas", [])
        bottom_areas = area_data.get("bottom_areas", []) if "bottom_areas" in area_data else []
        total_volume = area_data.get("total_volume", 0)
        
        # Generate AI insights using LLM
        llm = get_llm()
        gpt = SalesGPTCore(llm)
        insights = gpt.analyze_area_performance(
            top_areas=top_areas,
            bottom_areas=bottom_areas,
            total_volume=total_volume
        )
        
        return StandardResponse(
            data={"analysis": insights.get("analysis", "No insights available")},
            message="Area insights generated successfully"
        )
    except Exception as e:
        import logging
        logging.exception(f"Failed to generate area insights: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate insights: {str(e)}")

@router.post("/territory-insights", response_model=StandardResponse)
async def generate_territory_insights(
    unit_id: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    service: RegionalService = Depends(get_regional_service)
):
    """
    Generate AI insights for territory sales performance.
    Analyzes top and bottom territories to provide strategic recommendations.
    """
    try:
        from llm.chain import SalesGPTCore
        from llm.client import get_llm
        
        # Get territory performance data
        territory_data = await service.get_territory_performance(unit_id, year, month)
        
        top_territories = territory_data.get("top_territories", [])
        bottom_territories = territory_data.get("bottom_territories", []) if "bottom_territories" in territory_data else []
        total_volume = territory_data.get("total_volume", 0)
        
        # Generate AI insights using LLM
        llm = get_llm()
        gpt = SalesGPTCore(llm)
        insights = gpt.analyze_territory_performance(
            top_territories=top_territories,
            bottom_territories=bottom_territories,
            total_volume=total_volume
        )
        
        return StandardResponse(
            data={"analysis": insights.get("analysis", "No insights available")},
            message="Territory insights generated successfully"
        )
    except Exception as e:
        import logging
        logging.exception(f"Failed to generate territory insights: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate insights: {str(e)}")
