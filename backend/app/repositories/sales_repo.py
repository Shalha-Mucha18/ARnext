"""
Sales repository - handles all sales-related data access. This module provides secure, centralized access to sales data with proper
error handling and logging.
"""
from typing import Optional, Dict, Any, List, Tuple
from datetime import date, datetime
from decimal import Decimal
import ast
from core.logging import get_logger
from db.engine import get_sync_db

logger = get_logger(__name__)


def _parse_db_result(result_str: str) -> List[Tuple]:
    """ 
    Args:
        result_str: String representation of query result
        
    Returns:
        Parsed result as list of tuples
        
    Note:
        Uses ast.literal_eval() instead of eval() for security
    """
    if not result_str or result_str.strip() == '':
        return []
    
    try:
        return ast.literal_eval(result_str)
    except (SyntaxError, ValueError) as e:
        logger.error(f"Error parsing database result: {e}")
        return []


def _sanitize_unit_id(unit_id: Optional[str]) -> str:
    """
    Args:
        unit_id: Raw unit ID
        
    Returns:
        Sanitized unit ID string
    """
    if not unit_id:
        return ""
    return str(unit_id).replace("'", "''")


def _build_unit_filter(unit_id: Optional[str], column_name: str = "unit_id") -> str:
    """    
    Args:
        unit_id: Unit ID to filter by
        column_name: Column name for the filter
        
    Returns:
        SQL filter clause or empty string
    """
    if not unit_id:
        return ""
    
    try:
        unit_int = int(unit_id)
        return f"AND {column_name} = {unit_int}"
    except ValueError:
        sanitized = _sanitize_unit_id(unit_id)
        return f'AND {column_name} = \'{sanitized}\''


