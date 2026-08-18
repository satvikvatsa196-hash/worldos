import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.infrastructure.database import Base
from app.core.config import settings
from app.domain.simulation.generator import WorldGenerator, GeneratorConfig
from app.infrastructure.models import (
    World, City, Character, Faction, Resource, Inventory, Relationship, Goal
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
        # Use raw Postgres CASCADE to forcefully wipe all tables and avoid circular dependency drop issues
        from sqlalchemy import text
        await conn.execute(text("DROP SCHEMA public CASCADE;"))
        await conn.execute(text("CREATE SCHEMA public;"))

@pytest.fixture
def base_config():
    return GeneratorConfig(
        name="Test World",
        seed=12345,
        cities=3,
        characters=25,
        factions=3
    )

def test_deterministic_generation(base_config):
    gen1 = WorldGenerator(base_config)
    res1 = gen1.generate()
    
    gen2 = WorldGenerator(base_config)
    res2 = gen2.generate()
    
    assert res1["world"].id == res2["world"].id
    
    # Check all character IDs match exactly
    ids1 = [c.id for c in res1["characters"]]
    ids2 = [c.id for c in res2["characters"]]
    assert ids1 == ids2
    
    # Check relationships
    rels1 = [(r.source_character_id, r.target_character_id, r.friendship) for r in res1["relationships"]]
    rels2 = [(r.source_character_id, r.target_character_id, r.friendship) for r in res2["relationships"]]
    assert rels1 == rels2

@pytest.mark.asyncio
async def test_generator_persistence(base_config):
    generator = WorldGenerator(base_config)
    entities = generator.generate()
    
    async with AsyncSessionFactory() as session:
        session.add(entities["world"])
        session.add_all(entities["resources"])
        session.add_all(entities["cities"])
        session.add_all(entities["factions"])
        session.add_all(entities["characters"])
        session.add_all(entities["inventories"])
        session.add_all(entities["goals"])
        session.add_all(entities["relationships"])
        
        await session.commit()
        
        # Verify valid references and FKs
        stmt = select(World).options(selectinload(World.characters))
        result = await session.execute(stmt)
        world = result.scalars().first()
        
        assert world is not None
        assert len(world.characters) == base_config.characters
        
        # Check Factions logic
        stmt_factions = select(Faction)
        res_factions = await session.execute(stmt_factions)
        factions = res_factions.scalars().all()
        assert len(factions) == base_config.factions

@pytest.mark.asyncio
async def test_generator_consistency(base_config):
    generator = WorldGenerator(base_config)
    entities = generator.generate()
    
    characters = entities["characters"]
    factions = {f.id: f for f in entities["factions"]}
    inventories = entities["inventories"]
    resources = {r.id: r for r in entities["resources"]}
    cities = {c.id: c for c in entities["cities"]}
    
    # Verify city assignments
    for char in characters:
        assert char.city_id in cities
        
    # Verify faction logic
    for char in characters:
        if char.faction_id:
            assert char.faction_id in factions
            faction = factions[char.faction_id]
            # Verify basic coherence if possible, e.g., soldier -> military
            if char.occupation == "soldier":
                assert faction.type in ["military", "worker", "political"] # Can be broad but should be valid

    # Verify inventory consistency
    food_resource_id = next(r.id for r in resources.values() if r.name == "Food")
    for char in characters:
        char_invs = [inv for inv in inventories if inv.owner_id == char.id]
        
        # Everyone should have food
        has_food = any(inv.resource_id == food_resource_id and inv.quantity > 0 for inv in char_invs)
        assert has_food
        
        # Woodcutters should have wood
        if char.occupation == "woodcutter":
            wood_res_id = next(r.id for r in resources.values() if r.name == "Wood")
            has_wood = any(inv.resource_id == wood_res_id for inv in char_invs)
            assert has_wood
            
    # Verify relationship consistency
    for rel in entities["relationships"]:
        assert rel.source_character_id != rel.target_character_id
