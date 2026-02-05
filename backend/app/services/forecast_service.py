from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.forecast_repository import ForecastRepository
from app.schemas.forecast import ForecastChart, ChartPoint, ForecastResponse
from app.utils.exceptions import ValidationError
from starlette.concurrency import run_in_threadpool
from collections import defaultdict

class ForecastService:
    def __init__(self, db: AsyncSession):
        self.repository = ForecastRepository(db)

    async def get_sales_forecast(self, unit_id: Optional[str] = None) -> ForecastResponse:
        if not unit_id:
            return ForecastResponse(
                global_chart=[],
                items_charts=[],
                territories_charts=[],
                unit_id=None
            )

        # Ensure unit_id is int if possible
        unit_id_val = None
        if unit_id:
            try:
                unit_id_val = int(unit_id)
            except ValueError:
                pass

        # 1. Global Chart
        global_data = await self.repository.get_global_forecast(unit_id_val)
        global_chart = self._merge_data(global_data["actuals"], global_data["forecast"])
        
        # 2. Items Charts
        top_items = await self.repository.get_top_items(unit_id_val, limit=50) # Limit reasonable number
        items_chart_data = []
        if top_items:
            bulk_item_data = await self.repository.get_item_data_bulk(top_items, unit_id_val)
            # Organize by Item
            item_map = defaultdict(lambda: {"actuals": [], "forecast": []})
            for row in bulk_item_data:
                # Row: name, type, month, qty
                name, row_type, month, qty = row[0], row[1], row[2], float(row[3] or 0)
                if row_type == 'Historical':
                    item_map[name]["actuals"].append((month, qty))
                else:
                    item_map[name]["forecast"].append((month, qty))
            
            for name in top_items:
                if name in item_map:
                    merged = self._merge_data(item_map[name]["actuals"], item_map[name]["forecast"])
                    items_chart_data.append(ForecastChart(name=name, chart=merged))
        
        # 3. Territories Charts
        top_terrs = await self.repository.get_top_territories(unit_id_val, limit=50)
        terrs_chart_data = []
        if top_terrs:
            bulk_terr_data = await self.repository.get_territory_data_bulk(top_terrs, unit_id_val)
            terr_map = defaultdict(lambda: {"actuals": [], "forecast": []})
            for row in bulk_terr_data:
                name, row_type, month, qty = row[0], row[1], row[2], float(row[3] or 0)
                if row_type == 'Historical':
                    terr_map[name]["actuals"].append((month, qty))
                else:
                    terr_map[name]["forecast"].append((month, qty))
            
            for name in top_terrs:
                 if name in terr_map:
                    merged = self._merge_data(terr_map[name]["actuals"], terr_map[name]["forecast"])
                    terrs_chart_data.append(ForecastChart(name=name, chart=merged))

        return ForecastResponse(
            global_chart=global_chart,
            items_charts=items_chart_data,
            territories_charts=terrs_chart_data,
            unit_id=unit_id
        )

    def _merge_data(self, actual_rows: List, forecast_rows: List) -> List[ChartPoint]:
        data_map = {}
        
        # Track the last actual point to stitch the lines
        last_actual_month = None
        last_actual_qty = None
        
        # Ensure actuals are sorted to find the true last point
        sorted_actuals = sorted(actual_rows, key=lambda x: x[0])
        
        for row in sorted_actuals:
            m, qty = row[0], float(row[1] or 0)
            data_map[m] = {"month": m, "actual": qty, "forecast": None}
            last_actual_month = m
            last_actual_qty = qty
            
        # Process Forecasts
        for row in forecast_rows:
            m, qty = row[0], float(row[1] or 0)
            if m in data_map:
                data_map[m]["forecast"] = qty 
            else:
                data_map[m] = {"month": m, "actual": None, "forecast": qty}
        
        if last_actual_month and last_actual_qty is not None:
            if data_map[last_actual_month]["forecast"] is None:
                 data_map[last_actual_month]["forecast"] = last_actual_qty
        
        sorted_keys = sorted(data_map.keys())
        return [ChartPoint(**data_map[k]) for k in sorted_keys]

    async def generate_insights(self, unit_id: Optional[str], core_engine: Any) -> Dict[str, Any]:
        # Generating insights with auto-reload check
        if not core_engine:
            return {"analysis": "AI Engine unavailable"}

        if not unit_id:
            return {"analysis": "Please select a Business Unit to view forecast insights."}
            
        # Ensure unit_id is int if possible
        unit_id_val = None
        if unit_id:
            try:
                unit_id_val = int(unit_id)
            except ValueError:
                pass
        
        # 1. Fetch Forecast Data
        repo_data = await self.repository.get_global_forecast(unit_id_val)
        forecast_rows = repo_data["forecast"]
        total_forecast = [{"month": r[0], "qty": float(r[1])} for r in forecast_rows]
        

        top_items_names = await self.repository.get_top_items(unit_id_val, limit=5)
        top_territories_names = await self.repository.get_top_territories(unit_id_val, limit=5)
        
        top_items = []
        if top_items_names:
            bulk_item = await self.repository.get_item_data_bulk(top_items_names, unit_id_val)
            # Aggregate per item
            item_agg = defaultdict(float)
            for row in bulk_item:
                 if row[1] == 'Forecast': # Type
                     item_agg[row[0]] += float(row[3] or 0)
            top_items = [{"name": k, "qty": v} for k, v in item_agg.items()]
            top_items.sort(key=lambda x: x['qty'], reverse=True)
            
        top_territories = []
        if top_territories_names:
            bulk_terr = await self.repository.get_territory_data_bulk(top_territories_names, unit_id_val)
            terr_agg = defaultdict(float)
            for row in bulk_terr:
                 if row[1] == 'Forecast':
                     terr_agg[row[0]] += float(row[3] or 0)
            top_territories = [{"name": k, "qty": v} for k, v in terr_agg.items()]
            top_territories.sort(key=lambda x: x['qty'], reverse=True)

        # 3. Call AI Core
        return await run_in_threadpool(
            core_engine.analyze_forecast_ceo,
            total_forecast, top_items, top_territories
        ) 
