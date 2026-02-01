from typing import Optional, Dict, Any, List
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.analytics_repository import AnalyticsRepository
from app.utils.exceptions import ValidationError
from starlette.concurrency import run_in_threadpool
import logging

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.repository = AnalyticsRepository(db)

    async def get_available_months(self, unit_id: Optional[str] = None) -> List[Dict[str, str]]:
        unit_id_int = self._parse_unit_id(unit_id)
        months = await self.repository.get_available_months(unit_id_int)
        
        formatted = []
        for m in months:
            try:
                dt = datetime.strptime(m, "%Y-%m")
                label = dt.strftime("%B %Y")
                formatted.append({"value": m, "label": label})
            except:
                continue
        return formatted

    async def get_top_customers(
        self,
        unit_id: Optional[str] = None,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        start_date, end_date = self._get_date_range(year, month)
        unit_id_int = self._parse_unit_id(unit_id)
        
        return await self.repository.get_top_customers(start_date, end_date, unit_id_int)

    async def get_top_customers_by_month(
        self,
        unit_id: Optional[int] = None,
        month: Optional[int] = None,
        year: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get top customers with month and year as integers"""
        # Convert unit_id to string for _parse_unit_id
        unit_id_str = str(unit_id) if unit_id is not None else None
        
        # Use year and month directly
        start_date, end_date = self._get_date_range(year, month)
        unit_id_int = self._parse_unit_id(unit_id_str)
        
        return await self.repository.get_top_customers(start_date, end_date, unit_id_int)

    async def get_credit_ratio(
        self,
        unit_id: Optional[int] = None,
        month_str: Optional[str] = None, # "YYYY-MM"
        year: Optional[int] = None,
        generate_insights: bool = False,
        core_engine: Any = None
    ) -> Dict[str, Any]:
        
        if month_str:
            start_date, end_date = self._parse_month_str(month_str)
            display_month = month_str
        elif year:
            start_date, end_date = self._get_date_range(year, None)
            display_month = str(year)
        else:
            today = date.today()
            start_date, end_date = self._get_date_range(None, None) # Current month
            display_month = start_date.strftime("%Y-%m")

        rows = await self.repository.get_credit_ratio(start_date, end_date, unit_id)
        
        data = {
            "Total": {"orders": 0, "revenue": 0.0},
            "Credit": {"orders": 0, "revenue": 0.0},
            "Cash": {"orders": 0, "revenue": 0.0},
            "Both": {"orders": 0, "revenue": 0.0},
            "Other": {"orders": 0, "revenue": 0.0}
        }
        
        for row in rows:
            pay_type = row.pay_type
            orders = row.order_count
            revenue = float(row.total_revenue or 0)
            if pay_type in data:
                data[pay_type]["orders"] = orders
                data[pay_type]["revenue"] = revenue
        
        total_revenue = sum(d["revenue"] for d in data.values())
        total_orders = sum(d["orders"] for d in data.values())
        
        # Calculate percentages
        def calc_pct(val, total):
            return (val / total * 100) if total > 0 else 0.0
            
        result = {
            "month": display_month,
            "total_revenue": total_revenue,
            "total_orders": total_orders
        }
        
        for key in data:
            pct = calc_pct(data[key]["revenue"], total_revenue)
            result[key.lower()] = {
                "order_count": data[key]["orders"],
                "revenue": data[key]["revenue"],
                "percentage": round(pct, 2)
            }

        # AI Insights
        if generate_insights and core_engine and total_revenue > 0:
            try:
                credit_ai = {"percentage": result["credit"]["percentage"], "revenue": result["credit"]["revenue"]}
                cash_ai = {"percentage": result["cash"]["percentage"], "revenue": result["cash"]["revenue"]}
                both_ai = {"percentage": result["both"]["percentage"], "revenue": result["both"]["revenue"]}
                insights = await run_in_threadpool(
                    core_engine.analyze_credit_ratio_ceo,
                    credit_ai, cash_ai, both_ai, []
                )
                result["ai_insights"] = insights
            except Exception as e:
                logger.error(f"AI Insight error: {e}")
                
        return result

    async def get_concentration_risk(
        self,
        unit_id: Optional[str] = None,
        month_str: Optional[str] = None
    ) -> Dict[str, Any]:
        if month_str:
             start_date, end_date = self._parse_month_str(month_str)
        else:
             start_date, end_date = self._get_date_range(None, None)

        unit_id_int = self._parse_unit_id(unit_id)
        
        data = await self.repository.get_concentration_data(start_date, end_date, unit_id_int)
        
        concentration_ratio = (data["top_10_quantity"] / data["total_quantity"] * 100) if data["total_quantity"] > 0 else 0.0
        
        return {
            **data,
            "concentration_ratio": round(concentration_ratio, 2),
            "month": month_str or start_date.strftime("%Y-%m")
        }

    # Helpers
    def _parse_unit_id(self, unit_id: Optional[str]) -> Optional[int]:
        if unit_id and unit_id.lower() != "null":
            try:
                return int(unit_id)
            except ValueError:
                return None
        return None

    def _get_date_range(self, year: Optional[int], month: Optional[int]):
        today = date.today()
        if year and month:
            start = date(year, month, 1)
            next_month = month + 1 if month < 12 else 1
            next_year = year + 1 if month == 12 else year
            end = date(next_year, next_month, 1)
        elif year:
            start = date(year, 1, 1)
            end = date(year + 1, 1, 1)
        elif month:
            start = date(today.year, month, 1)
            next_month = month + 1 if month < 12 else 1
            next_year = today.year + 1 if month == 12 else today.year
            end = date(next_year, next_month, 1)
        else:
            # Current Month
            start = today.replace(day=1)
            next_month = today.month + 1 if today.month < 12 else 1
            next_year = today.year + 1 if today.month == 12 else today.year
            end = date(next_year, next_month, 1)
        return start, end

    def _parse_month_str(self, month_str: str):
        try:
            # "YYYY-MM"
            parts = month_str.split('-')
            year = int(parts[0])
            month = int(parts[1])
            return self._get_date_range(year, month)
        except Exception:
            # Fallback
            return self._get_date_range(None, None)
