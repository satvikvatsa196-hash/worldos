import pytest
import pytest_asyncio
import uuid
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from app.infrastructure.database import Base
from app.core.config import settings
from app.domain.event.models import WorldEvent, EventType
from app.domain.event.store import EventStore
from app.domain.event.bus import EventBus
from app.infrastructure.models import World, City, Faction

engine = create_async_engine(settings.async_database_url, echo=False, poolclass=NullPool)
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
def world_id():
    return uuid.uuid4()

@pytest.fixture
def city_id():
    return uuid.uuid4()

@pytest.fixture
def actor_id():
    return uuid.uuid4()

@pytest.fixture
def faction_id():
    return uuid.uuid4()

def test_event_creation(world_id):
    event = WorldEvent(
        world_id=world_id,
        tick=1,
        type=EventType.WORLD_TICK,
        payload={"message": "tick tock"}
    )
    assert event.world_id == world_id
    assert event.tick == 1
    assert event.type == EventType.WORLD_TICK
    assert event.payload == {"message": "tick tock"}
    assert event.id is not None
    assert event.created_at is not None

def test_event_immutability(world_id):
    event = WorldEvent(
        world_id=world_id,
        tick=1,
        type=EventType.WORLD_TICK
    )
    with pytest.raises(ValidationError):
        event.tick = 2

@pytest.mark.asyncio
async def test_event_persistence_and_filtering(world_id, city_id, actor_id, faction_id):
    async with AsyncSessionFactory() as session:
        # Create a world, city, and faction first because of foreign key constraint
        world = World(id=world_id, name="Test World", seed="123")
        session.add(world)
        
        city = City(id=city_id, world_id=world_id, name="Test City")
        session.add(city)
        
        faction = Faction(id=faction_id, world_id=world_id, name="Test Faction", type="Guild", ideology="Trade")
        session.add(faction)
        
        await session.commit()

        store = EventStore(session)
        
        event1 = WorldEvent(
            world_id=world_id,
            tick=1,
            type=EventType.WORLD_TICK
        )
        event2 = WorldEvent(
            world_id=world_id,
            tick=2,
            type=EventType.CHARACTER_ACTION,
            actor_id=actor_id,
            city_id=city_id
        )
        event3 = WorldEvent(
            world_id=world_id,
            tick=2,
            type=EventType.FACTION_ACTION,
            faction_id=faction_id
        )

        await store.save(event1)
        await store.save(event2)
        await store.save(event3)
        await session.commit()

        # Query by world
        events = await store.get_events(world_id=world_id)
        assert len(events) == 3

        # Query by tick
        events = await store.get_events(tick=2)
        assert len(events) == 2

        # Query by event type
        events = await store.get_events(event_type=EventType.CHARACTER_ACTION)
        assert len(events) == 1
        assert events[0].id == event2.id

        # Query by actor
        events = await store.get_events(actor_id=actor_id)
        assert len(events) == 1
        
        # Query by city
        events = await store.get_events(city_id=city_id)
        assert len(events) == 1

        # Query by faction
        events = await store.get_events(faction_id=faction_id)
        assert len(events) == 1

@pytest.mark.asyncio
async def test_parent_child_relationships(world_id):
    async with AsyncSessionFactory() as session:
        world = World(id=world_id, name="Test World 2", seed="123")
        session.add(world)
        await session.commit()

        store = EventStore(session)

        parent_event = WorldEvent(
            world_id=world_id,
            tick=1,
            type=EventType.POLITICAL_CHANGE
        )
        child_event = WorldEvent(
            world_id=world_id,
            tick=1,
            type=EventType.PROTEST,
            parent_event_id=parent_event.id
        )

        await store.save(parent_event)
        await store.save(child_event)
        await session.commit()

        events = await store.get_events(parent_event_id=parent_event.id)
        assert len(events) == 1
        assert events[0].id == child_event.id

@pytest.mark.asyncio
async def test_event_bus():
    bus = EventBus()
    received_events = []

    async def handler(event: WorldEvent):
        received_events.append(event)

    bus.subscribe(EventType.TRADE, handler)

    event1 = WorldEvent(
        world_id=uuid.uuid4(),
        tick=1,
        type=EventType.TRADE
    )
    event2 = WorldEvent(
        world_id=uuid.uuid4(),
        tick=1,
        type=EventType.WORLD_TICK
    )

    await bus.publish(event1)
    await bus.publish(event2) # Should not be received

    assert len(received_events) == 1
    assert received_events[0].id == event1.id
