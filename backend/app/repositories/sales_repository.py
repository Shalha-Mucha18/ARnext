from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import date
from app.db.utils import get_uom_conversion_sql
from app.utils.exceptions import DatabaseError

class SalesRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_metrics_by_date_range(
        self,
        start_date: date,
        end_date: date,
        unit_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get aggregated metrics for a date range using correct UOM logic.
        """
        try:
            uom_sql = get_uom_conversion_sql()
            from app.db.utils import get_uom_display
            uom_display_sql = get_uom_display()
            
            unit_clause = "AND unit_id = :unit_id" if unit_id is not None else ""

            query = text(f"""
                SELECT
                    COUNT(*) as total_orders,
                    ROUND(SUM({uom_sql})::numeric, 2) as total_quantity,
                    MAX({uom_display_sql}) as uom
                FROM tbldeliveryinfo
                WHERE delivery_date >= :start_date
                  AND delivery_date <= :end_date
                  AND delivery_date IS NOT NULL
                  {unit_clause}
            """)

            print(start_date, end_date)
            
            params = {
                "start_date": start_date,
                "end_date": end_date,
            }
            if unit_id is not None:
                params["unit_id"] = unit_id
            
            result = await self.db.execute(query, params)
            row = result.fetchone()
            
            if not row:
                return {"total_orders": 0, "total_quantity": 0.0, "uom": "Units"}
            
            return {
                "total_orders": row.total_orders,
                "total_quantity": float(row.total_quantity or 0),
                "uom": row.uom or "Units"
            }
            
        except Exception as e:
            raise DatabaseError(f"Error fetching metrics: {str(e)}")



    async def get_mtd_stats(
        self,
        start_date: date,
        end_date: date,
        unit_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Month-to-Date statistics"""
        try:
            uom_sql = get_uom_conversion_sql()
            from app.db.utils import get_uom_display
            uom_display_sql = get_uom_display()
            
            unit_clause = "AND unit_id = :unit_id" if unit_id is not None else ""
            
            query = text(f"""
                SELECT 
                    ROUND(SUM({uom_sql})::numeric, 2) as delivery_qty,
                    COUNT(*) as total_orders,
                    MAX({uom_display_sql}) as uom
                FROM tbldeliveryinfo
                WHERE delivery_date >= :start_date
                  AND delivery_date < :end_date
                  {unit_clause}
            """)
            
            params = {"start_date": start_date, "end_date": end_date}
            if unit_id is not None:
                params["unit_id"] = unit_id
                
            result = await self.db.execute(query, params)
            row = result.fetchone()
            
            return {
                "delivery_qty": float(row.delivery_qty or 0) if row else 0.0,
                "total_orders": row.total_orders if row else 0,
                "uom": row.uom if row and row.uom else "Units"
            }
        except Exception as e:
            raise DatabaseError(f"Error fetching MTD stats: {str(e)}")

    async def get_monthly_trend(self, unit_id: Optional[int], limit: int = 12, end_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """Get last 12 months sales trend."""
        try:
            uom_sql = get_uom_conversion_sql()
            unit_clause = "AND unit_id = :unit_id" if unit_id is not None else ""
            
            # Calculate start date in Python (1st day of month 11 months ago)
            # If end_date is 2024-12-31, we want 2024-01-01
            target_end = end_date if end_date else date.today()
            # First set to 1st of month
            clean_end = target_end.replace(day=1)
            # Subtract 11 months to get 12 month window including current
            from dateutil.relativedelta import relativedelta
            start_date = clean_end - relativedelta(months=11)
            
            query = text(f"""
                SELECT
                    TO_CHAR(delivery_date, 'YYYY-MM') as month,
                    COUNT(*) as order_count,
                    ROUND(SUM({uom_sql})::numeric, 2) as qty
                FROM tbldeliveryinfo
                WHERE delivery_date >= :start_date
                  AND delivery_date <= :end_date
                  AND delivery_date IS NOT NULL
                  {unit_clause}
                GROUP BY TO_CHAR(delivery_date, 'YYYY-MM')
                ORDER BY month ASC
            """)
            
            params = {
                "start_date": start_date, 
                "end_date": target_end
            }
            if unit_id is not None:
                params["unit_id"] = unit_id
            
            result = await self.db.execute(query, params)
            
            return [
                {
                    "month": row.month,
                    "order_count": int(row.order_count),
                    "qty": float(row.qty or 0)
                }
                for row in result.fetchall()
            ]
        except Exception as e:
            raise DatabaseError(f"Error fetching sales trend: {str(e)}")

    async def get_monthly_summary(self, unit_id: Optional[int], date_filter: date) -> Dict[str, Any]:
        """Get summary stats for a specific month."""
        try:
            uom_sql = get_uom_conversion_sql()
            from app.db.utils import get_uom_display
            uom_display_sql = get_uom_display()
            unit_clause = "AND unit_id = :unit_id" if unit_id is not None else ""
            
            # Calculate end date in Python to avoid SQL interval issues
            from dateutil.relativedelta import relativedelta
            end_date = date_filter + relativedelta(months=1)
            
            query = text(f"""
                SELECT
                    ROUND(SUM({uom_sql})::numeric, 2) as total_quantity,
                    COUNT(*) as total_orders,
                    MAX({uom_display_sql}) as uom
                FROM tbldeliveryinfo
                WHERE delivery_date >= :start_date
                  AND delivery_date < :end_date
                  {unit_clause}
            """)
            
            params = {
                "start_date": date_filter,
                "end_date": end_date
            }
            if unit_id is not None:
                params["unit_id"] = unit_id
            
            result = await self.db.execute(query, params)
            row = result.fetchone()
            
            if not row: return {}
            
            # Also get month label
            month_label = date_filter.strftime("%B %Y")
            
            return {
                "month": month_label,
                "total_quantity": float(row.total_quantity or 0),
                "total_orders": int(row.total_orders or 0),
                "uom": row.uom or "Units"
            }
        except Exception as e:
            raise DatabaseError(f"Error fetching monthly summary: {str(e)}")

    async def get_yearly_monthly_average(self, unit_id: Optional[int], year: int) -> Dict[str, Any]:
        """
        Get average monthly metrics for a specific year.
        Strategy: Get Total Year metrics, divide by 12 (or 1 if 0).
        subtitle is "Monthly Avg".
        """
        try:
            uom_sql = get_uom_conversion_sql()
            from app.db.utils import get_uom_display
            uom_display_sql = get_uom_display()
            unit_clause = "AND unit_id = :unit_id" if unit_id is not None else ""
            
            start_date = date(year, 1, 1)
            end_date = date(year, 12, 31)
            
            query = text(f"""
                SELECT
                    ROUND(SUM({uom_sql})::numeric, 2) as total_quantity,
                    COUNT(*) as total_orders,
                    MAX({uom_display_sql}) as uom
                FROM tbldeliveryinfo
                WHERE delivery_date >= :start_date
                  AND delivery_date <= :end_date
                  {unit_clause}
            """)
            
            params = {"unit_id": unit_id, "start_date": start_date, "end_date": end_date} if unit_id is not None else {"start_date": start_date, "end_date": end_date}
            
            result = await self.db.execute(query, params)
            row = result.fetchone()
            
            if not row: return {}
            
            # Helper to average
            def avg(val):
                return float(val or 0) / 12
            
            return {
                "month": f"Monthly Average ({year})",
                "total_quantity": avg(row.total_quantity),
                "total_orders": int((row.total_orders or 0) / 12),
                "uom": row.uom or "Units"
            }
        except Exception as e:
            raise DatabaseError(f"Error fetching yearly average: {str(e)}")
