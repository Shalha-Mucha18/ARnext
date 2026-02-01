"""
V1 API Router - aggregates all v1 endpoints.
"""
from fastapi import APIRouter
from app.api.v1.endpoints import health, units, sales, regional, analytics, forecast, chat, rfm

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(units.router, prefix="/units", tags=["units"])
api_router.include_router(sales.router, prefix="/sales", tags=["sales"])
api_router.include_router(regional.router, prefix="/regional", tags=["regional"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(forecast.router, prefix="/forecast", tags=["forecast"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(rfm.router, prefix="/rfm", tags=["rfm"])



