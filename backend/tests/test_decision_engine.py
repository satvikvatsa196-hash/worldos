import pytest
import uuid
from typing import List

from app.agents.engine import CharacterDecisionEngine, DecisionRecord, IDecisionStore
from app.agents.models import ActionType
from app.agents.mock import MockActionValidator
from app.llm.mock import MockLLMProvider
from app.llm.models import LLMResponse, LLMDecisionOutput, LLMActionSchema, LLMMetadata, LLMUsage

class MockDecisionStore(IDecisionStore):
    def __init__(self):
        self.records: List[DecisionRecord] = []
        
    async def save(self, record: DecisionRecord) -> None:
        self.records.append(record)

@pytest.fixture
def store():
    return MockDecisionStore()

@pytest.fixture
def agent_id():
    return uuid.uuid4()

@pytest.fixture
def world_id():
    return uuid.uuid4()

@pytest.mark.asyncio
async def test_engine_cooldown_behavior(store, agent_id, world_id):
    llm = MockLLMProvider()
    validator = MockActionValidator(accept_all=True)
    engine = CharacterDecisionEngine(llm, validator, store)
    
    # Tick 1: Should run
    assert engine.should_run(agent_id, 1, "HIGH") is True
    
    await engine.decide(agent_id, world_id, 1)
    
    # Tick 2: Should NOT run for HIGH (cooldown is 2)
    assert engine.should_run(agent_id, 2, "HIGH") is False
    
    # Tick 3: Should run for HIGH (3 - 1 = 2 >= 2)
    assert engine.should_run(agent_id, 3, "HIGH") is True
    
    # Normal priority
    assert engine.should_run(agent_id, 3, "NORMAL") is False # 3 - 1 = 2 < 9
    assert engine.should_run(agent_id, 10, "NORMAL") is True # 10 - 1 = 9 >= 9

@pytest.mark.asyncio
async def test_llm_invocation_and_persistence(store, agent_id, world_id):
    # Setup LLM returning specific action
    decision = LLMDecisionOutput(
        decision_summary="I want to work.",
        action=LLMActionSchema(type="WORK", parameters={}),
        confidence=0.9
    )
    response = LLMResponse(
        decision=decision,
        metadata=LLMMetadata(usage=LLMUsage(total_tokens=42), latency_ms=100.0),
        is_success=True
    )
    llm = MockLLMProvider(response=response)
    validator = MockActionValidator(accept_all=True)
    engine = CharacterDecisionEngine(llm, validator, store)
    
    action = await engine.decide(agent_id, world_id, 1)
    
    assert action is not None
    assert action.action_type == ActionType.WORK
    
    # Check persistence metadata
    assert len(store.records) == 1
    record = store.records[0]
    assert record.agent_id == agent_id
    assert record.decision_summary == "I want to work."
    assert record.confidence == 0.9
    assert record.latency == 100.0
    assert record.token_usage["total_tokens"] == 42
    
@pytest.mark.asyncio
async def test_llm_failure_and_fallback(store, agent_id, world_id):
    # Setup LLM to fail
    llm = MockLLMProvider(should_fail=True)
    validator = MockActionValidator(accept_all=True)
    engine = CharacterDecisionEngine(llm, validator, store)
    
    action = await engine.decide(agent_id, world_id, 1)
    
    # Should fallback to DO_NOTHING deterministically
    assert action is not None
    assert action.action_type == ActionType.DO_NOTHING
    
    # Verify persistence still records the fallback
    assert len(store.records) == 1
    record = store.records[0]
    assert record.decision_summary == "LLM failure fallback"
    assert record.action.action_type == ActionType.DO_NOTHING

@pytest.mark.asyncio
async def test_malformed_action_type(store, agent_id, world_id):
    # Setup LLM returning invalid ActionType string
    decision = LLMDecisionOutput(
        decision_summary="Inventing new action.",
        action=LLMActionSchema(type="NON_EXISTENT_ACTION", parameters={}),
        confidence=0.5
    )
    response = LLMResponse(
        decision=decision,
        metadata=LLMMetadata(is_success=True)
    )
    llm = MockLLMProvider(response=response)
    validator = MockActionValidator(accept_all=True)
    engine = CharacterDecisionEngine(llm, validator, store)
    
    action = await engine.decide(agent_id, world_id, 1)
    
    # Should gracefully default to DO_NOTHING when parsing fails
    assert action.action_type == ActionType.DO_NOTHING

@pytest.mark.asyncio
async def test_validator_rejection(store, agent_id, world_id):
    # LLM proposes valid format
    llm = MockLLMProvider() # defaults to DO_NOTHING usually, but valid format
    # Validator rejects it
    validator = MockActionValidator(accept_all=False)
    engine = CharacterDecisionEngine(llm, validator, store)
    
    action = await engine.decide(agent_id, world_id, 1)
    
    # Should be replaced by fallback
    assert action.justification_summary == "Proposed action was invalid for current context."
    assert action.action_type == ActionType.DO_NOTHING
    
    assert len(store.records) == 1
    assert store.records[0].decision_summary == "Validation failure fallback"
