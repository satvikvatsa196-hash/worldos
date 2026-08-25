from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import uuid
import asyncio
from app.infrastructure.redis_client import redis_client
from app.infrastructure.database import AsyncSessionFactory
from sqlalchemy import select
from app.infrastructure.models import World
from app.core.telemetry import TraceLogger, metrics

logger = TraceLogger(__name__)

router = APIRouter(tags=["websocket"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[uuid.UUID, list[WebSocket]] = {}
        self.listeners: dict[uuid.UUID, asyncio.Task] = {}
        
    async def connect(self, websocket: WebSocket, world_id: uuid.UUID) -> bool:
        logger.info(f"Attempting to accept WebSocket connection for world {world_id}")
        await websocket.accept()
        logger.info(f"WebSocket accepted for world {world_id}")
        
        # Verify world exists
        async with AsyncSessionFactory() as session:
            result = await session.execute(select(World).where(World.id == world_id))
            world = result.scalars().first()
            if not world:
                await websocket.close(code=1008, reason="Invalid world ID")
                return False
                
        if world_id not in self.active_connections:
            self.active_connections[world_id] = []
            self.listeners[world_id] = asyncio.create_task(self._redis_listener(world_id))
            
        self.active_connections[world_id].append(websocket)
        metrics.inc_gauge("websocket_connections", 1)
        return True
        
    def disconnect(self, websocket: WebSocket, world_id: uuid.UUID):
        if world_id in self.active_connections:
            if websocket in self.active_connections[world_id]:
                self.active_connections[world_id].remove(websocket)
                metrics.inc_gauge("websocket_connections", -1)
            if not self.active_connections[world_id]:
                del self.active_connections[world_id]
                if world_id in self.listeners:
                    self.listeners[world_id].cancel()
                    del self.listeners[world_id]

    async def _redis_listener(self, world_id: uuid.UUID):
        try:
            client = await redis_client.get_client()
            pubsub = client.pubsub()
            await pubsub.subscribe(f"world_{world_id}_events")
            
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"]
                    logger.info(f"Redis listener received message for world {world_id}")
                    if world_id in self.active_connections:
                        disconnected = []
                        for ws in self.active_connections[world_id]:
                            try:
                                text_data = data.decode("utf-8") if isinstance(data, bytes) else str(data)
                                logger.info(f"Sending message to frontend: {text_data[:50]}...")
                                await ws.send_text(text_data)
                            except Exception:
                                disconnected.append(ws)
                        for ws in disconnected:
                            self.disconnect(ws, world_id)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Redis listener error for world {world_id}: {e}")
        finally:
            try:
                await pubsub.unsubscribe(f"world_{world_id}_events")
            except Exception:
                pass

manager = ConnectionManager()

# Note: explicitly including /ws prefix because some FastAPI versions drop APIRouter prefix on websockets
@router.websocket("/ws/worlds/{world_id}")
async def websocket_endpoint(websocket: WebSocket, world_id: uuid.UUID):
    logger.info(f"WebSocket endpoint hit for world {world_id}")
    is_connected = await manager.connect(websocket, world_id)
    if not is_connected:
        return
        
    try:
        while True:
            # Keep alive / ping pong mechanism
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, world_id)
