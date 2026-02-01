from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.utils.exceptions import DatabaseError

class UnitsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_units(self) -> List[Dict[str, str]]:
        try:
            # Join with dim_business_unit to get proper business unit names
            query = text("""
                SELECT DISTINCT 
                    d."unit_id" as unit_id,
                    COALESCE(b."strBusinessUnitName", 'Unit ' || d."unit_id") as business_unit_name
                FROM tbldeliveryinfo d
                LEFT JOIN dim_business_unit b ON d."unit_id" = b."Unit_Id"
                WHERE d."unit_id" IS NOT NULL
                ORDER BY d."unit_id"
                LIMIT 50
            """)
            
            result = await self.db.execute(query)
            rows = result.fetchall()
            
            return [
                {"unit_id": str(row.unit_id), "business_unit_name": row.business_unit_name}
                for row in rows
            ]
        except Exception as e:
            try:
                q2 = text('SELECT DISTINCT "unit_id" FROM tbldeliveryinfo WHERE "unit_id" IS NOT NULL ORDER BY "unit_id"')
                res2 = await self.db.execute(q2)
                return [{"unit_id": str(r.unit_id), "business_unit_name": f"Unit {r.unit_id}"} for r in res2.fetchall()]
            except Exception:
                raise DatabaseError(f"Error fetching units: {str(e)}")
