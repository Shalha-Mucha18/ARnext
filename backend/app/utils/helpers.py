"""
Helper utilities for the application.
"""
from typing import Any, Dict
from fastapi.responses import JSONResponse


def success_response(data: Any, message: str = "Success") -> Dict[str, Any]:
    """
    Create a standard success response.
    
    Args:
        data: Response data
        message: Success message
        
    Returns:
        Standard success response dict
    """
    return {
        "success": True,
        "message": message,
        "data": data
    }


def error_response(message: str, status_code: int = 400, error_code: str = None) -> JSONResponse:
    """
    Create a standard error response.
    
    Args:
        message: Error message
        status_code: HTTP status code
        error_code: Optional error code
        
    Returns:
        JSONResponse with error details
    """
    content = {
        "success": False,
        "error": message
    }
    
    if error_code:
        content["error_code"] = error_code
    
    return JSONResponse(
        status_code=status_code,
        content=content
    )


def format_currency(value: float) -> str:
    """
    Format currency value with appropriate suffix.
    
    Args:
        value: Numeric value
        
    Returns:
        Formatted string (e.g., "1.5M", "250K")
    """
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    elif value >= 1_000:
        return f"{value / 1_000:.0f}K"
    else:
        return f"{value:.2f}"
