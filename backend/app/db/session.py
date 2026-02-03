from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from core.config import settings

async_engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    echo=False,
    poolclass=NullPool,     

)

# Create async session factory
async_session_maker = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)



import asyncio
from typing import AsyncGenerator

_db_semaphore = asyncio.Semaphore(1) 

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to provide an async database session.
    Automatically handles commit/rollback and closing.
    Uses a semaphore to prevent opening too many simultaneous connections.
    """
    async with _db_semaphore:
        async with async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                import traceback
                with open("backend_errors.txt", "a") as f:
                    f.write(f"DB Session Error: {str(e)}\n{traceback.format_exc()}\n")
                await session.rollback()
                raise
            finally:
                await session.close()
