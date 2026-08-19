import pytest
import uuid
from app.domain.economy.models import WorldEconomyState, InventoryState
from app.domain.economy.market import MarketEngine

def test_price_changes_based_on_scarcity():
    engine = MarketEngine(base_prices={"food": 1.0})
    world_id = uuid.uuid4()
    
    # Scenario 1: Demand > Supply (Price increases)
    state_high_demand = WorldEconomyState(world_id=world_id)
    state_high_demand.track_production("food", 10.0)
    state_high_demand.track_demand("food", 50.0)
    
    events = engine.update_prices(world_id, 1, state_high_demand)
    
    assert len(events) == 1
    assert events[0].new_price > 1.0
    assert state_high_demand.current_prices["food"] > 1.0

def test_price_bounds():
    engine = MarketEngine(base_prices={"food": 1.0})
    world_id = uuid.uuid4()
    
    # Extreme demand
    state_extreme = WorldEconomyState(world_id=world_id)
    state_extreme.track_production("food", 1.0)
    state_extreme.track_demand("food", 1000.0)
    
    engine.update_prices(world_id, 1, state_extreme)
    
    # Max multiplier is 5.0
    assert state_extreme.current_prices["food"] <= 5.0

def test_successful_transaction():
    engine = MarketEngine()
    world_id = uuid.uuid4()
    state = WorldEconomyState(world_id=world_id)
    state.current_prices["wood"] = 2.0
    
    buyer_inv = InventoryState(items={"money": 10.0})
    seller_inv = InventoryState(items={"wood": 5.0})
    
    buyer_id = uuid.uuid4()
    seller_id = uuid.uuid4()
    
    event = engine.execute_transaction(
        world_id=world_id,
        tick=1,
        buyer_id=buyer_id,
        buyer_inv=buyer_inv,
        seller_id=seller_id,
        seller_inv=seller_inv,
        resource_name="wood",
        quantity=3.0,
        economy_state=state
    )
    
    # Wood cost = 3.0 * 2.0 = 6.0
    assert buyer_inv.get_quantity("money") == 4.0
    assert seller_inv.get_quantity("money") == 6.0
    
    assert buyer_inv.get_quantity("wood") == 3.0
    assert seller_inv.get_quantity("wood") == 2.0
    
    assert event.total_price == 6.0

def test_failed_transaction_insufficient_money():
    engine = MarketEngine()
    world_id = uuid.uuid4()
    state = WorldEconomyState(world_id=world_id)
    state.current_prices["wood"] = 2.0
    
    buyer_inv = InventoryState(items={"money": 5.0}) # Needs 6.0
    seller_inv = InventoryState(items={"wood": 5.0})
    
    with pytest.raises(ValueError, match="Buyer does not have enough money"):
        engine.execute_transaction(
            world_id=world_id,
            tick=1,
            buyer_id=uuid.uuid4(),
            buyer_inv=buyer_inv,
            seller_id=uuid.uuid4(),
            seller_inv=seller_inv,
            resource_name="wood",
            quantity=3.0,
            economy_state=state
        )

def test_failed_transaction_insufficient_resource():
    engine = MarketEngine()
    world_id = uuid.uuid4()
    state = WorldEconomyState(world_id=world_id)
    
    buyer_inv = InventoryState(items={"money": 100.0})
    seller_inv = InventoryState(items={"wood": 2.0}) # Needs 3.0
    
    with pytest.raises(ValueError, match="Seller does not have enough"):
        engine.execute_transaction(
            world_id=world_id,
            tick=1,
            buyer_id=uuid.uuid4(),
            buyer_inv=buyer_inv,
            seller_id=uuid.uuid4(),
            seller_inv=seller_inv,
            resource_name="wood",
            quantity=3.0,
            economy_state=state
        )

def test_conservation_during_transaction():
    engine = MarketEngine()
    world_id = uuid.uuid4()
    state = WorldEconomyState(world_id=world_id)
    
    buyer_id = uuid.uuid4()
    seller_id = uuid.uuid4()
    
    buyer_inv = InventoryState(items={"money": 50.0, "wood": 0.0})
    seller_inv = InventoryState(items={"money": 10.0, "wood": 20.0})
    
    inventories = {buyer_id: buyer_inv, seller_id: seller_inv}
    
    # Initial state tracking
    state.track_production("money", 60.0)
    state.track_production("wood", 20.0)
    
    # Verify pre-transaction conservation
    assert state.verify_conservation(inventories) is True
    
    engine.execute_transaction(
        world_id=world_id,
        tick=1,
        buyer_id=buyer_id,
        buyer_inv=buyer_inv,
        seller_id=seller_id,
        seller_inv=seller_inv,
        resource_name="wood",
        quantity=5.0,
        economy_state=state
    )
    
    # Verify post-transaction conservation
    assert state.verify_conservation(inventories) is True
