from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
from langchain_community.utilities import SQLDatabase
from core.config import settings

def make_pg_url() -> str:
    return (
        f"postgresql+psycopg2://{settings.PG_USER}:{settings.PG_PASSWORD}"
        f"@{settings.PG_HOST}:{settings.PG_PORT}/{settings.PG_DB}"
    )
engine = create_engine(
    make_pg_url(),
    poolclass=QueuePool,
    pool_size=10,             # Balanced to prevent server exhaustion
    max_overflow=15,          # Total max: 25 connections for sync pool
    pool_pre_ping=True,       
    pool_recycle=1800,        # Recycle every 30 min
    pool_timeout=60,          # Wait up to 60s for connection          
    echo=False,
    connect_args={
        'connect_timeout': 10,
        'options': '-c statement_timeout=30000' 
    }
)

db = SQLDatabase(engine, schema=settings.PG_SCHEMA)
