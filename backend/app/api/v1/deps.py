from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.sales_service import SalesService
from app.services.regional_service import RegionalService

async def get_sales_service(
    db: AsyncSession = Depends(get_db)
) -> SalesService:
    """Dependency for SalesService"""
    return SalesService(db)

async def get_regional_service(
    db: AsyncSession = Depends(get_db)
) -> RegionalService:
    """Dependency for RegionalService"""
    return RegionalService(db)

from app.services.analytics_service import AnalyticsService
async def get_analytics_service(
    db: AsyncSession = Depends(get_db)
) -> AnalyticsService:
    return AnalyticsService(db)
