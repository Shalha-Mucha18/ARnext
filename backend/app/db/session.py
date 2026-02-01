from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from core.config import settings

# Optimized async engine with balanced pooling to prevent connection exhaustion
# Configuration: 10 base + 15 overflow = 25 max connections
async_engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    echo=False,
    pool_size=10,             # Balanced for concurrent requests without exhausting server
    max_overflow=15,          # Total max: 25 connections for async pool
    pool_pre_ping=True,
    pool_recycle=1800,        # Recycle connections every 30 min to prevent stale connections
    pool_timeout=60,          # Wait up to 60s for a connection
)

# Create async session factory
async_session_maker = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Dependency for FastAPI
async def get_db() -> AsyncSession:
    """
    Dependency to provide an async database session.
    Automatically handles commit/rollback and closing.
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
