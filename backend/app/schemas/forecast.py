"""
Forecast-related Pydantic schemas.
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class ForecastChartPoint(BaseModel):
    """Forecast chart data point."""
    month: str
    actual: Optional[float] = None
    forecast: Optional[float] = None

class ForecastResponse(BaseModel):
    """Forecast response."""
    global_chart: List[ForecastChartPoint]
    items_charts: List[Dict[str, Any]]
    territories_charts: List[Dict[str, Any]]
