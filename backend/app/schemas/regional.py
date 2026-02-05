from typing import List, Optional
from pydantic import BaseModel

class TerritoryMetric(BaseModel):
    name: str = "Unknown"
    quantity: float
    orders: int
    uom: str
    quantity_percentage: float
    mom_percentage: Optional[float] = None  
    yo_percentage: Optional[float] = None

class RegionalResponse(BaseModel):
    top_territories: List[TerritoryMetric]
    bottom_territories: List[TerritoryMetric]
    total_volume: float
