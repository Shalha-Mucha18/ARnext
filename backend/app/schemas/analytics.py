from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel

class TopCustomer(BaseModel):
    name: str
    uom: str
    quantity: float
    orders: int
    percentage: float

class TopCustomersResponse(BaseModel):
    top_customers: List[TopCustomer]
    error: Optional[str] = None

class CreditRatioMetric(BaseModel):
    order_count: int
    revenue: float
    percentage: float

class CreditRatioResponse(BaseModel):
    month: str
    credit: CreditRatioMetric
    cash: CreditRatioMetric
    both: CreditRatioMetric
    other: CreditRatioMetric
    total_revenue: float
    total_orders: int
    ai_insights: Optional[str] = None

class ChannelCreditMetric(BaseModel):
    channel_name: str
    revenue: float
    percentage_within_type: float

class ChannelCreditResponse(BaseModel):
    data: Dict[str, List[ChannelCreditMetric]]
    total_credit: float
    total_cash: float
    total_both: float

class ConcentrationCustomer(BaseModel):
    name: str
    quantity: float
    percentage: float

class ConcentrationResponse(BaseModel):
    concentration_ratio: float
    total_quantity: float
    top_10_quantity: float
    top_10_customers: List[ConcentrationCustomer]
    month: Optional[str] = None
    insights: Optional[str] = None
    generated_at: Optional[str] = None
