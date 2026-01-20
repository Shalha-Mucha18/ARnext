"""
Sales endpoints - YTD, MTD, metrics, credit ratio, concentration risk.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.repositories import sales_repo, units_repo
from app.schemas.sales import YtdSalesResponse, MtdStatsResponse
from core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/v1/ytd-sales")
def get_ytd_sales(
    unit_id: Optional[str] = Query(None, description="Business unit ID"),
    fiscal_year: bool = Query(False, description="Use fiscal year (July-June)")
) -> dict:
    """
    Get Year-to-Date sales comparison: Current Year vs Last Year.
    
    Args:
        unit_id: Optional business unit filter
        fiscal_year: If True, use fiscal year (July-June) instead of calendar year
        
    Returns:
        YTD sales data with growth metrics
    """
    try:
        data = sales_repo.get_ytd_sales(unit_id=unit_id, fiscal_year=fiscal_year)
        
        # Add business unit name
        data["business_unit_name"] = units_repo.get_business_unit_name(unit_id)
        
        return data
    except Exception as e:
        logger.error(f"Error in get_ytd_sales endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/mtd-stats")
def get_mtd_stats(
    unit_id: Optional[str] = Query(None, description="Business unit ID"),
    month: Optional[int] = Query(None, description="Month (1-12)"),
    year: Optional[int] = Query(None, description="Year")
) -> dict:
    """
    Get Month-to-Date statistics.
    
    Args:
        unit_id: Optional business unit filter
        month: Optional month (1-12)
        year: Optional year
        
    Returns:
        MTD statistics with growth metrics
    """
    try:
        return sales_repo.get_mtd_stats(unit_id=unit_id, month=month, year=year)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in get_mtd_stats endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))
