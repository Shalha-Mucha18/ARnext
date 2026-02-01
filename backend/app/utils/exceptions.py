from fastapi import HTTPException, status

class AppException(Exception):
    """Base application exception"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status.HTTP_404_NOT_FOUND)

class ValidationError(AppException):
    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, status.HTTP_422_UNPROCESSABLE_ENTITY)

class DatabaseError(AppException):
    def __init__(self, message: str = "Database error"):
        super().__init__(message, status.HTTP_500_INTERNAL_SERVER_ERROR)