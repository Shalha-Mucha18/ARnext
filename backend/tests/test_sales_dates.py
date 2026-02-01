
import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock
from app.api.v1.endpoints.sales import get_ytd_sales, get_sales_metrics
from app.services.sales_service import SalesService

# Define a mock YTDResponse class that matches the Pydantic schema
class MockYTDResponse:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def dict(self):
        return self.__dict__

@pytest.mark.asyncio
async def test_ytd_sales_with_year():
    # Mock Service
    mock_service = AsyncMock(spec=SalesService)
    
    # Mock return data
    mock_data = {
        "current_ytd": {"total_revenue": 1000},
        "last_ytd": {"total_revenue": 800},
        "growth_metrics": {"revenue_growth_pct": 25.0},
        "comparison_date": date(2023, 12, 31)
    }
    mock_service.get_ytd_comparison.return_value = mock_data

    # Call Endpoint
    response = await get_ytd_sales(
        unit_id="UNIT001", 
        fiscal_year=False, 
        year=2023, 
        month=12,
        sales_service=mock_service
    )
    
    # Verify Service Call
    mock_service.get_ytd_comparison.assert_called_once_with("UNIT001", False, 2023, 12)
    
    # Verify Response
    assert response.data == mock_data

@pytest.mark.asyncio
async def test_sales_metrics_with_year():
    # Mock Service
    mock_service = AsyncMock(spec=SalesService)
    
    # Mock return data
    mock_data = {
        "current_month": {"qty": 500},
        "sales_trend": [{"month": "2023-12", "qty": 500}]
    }
    mock_service.get_sales_metrics.return_value = mock_data

    # Call Endpoint
    response = await get_sales_metrics(
        unit_id="UNIT001", 
        year=2023, 
        month=12,
        service=mock_service
    )
    
    # Verify Service Call
    mock_service.get_sales_metrics.assert_called_once_with("UNIT001", 2023, 12)
    
    # Verify Response
    assert response.data == mock_data
