from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.core.config import settings

import sys
from sqlalchemy.pool import NullPool, QueuePool

is_testing = "pytest" in sys.modules

engine_kwargs = {
    "echo": False,
    "future": True,
    "pool_pre_ping": True,
}

if is_testing:
    engine_kwargs["poolclass"] = NullPool
else:
    engine_kwargs["poolclass"] = QueuePool
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 10

# Create async engine with connection pooling
engine = create_async_engine(
    settings.async_database_url,
    **engine_kwargs
)

# Async session factory
AsyncSessionFactory = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

Base = declarative_base()

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting an async database session.
    """
    async with AsyncSessionFactory() as session:
        yield session
