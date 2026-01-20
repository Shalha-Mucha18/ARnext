"""
Regional and territory-related Pydantic schemas.
"""
from pydantic import BaseModel
from typing import Optional, List

class RegionData(BaseModel):
    """Regional data."""
    name: str
    quantity: float
    orders: int
    uom: Optional[str] = "MT"
    percentage: Optional[float] = None

class RegionContributionResponse(BaseModel):
    """Regional contribution response."""
    top_regions: List[RegionData]
    bottom_regions: List[RegionData]
    total_volume: float

class TerritoryData(BaseModel):
    """Territory data."""
    name: str
    quantity: float
    orders: int

class TerritoryPerformanceResponse(BaseModel):
    """Territory performance response."""
    top_territories: List[TerritoryData]
    bottom_territories: List[TerritoryData]

class AreaData(BaseModel):
    """Area data."""
    name: str
    quantity: float
    orders: int
    uom: Optional[str] = "MT"
    percentage: Optional[float] = None

class AreaInsightsResponse(BaseModel):
    """Area insights response."""
    top_areas: List[AreaData]
    bottom_areas: List[AreaData]
    total_volume: float
