from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.logging import setup_logging
import os

# Initialize logging
setup_logging()

app = FastAPI(
    title="ARNext Intelligence API",
    version="2.0.0",
    description="Sales Analytics API with AI-powered insights"
)

# CORS Configuration
# TODO: Replace with specific origins in production
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include new V1 API router (refactored endpoints)
from app.api.v1.api import api_router
app.include_router(api_router)

# Include legacy router for endpoints not yet refactored
from .api_legacy import router as legacy_router
app.include_router(legacy_router)
