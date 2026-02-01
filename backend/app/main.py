from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.logging import setup_logging
import os
from fastapi import Request
from fastapi.responses import JSONResponse
from app.utils.exceptions import AppException

# Initialize logging
setup_logging()

app = FastAPI(
    title="ARNext Intelligence API",
    version="2.0.0",
    description="Akij Resource AI powered insights"
)

# CORS Configuration
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.v1.api import api_router
app.include_router(api_router, prefix="/api/v1")



@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.message,
            "path": str(request.url)
        }
    )