import pytest
import pytest_asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.exc import IntegrityError
from app.infrastructure.database import Base
from app.core.config import settings
from app.persistence.repository import UnitOfWork
from app.infrastructure.models import (
    World, City, Character, Faction, Resource, Inventory,
    Relationship, Goal, Memory, Event, EconomicTransaction
)

from sqlalchemy.pool import NullPool

engine = create_async_engine(settings.async_database_url, echo=False, poolclass=NullPool)
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        from sqlalchemy import text
        await conn.execute(text("DROP SCHEMA public CASCADE;"))
        await conn.execute(text("CREATE SCHEMA public;"))

@pytest.mark.asyncio
async def test_world_ownership_and_relationships():
    uow = UnitOfWork(AsyncSessionFactory)
    async with uow:
        # Create World
        world = World(name="Test World", seed="123")
        uow.session.add(world)
        await uow.session.flush()

        # Create City
        city = City(world_id=world.id, name="Test City")
        uow.session.add(city)
        await uow.session.flush()

        # Create Faction
        faction = Faction(world_id=world.id, name="Test Faction", type="Guild", ideology="Merchant")
        uow.session.add(faction)
        await uow.session.flush()

        # Create Character
        char1 = Character(
            world_id=world.id, 
            name="Alice", 
            age=30, 
            occupation="Merchant", 
            city_id=city.id,
            faction_id=faction.id,
            status="alive"
        )
        uow.session.add(char1)
        await uow.session.flush()
        
        # Verify world ownership
        assert city.world_id == world.id
        assert faction.world_id == world.id
        assert char1.world_id == world.id

@pytest.mark.asyncio
async def test_foreign_keys_and_valid_references():
    uow = UnitOfWork(AsyncSessionFactory)
    try:
        async with uow:
            invalid_city = City(world_id=uuid.uuid4(), name="Invalid City")
            uow.session.add(invalid_city)
            await uow.session.flush()
            # Should not reach here
            assert False, "Expected IntegrityError due to invalid foreign key"
    except IntegrityError:
        pass

@pytest.mark.asyncio
async def test_relationships():
    uow = UnitOfWork(AsyncSessionFactory)
    async with uow:
        world = World(name="Rel World", seed="rel")
        uow.session.add(world)
        await uow.session.flush()

        char1 = Character(world_id=world.id, name="Char1", age=20, occupation="A", status="alive")
        char2 = Character(world_id=world.id, name="Char2", age=25, occupation="B", status="alive")
        uow.session.add_all([char1, char2])
        await uow.session.flush()

        rel = Relationship(
            source_character_id=char1.id,
            target_character_id=char2.id,
            friendship=10.0
        )
        uow.session.add(rel)
        await uow.session.flush()

        # Cannot have self-relationship
        try:
            rel_self = Relationship(
                source_character_id=char1.id,
                target_character_id=char1.id
            )
            uow.session.add(rel_self)
            await uow.session.flush()
            assert False, "Expected IntegrityError due to self-relationship check constraint"
        except IntegrityError:
            await uow.session.rollback()

@pytest.mark.asyncio
async def test_transaction_rollback():
    uow = UnitOfWork(AsyncSessionFactory)
    world_id = None
    try:
        async with uow:
            world = World(name="Rollback World", seed="1")
            uow.session.add(world)
            await uow.session.flush()
            world_id = world.id
            raise ValueError("Trigger rollback")
    except ValueError:
        pass
        
    async with AsyncSessionFactory() as session:
        result = await session.get(World, world_id)
        assert result is None, "World should not exist after rollback"
