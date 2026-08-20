from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class LLMActionSchema(BaseModel):
    type: str
    parameters: Dict[str, Any] = Field(default_factory=dict)

class LLMDecisionOutput(BaseModel):
    decision_summary: str
    action: LLMActionSchema
    confidence: float = Field(ge=0.0, le=1.0)

class LLMUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

class LLMMetadata(BaseModel):
    usage: LLMUsage = Field(default_factory=LLMUsage)
    latency_ms: float = 0.0
    error: Optional[str] = None

class LLMResponse(BaseModel):
    decision: Optional[LLMDecisionOutput] = None
    metadata: LLMMetadata = Field(default_factory=LLMMetadata)
    is_success: bool = True
