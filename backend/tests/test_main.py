import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_health_check():
    from app.infrastructure.redis_client import redis_client
    redis_client.redis = None # Reset for the new event loop
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        data = response.json()
        if response.status_code != 200:
            with open("health_error.txt", "w") as f:
                f.write(str(data))
        assert response.status_code == 200, f"Health check failed: {data}"
        assert data == {"status": "ok", "service": "WORLDOS", "database": "ok", "redis": "ok"}
