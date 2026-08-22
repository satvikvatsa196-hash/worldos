import pytest
import pytest_asyncio
import uuid
from typing import Optional

from app.agents.engine import FactionDecisionEngine, IDecisionStore, DecisionRecord
from app.agents.agent import FactionAgent
from app.agents.models import AgentContext, AgentDecision, AgentAction, ActionType
from app.agents.interfaces import DecisionProvider, ActionValidator
from app.llm.provider import LLMProvider
from app.llm.models import LLMResponse, LLMDecisionOutput, LLMActionSchema, LLMMetadata, LLMUsage
import asyncio

@pytest_asyncio.fixture(autouse=True, scope="module")
async def debug_print():
    print("\n\n>>> STARTING MODULE test_faction_agents.py <<<", flush=True)
    tasks = asyncio.all_tasks()
    print(f">>> RUNNING TASKS: {len(tasks)}", flush=True)
    for t in tasks:
        print(f"Task: {t.get_coro()}", flush=True)
    yield
    print("\n\n>>> ENDING MODULE test_faction_agents.py <<<", flush=True)
class MockLLMProvider(LLMProvider):
    async def get_decision(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        return LLMResponse(
            is_success=True,
            decision=LLMDecisionOutput(
                action=LLMActionSchema(
                    type=ActionType.RECRUIT.value,
                    parameters={}
                ),
                decision_summary="We need more members to achieve our goals.",
                confidence=0.9
            ),
            metadata=LLMMetadata(
                usage=LLMUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
                latency_ms=100.0
            )
        )
    async def close(self): pass

class MockDecisionStore(IDecisionStore):
    def __init__(self):
        self.records = []
    async def save(self, record: DecisionRecord) -> None:
        self.records.append(record)

class AlwaysValidValidator(ActionValidator):
    def validate(self, action: AgentAction, context: AgentContext) -> bool:
        return True

class MockFaction:
    def __init__(self):
        self.id = uuid.UUID(int=1)
        self.wealth = 5000
        self.power = 80
        self.influence = 90
        self.ideology = "progressive"
        self.members = [uuid.uuid4(), uuid.uuid4()]

@pytest.mark.asyncio
async def test_faction_decision_engine():
    provider = MockLLMProvider()
    validator = AlwaysValidValidator()
    store = MockDecisionStore()
    
    engine = FactionDecisionEngine(
        llm_provider=provider,
        validator=validator,
        store=store
    )
    
    faction = MockFaction()
    world_id = uuid.uuid4()
    
    # Run decision loop
    action = await engine.decide(
        agent_id=faction.id,
        world_id=world_id,
        current_tick=1,
        faction=faction,
        world=None
    )
    
    assert action is not None
    assert action.action_type == ActionType.RECRUIT
    assert action.actor_id == faction.id
    
    assert len(store.records) == 1
    record = store.records[0]
    assert record.agent_id == faction.id
    assert record.action.action_type == ActionType.RECRUIT

@pytest.mark.asyncio
async def test_faction_agent_think():
    class TestProvider(DecisionProvider):
        async def decide(self, context: AgentContext) -> AgentDecision:
            return AgentDecision(
                actions=[
                    AgentAction(
                        action_type=ActionType.FUND_PROTEST,
                        actor_id=uuid.UUID(int=1),
                        justification_summary="Because we oppose the policy",
                        confidence=0.8
                    ),
                    AgentAction(
                        action_type=ActionType.RECRUIT,
                        actor_id=uuid.UUID(int=2), # Malicious action for another faction
                        justification_summary="Hack",
                        confidence=0.5
                    )
                ],
                reasoning="Test"
            )

    agent_id = uuid.UUID(int=1)
    provider = TestProvider()
    validator = AlwaysValidValidator()
    
    agent = FactionAgent(agent_id, provider, validator)
    context = AgentContext(
        character_state={}, needs={}, goals=[], relevant_memories=[], beliefs=[],
        nearby_entities=[], relationships=[], current_economic_conditions={}, recent_events=[]
    )
    
    actions = await agent.think(context)
    
    # Should only return the action where actor_id == agent_id
    assert len(actions) == 1
    assert actions[0].action_type == ActionType.FUND_PROTEST
    assert actions[0].actor_id == agent_id
