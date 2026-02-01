from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.utils import get_uom_conversion_sql
from app.utils.exceptions import DatabaseError

class AnalyticsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_available_months(self, unit_id: Optional[int] = None) -> List[str]:
        try:
            unit_clause = "AND unit_id = :unit_id" if unit_id is not None else ""
            query = text(f"""
                SELECT DISTINCT TO_CHAR(delivery_date, 'YYYY-MM') as month
                FROM tbldeliveryinfo
                WHERE delivery_date IS NOT NULL
                {unit_clause}
                ORDER BY month DESC
            """) 
            
            params = {"unit_id": unit_id} if unit_id is not None else {}
            result = await self.db.execute(query, params)
            return [row.month for row in result.fetchall() if row.month]
        except Exception as e:
            raise DatabaseError(f"Error fetching months: {str(e)}")

    async def get_top_customers(
        self,
        start_date: Any,
        end_date: Any,
        unit_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        try:
            uom_sql = get_uom_conversion_sql()
            unit_clause = "AND unit_id = :unit_id" if unit_id is not None else ""
            
            # Using same CTE logic as legac
            query = text(f"""
                WITH cust_sales AS (
                    SELECT
                        customer_name,
                        CASE
                            WHEN unit_id IN (4, 144, 188, 189, 232) THEN 'MT'
                            WHEN base_uom IN ('Metric Tons', 'Metric Ton', 'MT', 'Ton') THEN 'MT'
                            ELSE base_uom
                        END AS uom_shown,
                        SUM({uom_sql}) AS total_sales,
                        COUNT(*) AS order_count
                    FROM tbldeliveryinfo
                    WHERE delivery_date >= :start_date
                      AND delivery_date < :end_date
                      AND delivery_date IS NOT NULL
                      {unit_clause}
                    GROUP BY customer_name,
                        CASE
                            WHEN unit_id IN (4, 144, 188, 189, 232) THEN 'MT'
                            WHEN base_uom IN ('Metric Tons', 'Metric Ton', 'MT', 'Ton') THEN 'MT'
                            ELSE base_uom
                        END
                )
                SELECT
                    customer_name,
                    uom_shown,
                    ROUND(total_sales::numeric, 2) AS total_sales,
                    order_count,
                    ROUND((total_sales * 100.0 / SUM(total_sales) OVER ())::numeric, 2) AS percentage_of_total
                FROM cust_sales
                ORDER BY total_sales DESC
                LIMIT 5
            """)
            
            params = {"start_date": start_date, "end_date": end_date}
            if unit_id is not None:
                params["unit_id"] = unit_id
                
            result = await self.db.execute(query, params)
            rows = result.fetchall()
            
            return [
                {
                    "name": row.customer_name,
                    "uom": row.uom_shown,
                    "quantity": float(row.total_sales or 0),
                    "orders": row.order_count,
                    "percentage": float(row.percentage_of_total or 0)
                }
                for row in rows
            ]
        except Exception as e:
            raise DatabaseError(f"Error fetching top customers: {str(e)}")

    async def get_credit_ratio(
        self,
        start_date: Any,
        end_date: Any,
        unit_id: Optional[int] = None
    ) -> List[Any]:
        try:
            uom_sql = get_uom_conversion_sql()
            unit_clause = "AND unit_id = :unit_id" if unit_id is not None else ""
            
            query = text(f"""
                SELECT 
                    CASE
                        WHEN LOWER("credit_facility_type") = 'cash' THEN 'Cash'
                        WHEN LOWER("credit_facility_type") = 'both' THEN 'Both'
                        WHEN LOWER("credit_facility_type") = 'credit' THEN 'Credit'
                        ELSE 'Other'
                    END AS pay_type,
                    COUNT(*) as order_count,
                    ROUND(CAST(SUM({uom_sql}) AS NUMERIC), 2) as total_revenue
                FROM tbldeliveryinfo
                WHERE "delivery_date" >= :start_date
                  AND "delivery_date" < :end_date
                  AND "delivery_qty" IS NOT NULL
                  {unit_clause}
                GROUP BY pay_type
            """)
            
            params = {"start_date": start_date, "end_date": end_date}
            if unit_id is not None:
                params["unit_id"] = unit_id
                
            result = await self.db.execute(query, params)
            return result.fetchall()
            
        except Exception as e:
            raise DatabaseError(f"Error fetching credit ratio: {str(e)}")

    async def get_concentration_data(
        self,
        start_date: Any,
        end_date: Any,
        unit_id: Optional[int] = None
    ) -> Dict[str, Any]:
        try:
            uom_sql = get_uom_conversion_sql()
            unit_clause = "AND unit_id = :unit_id" if unit_id is not None else ""
            
            # 1. Total Qty
            q_total = text(f"""
                SELECT SUM({uom_sql}) AS total_qty
                FROM tbldeliveryinfo
                WHERE delivery_date >= :start_date
                  AND delivery_date < :end_date
                  AND delivery_qty IS NOT NULL
                  {unit_clause}
            """)
            
            # 2. Top 10 with Window Func
            q_top10 = text(f"""
                SELECT 
                    customer_name,
                    SUM({uom_sql}) as customer_qty,
                    ROUND(
                        SUM({uom_sql}) * 100.0 / NULLIF(SUM(SUM({uom_sql})) OVER(), 0),
                        2
                    ) as qty_share_pct
                FROM tbldeliveryinfo
                WHERE customer_name IS NOT NULL 
                  AND delivery_date >= :start_date
                  AND delivery_date < :end_date
                  {unit_clause}
                GROUP BY customer_name
                ORDER BY customer_qty DESC
                LIMIT 10
            """)
            
            params = {"start_date": start_date, "end_date": end_date}
            if unit_id is not None:
                params["unit_id"] = unit_id
            
            # Execute
            res_total = await self.db.execute(q_total, params)
            total_row = res_total.fetchone()
            total_qty = float(total_row.total_qty or 0) if total_row else 0.0
            
            res_top = await self.db.execute(q_top10, params)
            top_rows = res_top.fetchall()
            
            top_customers = []
            top10_sum = 0.0
            for row in top_rows:
                qty = float(row.customer_qty or 0)
                top10_sum += qty
                top_customers.append({
                     "name": row.customer_name,
                     "quantity": qty,
                     "percentage": float(row.qty_share_pct or 0)
                })
                
            return {
                "total_quantity": total_qty,
                "top_10_quantity": top10_sum,
                "top_10_customers": top_customers
            }
            
        except Exception as e:
            raise DatabaseError(f"Error fetching concentration data: {str(e)}")
