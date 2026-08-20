from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
import uuid

class ActionType(str, Enum):
    BUY_RESOURCE = "BUY_RESOURCE"
    SELL_RESOURCE = "SELL_RESOURCE"
    MOVE = "MOVE"
    WORK = "WORK"
    JOIN_FACTION = "JOIN_FACTION"
    LEAVE_FACTION = "LEAVE_FACTION"
    PROTEST = "PROTEST"
    NEGOTIATE = "NEGOTIATE"
    SPREAD_RUMOR = "SPREAD_RUMOR"
    SUPPORT_POLICY = "SUPPORT_POLICY"
    OPPOSE_POLICY = "OPPOSE_POLICY"
    GIVE_MONEY = "GIVE_MONEY"
    REQUEST_HELP = "REQUEST_HELP"
    DO_NOTHING = "DO_NOTHING"

class AgentAction(BaseModel):
    action_type: ActionType
    actor_id: uuid.UUID
    target_id: Optional[uuid.UUID] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    justification_summary: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    
    model_config = ConfigDict(frozen=True)

class AgentContext(BaseModel):
    character_state: Dict[str, Any]
    needs: Dict[str, Any]
    goals: List[Dict[str, Any]]
    relevant_memories: List[Dict[str, Any]]
    beliefs: Dict[str, Any]
    nearby_entities: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    current_economic_conditions: Dict[str, Any]
    recent_events: List[Dict[str, Any]]
    
    model_config = ConfigDict(frozen=True)

class AgentDecision(BaseModel):
    actions: List[AgentAction]
    reasoning: str
