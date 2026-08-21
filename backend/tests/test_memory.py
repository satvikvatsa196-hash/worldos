import pytest
import uuid
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from app.infrastructure.database import Base
from app.infrastructure.models import World, Character, Event, Memory
from app.domain.event.models import WorldEvent, EventType
from app.domain.character.memory import MemoryManager, PostgresMemoryRetriever, MemoryType
from app.agents.models import AgentContext
from app.persistence.repositories import MemoryRepository
from app.core.config import settings

engine = create_async_engine(settings.async_database_url, echo=False, poolclass=NullPool)
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

@pytest_asyncio.fixture
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
def memory_manager():
    return MemoryManager(importance_threshold=0.5)

def test_memory_creation_and_importance_filtering(memory_manager):
    char_id = uuid.uuid4()
    
    # 1. Low importance event
    low_event = WorldEvent(
        world_id=uuid.uuid4(),
        tick=1,
        type=EventType.CHARACTER_ACTION,
        actor_id=char_id,
        payload={"action": "walk"}
    )
    memory1 = memory_manager.evaluate_event(low_event, char_id)
    assert memory1 is None
    
    # 2. High importance trade
    target_id = uuid.uuid4()
    trade_event = WorldEvent(
        world_id=uuid.uuid4(),
        tick=2,
        type=EventType.TRADE,
        actor_id=char_id,
        target_id=target_id,
        payload={"amount": 2000}
    )
    memory2 = memory_manager.evaluate_event(trade_event, char_id)
    assert memory2 is not None
    assert memory2.importance >= 0.9
    assert memory2.type == MemoryType.TRANSACTION
    assert target_id in memory2.related_entities
    
    # 3. Betrayal conflict
    betrayal_event = WorldEvent(
        world_id=uuid.uuid4(),
        tick=3,
        type=EventType.CONFLICT,
        actor_id=target_id,
        target_id=char_id,
        payload={"betrayal": True}
    )
    memory3 = memory_manager.evaluate_event(betrayal_event, char_id)
    assert memory3 is not None
    assert memory3.importance == 1.0
    assert memory3.source_event_id == betrayal_event.id

@pytest.mark.asyncio
async def test_memory_persistence_and_retrieval(memory_manager, setup_database):
    async with AsyncSessionFactory() as session:
        # Create dependencies
        world = World(name="Test", seed="123", current_tick=1)
        session.add(world)
        await session.commit()
        
        char1 = Character(world_id=world.id, name="Alice", age=20, occupation="smith", status="alive")
        char2 = Character(world_id=world.id, name="Bob", age=25, occupation="farmer", status="alive")
        session.add(char1)
        session.add(char2)
        await session.commit()
        
        # Create memories in DB directly using repo
        repo = MemoryRepository(session)
        
        db_mem1 = Memory(
            character_id=char1.id,
            type=MemoryType.EVENT.value,
            summary="Met Bob",
            importance=0.6,
            tick=1,
            related_entities=[str(char2.id)]
        )
        db_mem2 = Memory(
            character_id=char1.id,
            type=MemoryType.TRANSACTION.value,
            summary="Bought something",
            importance=0.8,
            tick=2,
            related_entities=[]
        )
        repo.add(db_mem1)
        repo.add(db_mem2)
        await session.commit()
        
        # Test Retriever
        retriever = PostgresMemoryRetriever(repo)
        
        # Context where char1 is interacting with char2
        context = AgentContext(
            character_state={},
            needs={},
            goals=[],
            relevant_memories=[],
            beliefs=[],
            nearby_entities=[{"id": str(char2.id), "name": "Bob"}],
            relationships=[],
            current_economic_conditions={},
            recent_events=[]
        )
        
        memories = await retriever.retrieve_relevant_memories(char1.id, context, limit=2)
        assert len(memories) == 2
        
        # The memory involving char2 should be ranked higher due to entity overlap
        # score mem1 = 0.6 + (1 * 0.3) = 0.9
        # score mem2 = 0.8 + 0 = 0.8
        assert memories[0].summary == "Met Bob"
        assert memories[1].summary == "Bought something"
