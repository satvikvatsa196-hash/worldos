from abc import ABC, abstractmethod
from app.llm.models import LLMResponse

class LLMProvider(ABC):
    @abstractmethod
    async def get_decision(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """
        Sends a request to the LLM to get a structured decision output.
        Must handle retries, timeouts, schemas, etc.
        """
        pass
