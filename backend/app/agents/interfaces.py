from abc import ABC, abstractmethod
from typing import List
from app.agents.models import AgentAction, AgentContext, AgentDecision

class ActionValidator(ABC):
    @abstractmethod
    def validate(self, action: AgentAction, context: AgentContext) -> bool:
        """Validates if an action is permissible given the current context."""
        pass

class DecisionProvider(ABC):
    @abstractmethod
    async def decide(self, context: AgentContext) -> AgentDecision:
        """Decides on a list of actions based on the context."""
        pass
