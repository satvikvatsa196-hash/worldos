from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, Dict, Any
import uuid

class EventType(str, Enum):
    WORLD_TICK = "WORLD_TICK"
    TRADE = "TRADE"
    PRICE_CHANGED = "PRICE_CHANGED"
    RESOURCE_PRODUCED = "RESOURCE_PRODUCED"
    RESOURCE_CONSUMED = "RESOURCE_CONSUMED"
    RESOURCE_SHORTAGE = "RESOURCE_SHORTAGE"
    CHARACTER_ACTION = "CHARACTER_ACTION"
    RELATIONSHIP_CHANGED = "RELATIONSHIP_CHANGED"
    PROTEST = "PROTEST"
    POLICY_CHANGED = "POLICY_CHANGED"
    FACTION_ACTION = "FACTION_ACTION"
    JOB_CHANGED = "JOB_CHANGED"
    MIGRATION = "MIGRATION"
    CONFLICT = "CONFLICT"
    DEATH = "DEATH"
    POLITICAL_CHANGE = "POLITICAL_CHANGE"
    INTERVENTION = "INTERVENTION"

class WorldEvent(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    world_id: uuid.UUID
    tick: int
    type: EventType
    actor_id: Optional[uuid.UUID] = None
    target_id: Optional[uuid.UUID] = None
    city_id: Optional[uuid.UUID] = None
    faction_id: Optional[uuid.UUID] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    parent_event_id: Optional[uuid.UUID] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(frozen=True)
