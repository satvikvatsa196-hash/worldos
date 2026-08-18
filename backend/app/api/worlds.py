from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.infrastructure.database import get_db_session
from app.domain.simulation.generator import WorldGenerator, GeneratorConfig

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
