import pytest
import asyncio
import json
from unittest.mock import MagicMock, AsyncMock, patch

from pydantic import ValidationError

from app.llm.openai import OpenAIProvider, CircuitBreaker
from app.llm.models import LLMResponse

class MockChoice:
    def __init__(self, content):
        self.message = MagicMock()
        self.message.content = content

class MockResponse:
    def __init__(self, content):
        self.choices = [MockChoice(content)]
        self.usage = MagicMock()
        self.usage.prompt_tokens = 10
        self.usage.completion_tokens = 10
        self.usage.total_tokens = 20

@pytest.fixture
def valid_json_content():
    return json.dumps({
        "decision_summary": "Test decision",
        "action": {
            "type": "DO_NOTHING",
            "parameters": {}
        },
        "confidence": 0.9
    })

@pytest.fixture
def mock_openai_client(valid_json_content):
    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=MockResponse(valid_json_content))
    return client

@pytest.mark.asyncio
async def test_successful_decision(mock_openai_client):
    provider = OpenAIProvider()
    provider.client = mock_openai_client
    
    response = await provider.get_decision("sys", "user")
    assert response.is_success is True
    assert response.decision.action.type == "DO_NOTHING"
    assert provider.circuit_breaker.is_open is False

@pytest.mark.asyncio
async def test_timeout_retry(mock_openai_client, monkeypatch):
    provider = OpenAIProvider(timeout=0.1, max_retries=2)
    provider.client = mock_openai_client
    
    # Mock create to timeout on first call, succeed on second
    call_count = 0
    async def mock_create(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            await asyncio.sleep(0.2) # Will trigger timeout
            return None
        return MockResponse(json.dumps({
            "decision_summary": "Retry success",
            "action": {"type": "DO_NOTHING", "parameters": {}},
            "confidence": 0.9
        }))
        
    mock_openai_client.chat.completions.create = mock_create
    
    # Fast forward sleep so tests run quickly
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    
    response = await provider.get_decision("sys", "user")
    assert response.is_success is True
    assert call_count == 2

@pytest.mark.asyncio
async def test_exhaust_retries_and_circuit_breaker(mock_openai_client, monkeypatch):
    provider = OpenAIProvider(max_retries=3)
    provider.client = mock_openai_client
    provider.circuit_breaker.failure_threshold = 1 # Trip immediately on exhaust
    
    # Mock create to raise Exception always
    async def mock_create_fail(*args, **kwargs):
        raise Exception("Provider Outage")
        
    mock_openai_client.chat.completions.create = mock_create_fail
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    
    response = await provider.get_decision("sys", "user")
    
    assert response.is_success is False
    assert "Provider Outage" in response.metadata.error
    assert provider.circuit_breaker.is_open is True
    
    # Next call should fast-fail due to circuit breaker
    response2 = await provider.get_decision("sys", "user")
    assert response2.is_success is False
    assert "Circuit breaker is open" in response2.metadata.error

@pytest.mark.asyncio
async def test_malformed_json_retry(mock_openai_client, monkeypatch):
    provider = OpenAIProvider(max_retries=2)
    provider.client = mock_openai_client
    
    call_count = 0
    async def mock_create(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return MockResponse("INVALID JSON {")
        return MockResponse(json.dumps({
            "decision_summary": "Retry success",
            "action": {"type": "DO_NOTHING", "parameters": {}},
            "confidence": 0.9
        }))
        
    mock_openai_client.chat.completions.create = mock_create
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    
    response = await provider.get_decision("sys", "user")
    assert response.is_success is True
    assert call_count == 2

@pytest.mark.asyncio
async def test_schema_violation_retry(mock_openai_client, monkeypatch):
    provider = OpenAIProvider(max_retries=2)
    provider.client = mock_openai_client
    
    call_count = 0
    async def mock_create(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Missing action block
            return MockResponse(json.dumps({
                "decision_summary": "Bad Schema",
                "confidence": 100 # Invalid confidence too
            }))
        return MockResponse(json.dumps({
            "decision_summary": "Retry success",
            "action": {"type": "DO_NOTHING", "parameters": {}},
            "confidence": 0.9
        }))
        
    mock_openai_client.chat.completions.create = mock_create
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    
    response = await provider.get_decision("sys", "user")
    assert response.is_success is True
    assert call_count == 2
