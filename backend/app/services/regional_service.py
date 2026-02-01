from typing import Optional, Dict, Any
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.regional_repository import RegionalRepository
from app.utils.exceptions import ValidationError

class RegionalService:
    def __init__(self, db: AsyncSession):
        self.repository = RegionalRepository(db)

    async def get_territory_performance(
        self,
        unit_id: Optional[int] = None,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get top territories performance for a specific period.
        """
        start_date, end_date = self._get_date_range(year, month)
        return await self.repository.get_territory_performance(start_date, end_date, unit_id)

    async def get_regional_contribution(
        self,
        unit_id: Optional[int] = None,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> Dict[str, Any]:
        start_date, end_date = self._get_date_range(year, month)
        return await self.repository.get_region_performance(start_date, end_date, unit_id)

    async def get_area_performance(
        self,
        unit_id: Optional[int] = None,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> Dict[str, Any]:
        start_date, end_date = self._get_date_range(year, month)
        return await self.repository.get_area_performance(start_date, end_date, unit_id)

    def _get_date_range(self, year: Optional[int], month: Optional[int]):
        # Date Logic (replicated from api_legacy.py)
        today = date.today()

        if year and month:
            start_date = date(year, month, 1)
            # End date is start of next month
            if month == 12:
                end_date = date(year + 1, 1, 1)
            else:
                end_date = date(year, month + 1, 1)
        elif year:
            start_date = date(year, 1, 1)
            end_date = date(year + 1, 1, 1)
        elif month:
            start_date = date(today.year, month, 1)
            if month == 12:
                end_date = date(today.year + 1, 1, 1)
            else:
                end_date = date(today.year, month + 1, 1)
        else:
            # Current Month default
            start_date = today.replace(day=1)
            if start_date.month == 12:
                end_date = date(start_date.year + 1, 1, 1)
            else:
                end_date = date(start_date.year, start_date.month + 1, 1)
        
        return start_date, end_date
