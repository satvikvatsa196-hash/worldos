from typing import Callable, Dict, List, Awaitable
from app.domain.event.models import WorldEvent, EventType
import asyncio
from app.infrastructure.redis_client import redis_client

EventHandler = Callable[[WorldEvent], Awaitable[None]]

class EventBus:
    def __init__(self):
        self._subscribers: Dict[EventType, List[EventHandler]] = {}

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    async def publish(self, event: WorldEvent) -> None:
        handlers = self._subscribers.get(event.type, [])
        if handlers:
            await asyncio.gather(*(handler(event) for handler in handlers))
            
        # Publish to Redis for real-time WebSocket streaming
        try:
            client = await redis_client.get_client()
            # event.model_dump_json() serializes UUID and datetime correctly
            await client.publish(f"world_{event.world_id}_events", event.model_dump_json())
        except Exception:
            pass # Fail gracefully if Redis is unavailable
