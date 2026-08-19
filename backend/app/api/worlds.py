from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.infrastructure.database import get_db_session
from app.domain.simulation.generator import WorldGenerator, GeneratorConfig
from sqlalchemy import select
from app.infrastructure.models import World, Event
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
        
        # Save to database
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
