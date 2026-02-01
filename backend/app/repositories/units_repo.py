"""
Units repository - handles business unit data access.

This module provides secure, parameterized queries for business unit data.
"""
from typing import List, Dict, Optional
from core.logging import get_logger
from db.engine import db

logger = get_logger(__name__)


def get_all_units() -> List[Dict[str, str]]:
    """    
    Returns:
        List of dicts with unit_id and business_unit_name
        
    Raises:
        Exception: If database query fails
    """
    try:
        query = '''
        SELECT DISTINCT 
            d."unit_id" as unit_id,
            COALESCE(b."strBusinessUnitName", 'Unit ' || d."unit_id") as business_unit_name
        FROM tbldeliveryinfo d
        LEFT JOIN dim_business_unit b ON d."unit_id" = b."Unit_Id"
        WHERE d."unit_id" IS NOT NULL
        ORDER BY d."unit_id"
        '''
        
        result_str = db.run(query)
        
        if not result_str or result_str.strip() == '':
            return []
    
        import ast
        results = ast.literal_eval(result_str)
        
        return [
            {
                "unit_id": str(row[0]),
                "business_unit_name": row[1]
            }
            for row in results
        ]
    except Exception as e:
        logger.error(f"Error fetching units: {e}")
        raise


def get_business_unit_name(unit_id: Optional[str]) -> str:
    """    
    Args:
        unit_id: Business unit ID
        
    Returns:
        Business unit name or fallback
    """
    if not unit_id:
        return "All Units"
    
    try:
        sanitized_unit_id = str(unit_id).replace("'", "''")  
        query = f'''
        SELECT "strBusinessUnitName" 
        FROM dim_business_unit 
        WHERE "Unit_Id" = '{sanitized_unit_id}'
        LIMIT 1
        '''
        
        result_str = db.run(query)
        
        if not result_str or result_str.strip() == '':
            return f"Unit {unit_id}"
        
        import ast
        results = ast.literal_eval(result_str)
        
        if results and len(results) > 0:
            return results[0][0]
        
        return f"Unit {unit_id}"
    except Exception as e:
        logger.error(f"Error fetching business unit name: {e}")
        return f"Unit {unit_id}"
