import pytest
import uuid
import json
import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.infrastructure.database import Base, engine, AsyncSessionFactory
from app.infrastructure.models import World
from app.domain.event.models import WorldEvent, EventType
from app.domain.event.bus import EventBus
from app.infrastructure.redis_client import redis_client
from starlette.websockets import WebSocketDisconnect

@pytest.mark.asyncio
async def test_websocket_streaming():
    world_id = uuid.uuid4()
    
    # 1. Setup DB
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        
    async with AsyncSessionFactory() as session:
        world = World(id=world_id, name="WS Test", seed="123", current_tick=0, simulation_status="initialized")
        session.add(world)
        await session.commit()
        
    # We will use httpx AsyncClient for websocket testing or just mock the websocket since TestClient is sync.
    # Actually, Starlette's TestClient websocket context manager is synchronous, so we can't easily await async functions inside it.
    # To fix this, we will run the TestClient in a separate thread or just mock the redis_listener for this integration test.
    # Wait, the easiest way to test it without loop conflicts is to run the exact code that triggers the WS.
    
    # Let's use a background task to publish the event so we don't block the TestClient.
    def run_test():
        with TestClient(app) as client:
            invalid_id = uuid.uuid4()
            with pytest.raises(WebSocketDisconnect) as e:
                with client.websocket_connect(f"/ws/worlds/{invalid_id}") as websocket:
                    websocket.receive_text()
            assert e.value.code == 1008
            
            with client.websocket_connect(f"/ws/worlds/{world_id}") as websocket:
                websocket.send_text("ping")
                assert websocket.receive_text() == "pong"
                
                # Directly publish to redis using a sync wrapper that creates its own redis connection to avoid loop sharing
                import redis
                from app.core.config import settings
                sync_r = redis.Redis.from_url(settings.REDIS_URL)
                
                event = WorldEvent(
                    world_id=world_id, tick=1, type=EventType.WORLD_TICK, payload={"message": "Tick started"}
                )
                # Publish raw JSON to redis
                sync_r.publish(f"world_{world_id}_events", event.model_dump_json())
                
                event_data = websocket.receive_text()
                event_dict = json.loads(event_data)
                
                assert event_dict["world_id"] == str(world_id)
                assert event_dict["tick"] == 1
                assert event_dict["payload"]["message"] == "Tick started"
                
                sync_r.close()

    # Run the synchronous test wrapper
    await asyncio.to_thread(run_test)
    
    # CRITICAL: Reset the global redis_client because TestClient started it in a different event loop
    from app.infrastructure.redis_client import redis_client
    redis_client.redis = None
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
