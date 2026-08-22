import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
import uuid

from app.main import app
from app.infrastructure.database import Base, engine

@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_world_persistence_flow():
    world_id = None
    
    # Session 1: Simulate the application running for the first time
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Create World
        gen_payload = {
            "name": "Persistence Test World",
            "seed": 42,
            "cities": 1,
            "characters": 5,
            "factions": 1
        }
        res = await client.post("/worlds/generate", json=gen_payload)
        assert res.status_code == 200, res.text
        world_id = res.json()["world_id"]
        
        # 2. Run simulation
        res = await client.post(f"/worlds/{world_id}/simulation/start")
        assert res.status_code == 200
        
        # Advance ticks
        res = await client.post(f"/worlds/{world_id}/simulation/advance", json={"ticks": 3})
        assert res.status_code == 200
        assert res.json()["current_tick"] >= 3
        
    # 3. Restart application simulation
    # The database state is persisted (SQLite or test DB used by `engine`). 
    # Re-instantiating the AsyncClient simulates a fresh restart handling new requests.
    
    # Session 2: After Application Restart
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as new_client:
        # 4. Reload world
        res = await new_client.get(f"/worlds/{world_id}")
        assert res.status_code == 200
        world_data = res.json()
        assert world_data["name"] == "Persistence Test World"
        assert world_data["current_tick"] >= 3
        assert world_data["cities_count"] == 1
        assert world_data["characters_count"] == 5
        assert world_data["factions_count"] == 1
        
        # 5. Verify state
        state_res = await new_client.get(f"/worlds/{world_id}/state")
        assert state_res.status_code == 200
        state = state_res.json()
        
        assert state["world"]["id"] == world_id
        assert state["world"]["tick"] >= 3
        assert len(state["cities"]) == 1
        assert len(state["characters"]) == 5
        assert len(state["factions"]) == 1
        
        # 6. Verify events (filtering & pagination test)
        events_res = await new_client.get(f"/worlds/{world_id}/events?limit=2&skip=0")
        assert events_res.status_code == 200
        events = events_res.json()
        assert len(events) == 2  # Due to limit
        
        # 7. Verify timeline
        timeline_res = await new_client.get(f"/worlds/{world_id}/timeline")
        assert timeline_res.status_code == 200
        timeline = timeline_res.json()
        # Should have WorldTick events since we advanced 3 ticks
        assert len(timeline) >= 3
        assert all("tick" in e for e in timeline)
        assert all("description" in e for e in timeline)
