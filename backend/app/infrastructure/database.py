from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy import event
from app.core.config import settings
from app.core.telemetry import metrics
import time

import sys
from sqlalchemy.pool import NullPool

is_testing = "pytest" in sys.modules

engine_kwargs = {
    "echo": False,
    "future": True,
    "pool_pre_ping": True,
}

if is_testing:
    engine_kwargs["poolclass"] = NullPool
else:
    # Let create_async_engine use its default AsyncAdaptedQueuePool
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 10

# Create async engine with connection pooling
engine = create_async_engine(
    settings.async_database_url,
    **engine_kwargs
)

@event.listens_for(engine.sync_engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()

@event.listens_for(engine.sync_engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - context._query_start_time
    metrics.observe_latency("db_latency", total * 1000.0)

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
