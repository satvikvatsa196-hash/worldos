import uuid
from typing import List, Dict, Tuple
from pydantic import BaseModel
from app.domain.economy.models import (
    InventoryState, 
    ProductionEvent, 
    ConsumptionEvent, 
    WorldEconomyState
)

class CharacterEconomySnapshot(BaseModel):
    character_id: uuid.UUID
    occupation: str
    inventory: InventoryState

class ProductionEngine:
    def __init__(self):
        # Maps occupation to a list of (resource_name, quantity_per_tick)
        self.production_rules = {
            "farmer": [("grain", 5.0)],
            "miner": [("iron", 2.0)],
            "woodcutter": [("wood", 3.0)],
            "merchant": [("trading_activity", 1.0)]
        }

    def process_tick(
        self, 
        world_id: uuid.UUID, 
        tick: int, 
        characters: List[CharacterEconomySnapshot], 
        economy_state: WorldEconomyState
    ) -> List[ProductionEvent]:
        
        events = []
        for char in characters:
            rules = self.production_rules.get(char.occupation.lower(), [])
            for resource_name, qty in rules:
                char.inventory.add(resource_name, qty)
                economy_state.track_production(resource_name, qty)
                
                events.append(ProductionEvent(
                    world_id=world_id,
                    tick=tick,
                    actor_id=char.character_id,
                    resource_name=resource_name,
                    quantity=qty
                ))
        return events

class ConsumptionEngine:
    def __init__(self):
        # Maps occupation to a list of (resource_name, demand_quantity_per_tick)
        self.consumption_rules = {
            "citizen": [("food", 1.0)],
            "worker": [("food", 2.0)],
            "soldier": [("food", 3.0)],
            "farmer": [("food", 1.5)],
            "miner": [("food", 2.0)],
            "woodcutter": [("food", 2.0)],
            "merchant": [("food", 1.0)]
        }
        
    def process_tick(
        self, 
        world_id: uuid.UUID, 
        tick: int, 
        characters: List[CharacterEconomySnapshot], 
        economy_state: WorldEconomyState
    ) -> List[ConsumptionEvent]:
        
        events = []
        for char in characters:
            rules = self.consumption_rules.get(char.occupation.lower(), [("food", 1.0)])
            for resource_name, qty in rules:
                # Always track the demand
                economy_state.track_demand(resource_name, qty)
                
                # Check available inventory
                available = char.inventory.get_quantity(resource_name)
                consumed = min(available, qty)
                
                if consumed > 0:
                    char.inventory.remove(resource_name, consumed)
                    economy_state.track_consumption(resource_name, consumed)
                    
                    events.append(ConsumptionEvent(
                        world_id=world_id,
                        tick=tick,
                        actor_id=char.character_id,
                        resource_name=resource_name,
                        quantity=consumed
                    ))
        return events
