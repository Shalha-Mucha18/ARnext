from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel

class ChartPoint(BaseModel):
    month: str
    actual: Optional[float] = None
    forecast: Optional[float] = None

class ForecastChart(BaseModel):
    name: str
    chart: List[ChartPoint]

class ForecastResponse(BaseModel):
    global_chart: List[ChartPoint]
    items_charts: List[ForecastChart]
    territories_charts: List[ForecastChart]
    unit_id: Optional[str] = None

class ForecastInsightsResponse(BaseModel):
    insights: str
    generated_at: Optional[str] = None
