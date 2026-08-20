from typing import List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.models import Event
from app.domain.event.models import WorldEvent, EventType

class EventStore:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, event: WorldEvent) -> None:
        db_event = Event(
            id=event.id,
            world_id=event.world_id,
            tick=event.tick,
            type=event.type.value,
            actor_id=event.actor_id,
            target_id=event.target_id,
            city_id=event.city_id,
            faction_id=event.faction_id,
            payload=event.payload,
            parent_event_id=event.parent_event_id,
            created_at=event.created_at
        )
        self.session.add(db_event)

    async def get_events(
        self,
        world_id: Optional[uuid.UUID] = None,
        tick: Optional[int] = None,
        event_type: Optional[EventType] = None,
        actor_id: Optional[uuid.UUID] = None,
        city_id: Optional[uuid.UUID] = None,
        faction_id: Optional[uuid.UUID] = None,
        parent_event_id: Optional[uuid.UUID] = None,
    ) -> List[WorldEvent]:
        stmt = select(Event)
        if world_id:
            stmt = stmt.where(Event.world_id == world_id)
        if tick is not None:
            stmt = stmt.where(Event.tick == tick)
        if event_type:
            stmt = stmt.where(Event.type == event_type.value)
        if actor_id:
            stmt = stmt.where(Event.actor_id == actor_id)
        if city_id:
            stmt = stmt.where(Event.city_id == city_id)
        if faction_id:
            stmt = stmt.where(Event.faction_id == faction_id)
        if parent_event_id:
            stmt = stmt.where(Event.parent_event_id == parent_event_id)

        stmt = stmt.order_by(Event.created_at.asc())
        result = await self.session.execute(stmt)
        db_events = result.scalars().all()

        return [
            WorldEvent(
                id=e.id,
                world_id=e.world_id,
                tick=e.tick,
                type=EventType(e.type),
                actor_id=e.actor_id,
                target_id=e.target_id,
                city_id=e.city_id,
                faction_id=e.faction_id,
                payload=e.payload,
                parent_event_id=e.parent_event_id,
                created_at=e.created_at
            ) for e in db_events
        ]
