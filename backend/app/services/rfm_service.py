from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.rfm_repository import RFMRepository
class RFMService:
    """Service for RFM analysis business logic"""
    
    def __init__(self, db: AsyncSession):
        self.repository = RFMRepository(db)
    
    def calculate_rfm(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate RFM metrics for all customers"""
        if df.empty:
            return pd.DataFrame()
        
        df['delivery_date'] = pd.to_datetime(df['delivery_date'])
        
        reference_date = df['delivery_date'].max() + timedelta(days=1)
        
        rfm_df = df.groupby(['customer_id', 'customer_name']).agg(
            Recency=('delivery_date', lambda x: (reference_date - x.max()).days),
            Frequency=('delivery_date', 'count'),
            Monetary=('monetary', 'sum')
        ).reset_index()
        
        # Calculate rank percentiles (normalized scores 0-100)
        rfm_df['R_rank_norm'] = rfm_df['Recency'].rank(pct=True, ascending=False) * 100
        rfm_df['F_rank_norm'] = rfm_df['Frequency'].rank(pct=True) * 100
        rfm_df['M_rank_norm'] = rfm_df['Monetary'].rank(pct=True) * 100
        
        # Calculate weighted RFM score (25% R, 30% F, 45% M) scaled to 0-5
        rfm_df['RFM_Score'] = (
            0.25 * rfm_df['R_rank_norm'] + 
            0.30 * rfm_df['F_rank_norm'] + 
            0.45 * rfm_df['M_rank_norm']
        ) * 0.05
        
        # Assign segments based on RFM score
        rfm_df['Customer_segment'] = pd.cut(
            rfm_df['RFM_Score'],
            bins=[0, 1.6, 3.0, 4.0, 4.5, 5.0],
            labels=['Inactive', 'Occasional', 'Silver', 'Gold', 'Platinum'],
            include_lowest=True
        )
        
        # Round values for display
        rfm_df = rfm_df.round(2)
        
        return rfm_df
    
    def get_segment_summary(self, rfm_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Get summary statistics by customer segment"""
        if rfm_df.empty:
            return []
        
        segment_summary = rfm_df.groupby('Customer_segment').agg({
            'customer_id': 'count',
            'Frequency': 'sum',
            'Monetary': 'sum',
            'RFM_Score': 'mean'
        }).reset_index()
        
        segment_summary.columns = [
            'segment', 'customer_count', 'total_orders', 
            'total_volume', 'avg_rfm_score'
        ]
        
        # Calculate percentages
        total_customers = segment_summary['customer_count'].sum()
        total_volume = segment_summary['total_volume'].sum()
        
        segment_summary['customer_percentage'] = (
            segment_summary['customer_count'] / total_customers * 100
        ).round(2)
        
        segment_summary['volume_percentage'] = (
            segment_summary['total_volume'] / total_volume * 100
        ).round(2)
        
        segment_summary['avg_rfm_score'] = segment_summary['avg_rfm_score'].round(2)
        segment_summary['total_volume'] = segment_summary['total_volume'].round(2)
        
        # Sort by segment priority
        segment_order = {'Platinum': 0, 'Gold': 1, 'Silver': 2, 'Occasional': 3, 'Inactive': 4}
        segment_summary['sort_order'] = segment_summary['segment'].map(segment_order)
        segment_summary = segment_summary.sort_values('sort_order').drop('sort_order', axis=1)
        
        return segment_summary.to_dict('records')
    
    async def get_rfm_analysis(
        self, 
        unit_id: Optional[int] = None,
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get complete RFM analysis with all metrics"""
        # Get transaction data
        df = await self.repository.get_customer_transactions(unit_id, start_date, end_date)
        
        if df.empty:
            return {
                'customers': [],
                'segment_summary': [],
                'metadata': {
                    'total_customers': 0,
                    'total_transactions': 0,
                    'total_volume': 0,
                    'analysis_date': datetime.now().isoformat(),
                    'unit_id': unit_id,
                    'date_range': {
                        'start': start_date,
                        'end': end_date
                    }
                }
            }
        
        # Calculate RFM
        rfm_df = self.calculate_rfm(df)
        
        # Get segment summary
        segment_summary = self.get_segment_summary(rfm_df)
        
        # Get summary stats
        summary = await self.repository.get_rfm_summary(unit_id, start_date, end_date)
        
        # Convert DataFrame to list of dicts
        customers = rfm_df.to_dict('records')
        
        return {
            'customers': customers,
            'segment_summary': segment_summary,
            'metadata': {
                'total_customers': len(customers),
                'total_transactions': summary.get('total_transactions', 0),
                'total_volume': summary.get('total_volume', 0),
                'analysis_date': datetime.now().isoformat(),
                'unit_id': unit_id,
                'date_range': {
                    'start': summary.get('earliest_date') if not start_date else start_date,
                    'end': summary.get('latest_date') if not end_date else end_date
                }
            }
        }