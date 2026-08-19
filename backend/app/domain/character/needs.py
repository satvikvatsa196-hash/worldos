import uuid
from pydantic import BaseModel, Field, ConfigDict

class CharacterNeeds(BaseModel):
    food: float = Field(default=100.0, ge=0.0, le=100.0) # 100 = full, 0 = starving
    shelter: float = Field(default=100.0, ge=0.0, le=100.0)
    wealth: float = Field(default=50.0, ge=0.0, le=100.0)
    safety: float = Field(default=100.0, ge=0.0, le=100.0)
    social: float = Field(default=100.0, ge=0.0, le=100.0)
    status: float = Field(default=50.0, ge=0.0, le=100.0)

class CharacterStateSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    character_id: uuid.UUID
    name: str
    occupation: str
    health: float
    wealth_balance: float
    needs: CharacterNeeds
    
    # Environmental/Contextual flags
    has_job: bool = True
    in_danger: bool = False
    is_isolated: bool = False

class NeedEngine:
    def __init__(self):
        # Base changes per tick
        self.decay_rates = {
            "food": 2.0,
            "shelter": 0.5,
            "social": 1.0,
            "safety": 0.5,
            "status": 0.1
        }

    def process_tick(self, snapshot: CharacterStateSnapshot) -> CharacterNeeds:
        new_needs = snapshot.needs.model_copy()
        
        # 1. Hunger increases with time (food need decreases)
        new_needs.food -= self.decay_rates["food"]
        
        # 2. Unemployment affects wealth
        if not snapshot.has_job:
            new_needs.wealth -= 2.0
        else:
            new_needs.wealth += 0.5
            
        # 3. Danger affects safety
        if snapshot.in_danger:
            new_needs.safety -= 10.0
        else:
            new_needs.safety += self.decay_rates["safety"]
            
        # 4. Isolation affects social need
        if snapshot.is_isolated:
            new_needs.social -= 5.0
        else:
            new_needs.social -= self.decay_rates["social"]
            
        # 5. Shelter decays slowly over time
        new_needs.shelter -= self.decay_rates["shelter"]
        
        # Clamp all values
        self._clamp_needs(new_needs)
        return new_needs

    def consume_food(self, needs: CharacterNeeds, nutrition_value: float = 30.0) -> CharacterNeeds:
        """Eating reduces hunger (increases food need satisfaction)."""
        new_needs = needs.model_copy()
        new_needs.food += nutrition_value
        self._clamp_needs(new_needs)
        return new_needs
        
    def _clamp_needs(self, needs: CharacterNeeds) -> None:
        needs.food = max(0.0, min(100.0, needs.food))
        needs.shelter = max(0.0, min(100.0, needs.shelter))
        needs.wealth = max(0.0, min(100.0, needs.wealth))
        needs.safety = max(0.0, min(100.0, needs.safety))
        needs.social = max(0.0, min(100.0, needs.social))
        needs.status = max(0.0, min(100.0, needs.status))
