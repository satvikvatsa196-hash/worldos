from pydantic import BaseModel, ConfigDict
from typing import Dict, List
import uuid
from app.domain.economy.models import WorldEconomyState, InventoryState

class PriceChangedEvent(BaseModel):
    model_config = ConfigDict(frozen=True)
    world_id: uuid.UUID
    tick: int
    resource_name: str
    previous_price: float
    new_price: float
    reason: str

class MarketTransactionEvent(BaseModel):
    model_config = ConfigDict(frozen=True)
    world_id: uuid.UUID
    tick: int
    buyer_id: uuid.UUID
    seller_id: uuid.UUID
    resource_name: str
    quantity: float
    unit_price: float
    total_price: float

class MarketEngine:
    def __init__(self, base_prices: Dict[str, float] = None):
        self.base_prices = base_prices or {
            "food": 1.0,
            "grain": 0.5,
            "iron": 2.0,
            "wood": 1.0,
            "trading_activity": 1.5
        }
        self.price_elasticity = 0.1

    def update_prices(self, world_id: uuid.UUID, tick: int, economy_state: WorldEconomyState) -> List[PriceChangedEvent]:
        events = []
        
        for resource, base_price in self.base_prices.items():
            supply = economy_state.total_supply.get(resource, 0.0)
            demand = economy_state.total_demand.get(resource, 0.0)
            
            # Simple, explainable pricing formula:
            # Price = Base Price * (1 + (Demand - Supply) / (Supply + 1) * Elasticity)
            imbalance_factor = (demand - supply) / (supply + 1.0)
            
            # Bound multiplier between 0.1 and 5.0 to prevent extreme runaway prices
            multiplier = 1.0 + (imbalance_factor * self.price_elasticity)
            multiplier = max(0.1, min(5.0, multiplier))
            
            new_price = round(base_price * multiplier, 2)
            previous_price = economy_state.current_prices.get(resource, base_price)
            
            if abs(previous_price - new_price) > 0.001:
                reason = f"Supply: {supply}, Demand: {demand}, Imbalance: {round(imbalance_factor, 2)}"
                
                events.append(PriceChangedEvent(
                    world_id=world_id,
                    tick=tick,
                    resource_name=resource,
                    previous_price=previous_price,
                    new_price=new_price,
                    reason=reason
                ))
                
            economy_state.current_prices[resource] = new_price
                    
        return events

    def execute_transaction(
        self,
        world_id: uuid.UUID,
        tick: int,
        buyer_id: uuid.UUID,
        buyer_inv: InventoryState,
        seller_id: uuid.UUID,
        seller_inv: InventoryState,
        resource_name: str,
        quantity: float,
        economy_state: WorldEconomyState
    ) -> MarketTransactionEvent:
        
        if quantity <= 0:
            raise ValueError("Transaction quantity must be positive")
            
        unit_price = economy_state.current_prices.get(resource_name)
        if unit_price is None:
            unit_price = self.base_prices.get(resource_name, 1.0)
            
        total_price = round(unit_price * quantity, 2)
        
        # Validation
        if seller_inv.get_quantity(resource_name) < quantity:
            raise ValueError(f"Seller does not have enough {resource_name}")
            
        if buyer_inv.get_quantity("money") < total_price:
            raise ValueError("Buyer does not have enough money")
            
        # Execute transaction transactionally (in-memory)
        buyer_inv.remove("money", total_price)
        seller_inv.add("money", total_price)
        
        seller_inv.remove(resource_name, quantity)
        buyer_inv.add(resource_name, quantity)
        
        return MarketTransactionEvent(
            world_id=world_id,
            tick=tick,
            buyer_id=buyer_id,
            seller_id=seller_id,
            resource_name=resource_name,
            quantity=quantity,
            unit_price=unit_price,
            total_price=total_price
        )
