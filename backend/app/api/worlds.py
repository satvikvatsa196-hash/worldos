from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, delete
from sqlalchemy.orm import selectinload, make_transient
from typing import List, Optional, Any
import uuid

from app.infrastructure.database import get_db_session
from app.domain.simulation.generator import WorldGenerator, GeneratorConfig
from app.infrastructure.models import (
    World, Event, City, Character, Faction, Resource, Inventory, Relationship, Goal, Memory, EconomicTransaction, Belief, AgentDecisionRecord
)
from app.domain.simulation.engine import SimulationEngine

router = APIRouter(prefix="/worlds", tags=["worlds"])

class GenerateWorldRequest(BaseModel):
    name: str
    seed: int
    cities: int = 4
    characters: int = 30
    factions: int = 4

class GenerateWorldResponse(BaseModel):
    world_id: uuid.UUID
    summary: str

class AdvanceSimulationRequest(BaseModel):
    ticks: int

class SimulationResponse(BaseModel):
    world_id: uuid.UUID
    current_tick: int
    status: str

class WorldStateResponse(BaseModel):
    id: uuid.UUID
    name: str
    seed: str
    current_tick: int
    simulation_status: str
    cities_count: int
    characters_count: int
    factions_count: int

@router.get("", response_model=List[WorldStateResponse])
async def list_worlds(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session)
):
    result = await db.execute(select(World).offset(skip).limit(limit))
    worlds = result.scalars().all()
    
    responses = []
    for w in worlds:
        cities = await db.execute(select(City).where(City.world_id == w.id))
        chars = await db.execute(select(Character).where(Character.world_id == w.id))
        facts = await db.execute(select(Faction).where(Faction.world_id == w.id))
        responses.append(WorldStateResponse(
            id=w.id, name=w.name, seed=w.seed, current_tick=w.current_tick, 
            simulation_status=w.simulation_status,
            cities_count=len(cities.scalars().all()),
            characters_count=len(chars.scalars().all()),
            factions_count=len(facts.scalars().all())
        ))
    return responses

@router.get("/{world_id}", response_model=WorldStateResponse)
async def get_world(world_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(World).where(World.id == world_id))
    w = result.scalars().first()
    if not w:
        raise HTTPException(status_code=404, detail="World not found")
        
    cities = await db.execute(select(City).where(City.world_id == w.id))
    chars = await db.execute(select(Character).where(Character.world_id == w.id))
    facts = await db.execute(select(Faction).where(Faction.world_id == w.id))
    
    return WorldStateResponse(
        id=w.id, name=w.name, seed=w.seed, current_tick=w.current_tick, 
        simulation_status=w.simulation_status,
        cities_count=len(cities.scalars().all()),
        characters_count=len(chars.scalars().all()),
        factions_count=len(facts.scalars().all())
    )

@router.get("/{world_id}/state")
async def get_world_state(world_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(World).where(World.id == world_id))
    w = result.scalars().first()
    if not w:
        raise HTTPException(status_code=404, detail="World not found")
        
    cities_res = await db.execute(select(City).where(City.world_id == world_id))
    cities = [{"id": c.id, "name": c.name, "population": c.population, "wealth": c.wealth} for c in cities_res.scalars().all()]
    
    chars_res = await db.execute(select(Character).where(Character.world_id == world_id))
    chars = [{"id": c.id, "name": c.name, "role": c.occupation, "wealth": c.wealth} for c in chars_res.scalars().all()]
    
    factions_res = await db.execute(select(Faction).where(Faction.world_id == world_id))
    factions = [{"id": f.id, "name": f.name, "power": f.power} for f in factions_res.scalars().all()]
    
    resources_res = await db.execute(select(Resource).where(Resource.world_id == world_id))
    resources = [{"id": r.id, "name": r.name, "price": r.current_price} for r in resources_res.scalars().all()]
    
    return {
        "world": {"id": w.id, "name": w.name, "tick": w.current_tick},
        "cities": cities,
        "characters": chars,
        "factions": factions,
        "resources": resources
    }

