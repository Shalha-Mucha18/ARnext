"""
Sales-related Pydantic schemas.
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from .common import MetricsBase

class YtdMetrics(MetricsBase):
    """Year-to-date metrics."""
    period: str
    year: int
    period_start: str
    period_end: str
    total_revenue: Optional[float] = None

class GrowthMetrics(BaseModel):
    """Growth metrics comparison."""
    order_growth_pct: float
    quantity_growth_pct: float
    revenue_growth_pct: Optional[float] = None
    order_change: int
    quantity_change: float
    revenue_change: Optional[float] = None

class YtdSalesResponse(BaseModel):
    """YTD sales response."""
    business_unit_name: str
    current_ytd: YtdMetrics
    last_ytd: YtdMetrics
    growth_metrics: GrowthMetrics
    comparison_date: str

class MtdMetrics(MetricsBase):
    """Month-to-date metrics."""
    month: str
    year: int

class MtdStatsResponse(BaseModel):
    """MTD stats response."""
    current_month: MtdMetrics
    previous_month: MtdMetrics
    growth: GrowthMetrics

class SalesMetricsMonth(BaseModel):
    """Sales metrics for a specific month."""
    month: str
    order_count: int
    qty: float
    revenue: float

class SalesMetricsResponse(BaseModel):
    """Sales metrics response."""
    current_month: SalesMetricsMonth
    last_12_months: List[SalesMetricsMonth]

class CreditSalesData(BaseModel):
    """Credit sales data."""
    percentage: float
    revenue: float
    order_count: int

class CreditSalesRatioResponse(BaseModel):
    """Credit sales ratio response."""
    month: str
    credit: CreditSalesData
    cash: CreditSalesData
    both: CreditSalesData
    other: CreditSalesData
    total_revenue: float

class CustomerData(BaseModel):
    """Customer data."""
    name: str
    quantity: float
    percentage: float

class ConcentrationRiskResponse(BaseModel):
    """Concentration risk response."""
    concentration_ratio: float
    top_10_customers: List[CustomerData]
    total_quantity: float

class InsightsResponse(BaseModel):
    """AI insights response."""
    insights: str
    generated_at: Optional[str] = None
    performance_status: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
