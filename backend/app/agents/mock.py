from typing import List, Optional
from app.agents.models import AgentAction, AgentContext, AgentDecision
from app.agents.interfaces import DecisionProvider, ActionValidator

class MockDecisionProvider(DecisionProvider):
    def __init__(self, predefined_actions: Optional[List[AgentAction]] = None, reasoning: str = "Mock reasoning"):
        self.predefined_actions = predefined_actions or []
        self.reasoning = reasoning
        
    async def decide(self, context: AgentContext) -> AgentDecision:
        return AgentDecision(
            actions=self.predefined_actions,
            reasoning=self.reasoning
        )

class MockActionValidator(ActionValidator):
    def __init__(self, accept_all: bool = True):
        self.accept_all = accept_all
        
    def validate(self, action: AgentAction, context: AgentContext) -> bool:
        return self.accept_all
