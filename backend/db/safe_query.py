from typing import List, Tuple, Optional, Any, Dict
from sqlalchemy import text
from db.engine import engine
import logging

logger = logging.getLogger(__name__)


def safe_execute(query: str, params: Optional[Dict[str, Any]] = None) -> List[Tuple]:

    try:
        with engine.connect() as conn:
            if params:
                result = conn.execute(text(query), params)
            else:
                result = conn.execute(text(query))
            
            # Fetch all results and convert to list of tuples
            rows = result.fetchall()
            return [tuple(row) for row in rows]
    except Exception as e:
        logger.error(f"Query execution failed: {e}\nQuery: {query}\nParams: {params}")
        raise


def safe_execute_one(query: str, params: Optional[Dict[str, Any]] = None) -> Optional[Tuple]:
    results = safe_execute(query, params)
    return results[0] if results else None


def safe_execute_scalar(query: str, params: Optional[Dict[str, Any]] = None) -> Any:
 
    result = safe_execute_one(query, params)
    return result[0] if result else None


def safe_execute_dict(query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:

    try:
        with engine.connect() as conn:
            if params:
                result = conn.execute(text(query), params)
            else:
                result = conn.execute(text(query))
            
            # Get column names
            columns = result.keys()
            
            # Convert rows to dictionaries
            rows = result.fetchall()
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.error(f"Query execution failed: {e}\nQuery: {query}\nParams: {params}")
        raise
