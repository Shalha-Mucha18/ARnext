from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from datetime import date

class GrowthMetrics(BaseModel):
    order_growth_pct: float
    quantity_growth_pct: float
    quantity_change: float

class YTDMetrics(BaseModel):
    total_orders: int
    total_quantity: float
    period_start: date
    period_end: date
    # Optional fields for UI display
    business_unit_name: Optional[str] = None
    uom: Optional[str] = "MT"

class YTDResponse(BaseModel):
    current_ytd: YTDMetrics
    last_ytd: YTDMetrics
    growth_metrics: GrowthMetrics
    business_unit_name: Optional[str] = None
    comparison_date: date

class TrendPoint(BaseModel):
    month: str
    order_count: int
    qty: float

class SalesTrendResponse(BaseModel):
    trend_data: List[TrendPoint]
    analysis: Optional[Dict] = None

class MonthlyMetricsResponse(BaseModel):
    current_month: Dict
    previous_month: Dict
    growth_metrics: Dict
