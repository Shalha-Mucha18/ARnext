from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.utils import get_uom_conversion_sql
from app.utils.exceptions import DatabaseError
from dateutil.relativedelta import relativedelta

class RegionalRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_territory_performance(
        self,
        start_date: Any,
        end_date: Any,
        unit_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get top 10 and bottom 10 territories by volume.
        """
        try:
            print(f"DEBUG: Executing get_territory_performance, start={start_date}, end={end_date}")
            data = await self._get_aggregated_performance("territory", start_date, end_date, unit_id)
            
            # Map keys to match existing schema
            # Helper returns 'top_territorys' (dumb pluralization), we need 'top_territories'
            # Helper items have 'percentage', we need 'quantity_percentage'
            
            def map_items(items):
                mapped = []
                for item in items:
                    # Create new dict to avoid mutation issues
                    mapped_item = {
                        "name": item["name"],
                        "uom": item["uom"],
                        "quantity": item["quantity"],
                        "orders": item["orders"],
                        "quantity_percentage": item.get("percentage", 0),
                        "mom_percentage": item.get("mom_percentage"),  # Preserve MoM
                        "yo_percentage": item.get("yo_percentage")      # Preserve YoY
                    }
                    mapped.append(mapped_item)
                return mapped

            return {
                "top_territories": map_items(data.get("top_territorys", [])),
                "bottom_territories": map_items(data.get("bottom_territorys", [])),
                "total_volume": data.get("total_volume", 0),
                "all_count": len(data.get("top_territorys", [])) + len(data.get("bottom_territorys", []))
            }

        except Exception as e:
            raise DatabaseError(f"Error fetching territory performance: {str(e)}")

    async def get_region_performance(self, start_date: Any, end_date: Any, unit_id: Optional[int] = None) -> Dict[str, Any]:
        """Get top regions by volume."""
        return await self._get_aggregated_performance("region", start_date, end_date, unit_id)

    async def get_area_performance(self, start_date: Any, end_date: Any, unit_id: Optional[int] = None) -> Dict[str, Any]:
        """Get top areas by volume."""
        return await self._get_aggregated_performance("area", start_date, end_date, unit_id)

    async def _get_aggregated_performance(self, group_col: str, start_date: Any, end_date: Any, unit_id: Optional[int] = None) -> Dict[str, Any]:
        try:
            uom_sql = get_uom_conversion_sql()
            unit_clause = "AND unit_id = :unit_id" if unit_id is not None else ""
            
            query = text(f"""
                WITH sales AS (
                    SELECT
                        COALESCE({group_col}, 'Unknown') as name,
                        CASE
                            WHEN unit_id IN (4, 144, 188, 189, 232) THEN 'MT'
                            WHEN base_uom IN ('Metric Tons', 'Metric Ton', 'MT', 'Ton') THEN 'MT'
                            ELSE base_uom
                        END AS uom_shown,
                        SUM({uom_sql}) AS total_quantity,
                        COUNT(*) AS total_orders
                    FROM tbldeliveryinfo
                    WHERE delivery_date >= :start_date
                      AND delivery_date < :end_date
                      AND delivery_date IS NOT NULL
                      {unit_clause}
                    GROUP BY
                        {group_col},
                        CASE
                            WHEN unit_id IN (4, 144, 188, 189, 232) THEN 'MT'
                            WHEN base_uom IN ('Metric Tons', 'Metric Ton', 'MT', 'Ton') THEN 'MT'
                            ELSE base_uom
                        END
                ),
                total_vol AS (
                    SELECT SUM(total_quantity) as grand_total FROM sales
                )
                SELECT
                    s.name,
                    COALESCE(s.uom_shown, 'MT') as uom,
                    ROUND(s.total_quantity::numeric, 2) as quantity,
                    s.total_orders,
                    ROUND((s.total_quantity / NULLIF(v.grand_total, 0) * 100)::numeric, 2) as pct
                FROM sales s, total_vol v
                ORDER BY s.total_quantity DESC
            """)
            
            params = {"start_date": start_date, "end_date": end_date}
            if unit_id is not None: params["unit_id"] = unit_id
            
            result = await self.db.execute(query, params)
            rows = result.fetchall()
            items = []
            for row in rows:
                items.append({
                    "name": row.name,
                    "uom": str(row.uom),
                    "quantity": float(row.quantity or 0),
                    "orders": int(row.total_orders),
                    "percentage": float(row.pct or 0),
                    "mom_percentage": None, # Default
                    "yo_percentage": None   # Default
                })

            # MOM: Previous Month
            # YOT: Same Period Last Year
            
            # Ensure dates are datetime.date objects
            if not hasattr(start_date, 'year'):
                pass

            prev_month_start = start_date - relativedelta(months=1)
            prev_month_end = start_date
            
            sply_start = start_date - relativedelta(years=1)
            sply_end = end_date - relativedelta(years=1)

            # Get names for filtering 
            if items:
                names = [item["name"] for item in items]
                
                async def fetch_volumes(s_date, e_date, entity_names):
                    if not entity_names: return {}
                    
                    # Build IN clause with individual parameters to avoid ANY array binding issues
                    placeholders = ', '.join([f':name_{i}' for i in range(len(entity_names))])
                    
                    q = text(f"""
                        SELECT 
                            COALESCE({group_col}, 'Unknown') as name,
                            SUM({uom_sql}) as volume
                        FROM tbldeliveryinfo
                        WHERE delivery_date >= :s_date
                          AND delivery_date < :e_date
                          AND {group_col} IN ({placeholders})
                          {unit_clause}
                        GROUP BY {group_col}
                    """)
                    
                    p = {
                        "s_date": s_date, 
                        "e_date": e_date,
                    }
                    # Add individual name parameters
                    for i, name in enumerate(entity_names):
                        p[f"name_{i}"] = name
                    
                    if unit_id is not None: p["unit_id"] = unit_id
                    
                    r = await self.db.execute(q, p)
                    return {row.name: float(row.volume or 0) for row in r.fetchall()}

                # Fetch comparison data
                print(f"DEBUG: Fetching prev month volumes for {len(names)} entities: {names[:3]}...")
                prev_month_vols = await fetch_volumes(prev_month_start, prev_month_end, names)
                print(f"DEBUG: Found {len(prev_month_vols)} prev month results: {dict(list(prev_month_vols.items())[:2])}")
                
                sply_vols = await fetch_volumes(sply_start, sply_end, names)
                print(f"DEBUG: Found {len(sply_vols)} SPLY results")
                
                # Calculate Growth
                for item in items:
                    name = item["name"]
                    curr_vol = item["quantity"]
                    
                    # MOM
                    prev_vol = prev_month_vols.get(name, 0)
                    if prev_vol > 0:
                        growth = ((curr_vol - prev_vol) / prev_vol) * 100
                        item["mom_percentage"] = growth
                        print(f"DEBUG: {name} MOM: {curr_vol} vs {prev_vol} = {growth:.1f}%")
                    else:
                        item["mom_percentage"] = None 
                        print(f"DEBUG: {name} MOM: n/a (prev_vol={prev_vol})")
                        
                    # YOT (YOY)
                    last_year_vol = sply_vols.get(name, 0)
                    if last_year_vol > 0:
                        growth = ((curr_vol - last_year_vol) / last_year_vol) * 100
                        item["yo_percentage"] = growth
                    else:
                        item["yo_percentage"] = None

            return {
                f"top_{group_col.replace('str', '').lower()}s": items[:10],
                f"bottom_{group_col.replace('str', '').lower()}s": items[-10:] if len(items) > 10 else [],
                "total_volume": sum(x["quantity"] for x in items)
            }
        except Exception as e:
            raise DatabaseError(f"Error aggregating {group_col}: {str(e)}")
