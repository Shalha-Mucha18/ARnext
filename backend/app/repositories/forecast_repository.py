from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.utils.exceptions import DatabaseError

class ForecastRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_global_forecast(self, unit_id: Optional[str] = None) -> Dict[str, List]:
        try:
            unit_filter = "AND \"Unit_Id\" = :unit_id" if unit_id else ""
            params = {"unit_id": unit_id} if unit_id else {}

            # Global Actuals (Historical)
            q_act = text(f"""
                SELECT 
                    TO_CHAR("Date", 'YYYY-MM') AS month,
                    SUM("numDeliveryQtyMT") AS total_qty
                FROM "AIL_Monthly_Total_Forecast"
                WHERE 1=1
                  {unit_filter}
                  AND "Type" != 'Forecasted'
                  AND "Date" >= '2022-01-01'
                  AND "Date" <= '2026-12-31'
                  AND "Date" IS NOT NULL
                GROUP BY month
                ORDER BY month ASC
            """)

            # Global Forecast
            q_for = text(f"""
                SELECT 
                    TO_CHAR("Date", 'YYYY-MM') AS month,
                    SUM("numDeliveryQtyMT") AS total_qty
                FROM "AIL_Monthly_Total_Forecast"
                WHERE "Type" = 'Forecasted'
                  {unit_filter}
                  AND "Date" >= '2022-01-01'
                  AND "Date" <= '2026-12-31'
                  AND "Date" IS NOT NULL
                GROUP BY month
                ORDER BY month ASC
            """)

            res_act = await self.db.execute(q_act, params)
            res_for = await self.db.execute(q_for, params)
            
            return {
                "actuals": res_act.fetchall(),
                "forecast": res_for.fetchall()
            }
        except Exception as e:
            raise DatabaseError(f"Error fetching global forecast: {str(e)}")

    async def get_top_items(self, unit_id: Optional[str] = None, limit: int = 100) -> List[str]:
        try:
            unit_filter = "AND \"Unit_Id\" = :unit_id" if unit_id else ""
            params = {"unit_id": unit_id} if unit_id else {}
            
            q = text(f"""
                SELECT "Item_Name" FROM "AIL_Monthly_Total_Item" 
                WHERE "Type" = 'Forecasted'
                {unit_filter}
                ORDER BY "numDeliveryQtyMT" DESC LIMIT :limit
            """)
            
            result = await self.db.execute(q, {**params, "limit": limit})
            rows = result.fetchall()
            # Deduplicate
            return list(dict.fromkeys([row[0] for row in rows]))
        except Exception as e:
            raise DatabaseError(f"Error fetching top items: {str(e)}")

    async def get_item_data_bulk(self, item_names: List[str], unit_id: Optional[str] = None):
        if not item_names:
            return []
            
        try:
            unit_filter = "AND \"Unit_Id\" = :unit_id" if unit_id else ""
            params = {"unit_id": unit_id} if unit_id else {}
            
            # safe expansion:
            q = text(f"""
                SELECT "Item_Name", 
                       CASE WHEN "Date" < date_trunc('month', CURRENT_DATE) THEN 'Historical' ELSE "Type" END as "Type",
                       TO_CHAR("Date", 'YYYY-MM') as month, 
                       SUM("numDeliveryQtyMT") as qty
                FROM "AIL_Monthly_Total_Item" 
                WHERE "Item_Name" = ANY(:names)
                {unit_filter}
                AND "Date" >= '2022-01-01'
                AND "Date" <= '2026-12-31'
                AND "Date" IS NOT NULL
                GROUP BY 1, 2, 3
                ORDER BY 3 ASC
            """)
            
            result = await self.db.execute(q, {**params, "names": item_names})
            return result.fetchall()
        except Exception as e:
            raise DatabaseError(f"Error fetching item data bulk: {str(e)}")

    async def get_top_territories(self, unit_id: Optional[str] = None, limit: int = 100) -> List[str]:
         # Similar to items
         try:
            unit_filter = "AND \"Unit_Id\" = :unit_id" if unit_id else ""
            params = {"unit_id": unit_id} if unit_id else {}
            
            q = text(f"""
                SELECT "Territory" FROM "AIL_Monthly_Total_Final_Territory"
                WHERE "Type" = 'Forecasted'
                {unit_filter}
                ORDER BY "numDeliveryQtyMT" DESC LIMIT :limit
            """)
            
            result = await self.db.execute(q, {**params, "limit": limit})
            rows = result.fetchall()
            return list(dict.fromkeys([row[0] for row in rows]))
         except Exception:
             return []

    async def get_territory_data_bulk(self, terr_names: List[str], unit_id: Optional[str] = None):
        if not terr_names: return []
        try:
            unit_filter = "AND \"Unit_Id\" = :unit_id" if unit_id else ""
            params = {"unit_id": unit_id} if unit_id else {}
            
            q = text(f"""
                SELECT "Territory", 
                       CASE WHEN "Date" < date_trunc('month', CURRENT_DATE) THEN 'Historical' ELSE "Type" END as "Type",
                       TO_CHAR("Date", 'YYYY-MM') as month, 
                       SUM("numDeliveryQtyMT") as qty
                FROM "AIL_Monthly_Total_Final_Territory"
                WHERE "Territory" = ANY(:names)
                {unit_filter}
                AND "Date" >= '2022-01-01'
                AND "Date" <= '2026-12-31'
                AND "Date" IS NOT NULL
                GROUP BY 1, 2, 3
                ORDER BY 3 ASC
            """)
            
            result = await self.db.execute(q, {**params, "names": terr_names})
            return result.fetchall()
        except Exception:
            return []
