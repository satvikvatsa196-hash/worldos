from typing import Optional, List
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.persistence.repository import BaseRepository
from app.domain.interfaces import IWorldRepository, ICityRepository, ICharacterRepository, IEventRepository, IMemoryRepository
from app.infrastructure.models import World, City, Character, Event, Memory

class WorldRepository(BaseRepository[World, uuid.UUID], IWorldRepository[World]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, World)

    async def get_by_name(self, name: str) -> Optional[World]:
        stmt = select(World).where(World.name == name)
        result = await self.session.execute(stmt)
        return result.scalars().first()

class CityRepository(BaseRepository[City, uuid.UUID], ICityRepository[City]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, City)

    async def get_by_world_id(self, world_id: uuid.UUID) -> List[City]:
        stmt = select(City).where(City.world_id == world_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

class CharacterRepository(BaseRepository[Character, uuid.UUID], ICharacterRepository[Character]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Character)

    async def get_by_city_id(self, city_id: uuid.UUID) -> List[Character]:
        stmt = select(Character).where(Character.city_id == city_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

class EventRepository(BaseRepository[Event, uuid.UUID], IEventRepository[Event]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Event)

    async def get_by_world_and_tick(self, world_id: uuid.UUID, tick: int) -> List[Event]:
        stmt = select(Event).where(Event.world_id == world_id, Event.tick == tick)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

class MemoryRepository(BaseRepository[Memory, uuid.UUID], IMemoryRepository[Memory]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Memory)

    async def get_by_character_id(self, character_id: uuid.UUID) -> List[Memory]:
        stmt = select(Memory).where(Memory.character_id == character_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
