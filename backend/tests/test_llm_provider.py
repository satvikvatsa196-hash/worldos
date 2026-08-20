import pytest
from pydantic import ValidationError
from app.llm.models import LLMDecisionOutput, LLMActionSchema, LLMResponse, LLMMetadata
from app.llm.mock import MockLLMProvider

def test_schema_validation():
    # Valid output
    valid_data = {
        "decision_summary": "I need food.",
        "action": {
            "type": "BUY_RESOURCE",
            "parameters": {"resource": "food"}
        },
        "confidence": 0.8
    }
    decision = LLMDecisionOutput.model_validate(valid_data)
    assert decision.decision_summary == "I need food."
    assert decision.action.type == "BUY_RESOURCE"
    assert decision.confidence == 0.8

    # Invalid confidence (out of bounds)
    invalid_data = valid_data.copy()
    invalid_data["confidence"] = 1.2
    with pytest.raises(ValidationError):
        LLMDecisionOutput.model_validate(invalid_data)
        
    # Missing action
    invalid_data2 = {
        "decision_summary": "Thinking...",
        "confidence": 0.5
    }
    with pytest.raises(ValidationError):
        LLMDecisionOutput.model_validate(invalid_data2)

@pytest.mark.asyncio
async def test_mock_provider_success():
    provider = MockLLMProvider()
    response = await provider.get_decision("System", "User")
    
    assert response.is_success is True
    assert response.decision is not None
    assert response.decision.decision_summary == "Mocked decision summary"
    assert response.decision.action.type == "DO_NOTHING"
    assert response.metadata.usage.total_tokens == 25
    assert response.metadata.latency_ms > 0

@pytest.mark.asyncio
async def test_mock_provider_controlled_failure():
    provider = MockLLMProvider(should_fail=True)
    response = await provider.get_decision("System", "User")
    
    assert response.is_success is False
    assert response.decision is None
    assert response.metadata.error == "Mock controlled failure"
    assert response.metadata.latency_ms > 0
