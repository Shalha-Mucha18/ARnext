from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import logging

from app.db.session import get_db
from app.api.v1.deps import get_sales_service
from app.services.sales_service import SalesService
from app.schemas.sales import YTDResponse
from app.schemas.common import StandardResponse
from app.utils.cache import cache_response
from app.utils.exceptions import NotFoundError, DatabaseError

logger = logging.getLogger(__name__)

# Using 'sales' prefix from router inclusion, so path is /ytd
router = APIRouter()

@router.get(
    "/ytd",
    response_model=StandardResponse[YTDResponse],
    status_code=status.HTTP_200_OK,
    summary="Get YTD Sales Analysis"
)
@cache_response(expire=300)
async def get_ytd_sales(
    unit_id: Optional[str] = Query(
        None,
        description="Business unit ID",
        examples=["UNIT001"]
    ),
    fiscal_year: bool = Query(
        False,
        description="Use fiscal year instead of calendar year"
    ),
    year: Optional[int] = Query(
        None,
        description="Target year for analysis"
    ),
    month: Optional[int] = Query(
        None,
        description="Target month for analysis"
    ),
    sales_service: SalesService = Depends(get_sales_service)
):
    """
    Retrieve Year-to-Date sales analysis with comprehensive metrics.
    
    **Features:**
    - Current YTD metrics (orders, quantity, revenue)
    - Previous year comparison
    - Growth percentages
    - Cached for 5 minutes
    """
    try:
        data = await sales_service.get_ytd_comparison(unit_id, fiscal_year, year, month)
        
        return StandardResponse(
            status="success",
            data=data,
            message="YTD analysis retrieved successfully"
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except DatabaseError as e:
        logger.error(f"Database error: {e.message}")
        import traceback, sys
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail="Failed to retrieve sales data")
    except Exception as e:
        import traceback, sys
        # Write to stderr so it appears in console logs
        sys.stderr.write(f"Error in ytd_sales: {str(e)}\n")
        traceback.print_exc(file=sys.stderr)
        
        # Also try to write to file if possible
        try:
            with open("/tmp/backend_debug.log", "a") as f:
                f.write(f"Error in ytd_sales: {str(e)}\n")
                f.write(traceback.format_exc())
                f.write("\n" + "-"*20 + "\n")
        except:
            pass
            
        logger.exception(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/mtd",
    response_model=StandardResponse,
    summary="Get Month-to-Date Stats"
)
@cache_response(expire=300)
async def get_mtd_stats(
    unit_id: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    service: SalesService = Depends(get_sales_service)
):
    try:
        data = await service.get_mtd_stats(unit_id, year, month)
        return StandardResponse(data=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics", response_model=StandardResponse)
@cache_response(expire=300)
async def get_sales_metrics(
    unit_id: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    service: SalesService = Depends(get_sales_service)
):
    try:
        print(f"DEBUG: get_sales_metrics called with year={year}, month={month}")
        data = await service.get_sales_metrics(unit_id, year, month)
        return StandardResponse(data=data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/monthly-summary", response_model=StandardResponse)
@cache_response(expire=300)
async def get_monthly_summary(
    month: Optional[int] = Query(None, description="Month in YYYY-MM format"),
    year: Optional[int] = Query(None, description="Year for yearly average"),
    unit_id: Optional[int] = Query(None),
    service: SalesService = Depends(get_sales_service)
):
    try:
        data = await service.get_monthly_summary(month, year, unit_id)
        return StandardResponse(data=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ytd-insights", response_model=StandardResponse)
async def get_ytd_insights(
    unit_id: Optional[str] = Query(None),
    fiscal_year: bool = Query(False),
    service: SalesService = Depends(get_sales_service)
):
    """
    Generate AI insights for YTD sales performance.
    Uses LLM to analyze YTD year-over-year growth trends and provide strategic recommendations.
    """
    try:
        from llm.chain import SalesGPTCore
        from llm.client import get_llm
        
        # Get YTD data (current YTD vs last year YTD)
        ytd_data = await service.get_ytd_comparison(unit_id, fiscal_year)
        
        current_ytd = ytd_data.get("current_ytd", {})
        last_ytd = ytd_data.get("last_ytd", {})
        growth_metrics = ytd_data.get("growth_metrics", {})
        
        # Transform YTD data for LLM analysis
        transformed_current = {
            "revenue": current_ytd.get("total_revenue", 0),
            "qty": current_ytd.get("total_quantity", 0),
            "order_count": current_ytd.get("total_orders", 0),
            "month": f"YTD {current_ytd.get('period_end', '')}"
        }
        
        # Create a "trend" with just current and last year for YoY comparison
        transformed_trend = [
            {
                "month": f"YTD {current_ytd.get('period_end', '')}",
                "revenue": current_ytd.get("total_revenue", 0),
                "qty": current_ytd.get("total_quantity", 0),
                "order_count": current_ytd.get("total_orders", 0)
            },
            {
                "month": f"YTD {last_ytd.get('period_end', '')}",
                "revenue": last_ytd.get("total_revenue", 0),
                "qty": last_ytd.get("total_quantity", 0),
                "order_count": last_ytd.get("total_orders", 0)
            }
        ]
        
        # Generate AI insights using LLM
        llm = get_llm()
        gpt = SalesGPTCore(llm)
        insights = gpt.analyze_sales_diagnostics(
            current_month=transformed_current,
            trend_data=transformed_trend
        )
        
        return StandardResponse(
            data={"insights": insights},
            message="YTD insights generated successfully"
        )
    except Exception as e:
        logger.exception(f"Failed to generate YTD insights: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate insights: {str(e)}")

@router.get("/mtd-insights", response_model=StandardResponse)
async def get_mtd_insights(
    unit_id: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    service: SalesService = Depends(get_sales_service)
):
    """
    Generate AI insights for MTD (Month-to-Date) sales performance.
    Analyzes current month vs previous month performance.
    """
    try:
        from llm.chain import SalesGPTCore
        from llm.client import get_llm
        
        # Get MTD data (current month vs previous month)
        mtd_data = await service.get_mtd_stats(unit_id, year, month)
        
        current_month = mtd_data.get("current_month", {})
        previous_month = mtd_data.get("previous_month", {})
        
        # Transform MTD data for LLM analysis
        transformed_current = {
            "revenue": 0, # Not available in MTD stats currently
            "qty": current_month.get("delivery_qty", 0),
            "order_count": current_month.get("total_orders", 0),
            "month": f"MTD {current_month.get('year', '')}-{str(current_month.get('month', '')).zfill(2)}"
        }
        
        # Create trend with current and previous month
        transformed_trend = [
            {
                "month": f"{current_month.get('year', '')}-{str(current_month.get('month', '')).zfill(2)}",
                "revenue": 0,
                "qty": current_month.get("delivery_qty", 0),
                "order_count": current_month.get("total_orders", 0)
            },
            {
                "month": "Previous Month",
                "revenue": 0,
                "qty": previous_month.get("delivery_qty", 0),
                "order_count": previous_month.get("total_orders", 0)
            }
        ]
        
        # Generate AI insights using LLM
        llm = get_llm()
        gpt = SalesGPTCore(llm)
        insights = gpt.analyze_sales_diagnostics(
            current_month=transformed_current,
            trend_data=transformed_trend
        )
        
        return StandardResponse(
            data={"insights": insights},
            message="MTD insights generated successfully"
        )
    except Exception as e:
        logger.exception(f"Failed to generate MTD insights: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate insights: {str(e)}")