def get_ytd_sales(
    unit_id: Optional[str] = None,
    fiscal_year: bool = False
) -> Dict[str, Any]:
    """   
    Args:
        unit_id: Optional business unit filter
        fiscal_year: If True, use fiscal year (July-June) instead of calendar year
    Returns:
        Dict with current_ytd, last_ytd, and growth_metrics
    Raises:
        Exception: If database query fails
    """
    try:
        unit_filter = _build_unit_filter(unit_id)
        today = date.today()
        
        if fiscal_year:
            # FY label = end year (Jul-Jun)
            if today.month < 7:
                current_year = today.year
                current_ytd_start = f"{today.year - 1}-07-01"
            else:
                current_year = today.year + 1
                current_ytd_start = f"{today.year}-07-01"
            
            current_ytd_end = today.strftime("%Y-%m-%d")
            last_year = current_year - 1
            last_ytd_start = f"{int(current_ytd_start[:4]) - 1}-07-01"
            last_ytd_end = f"{today.year - 1}-{today.month:02d}-{today.day:02d}"
        else:
            current_year = today.year
            last_year = current_year - 1
            
            current_ytd_start = f"{current_year}-01-01"
            current_ytd_end = today.strftime("%Y-%m-%d")
            
            last_ytd_start = f"{last_year}-01-01"
            last_ytd_end = f"{last_year}-{today.month:02d}-{today.day:02d}"
        
        # Query template with unit conversion logic
        query_template = """
            SELECT
            unit_id,
            CASE
                WHEN unit_id IN (4, 144, 188, 189, 232) THEN 'MT'
                WHEN base_uom IN ('Metric Tons', 'Metric Ton', 'MT', 'Ton') THEN 'MT'
                ELSE base_uom
            END AS uom_shown,
            COUNT(*) AS total_order,
            ROUND(
                SUM(
                CASE
                    WHEN unit_id = 4 AND base_uom = 'Ton' THEN delivery_qty
                    WHEN unit_id = 4 THEN (delivery_qty * numgrossweight) / 1000.0
                    WHEN unit_id IN (188, 189, 232) THEN (delivery_qty * numgrossweight) / 1000.0
                    WHEN unit_id = 144 AND base_uom = 'Metric Tons' THEN delivery_qty
                    WHEN unit_id = 144 THEN (delivery_qty * numgrossweight) / 1000.0
                    ELSE delivery_qty
                END
                )::numeric,
                2
            ) AS total_sales_quantity
            FROM public.tbldeliveryinfo
            WHERE delivery_date BETWEEN '{start_date}' AND '{end_date}'
            {unit_filter}
            GROUP BY
            unit_id,
            CASE
                WHEN unit_id IN (4, 144, 188, 189, 232) THEN 'MT'
                WHEN base_uom IN ('Metric Tons', 'Metric Ton', 'MT', 'Ton') THEN 'MT'
                ELSE base_uom
            END
        """
        
        # Execute queries
        current_query = query_template.format(
            start_date=current_ytd_start,
            end_date=current_ytd_end,
            unit_filter=unit_filter
        )
        
        last_query = query_template.format(
            start_date=last_ytd_start,
            end_date=last_ytd_end,
            unit_filter=unit_filter
        )
        
        current_results = _parse_db_result(get_sync_db().run(current_query))
        last_results = _parse_db_result(get_sync_db().run(last_query))
        
        if not current_results or not last_results:
            logger.warning("No YTD data found")
            return {
                "current_ytd": {
                    "period": "Current YTD",
                    "year": current_year,
                    "uom": "MT",
                    "total_orders": 0,
                    "total_quantity": 0.0,
                    "period_start": current_ytd_start,
                    "period_end": current_ytd_end
                },
                "last_ytd": {
                    "period": "Last YTD",
                    "year": last_year,
                    "uom": "MT",
                    "total_orders": 0,
                    "total_quantity": 0.0,
                    "period_start": last_ytd_start,
                    "period_end": last_ytd_end
                },
                "growth_metrics": {
                    "order_growth_pct": 0.0,
                    "quantity_growth_pct": 0.0,
                    "order_change": 0,
                    "quantity_change": 0.0
                }
            }
        
        current_result = current_results[0]
        last_result = last_results[0]
        
        # Build response
        current_ytd = {
            "period": "Current YTD",
            "year": current_year,
            "uom": current_result[1] if current_result else "MT",
            "total_orders": current_result[2] or 0,
            "total_quantity": float(current_result[3] or 0),
            "period_start": current_ytd_start,
            "period_end": current_ytd_end
        }
        
        last_ytd = {
            "period": "Last YTD",
            "year": last_year,
            "uom": last_result[1] if last_result else "MT",
            "total_orders": last_result[2] or 0,
            "total_quantity": float(last_result[3] or 0),
            "period_start": last_ytd_start,
            "period_end": last_ytd_end
        }
        
        # Calculate growth
        order_growth = 0
        quantity_growth = 0
        
        if last_ytd["total_orders"] > 0:
            order_growth = ((current_ytd["total_orders"] - last_ytd["total_orders"]) / 
                          last_ytd["total_orders"]) * 100
        
        if last_ytd["total_quantity"] > 0:
            quantity_growth = ((current_ytd["total_quantity"] - last_ytd["total_quantity"]) / 
                             last_ytd["total_quantity"]) * 100
        
        growth_metrics = {
            "order_growth_pct": round(order_growth, 2),
            "quantity_growth_pct": round(quantity_growth, 2),
            "order_change": current_ytd["total_orders"] - last_ytd["total_orders"],
            "quantity_change": round(current_ytd["total_quantity"] - last_ytd["total_quantity"], 2)
        }
        
        return {
            "current_ytd": current_ytd,
            "last_ytd": last_ytd,
            "growth_metrics": growth_metrics,
            "comparison_date": today.strftime("%Y-%m-%d")
        }
        
    except Exception as e:
        logger.error(f"Error in get_ytd_sales: {e}")
        raise


