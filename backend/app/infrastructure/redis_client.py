from redis.asyncio import Redis, from_url
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        self.redis: Redis | None = None

    async def connect(self):
        try:
            self.redis = await from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis.ping()
            logger.info("Successfully connected to Redis.")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def close(self):
        if self.redis is not None:
            await self.redis.aclose()
            logger.info("Closed Redis connection.")

    async def get_client(self) -> Redis:
        if self.redis is None:
            await self.connect()
        return self.redis

redis_client = RedisClient()
