from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import router
import os

app = FastAPI(title="SalesGPT Backend", version="1.0.0")


origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
