from typing import Optional
from app.llm.provider import LLMProvider
from app.llm.models import LLMResponse, LLMDecisionOutput, LLMActionSchema, LLMMetadata, LLMUsage

class MockLLMProvider(LLMProvider):
    def __init__(self, response: Optional[LLMResponse] = None, should_fail: bool = False):
        self._response = response
        self.should_fail = should_fail
        
    async def get_decision(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        if self.should_fail:
            return LLMResponse(
                is_success=False,
                metadata=LLMMetadata(error="Mock controlled failure", latency_ms=10.0)
            )
            
        if self._response:
            return self._response
            
        decision = LLMDecisionOutput(
            decision_summary="Mocked decision summary",
            action=LLMActionSchema(
                type="DO_NOTHING",
                parameters={}
            ),
            confidence=0.9
        )
        return LLMResponse(
            decision=decision,
            metadata=LLMMetadata(
                usage=LLMUsage(prompt_tokens=15, completion_tokens=10, total_tokens=25),
                latency_ms=12.5
            ),
            is_success=True
        )
