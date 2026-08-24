import asyncio
import time
import json
import logging
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

logger = logging.getLogger(__name__)

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0.0
        self.is_open = False
        
    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.is_open = True
            
    def record_success(self):
        self.failures = 0
        self.is_open = False
        
    def check_circuit(self) -> bool:
        if self.is_open:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.is_open = False
                self.failures = 0 # Half-open state
                return True
            return False
        return True

class OpenAIProvider(LLMProvider):
    def __init__(self, timeout: float = 10.0, max_retries: int = 3, model_name: str = None):
        self.timeout = timeout
        self.max_retries = max_retries
        self.model_name = model_name or settings.OPENAI_MODEL or "gpt-4-turbo"
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if OPENAI_AVAILABLE and settings.OPENAI_API_KEY else None
        self.circuit_breaker = CircuitBreaker()
        
    async def get_decision(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        if not self.client:
            logger.error("LLM Provider failed: OpenAI client not configured.")
            return LLMResponse(
                is_success=False, 
                metadata=LLMMetadata(error="OpenAI client not configured or openai library not installed.")
            )
            
        if not self.circuit_breaker.check_circuit():
            logger.warning("LLM Provider circuit is OPEN. Fast-failing.")
            return LLMResponse(
                is_success=False,
                metadata=LLMMetadata(error="Circuit breaker is open due to consecutive failures.", latency_ms=0.0)
            )
            
        last_error = None
        latency_ms = 0.0
        
        for attempt in range(self.max_retries):
            start_time = time.time()
            try:
                # We use JSON mode to enforce structured output
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=self.model_name,
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
                
                self.circuit_breaker.record_success()
                return LLMResponse(
                    decision=decision,
                    metadata=LLMMetadata(usage=usage, latency_ms=latency_ms),
                    is_success=True
                )
                
            except asyncio.TimeoutError:
                last_error = "Timeout Error"
                latency_ms = (time.time() - start_time) * 1000
                logger.error(f"LLM Provider Timeout (Attempt {attempt+1}/{self.max_retries})")
            except json.JSONDecodeError as e:
                last_error = f"Malformed JSON: {str(e)}"
                latency_ms = (time.time() - start_time) * 1000
                logger.error(f"LLM Provider JSONDecodeError (Attempt {attempt+1}/{self.max_retries}): {e}")
            except ValidationError as e:
                last_error = f"Schema Validation Error: {str(e)}"
                latency_ms = (time.time() - start_time) * 1000
                logger.error(f"LLM Provider ValidationError (Attempt {attempt+1}/{self.max_retries}): {e}")
            except OpenAIError as e:
                last_error = f"Provider Error: {str(e)}"
                latency_ms = (time.time() - start_time) * 1000
                logger.error(f"LLM Provider OpenAIError (Attempt {attempt+1}/{self.max_retries}): {e}")
            except Exception as e:
                last_error = f"Unexpected Error: {str(e)}"
                latency_ms = (time.time() - start_time) * 1000
                logger.error(f"LLM Provider Unexpected Error (Attempt {attempt+1}/{self.max_retries}): {e}")
                
            # Exponential backoff
            if attempt < self.max_retries - 1:
                backoff = 2 ** attempt
                logger.info(f"Retrying in {backoff} seconds...")
                await asyncio.sleep(backoff)
                
        self.circuit_breaker.record_failure()
        logger.error(f"LLM Provider exhausted all {self.max_retries} retries. Final error: {last_error}")
        
        # Return controlled failure if max retries exceeded
        return LLMResponse(
            is_success=False,
            metadata=LLMMetadata(error=last_error, latency_ms=latency_ms)
        )
