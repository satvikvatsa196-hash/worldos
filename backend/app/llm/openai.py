import asyncio
import time
import json
from typing import Optional

try:
    from openai import AsyncOpenAI
    from openai import OpenAIError
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAIError = Exception
    
from pydantic import ValidationError

from app.llm.provider import LLMProvider
from app.llm.models import LLMResponse, LLMDecisionOutput, LLMMetadata, LLMUsage
from app.core.config import settings

class OpenAIProvider(LLMProvider):
    def __init__(self, timeout: float = 10.0, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if OPENAI_AVAILABLE and settings.OPENAI_API_KEY else None
        
    async def get_decision(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        if not self.client:
            return LLMResponse(
                is_success=False, 
                metadata=LLMMetadata(error="OpenAI client not configured or openai library not installed.")
            )
            
        last_error = None
        latency_ms = 0.0
        
        for attempt in range(self.max_retries):
            start_time = time.time()
            try:
                # We use JSON mode to enforce structured output
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=settings.OPENAI_MODEL,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        response_format={ "type": "json_object" },
                        temperature=0.0
                    ),
                    timeout=self.timeout
                )
                
                latency_ms = (time.time() - start_time) * 1000
                content = response.choices[0].message.content
                
                usage = LLMUsage()
                if response.usage:
                    usage.prompt_tokens = response.usage.prompt_tokens
                    usage.completion_tokens = response.usage.completion_tokens
                    usage.total_tokens = response.usage.total_tokens
                    
                parsed_json = json.loads(content)
                decision = LLMDecisionOutput.model_validate(parsed_json)
                
                return LLMResponse(
                    decision=decision,
                    metadata=LLMMetadata(usage=usage, latency_ms=latency_ms),
                    is_success=True
                )
                
            except asyncio.TimeoutError:
                last_error = "Timeout Error"
                latency_ms = (time.time() - start_time) * 1000
            except json.JSONDecodeError as e:
                last_error = f"Malformed JSON: {str(e)}"
                latency_ms = (time.time() - start_time) * 1000
            except ValidationError as e:
                last_error = f"Schema Validation Error: {str(e)}"
                latency_ms = (time.time() - start_time) * 1000
            except OpenAIError as e:
                last_error = f"Provider Error: {str(e)}"
                latency_ms = (time.time() - start_time) * 1000
            except Exception as e:
                last_error = f"Unexpected Error: {str(e)}"
                latency_ms = (time.time() - start_time) * 1000
                
        # Return controlled failure if max retries exceeded
        return LLMResponse(
            is_success=False,
            metadata=LLMMetadata(error=last_error, latency_ms=latency_ms)
        )
