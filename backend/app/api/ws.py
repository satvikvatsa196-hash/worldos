from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import uuid
import asyncio
from app.infrastructure.redis_client import redis_client
from app.infrastructure.database import AsyncSessionFactory
from sqlalchemy import select
from app.infrastructure.models import World
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[uuid.UUID, list[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, world_id: uuid.UUID) -> bool:
        await websocket.accept()
        
        # Verify world exists
        async with AsyncSessionFactory() as session:
            result = await session.execute(select(World).where(World.id == world_id))
            world = result.scalars().first()
            if not world:
                await websocket.close(code=1008, reason="Invalid world ID")
                return False
                
        if world_id not in self.active_connections:
            self.active_connections[world_id] = []
        self.active_connections[world_id].append(websocket)
        return True
        
    def disconnect(self, websocket: WebSocket, world_id: uuid.UUID):
        if world_id in self.active_connections:
            if websocket in self.active_connections[world_id]:
                self.active_connections[world_id].remove(websocket)
            if not self.active_connections[world_id]:
                del self.active_connections[world_id]

manager = ConnectionManager()

async def redis_listener(world_id: uuid.UUID):
    try:
        client = await redis_client.get_client()
        pubsub = client.pubsub()
        await pubsub.subscribe(f"world_{world_id}_events")
        
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = message["data"]
                if world_id in manager.active_connections:
                    disconnected = []
                    for ws in manager.active_connections[world_id]:
                        try:
                            await ws.send_text(data)
                        except Exception:
                            disconnected.append(ws)
                    for ws in disconnected:
                        manager.disconnect(ws, world_id)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Redis listener error for world {world_id}: {e}")
    finally:
        try:
            await pubsub.unsubscribe(f"world_{world_id}_events")
        except Exception:
            pass

@router.websocket("/worlds/{world_id}")
async def websocket_endpoint(websocket: WebSocket, world_id: uuid.UUID):
    is_connected = await manager.connect(websocket, world_id)
    if not is_connected:
        return
        
    listener_task = asyncio.create_task(redis_listener(world_id))
    
    try:
        while True:
            # Keep alive / ping pong mechanism
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, world_id)
    finally:
        listener_task.cancel()
