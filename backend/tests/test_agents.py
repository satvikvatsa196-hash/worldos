import pytest
import uuid
from pydantic import ValidationError

from app.agents.models import ActionType, AgentAction, AgentContext
from app.agents.mock import MockDecisionProvider, MockActionValidator
from app.agents.agent import CharacterAgent

@pytest.fixture
def base_context():
    return AgentContext(
        character_state={"health": 100, "wealth": 50},
        needs={"food": 0.8},
        goals=[{"type": "survive"}],
        relevant_memories=[],
        beliefs=[],
        nearby_entities=[],
        relationships=[],
        current_economic_conditions={"food_price": 2.0},
        recent_events=[]
    )

def test_schema_validation():
    # Valid action
    valid_action = AgentAction(
        action_type=ActionType.BUY_RESOURCE,
        actor_id=uuid.uuid4(),
        parameters={"resource": "food", "quantity": 1},
        justification_summary="I am hungry",
        confidence=0.9
    )
    assert valid_action.action_type == ActionType.BUY_RESOURCE
    assert valid_action.confidence == 0.9

    # Invalid confidence (out of bounds)
    with pytest.raises(ValidationError):
        AgentAction(
            action_type=ActionType.BUY_RESOURCE,
            actor_id=uuid.uuid4(),
            justification_summary="I am hungry",
            confidence=1.5
        )

    # Missing justification summary
    with pytest.raises(ValidationError):
        AgentAction(
            action_type=ActionType.BUY_RESOURCE,
            actor_id=uuid.uuid4(),
            confidence=0.9
        )

def test_context_construction_and_immutability(base_context):
    # Verify properties
    assert base_context.character_state["health"] == 100
    
    # Verify immutability
    with pytest.raises(ValidationError):
        base_context.needs = {"food": 1.0}

@pytest.mark.asyncio
async def test_invalid_actions_rejected(base_context):
    actor_id = uuid.uuid4()
    
    # Setup mock provider to propose an action
    action = AgentAction(
        action_type=ActionType.DO_NOTHING,
        actor_id=actor_id,
        justification_summary="Just resting",
        confidence=1.0
    )
    provider = MockDecisionProvider(predefined_actions=[action])
    
    # Validator rejects all
    validator = MockActionValidator(accept_all=False)
    
    agent = CharacterAgent(character_id=actor_id, provider=provider, validator=validator)
    
    # Think
    proposed_actions = await agent.think(base_context)
    
    # Action should be rejected by validator
    assert len(proposed_actions) == 0

@pytest.mark.asyncio
async def test_valid_actions_accepted(base_context):
    actor_id = uuid.uuid4()
    
    action = AgentAction(
        action_type=ActionType.DO_NOTHING,
        actor_id=actor_id,
        justification_summary="Just resting",
        confidence=1.0
    )
    provider = MockDecisionProvider(predefined_actions=[action])
    
    # Validator accepts all
    validator = MockActionValidator(accept_all=True)
    
    agent = CharacterAgent(character_id=actor_id, provider=provider, validator=validator)
    
    proposed_actions = await agent.think(base_context)
    
    # Action should be accepted
    assert len(proposed_actions) == 1
    assert proposed_actions[0].action_type == ActionType.DO_NOTHING

@pytest.mark.asyncio
async def test_mock_agent_decisions(base_context):
    actor_id = uuid.uuid4()
    wrong_actor_id = uuid.uuid4()
    
    # Propose one valid action for itself and one for another agent
    action1 = AgentAction(
        action_type=ActionType.WORK,
        actor_id=actor_id,
        justification_summary="Need money",
        confidence=0.8
    )
    action2 = AgentAction(
        action_type=ActionType.MOVE,
        actor_id=wrong_actor_id,
        justification_summary="Someone else should move",
        confidence=0.5
    )
    
    provider = MockDecisionProvider(predefined_actions=[action1, action2])
    validator = MockActionValidator(accept_all=True)
    
    agent = CharacterAgent(character_id=actor_id, provider=provider, validator=validator)
    
    proposed_actions = await agent.think(base_context)
    
    # Should only return the action meant for itself
    assert len(proposed_actions) == 1
    assert proposed_actions[0].actor_id == actor_id
    assert proposed_actions[0].action_type == ActionType.WORK