@router.get("/{world_id}/events")
async def get_world_events(
    world_id: uuid.UUID, 
    tick: Optional[int] = None, 
    event_type: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(Event).where(Event.world_id == world_id)
    if tick is not None:
        stmt = stmt.where(Event.tick == tick)
    if event_type:
        stmt = stmt.where(Event.type == event_type)
        
    stmt = stmt.order_by(desc(Event.tick), desc(Event.created_at)).offset(skip).limit(limit)
    result = await db.execute(stmt)
    
    events = result.scalars().all()
    return [{"id": e.id, "tick": e.tick, "type": e.type, "payload": e.payload, "actor_id": e.actor_id} for e in events]

@router.get("/{world_id}/timeline")
async def get_world_timeline(world_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    stmt = select(Event).where(Event.world_id == world_id).order_by(Event.tick, Event.created_at)
    result = await db.execute(stmt)
    events = result.scalars().all()
    
    timeline = []
    for e in events:
        timeline.append({
            "tick": e.tick,
            "type": e.type,
            "description": f"{e.type} occurred by {e.actor_id or 'World'}",
            "payload": e.payload
        })
    return timeline

@router.post("", response_model=GenerateWorldResponse)
@router.post("/generate", response_model=GenerateWorldResponse)
async def generate_world(request: GenerateWorldRequest, db: AsyncSession = Depends(get_db_session)):
    try:
        config = GeneratorConfig(
            name=request.name,
            seed=request.seed,
            cities=request.cities,
            characters=request.characters,
            factions=request.factions
        )
        
        generator = WorldGenerator(config)
        entities = generator.generate()
        
        db.add(entities["world"])
        db.add_all(entities["resources"])
        db.add_all(entities["cities"])
        db.add_all(entities["factions"])
        db.add_all(entities["characters"])
        db.add_all(entities["inventories"])
        db.add_all(entities["goals"])
        db.add_all(entities["relationships"])
        
        await db.commit()
        
        summary = (
            f"Generated world '{request.name}' with "
            f"{len(entities['cities'])} cities, "
            f"{len(entities['factions'])} factions, and "
            f"{len(entities['characters'])} characters."
        )
        
        return GenerateWorldResponse(world_id=entities["world"].id, summary=summary)
    
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{world_id}/simulation/start", response_model=SimulationResponse)
async def start_simulation(world_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(World).filter(World.id == world_id))
    world = result.scalars().first()
    if not world:
        raise HTTPException(status_code=404, detail="World not found")
        
    engine = SimulationEngine(world_id=world.id, initial_tick=world.current_tick, initial_status=world.simulation_status)
    engine.start()
    
    world.simulation_status = engine.clock.simulation_status.value
    await db.commit()
    
    return SimulationResponse(world_id=world.id, current_tick=world.current_tick, status=world.simulation_status)

@router.post("/{world_id}/simulation/pause", response_model=SimulationResponse)
async def pause_simulation(world_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(World).filter(World.id == world_id))
    world = result.scalars().first()
    if not world:
        raise HTTPException(status_code=404, detail="World not found")
        
    engine = SimulationEngine(world_id=world.id, initial_tick=world.current_tick, initial_status=world.simulation_status)
    engine.pause()
    
    world.simulation_status = engine.clock.simulation_status.value
    await db.commit()
    
    return SimulationResponse(world_id=world.id, current_tick=world.current_tick, status=world.simulation_status)

@router.post("/{world_id}/simulation/tick", response_model=SimulationResponse)
async def tick_simulation(world_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(World).filter(World.id == world_id))
    world = result.scalars().first()
    if not world:
        raise HTTPException(status_code=404, detail="World not found")
        
    engine = SimulationEngine(world_id=world.id, initial_tick=world.current_tick, initial_status=world.simulation_status)
    engine.advance_one_tick()
    
    world.current_tick = engine.clock.current_tick
    
    db_events = []
    for evt in engine.pending_events:
        db_events.append(Event(
            world_id=evt.world_id,
            tick=evt.tick,
            type="WorldTick",
            payload={"day": evt.day, "hour": evt.hour}
        ))
    db.add_all(db_events)
    await db.commit()
    
    return SimulationResponse(world_id=world.id, current_tick=world.current_tick, status=world.simulation_status)

@router.post("/{world_id}/simulation/advance", response_model=SimulationResponse)
async def advance_simulation(world_id: uuid.UUID, request: AdvanceSimulationRequest, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(World).filter(World.id == world_id))
    world = result.scalars().first()
    if not world:
        raise HTTPException(status_code=404, detail="World not found")
        
    engine = SimulationEngine(world_id=world.id, initial_tick=world.current_tick, initial_status=world.simulation_status)
    engine.advance_ticks(request.ticks)
    
    world.current_tick = engine.clock.current_tick
    
    db_events = []
    for evt in engine.pending_events:
        db_events.append(Event(
            world_id=evt.world_id,
            tick=evt.tick,
            type="WorldTick",
            payload={"day": evt.day, "hour": evt.hour}
        ))
    db.add_all(db_events)
    await db.commit()
    
    return SimulationResponse(world_id=world.id, current_tick=world.current_tick, status=world.simulation_status)

@router.post("/{world_id}/simulation/reset", response_model=SimulationResponse)
async def reset_simulation(world_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    # Reset simulation deletes all events, transactions, memories, and sets tick to 0
    # BUT we are going to do a proper reset: read original counts, delete world, and regenerate.
    result = await db.execute(select(World).where(World.id == world_id))
    world = result.scalars().first()
    if not world:
        raise HTTPException(status_code=404, detail="World not found")
        
    name = world.name
    try:
        seed = int(world.seed)
    except ValueError:
        seed = 42

    cities = await db.execute(select(City).where(City.world_id == world_id))
    chars = await db.execute(select(Character).where(Character.world_id == world_id))
    facts = await db.execute(select(Faction).where(Faction.world_id == world_id))
    
    c_count = len(cities.scalars().all())
    ch_count = len(chars.scalars().all())
    f_count = len(facts.scalars().all())
    
    # Cascade delete the existing world
    await db.delete(world)
    await db.flush()
    
    # Regenerate
    config = GeneratorConfig(
        name=name,
        seed=seed,
        cities=c_count,
        characters=ch_count,
        factions=f_count
    )
    generator = WorldGenerator(config)
    entities = generator.generate()
    
    # Assign the OLD id to the new world so it feels like a true reset in place
    entities["world"].id = world_id
    # Cascade ID changes to dependencies explicitly generated by WorldGenerator?
    # Actually WorldGenerator generated new world_id. We need to overwrite them.
    for entity_group in entities.values():
        if isinstance(entity_group, list):
            for e in entity_group:
                if hasattr(e, "world_id"):
                    e.world_id = world_id
                    
    db.add(entities["world"])
    db.add_all(entities["resources"])
    db.add_all(entities["cities"])
    db.add_all(entities["factions"])
    db.add_all(entities["characters"])
    db.add_all(entities["inventories"])
    db.add_all(entities["goals"])
    db.add_all(entities["relationships"])
    
    await db.commit()
    
    return SimulationResponse(world_id=world_id, current_tick=0, status="initialized")

@router.delete("/{world_id}")
async def delete_world(world_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(World).where(World.id == world_id))
    world = result.scalars().first()
    if not world:
        raise HTTPException(status_code=404, detail="World not found")
        
    await db.delete(world)
    await db.commit()
    return {"status": "success", "message": f"World {world_id} deleted."}

@router.post("/{world_id}/clone", response_model=GenerateWorldResponse)
async def clone_world(world_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    # To clone a world without mutating the original, we load it deeply and duplicate instances.
    result = await db.execute(
        select(World)
        .options(
            selectinload(World.cities),
            selectinload(World.factions),
            selectinload(World.characters).selectinload(Character.relationships_out),
            selectinload(World.characters).selectinload(Character.goals),
            selectinload(World.characters).selectinload(Character.memories),
            selectinload(World.characters).selectinload(Character.beliefs),
            selectinload(World.resources),
            selectinload(World.events)
        )
        .where(World.id == world_id)
    )
    
    world = result.scalars().first()
    if not world:
        raise HTTPException(status_code=404, detail="World not found")
        
    id_map = {}
    
    def copy_instance(instance):
        make_transient(instance)
        old_id = instance.id
        instance.id = uuid.uuid4()
        id_map[old_id] = instance.id
        return instance

    # 1. Clone the World
    make_transient(world)
    old_world_id = world.id
    new_world_id = uuid.uuid4()
    world.id = new_world_id
    world.name = f"{world.name} (Clone)"
    
    # 2. Clone Cities
    new_cities = []
    for city in world.cities:
        new_cities.append(copy_instance(city))
        
    # 3. Clone Factions
    new_factions = []
    for faction in world.factions:
        new_factions.append(copy_instance(faction))
        
    # 4. Clone Resources
    new_resources = []
    for resource in world.resources:
        new_resources.append(copy_instance(resource))
        
    # 5. Clone Characters and their dependents
    new_characters = []
    new_goals = []
    new_memories = []
    new_beliefs = []
    new_relationships = []
    
    for character in world.characters:
        char_goals = list(character.goals)
        char_mems = list(character.memories)
        char_beliefs = list(character.beliefs)
        char_rels = list(character.relationships_out)
        
        new_char = copy_instance(character)
        new_characters.append(new_char)
        
        for goal in char_goals:
            new_goals.append(copy_instance(goal))
            
        for mem in char_mems:
            new_memories.append(copy_instance(mem))
            
        for b in char_beliefs:
            new_beliefs.append(copy_instance(b))
            
        for rel in char_rels:
            new_relationships.append(copy_instance(rel))
            
    # 6. Clone Events
    new_events = []
    for event in world.events:
        new_events.append(copy_instance(event))
        
    # Also clone inventories manually since they attach to resources
    inv_res = await db.execute(select(Inventory).where(Inventory.resource_id.in_([r.id for r in world.resources]))) # Wait, old resource IDs are lost. Let's query by owner_id or just all in old world
    # Since Inventory doesn't have world_id directly, we find them by old owners
    old_owners = [old_world_id] + [k for k in id_map.keys()]
    inv_res = await db.execute(select(Inventory).where(Inventory.owner_id.in_(old_owners)))
    inventories = inv_res.scalars().all()
    new_inventories = []
    for inv in inventories:
        new_inv = copy_instance(inv)
        new_inventories.append(new_inv)

    # Now, remap foreign keys
    world.cities = new_cities
    world.factions = new_factions
    world.characters = new_characters
    world.resources = new_resources
    world.events = new_events
    
    for entity_list in [new_cities, new_factions, new_resources, new_characters, new_events]:
        for e in entity_list:
            e.world_id = new_world_id
            
    new_characters_map = {c.id: c for c in new_characters}
    
    for f in new_factions:
        if f.leader_id in id_map:
            new_char_id = id_map[f.leader_id]
            f.leader = new_characters_map[new_char_id]
            # Clear the raw FK to ensure post_update is utilized correctly by SQLAlchemy
            f.leader_id = None
        
    for c in new_characters:
        if c.city_id in id_map: c.city_id = id_map[c.city_id]
        if c.faction_id in id_map: c.faction_id = id_map[c.faction_id]
        
    for item_list in [new_goals, new_memories, new_beliefs]:
        for item in item_list:
            if item.character_id in id_map: item.character_id = id_map[item.character_id]
            
    for rel in new_relationships:
        if rel.source_character_id in id_map: rel.source_character_id = id_map[rel.source_character_id]
        if rel.target_character_id in id_map: rel.target_character_id = id_map[rel.target_character_id]
        
    for inv in new_inventories:
        if inv.owner_id in id_map: inv.owner_id = id_map[inv.owner_id]
        if inv.resource_id in id_map: inv.resource_id = id_map[inv.resource_id]
        
    db.add(world)
    db.add_all(new_inventories)
    db.add_all(new_goals)
    db.add_all(new_memories)
    db.add_all(new_beliefs)
    db.add_all(new_relationships)
    
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Clone failed: {e}")
        
    return GenerateWorldResponse(world_id=new_world_id, summary=f"Cloned world successfully to tick {world.current_tick}")
