from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
from langchain_community.utilities import SQLDatabase
from core.config import settings

def make_pg_url() -> str:
    return (
        f"postgresql+psycopg2://{settings.PG_USER}:{settings.PG_PASSWORD}"
        f"@{settings.PG_HOST}:{settings.PG_PORT}/{settings.PG_DB}"
    )

# Use minimal connection pool for Azure PostgreSQL limits
engine = create_engine(
    make_pg_url(),
    poolclass=QueuePool,
    pool_size=2,              # Minimal pool size
    max_overflow=3,           # Very limited overflow
    pool_pre_ping=True,       # Verify connections before using
    pool_recycle=300,         # Recycle connections after 5 minutes
    pool_timeout=30,          # Timeout waiting for connection
    echo=False,
    connect_args={
        'connect_timeout': 10,
        'options': '-c statement_timeout=30000'  # 30 second query timeout
    }
)

db = SQLDatabase(engine, schema=settings.PG_SCHEMA)
