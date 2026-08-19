from pydantic import BaseModel, ConfigDict, Field
from typing import Dict
import uuid

class ResourceTransaction(BaseModel):
    model_config = ConfigDict(frozen=True)
    world_id: uuid.UUID
    tick: int
    actor_id: uuid.UUID
    resource_name: str
    quantity: float

class ProductionEvent(ResourceTransaction):
    pass

class ConsumptionEvent(ResourceTransaction):
    pass

class InventoryState(BaseModel):
    # Mapping of resource_name to quantity
    items: Dict[str, float] = Field(default_factory=dict)
    
    def get_quantity(self, resource_name: str) -> float:
        return self.items.get(resource_name, 0.0)

    def add(self, resource_name: str, quantity: float) -> None:
        if quantity < 0:
            raise ValueError("Cannot add negative quantity")
        self.items[resource_name] = self.get_quantity(resource_name) + quantity

    def remove(self, resource_name: str, quantity: float) -> None:
        if quantity < 0:
            raise ValueError("Cannot remove negative quantity")
        current = self.get_quantity(resource_name)
        if current < quantity:
            raise ValueError(f"Insufficient {resource_name}: have {current}, need {quantity}")
        self.items[resource_name] = current - quantity

class WorldEconomyState(BaseModel):
    world_id: uuid.UUID
    total_supply: Dict[str, float] = Field(default_factory=dict)
    total_demand: Dict[str, float] = Field(default_factory=dict)
    current_prices: Dict[str, float] = Field(default_factory=dict)
    
    def track_production(self, resource_name: str, quantity: float) -> None:
        self.total_supply[resource_name] = self.total_supply.get(resource_name, 0.0) + quantity

    def track_consumption(self, resource_name: str, quantity: float) -> None:
        self.total_supply[resource_name] = self.total_supply.get(resource_name, 0.0) - quantity
        
    def track_demand(self, resource_name: str, quantity: float) -> None:
        self.total_demand[resource_name] = self.total_demand.get(resource_name, 0.0) + quantity

    def verify_conservation(self, inventories: Dict[uuid.UUID, InventoryState]) -> bool:
        """
        Validates that no resources have magically appeared or disappeared.
        The sum of all individual inventories must perfectly match the tracked total supply.
        """
        calculated_supply: Dict[str, float] = {}
        for inv in inventories.values():
            for res, qty in inv.items.items():
                calculated_supply[res] = calculated_supply.get(res, 0.0) + qty
                
        for res, qty in self.total_supply.items():
            calc_qty = calculated_supply.get(res, 0.0)
            if abs(qty - calc_qty) > 0.001:
                return False
                
        for res, calc_qty in calculated_supply.items():
            qty = self.total_supply.get(res, 0.0)
            if abs(qty - calc_qty) > 0.001:
                return False
                
        return True
