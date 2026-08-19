import pytest
import uuid
from app.domain.economy.models import InventoryState, WorldEconomyState
from app.domain.economy.engines import CharacterEconomySnapshot, ProductionEngine, ConsumptionEngine

def test_inventory_operations():
    inv = InventoryState()
    
    # Check default
    assert inv.get_quantity("grain") == 0.0
    
    # Test valid add
    inv.add("grain", 10.0)
    assert inv.get_quantity("grain") == 10.0
    
    # Test valid remove
    inv.remove("grain", 4.0)
    assert inv.get_quantity("grain") == 6.0
    
    # Test invalid operations
    with pytest.raises(ValueError):
        inv.add("grain", -5.0)
        
    with pytest.raises(ValueError):
        inv.remove("grain", -2.0)
        
    with pytest.raises(ValueError):
        inv.remove("grain", 10.0) # Insufficient amount

def test_production_engine():
    engine = ProductionEngine()
    world_id = uuid.uuid4()
    state = WorldEconomyState(world_id=world_id)
    
    farmer_inv = InventoryState()
    miner_inv = InventoryState()
    
    chars = [
        CharacterEconomySnapshot(character_id=uuid.uuid4(), occupation="farmer", inventory=farmer_inv),
        CharacterEconomySnapshot(character_id=uuid.uuid4(), occupation="miner", inventory=miner_inv)
    ]
    
    events = engine.process_tick(world_id, 1, chars, state)
    
    assert len(events) == 2
    
    # Check Farmer
    assert farmer_inv.get_quantity("grain") == 5.0
    assert farmer_inv.get_quantity("iron") == 0.0
    
    # Check Miner
    assert miner_inv.get_quantity("iron") == 2.0
    
    # Check World State Trackers
    assert state.total_supply["grain"] == 5.0
    assert state.total_supply["iron"] == 2.0
    
    # Check events
    grain_event = next(e for e in events if e.resource_name == "grain")
    assert grain_event.quantity == 5.0
    assert grain_event.actor_id == chars[0].character_id

def test_consumption_engine():
    engine = ConsumptionEngine()
    world_id = uuid.uuid4()
    state = WorldEconomyState(world_id=world_id)
    
    # Populate initial supply manually to simulate existing inventory
    soldier_inv = InventoryState(items={"food": 5.0})
    citizen_inv = InventoryState(items={"food": 0.5})
    
    state.track_production("food", 5.5)
    
    chars = [
        CharacterEconomySnapshot(character_id=uuid.uuid4(), occupation="soldier", inventory=soldier_inv),
        CharacterEconomySnapshot(character_id=uuid.uuid4(), occupation="citizen", inventory=citizen_inv)
    ]
    
    events = engine.process_tick(world_id, 1, chars, state)
    
    # Soldier demands 3.0, consumes 3.0
    assert soldier_inv.get_quantity("food") == 2.0
    
    # Citizen demands 1.0, but only has 0.5, consumes 0.5
    assert citizen_inv.get_quantity("food") == 0.0
    
    # Check events
    assert len(events) == 2
    
    # World state checks
    assert state.total_demand["food"] == 4.0 # 3.0 + 1.0
    assert state.total_supply["food"] == 2.0 # 5.5 - 3.0 - 0.5

def test_resource_conservation():
    prod_engine = ProductionEngine()
    cons_engine = ConsumptionEngine()
    
    world_id = uuid.uuid4()
    state = WorldEconomyState(world_id=world_id)
    
    farmer_id = uuid.uuid4()
    farmer_inv = InventoryState(items={"food": 2.0}) # Initial state must be tracked
    state.track_production("food", 2.0)
    
    soldier_id = uuid.uuid4()
    soldier_inv = InventoryState(items={"food": 5.0, "iron": 10.0})
    state.track_production("food", 5.0)
    state.track_production("iron", 10.0)
    
    chars = [
        CharacterEconomySnapshot(character_id=farmer_id, occupation="farmer", inventory=farmer_inv),
        CharacterEconomySnapshot(character_id=soldier_id, occupation="soldier", inventory=soldier_inv)
    ]
    
    inventories = {
        farmer_id: farmer_inv,
        soldier_id: soldier_inv
    }
    
    # Initial invariant check
    assert state.verify_conservation(inventories) is True
    
    # Process production tick
    prod_engine.process_tick(world_id, 1, chars, state)
    
    # Invariant should hold after production
    assert state.verify_conservation(inventories) is True
    
    # Process consumption tick
    cons_engine.process_tick(world_id, 1, chars, state)
    
    # Invariant should hold after consumption
    assert state.verify_conservation(inventories) is True
    
    # Let's forcefully break invariant and ensure it catches it
    farmer_inv.items["magical_grain"] = 50.0
    assert state.verify_conservation(inventories) is False
