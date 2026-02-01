from typing import Optional, Dict, Any
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.sales_repository import SalesRepository
from app.utils.exceptions import ValidationError

class SalesService:
    def __init__(self, db: AsyncSession):
        self.repository = SalesRepository(db)

    async def get_ytd_comparison(
        self, 
        unit_id: Optional[str] = None, 
        fiscal_year: bool = False,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Calculate YTD growth metrics comparing current period vs last year.
        Handles fiscal year logic (July-June) vs Calendar year.
        """
        # Convert unit_id to int if present, handle potential invalid input
        unit_id_int = None
        if unit_id:
            if unit_id.lower() == "null" or unit_id == "":
                unit_id_int = None
            else:
                try:
                    unit_id_int = int(unit_id)
                except ValueError:
                        pass


        today = date.today()
        # Use provided year or default to current year
        target_year = year if year else today.year
        
        # YTD always means: January 1 → Today (or Dec 31 for past years)
        if target_year < today.year:
            # Past year: Jan 1 → Dec 31 of that year
            compare_date = date(target_year, 12, 31)
        elif target_year == today.year:
            # Current year: Jan 1 → Today
            compare_date = today
        else:
            # Future year: Jan 1 → Jan 1 (empty range)
            compare_date = date(target_year, 1, 1)

        # Calculate start dates based on fiscal year setting
        if fiscal_year:
            # Fiscal year: July 1 → June 30
            if compare_date.month < 7:
                current_start = date(compare_date.year - 1, 7, 1)
                last_start = date(compare_date.year - 2, 7, 1)
            else:
                current_start = date(compare_date.year, 7, 1)
                last_start = date(compare_date.year - 1, 7, 1)
        else:
            # Calendar year: Jan 1 → Dec 31
            current_start = date(compare_date.year, 1, 1)
            last_start = date(compare_date.year - 1, 1, 1)
            
        current_end = compare_date
        
  
        try:
            if fiscal_year and compare_date.month < 7:
                 last_end_year = last_start.year + 1
            else:
                 last_end_year = last_start.year
            
            last_end = date(last_end_year, compare_date.month, compare_date.day)
        except ValueError: # Handle leap years (Feb 29)
            last_end = date(last_end_year, 2, 28)
        
        # Fetch Data
        current_data = await self.repository.get_metrics_by_date_range(current_start, current_end, unit_id_int)
        last_data = await self.repository.get_metrics_by_date_range(last_start, last_end, unit_id_int)
        
        # Calculate Growth
        growth = self._calculate_growth(current_data, last_data)
        
        return {
            "current_ytd": {**current_data, "period_start": current_start, "period_end": current_end},
            "last_ytd": {**last_data, "period_start": last_start, "period_end": last_end},
            "growth_metrics": growth,
            "comparison_date": compare_date
        }

    def _calculate_growth(self, current: Dict, last: Dict) -> Dict:
        """Calculate percentage growth safely"""
        def calc_pct(curr, prev):
            return ((curr - prev) / prev * 100) if prev > 0 else 0.0
            
        return {
            "order_growth_pct": calc_pct(current["total_orders"], last["total_orders"]),
            "quantity_growth_pct": calc_pct(current["total_quantity"], last["total_quantity"]),
            "quantity_change": current["total_quantity"] - last["total_quantity"]
        }

    async def get_mtd_stats(
        self,
        unit_id: Optional[str] = None,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> Dict[str, Any]:
        
        # Unit ID
        unit_id_int = None
        if unit_id:
             try: unit_id_int = int(unit_id)
             except: pass
        
        today = date.today()
        target_year = year if year else today.year
        target_month = month if month else today.month
        
        curr_start = date(target_year, target_month, 1)
        
        if target_month == 12:
            curr_end = date(target_year + 1, 1, 1)
        else:
            curr_end = date(target_year, target_month + 1, 1)
        if target_month == 1:
            prev_start = date(target_year - 1, 12, 1)
            prev_month_end_limit = date(target_year, 1, 1) # Start of Jan (Target)
        else:
            prev_start = date(target_year, target_month - 1, 1)
            prev_month_end_limit = date(target_year, target_month, 1) # Start of Target Month

        # Standard full-month previous end
        prev_end = prev_month_end_limit

    
        if target_year == today.year and target_month == today.month:
             from datetime import timedelta
             same_day_end = prev_start + timedelta(days=today.day)
             if same_day_end < prev_month_end_limit:
                 prev_end = same_day_end
        
        # Fetch data
        current = await self.repository.get_mtd_stats(curr_start, curr_end, unit_id_int)
        previous = await self.repository.get_mtd_stats(prev_start, prev_end, unit_id_int)
        
        # Calculate Growth
        qty_growth = ((current["delivery_qty"] - previous["delivery_qty"]) / previous["delivery_qty"] * 100) if previous["delivery_qty"] > 0 else 0.0
        orders_growth = ((current["total_orders"] - previous["total_orders"]) / previous["total_orders"] * 100) if previous["total_orders"] > 0 else 0.0
        
        return {
            "current_month": {**current, "year": target_year, "month": target_month},
            "previous_month": {**previous},
            "growth": {
                "delivery_qty_pct": qty_growth,
                "orders_pct": orders_growth
            }
        }

    async def get_sales_metrics(
        self, 
        unit_id: Optional[str] = None,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Exec View Metrics: Current Month stats + 12 Month Trend
        """
        unit_id_int = None
        if unit_id:
             try: unit_id_int = int(unit_id)
             except: pass
        
        today = date.today()
        target_year = year if year else today.year
        target_month = month if month else today.month
        
        start = date(target_year, target_month, 1)
        if target_month == 12: end = date(target_year + 1, 1, 1)
        else: end = date(target_year, target_month + 1, 1)
        
        
        # Trend needs to end at the selected month
        import calendar
        last_day = calendar.monthrange(target_year, target_month)[1]
        trend_cutoff = date(target_year, target_month, last_day)

        current = await self.repository.get_mtd_stats(start, end, unit_id_int)
        trend = await self.repository.get_monthly_trend(unit_id_int, end_date=trend_cutoff)
        
        return {
            "current_month": {
                "month": start.strftime("%B"),
                "order_count": current["total_orders"],
                "qty": current["delivery_qty"]
            },
            "sales_trend": trend
        }

    async def get_monthly_summary(
        self, 
        month: Optional[int] = None, 
        year: Optional[int] = None,
        unit_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Summary for a month OR yearly average if only year provided.
        """
        unit_id_int = unit_id
             
        try:
             # Case 1: Specific Month Selected
             if month:
                 target_year = year if year else date.today().year
                 target = date(target_year, month, 1)
                 return await self.repository.get_monthly_summary(unit_id_int, target)
             
             # Case 2: Year Selected (Yearly Average)
             elif year:
                 return await self.repository.get_yearly_monthly_average(unit_id_int, year)
             
             # Case 3: Default to Current Month
             else: 
                 today = date.today()
                 target = date(today.year, today.month, 1)
                 return await self.repository.get_monthly_summary(unit_id_int, target)
                 
        except:
             return {}
