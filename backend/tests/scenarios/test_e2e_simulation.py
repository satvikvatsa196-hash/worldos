import pytest
import pytest_asyncio
import uuid
import asyncio
from typing import Dict, Any, Optional

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, func
from sqlalchemy.pool import NullPool

from app.main import app
from app.infrastructure.database import Base, engine, AsyncSessionFactory
from app.infrastructure.models import World, City, Character, Faction, Event, Resource, Inventory, Memory
from app.domain.simulation.generator import WorldGenerator, GeneratorConfig
from app.agents.scheduler import AgentScheduler
from app.agents.engine import CharacterDecisionEngine, DecisionRecord, IDecisionStore
from app.domain.event.bus import EventBus
from app.agents.executor import ActionExecutionEngine, ExecutionStatus, ActionExecutionResult
from app.llm.provider import LLMProvider
from app.llm.models import LLMResponse, LLMDecisionOutput, LLMActionSchema, LLMMetadata
from app.agents.models import ActionType
from app.domain.event.models import EventType, WorldEvent

class E2EMockLLMProvider(LLMProvider):
    async def get_decision(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        # Everyone tries to WORK to earn money or DO_NOTHING
        # Alternate based on some state? We'll just return WORK
        decision = LLMDecisionOutput(
            decision_summary="Working to test economy",
            action=LLMActionSchema(type="WORK", parameters={}),
            confidence=0.9
        )
        return LLMResponse(decision=decision, metadata=LLMMetadata(usage={"total_tokens": 10}), is_success=True)

class E2EDecisionStore(IDecisionStore):
    async def save(self, record: DecisionRecord) -> None:
        pass # fast no-op for E2E speed

class E2EActionValidator:
    def validate(self, action, context) -> bool:
        return True

@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_comprehensive_e2e_simulation():
    # 1. Generate world
    async with AsyncSessionFactory() as session:
        config = GeneratorConfig(name="E2E World", seed=123, cities=1, characters=10, factions=2)
        generator = WorldGenerator(config)
        world_data = generator.generate()
        
        world = world_data["world"]
        session.add(world)
        
        # Add the generated cities, but give them wealth for our test
        for city in world_data["cities"]:
            city.wealth = 50000.0
            session.add(city)
            
        for c in world_data["characters"]:
            c.wealth = 100.0
            session.add(c)
            
        for f in world_data["factions"]:
            f.wealth = 500.0
            session.add(f)
            
        await session.commit()
        
    world_id = world.id

    # 2. Capture Initial Invariants
    async with AsyncSessionFactory() as session:
        total_city_wealth = await session.scalar(select(func.sum(City.wealth)).where(City.world_id == world_id)) or 0.0
        total_char_wealth = await session.scalar(select(func.sum(Character.wealth)).where(Character.world_id == world_id)) or 0.0
        total_faction_wealth = await session.scalar(select(func.sum(Faction.wealth)).where(Faction.world_id == world_id)) or 0.0
        
        initial_money = total_city_wealth + total_char_wealth + total_faction_wealth

    # 3. Setup Agent Pipeline
    llm = E2EMockLLMProvider()
    store = E2EDecisionStore()
    validator = E2EActionValidator()
    decision_engine = CharacterDecisionEngine(llm, validator, store)
    event_bus = EventBus()
    
    # Simple event listener to form a memory on trade or character action
    async def memory_forming_listener(event):
        if event.type.value in ["CHARACTER_ACTION", "TRADE"]:
            async with AsyncSessionFactory() as session:
                mem = Memory(
                    character_id=event.actor_id,
                    tick=event.tick,
                    type=event.type.value,
                    summary=f"Did {event.type.value}",
                    importance=5.0
                )
                session.add(mem)
                await session.commit()
                
    event_bus.subscribe(EventType.CHARACTER_ACTION, memory_forming_listener)
    
    # 4. Run 100 Ticks
    for tick in range(1, 101):
        async with AsyncSessionFactory() as session:
            executor = ActionExecutionEngine(session)
            scheduler = AgentScheduler(decision_engine, event_bus, action_executor=executor, max_concurrency=10)
            
            chars = await session.execute(select(Character).where(Character.world_id == world_id))
            for char in chars.scalars():
                scheduler.register_agent(char.id, {"role": char.occupation})
                scheduler.schedule_agent(char.id, priority=1, urgency=10, reason="TICK")
            
            await scheduler.run_tick(world_id, tick)
            
            # Persist tick
            world_obj = await session.get(World, world_id)
            world_obj.current_tick = tick
            await session.commit()
            
    # 5. Verify Final State and Invariants
    async with AsyncSessionFactory() as session:
        # Reload World
        world_obj = await session.get(World, world_id)
        assert world_obj.current_tick == 100
        
        # Verify Money Conservation
        total_city_wealth = await session.scalar(select(func.sum(City.wealth)).where(City.world_id == world_id)) or 0.0
        total_char_wealth = await session.scalar(select(func.sum(Character.wealth)).where(Character.world_id == world_id)) or 0.0
        total_faction_wealth = await session.scalar(select(func.sum(Faction.wealth)).where(Faction.world_id == world_id)) or 0.0
        
        final_money = total_city_wealth + total_char_wealth + total_faction_wealth
        assert initial_money == final_money, f"Invariant Failed: Money not conserved! {initial_money} != {final_money}"
        
        # Verify Actions executed and events generated
        # We need to join with Character to filter by world_id
        memories = await session.execute(
            select(Memory).join(Character).where(Character.world_id == world_id)
        )
        assert len(memories.scalars().all()) > 0, "No memories were formed during simulation"
        
        # Verify Locations (all characters still in a valid city)
        chars = await session.execute(select(Character).where(Character.world_id == world_id))
        for char in chars.scalars():
            assert char.city_id is not None
            city = await session.get(City, char.city_id)
            assert city is not None, "Invalid location"
            
        # Verify valid faction membership
        factions = await session.execute(select(Faction).where(Faction.world_id == world_id))
        faction_ids = {f.id for f in factions.scalars()}
        for char in chars.scalars():
            if char.faction_id:
                assert char.faction_id in faction_ids, "Invalid faction membership"
