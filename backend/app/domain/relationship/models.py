import uuid
from pydantic import BaseModel, Field

class CharacterRelationship(BaseModel):
    source_character_id: uuid.UUID
    target_character_id: uuid.UUID
    trust: float = Field(default=0.0, ge=-1.0, le=1.0)
    respect: float = Field(default=0.0, ge=-1.0, le=1.0)
    fear: float = Field(default=0.0, ge=0.0, le=1.0)
    friendship: float = Field(default=0.0, ge=-1.0, le=1.0)
    hostility: float = Field(default=0.0, ge=0.0, le=1.0)
    influence: float = Field(default=0.0, ge=-1.0, le=1.0)
    obligation: float = Field(default=0.0, ge=-1.0, le=1.0)
