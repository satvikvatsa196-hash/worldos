from abc import ABC, abstractmethod
from typing import List
import uuid

from app.agents.models import AgentAction, AgentContext
from app.agents.interfaces import DecisionProvider, ActionValidator

class Agent(ABC):
    @abstractmethod
    async def think(self, context: AgentContext) -> List[AgentAction]:
        """Propose actions based on context without mutating world state."""
        pass

class CharacterAgent(Agent):
    def __init__(self, character_id: uuid.UUID, provider: DecisionProvider, validator: ActionValidator):
        self.character_id = character_id
        self.provider = provider
        self.validator = validator
        
    async def think(self, context: AgentContext) -> List[AgentAction]:
        decision = await self.provider.decide(context)
        valid_actions = []
        for action in decision.actions:
            # Enforce that agent only proposes actions for itself
            if action.actor_id != self.character_id:
                continue
            # Validate action
            if self.validator.validate(action, context):
                valid_actions.append(action)
        return valid_actions
