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
async def test_world_lifecycle():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Create World using POST /worlds
        gen_payload = {
            "name": "Lifecycle Test World",
            "seed": 100,
            "cities": 2,
            "characters": 10,
            "factions": 2
        }
        res = await client.post("/worlds", json=gen_payload)
        data = res.json()
        if res.status_code != 200:
            with open("lifecycle_error.txt", "w") as f:
                f.write(str(data))
        assert res.status_code == 200, f"Generate world failed: {data}"
        world_id = res.json()["world_id"]
        
        # Advance simulation
        await client.post(f"/worlds/{world_id}/simulation/start")
        await client.post(f"/worlds/{world_id}/simulation/advance", json={"ticks": 2})
        
        # 2. Clone World
        clone_res = await client.post(f"/worlds/{world_id}/clone")
        if clone_res.status_code != 200:
            with open("clone_error.txt", "w") as f:
                f.write(str(clone_res.json()))
        assert clone_res.status_code == 200
        cloned_world_id = clone_res.json()["world_id"]
        assert cloned_world_id != world_id
        
        # Verify Clone State matches Original State
        orig_state = await client.get(f"/worlds/{world_id}/state")
        clone_state = await client.get(f"/worlds/{cloned_world_id}/state")
        
        assert orig_state.status_code == 200
        assert clone_state.status_code == 200
        
        os_json = orig_state.json()
        cs_json = clone_state.json()
        
        assert os_json["world"]["tick"] == 2
        assert cs_json["world"]["tick"] == 2
        
        assert len(os_json["cities"]) == len(cs_json["cities"]) == 2
        assert len(os_json["characters"]) == len(cs_json["characters"]) == 10
        assert len(os_json["factions"]) == len(cs_json["factions"]) == 2
        
        # 3. Test Independence
        # Advance cloned world
        await client.post(f"/worlds/{cloned_world_id}/simulation/start")
        await client.post(f"/worlds/{cloned_world_id}/simulation/advance", json={"ticks": 5})
        
        orig_state_updated = (await client.get(f"/worlds/{world_id}/state")).json()
        clone_state_updated = (await client.get(f"/worlds/{cloned_world_id}/state")).json()
        
        # Original remains at tick 2, Clone advanced to 7 (2+5)
        assert orig_state_updated["world"]["tick"] == 2
        assert clone_state_updated["world"]["tick"] == 7
        
        # 4. Reset Original World
        reset_res = await client.post(f"/worlds/{world_id}/simulation/reset")
        assert reset_res.status_code == 200
        assert reset_res.json()["current_tick"] == 0
        
        orig_state_reset = (await client.get(f"/worlds/{world_id}/state")).json()
        assert orig_state_reset["world"]["tick"] == 0
        assert len(orig_state_reset["characters"]) == 10  # Ensured regeneration worked
        
        # 5. Delete World
        del_res = await client.delete(f"/worlds/{world_id}")
        assert del_res.status_code == 200
        
        get_res = await client.get(f"/worlds/{world_id}")
        assert get_res.status_code == 404
