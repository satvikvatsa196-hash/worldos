from enum import Enum
from pydantic import BaseModel, Field
import uuid
from typing import Dict, Any, List, Optional

class PolicyType(str, Enum):
    TAX = "TAX"
    FOOD_PRICE = "FOOD_PRICE"
    TRADE = "TRADE"
    WAGE = "WAGE"
    SUBSIDY = "SUBSIDY"
    MILITARY_SPENDING = "MILITARY_SPENDING"
    MARKET_REGULATION = "MARKET_REGULATION"

class Policy(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str
    type: PolicyType
    value: float # Magnitude or specific value of the policy
    active: bool = True
    effects: Dict[str, Any] = Field(default_factory=dict)
    
class Government(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    world_id: uuid.UUID
    city_id: Optional[uuid.UUID] = None # Global or city-level government
    approval: float = Field(default=0.5, ge=0.0, le=1.0)
    stability: float = Field(default=0.5, ge=0.0, le=1.0)
    political_influence: float = Field(default=0.5, ge=0.0, le=1.0)
    security_capacity: float = Field(default=0.5, ge=0.0, le=1.0)
    active_policies: List[Policy] = Field(default_factory=list)
