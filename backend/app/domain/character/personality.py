from pydantic import BaseModel, Field

class PersonalityTraits(BaseModel):
    greed: float = Field(default=0.5, ge=0.0, le=1.0)
    ambition: float = Field(default=0.5, ge=0.0, le=1.0)
    loyalty: float = Field(default=0.5, ge=0.0, le=1.0)
    risk_tolerance: float = Field(default=0.5, ge=0.0, le=1.0)
    aggression: float = Field(default=0.5, ge=0.0, le=1.0)
    empathy: float = Field(default=0.5, ge=0.0, le=1.0)
    sociability: float = Field(default=0.5, ge=0.0, le=1.0)
    political_alignment: float = Field(default=0.5, ge=0.0, le=1.0)
