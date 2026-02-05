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
    pool_size=2,             
    max_overflow=1,           
    pool_pre_ping=True,       
    echo=False,
    connect_args={
        'connect_timeout': 10,
        'options': '-c statement_timeout=30000' 
    }
)


# Singleton instance for lazy loading
_db_instance = None

def get_sync_db() -> SQLDatabase:
    """
    This prevents the app from crashing at startup if the DB is full.
    Connection is only established when this function is first called.
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = SQLDatabase(engine, schema=settings.PG_SCHEMA)
    return _db_instance