def get_mtd_stats(
    unit_id: Optional[str] = None,
    month: Optional[int] = None,
    year: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get Month-to-Date statistics.
    
    Args:
        unit_id: Optional business unit filter
        month: Optional month (1-12)
        year: Optional year
        
    Returns:
        Dict with current_month, previous_month, and growth metrics
        
    Raises:
        Exception: If database query fails
    """
    from dateutil.relativedelta import relativedelta
    import datetime as dt
    
    try:
        today = date.today()
        unit_filter = _build_unit_filter(unit_id)
        
        # Determine target month
        if month:
            if not 1 <= month <= 12:
                raise ValueError("Month must be between 1 and 12")
            
            target_year = year if year else today.year
            current_month_start = date(target_year, month, 1)
            cutoff_day = today.day
        else:
            current_month_start = today.replace(day=1)
            cutoff_day = today.day
        
        # Calculate date ranges
        last_day_current = (current_month_start + relativedelta(months=1) - dt.timedelta(days=1)).day
        current_cutoff_day = min(cutoff_day, last_day_current)
        current_month_end = current_month_start.replace(day=current_cutoff_day)
        
        prev_month_start = current_month_start - relativedelta(months=1)
        last_day_prev = (prev_month_start + relativedelta(months=1) - dt.timedelta(days=1)).day
        prev_cutoff_day = min(cutoff_day, last_day_prev)
        prev_month_end = prev_month_start.replace(day=prev_cutoff_day)
        
        # Query template
        query_template = """
            SELECT
            unit_id,
            CASE
                WHEN unit_id IN (4, 144, 188, 189, 232) THEN 'MT'
                WHEN base_uom IN ('Metric Tons', 'Metric Ton', 'MT', 'Ton') THEN 'MT'
                ELSE base_uom
            END AS uom_shown,
            ROUND(
                SUM(
                CASE
                    WHEN unit_id = 4 AND base_uom = 'Ton' THEN delivery_qty
                    WHEN unit_id = 4 THEN (delivery_qty * numgrossweight) / 1000.0
                    WHEN unit_id IN (188, 189, 232) THEN (delivery_qty * numgrossweight) / 1000.0
                    WHEN unit_id = 144 AND base_uom = 'Metric Tons' THEN delivery_qty
                    WHEN unit_id = 144 THEN (delivery_qty * numgrossweight) / 1000.0
                    ELSE delivery_qty
                END
                )::numeric,
                2
            ) AS total_quantity,
            COUNT(*) AS total_orders
            FROM public.tbldeliveryinfo
            WHERE delivery_date BETWEEN DATE '{start_date}' AND DATE '{end_date}'
            {unit_filter}
            GROUP BY
            unit_id,
            CASE
                WHEN unit_id IN (4, 144, 188, 189, 232) THEN 'MT'
                WHEN base_uom IN ('Metric Tons', 'Metric Ton', 'MT', 'Ton') THEN 'MT'
                ELSE base_uom
            END
        """
        
        current_query = query_template.format(
            start_date=current_month_start,
            end_date=current_month_end,
            unit_filter=unit_filter
        )
        
        prev_query = query_template.format(
            start_date=prev_month_start,
            end_date=prev_month_end,
            unit_filter=unit_filter
        )
        
        current_results = _parse_db_result(get_sync_db().run(current_query))
        prev_results = _parse_db_result(get_sync_db().run(prev_query))
        
        if not current_results or not prev_results:
            logger.warning("No MTD data found")
            return {
                "current_month": {
                    "total_quantity": 0.0,
                    "total_orders": 0,
                    "month": current_month_start.strftime("%B"),
                    "year": current_month_start.year,
                    "uom": "MT",
                },
                "previous_month": {
                    "total_quantity": 0.0,
                    "total_orders": 0,
                    "month": prev_month_start.strftime("%B"),
                    "year": prev_month_start.year,
                    "uom": "MT",
                },
                "growth": {
                    "quantity_growth_pct": 0.0,
                    "order_growth_pct": 0.0,
                    "quantity_change": 0.0,
                    "order_change": 0
                }
            }
        
        current_result = current_results[0]
        prev_result = prev_results[0]
        
        current_qty = float(current_result[2] or 0)
        current_orders = int(current_result[3] or 0)
        prev_qty = float(prev_result[2] or 0)
        prev_orders = int(prev_result[3] or 0)
        
        qty_growth = ((current_qty - prev_qty) / prev_qty * 100) if prev_qty > 0 else 0.0
        order_growth = ((current_orders - prev_orders) / prev_orders * 100) if prev_orders > 0 else 0.0
        
        return {
            "current_month": {
                "total_quantity": round(current_qty, 2),
                "total_orders": current_orders,
                "month": current_month_start.strftime("%B"),
                "year": current_month_start.year,
                "uom": current_result[1] if current_result else "MT",
            },
            "previous_month": {
                "total_quantity": round(prev_qty, 2),
                "total_orders": prev_orders,
                "month": prev_month_start.strftime("%B"),
                "year": prev_month_start.year,
                "uom": prev_result[1] if prev_result else "MT",
            },
            "growth": {
                "quantity_growth_pct": round(qty_growth, 2),
                "order_growth_pct": round(order_growth, 2),
                "quantity_change": round(current_qty - prev_qty, 2),
                "order_change": current_orders - prev_orders
            }
        }
        
    except Exception as e:
        logger.error(f"Error in get_mtd_stats: {e}")
        raise
