from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.utils import get_uom_conversion_sql


class RFMRepository:
    """Repository for RFM analysis data access using tbldeliveryinfo"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_customer_transactions(
        self, 
        unit_id: Optional[int] = None,
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Fetch customer transaction data for RFM analysis from tbldeliveryinfo
        
        Args:
            unit_id: Optional business unit filter
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)
            
        Returns:
            DataFrame with customer_id, customer_name, delivery_date, monetary
        """
        # Get UOM conversion SQL for monetary calculation
        uom_sql = get_uom_conversion_sql()
        
        # Build unit filter
        unit_clause = "AND unit_id = :unit_id" if unit_id is not None else ""
        
        # Build date filters
        date_clauses = []
        if start_date:
            date_clauses.append("AND delivery_date >= :start_date")
        if end_date:
            date_clauses.append("AND delivery_date <= :end_date")
        date_clause = " ".join(date_clauses)
        
        query_str = f"""
        SELECT 
            customer_id,
            customer_name,
            delivery_date,
            {uom_sql} as monetary
        FROM tbldeliveryinfo
        WHERE delivery_date IS NOT NULL
          AND customer_id IS NOT NULL
          AND customer_name IS NOT NULL
          {unit_clause}
          {date_clause}
        ORDER BY customer_id, delivery_date
        """
        
        query = text(query_str)
        
        # Build parameters dict - convert string dates to date objects for asyncpg
        params = {}
        if unit_id is not None:
            params['unit_id'] = unit_id
        if start_date:
            # Convert string to date object
            params['start_date'] = datetime.fromisoformat(start_date).date()
        if end_date:
            params['end_date'] = datetime.fromisoformat(end_date).date()
        
        result = await self.db.execute(query, params)
        rows = result.fetchall()
        
        # Convert to DataFrame
        if not rows:
            return pd.DataFrame(columns=['customer_id', 'customer_name', 'delivery_date', 'monetary'])
        
        df = pd.DataFrame(rows, columns=['customer_id', 'customer_name', 'delivery_date', 'monetary'])
        # Ensure monetary is numeric (handle Decimals/Objects)
        df['monetary'] = pd.to_numeric(df['monetary'], errors='coerce').fillna(0.0)
        return df
    
    async def get_rfm_summary(
        self, 
        unit_id: Optional[int] = None,
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get summary statistics for RFM analysis"""
        unit_clause = "AND unit_id = :unit_id" if unit_id is not None else ""
        
        # Build date filters
        date_clauses = []
        if start_date:
            date_clauses.append("AND delivery_date >= :start_date")
        if end_date:
            date_clauses.append("AND delivery_date <= :end_date")
        date_clause = " ".join(date_clauses)
        
        query_str = f"""
        SELECT 
            COUNT(DISTINCT customer_id) as total_customers,
            COUNT(*) as total_transactions,
            SUM({get_uom_conversion_sql()}) as total_volume,
            MIN(delivery_date) as earliest_date,
            MAX(delivery_date) as latest_date
        FROM tbldeliveryinfo
        WHERE delivery_date IS NOT NULL
          AND customer_id IS NOT NULL
          {unit_clause}
          {date_clause}
        """
        
        query = text(query_str)
        
        params = {}
        if unit_id is not None:
            params['unit_id'] = unit_id
        if start_date:
            params['start_date'] = datetime.fromisoformat(start_date).date()
        if end_date:
            params['end_date'] = datetime.fromisoformat(end_date).date()
            
        if params:
            query = query.bindparams(**params)
        
        result = await self.db.execute(query)
        row = result.fetchone()
        
        if not row:
            return {
                'total_customers': 0,
                'total_transactions': 0,
                'total_volume': 0,
                'earliest_date': None,
                'latest_date': None
            }
        
        return {
            'total_customers': row[0] or 0,
            'total_transactions': row[1] or 0,
            'total_volume': float(row[2]) if row[2] else 0,
            'earliest_date': row[3].isoformat() if row[3] else None,
            'latest_date': row[4].isoformat() if row[4] else None
        }