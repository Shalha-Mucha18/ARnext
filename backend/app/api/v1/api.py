"""
V1 API Router - aggregates all v1 endpoints.
"""
from fastapi import APIRouter
from app.api.v1.endpoints import health, units  # , sales

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health.router, tags=["health"])
api_router.include_router(units.router, tags=["units"])
# Temporarily disabled - using legacy endpoints instead due to query bugs
# api_router.include_router(sales.router, tags=["sales"])

# TODO: Add remaining routers as they are created
# api_router.include_router(chat.router, tags=["chat"])
# api_router.include_router(regional.router, tags=["regional"])
# api_router.include_router(forecast.router, tags=["forecast"])
# api_router.include_router(insights.router, tags=["insights"])
