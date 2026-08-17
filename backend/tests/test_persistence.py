import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import Column, Integer, String, text
from app.infrastructure.database import Base
from app.persistence.repository import UnitOfWork, BaseRepository
from app.core.config import settings
from app.infrastructure.redis_client import redis_client

# A dummy model for testing
class DummyModel(Base):
    __tablename__ = "dummy_model"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)

from sqlalchemy.pool import NullPool

# Configure a test database url - we use the existing one but create tables dynamically
# In a real app we might use a dedicated test db, but for these tests we'll just use the main db config 
# and create/drop the dummy table.
engine = create_async_engine(settings.async_database_url, echo=False, poolclass=NullPool)
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_database_connection():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1

@pytest.mark.asyncio
async def test_redis_connection():
    await redis_client.connect()
    client = await redis_client.get_client()
    assert await client.ping() == True
    await redis_client.close()

@pytest.mark.asyncio
async def test_transaction_commit():
    uow = UnitOfWork(AsyncSessionFactory)
    async with uow:
        repo = uow.repository(DummyModel)
        dummy = DummyModel(name="test_commit")
        repo.add(dummy)
        # Commit happens implicitly on exit if no exception

    async with AsyncSessionFactory() as session:
        repo = BaseRepository(session, DummyModel)
        results = await repo.get_all()
        assert len(results) == 1
        assert results[0].name == "test_commit"

@pytest.mark.asyncio
async def test_transaction_rollback():
    uow = UnitOfWork(AsyncSessionFactory)
    try:
        async with uow:
            repo = uow.repository(DummyModel)
            dummy = DummyModel(name="test_rollback")
            repo.add(dummy)
            raise ValueError("Trigger rollback")
    except ValueError:
        pass

    async with AsyncSessionFactory() as session:
        repo = BaseRepository(session, DummyModel)
        results = await repo.get_all()
        # Should be 0 since the transaction was rolled back
        assert len(results) == 0

@pytest.mark.asyncio
async def test_repository_behavior():
    uow = UnitOfWork(AsyncSessionFactory)
    async with uow:
        repo = uow.repository(DummyModel)
        dummy1 = DummyModel(name="dummy1")
        dummy2 = DummyModel(name="dummy2")
        repo.add(dummy1)
        repo.add(dummy2)

    async with AsyncSessionFactory() as session:
        repo = BaseRepository(session, DummyModel)
        results = await repo.get_all()
        assert len(results) == 2
        
        # Test get_by_id
        fetched = await repo.get_by_id(results[0].id)
        assert fetched is not None
        assert fetched.name == results[0].name

        # Test delete
        await repo.delete(fetched)
        await session.commit()

    async with AsyncSessionFactory() as session:
        repo = BaseRepository(session, DummyModel)
        results = await repo.get_all()
        assert len(results) == 1
