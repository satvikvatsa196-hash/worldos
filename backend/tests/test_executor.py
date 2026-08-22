import pytest
import pytest_asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from app.infrastructure.database import Base
from app.infrastructure.models import World, Character, City, Faction, Resource, Inventory
from app.agents.models import AgentAction, ActionType
from app.agents.executor import ActionExecutionEngine, ExecutionStatus

from app.core.config import settings

engine = create_async_engine(settings.async_database_url, echo=False, poolclass=NullPool)
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    print("\n[test_executor] Setting up DB...", flush=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    print("\n[test_executor] Tearing down DB... (drop_all)", flush=True)
    try:
        await engine.dispose() # Force dispose any lingering connections
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        print("[test_executor] Teardown complete!", flush=True)
    except Exception as e:
        print(f"[test_executor] Teardown ERROR: {e}", flush=True)

@pytest_asyncio.fixture
async def session():
    async with AsyncSessionFactory() as session:
        yield session

@pytest_asyncio.fixture
async def seed_data(session: AsyncSession):
    world_id = uuid.uuid4()
    world = World(id=world_id, name="Test World", seed="123")
    
    city_id = uuid.uuid4()
    city = City(id=city_id, world_id=world_id, name="Test City")
    
    faction_id = uuid.uuid4()
    faction = Faction(id=faction_id, world_id=world_id, name="Test Faction", type="Guild", ideology="Capitalism")
    
    char_id = uuid.uuid4()
    character = Character(
        id=char_id,
        world_id=world_id,
        name="Test Actor",
        age=30,
        occupation="Worker",
        wealth=100.0,
        health=100.0,
        city_id=city_id,
        status="alive"
    )
    
    target_id = uuid.uuid4()
    target_char = Character(
        id=target_id,
        world_id=world_id,
        name="Test Target",
        age=30,
        occupation="Worker",
        wealth=50.0,
        health=100.0,
        city_id=city_id,
        status="alive"
    )
    
    resource_id = uuid.uuid4()
    resource = Resource(id=resource_id, world_id=world_id, name="Wood", current_price=10.0)
    
    session.add_all([world, city, faction, character, target_char, resource])
    await session.commit()
    
    return {
        "world_id": world_id,
        "city_id": city_id,
        "faction_id": faction_id,
        "char_id": char_id,
        "target_id": target_id,
        "resource_id": resource_id
    }

@pytest.mark.asyncio
async def test_buying_without_money(session, seed_data):
    executor = ActionExecutionEngine(session)
    action = AgentAction(
        action_type=ActionType.BUY_RESOURCE,
        actor_id=seed_data["char_id"],
        parameters={"resource_id": str(seed_data["resource_id"]), "quantity": 100}, # 100 * 10 = 1000 > 100
        justification_summary="Need wood",
        confidence=1.0
    )
    
    result = await executor.execute(action, seed_data["world_id"], 1)
    
    assert result.status == ExecutionStatus.REJECTED
    assert "Insufficient wealth" in result.reason

@pytest.mark.asyncio
async def test_selling_nonexistent_inventory(session, seed_data):
    executor = ActionExecutionEngine(session)
    action = AgentAction(
        action_type=ActionType.SELL_RESOURCE,
        actor_id=seed_data["char_id"],
        parameters={"resource_id": str(seed_data["resource_id"]), "quantity": 5},
        justification_summary="Selling air",
        confidence=1.0
    )
    
    result = await executor.execute(action, seed_data["world_id"], 1)
    
    assert result.status == ExecutionStatus.REJECTED
    assert "Insufficient inventory" in result.reason

@pytest.mark.asyncio
async def test_moving_to_nonexistent_city(session, seed_data):
    executor = ActionExecutionEngine(session)
    action = AgentAction(
        action_type=ActionType.MOVE,
        actor_id=seed_data["char_id"],
        parameters={"city_id": str(uuid.uuid4())}, # Fake city
        justification_summary="Moving to nowhere",
        confidence=1.0
    )
    
    result = await executor.execute(action, seed_data["world_id"], 1)
    
    assert result.status == ExecutionStatus.REJECTED
    assert "City does not exist" in result.reason

@pytest.mark.asyncio
async def test_joining_nonexistent_faction(session, seed_data):
    executor = ActionExecutionEngine(session)
    action = AgentAction(
        action_type=ActionType.JOIN_FACTION,
        actor_id=seed_data["char_id"],
        parameters={"faction_id": str(uuid.uuid4())},
        justification_summary="Joining ghosts",
        confidence=1.0
    )
    
    result = await executor.execute(action, seed_data["world_id"], 1)
    
    assert result.status == ExecutionStatus.REJECTED
    assert "Faction does not exist" in result.reason

@pytest.mark.asyncio
async def test_giving_more_money_than_owned(session, seed_data):
    executor = ActionExecutionEngine(session)
    action = AgentAction(
        action_type=ActionType.GIVE_MONEY,
        actor_id=seed_data["char_id"],
        target_id=seed_data["target_id"],
        parameters={"amount": 500.0}, # Actor only has 100
        justification_summary="Generous",
        confidence=1.0
    )
    
    result = await executor.execute(action, seed_data["world_id"], 1)
    
    assert result.status == ExecutionStatus.REJECTED
    assert "Insufficient wealth" in result.reason
    
@pytest.mark.asyncio
async def test_successful_buy_and_sell(session, seed_data):
    executor = ActionExecutionEngine(session)
    
    # 1. Buy 5 Wood (5 * 10 = 50 cost)
    buy_action = AgentAction(
        action_type=ActionType.BUY_RESOURCE,
        actor_id=seed_data["char_id"],
        parameters={"resource_id": str(seed_data["resource_id"]), "quantity": 5},
        justification_summary="Need wood",
        confidence=1.0
    )
    result = await executor.execute(buy_action, seed_data["world_id"], 1)
    
    assert result.status == ExecutionStatus.SUCCESS
    assert len(result.events_generated) == 1
    
    # Verify DB state update
    char = await session.get(Character, seed_data["char_id"])
    assert char.wealth == 50.0 # 100 - 50
    
    # 2. Sell 2 Wood (2 * 10 = 20 revenue)
    sell_action = AgentAction(
        action_type=ActionType.SELL_RESOURCE,
        actor_id=seed_data["char_id"],
        parameters={"resource_id": str(seed_data["resource_id"]), "quantity": 2},
        justification_summary="Too much wood",
        confidence=1.0
    )
    result2 = await executor.execute(sell_action, seed_data["world_id"], 2)
    
    assert result2.status == ExecutionStatus.SUCCESS
    await session.refresh(char)
    assert char.wealth == 70.0 # 50 + 20
    
    await session.commit() # Ensure transaction is cleanly ended
