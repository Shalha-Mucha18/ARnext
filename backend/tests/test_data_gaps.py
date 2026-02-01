
import pytest
from unittest.mock import AsyncMock, MagicMock, ANY
from app.api.v1.endpoints.sales import get_monthly_summary
from app.api.v1.endpoints.analytics import get_credit_sales_ratio
from app.services.sales_service import SalesService
from app.services.analytics_service import AnalyticsService

@pytest.mark.asyncio
async def test_monthly_summary_yearly_average():
    # Mock Service
    mock_service = AsyncMock(spec=SalesService)
    
    # Mock return data
    mock_data = {
        "month": "Monthly Average (2025)",
        "total_revenue": 5000.0,
        "total_orders": 100
    }
    mock_service.get_monthly_summary.return_value = mock_data

    # Call Endpoint with Year
    response = await get_monthly_summary(
        month=None,
        year=2025,
        unit_id="UNIT001", 
        service=mock_service
    )
    
    # Verify Service Call
    mock_service.get_monthly_summary.assert_called_once_with(None, 2025, "UNIT001")
    
    # Verify Response
    assert response.data == mock_data

@pytest.mark.asyncio
async def test_credit_ratio_yearly():
    # Mock Service
    mock_service = AsyncMock(spec=AnalyticsService)
    
    # Mock return data
    mock_data = {
        "month": "2025",
        "total_revenue": 120000,
        "credit": {"percentage": 60.0},
        "cash": {"percentage": 40.0}
    }
    mock_service.get_credit_ratio.return_value = mock_data

    # Call Endpoint with Year
    response = await get_credit_sales_ratio(
        unit_id=1, 
        month=None,
        year=2025,
        generate_insights=False,
        service=mock_service,
        core=MagicMock()
    )
    
    # Verify Service Call
    mock_service.get_credit_ratio.assert_called_once_with(1, None, 2025, False, ANY)
    
    # Verify Response
    assert response.data == mock_data
