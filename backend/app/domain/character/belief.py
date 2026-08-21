from pydantic import BaseModel, Field, ConfigDict
import uuid
from typing import Optional, List
from enum import Enum
from app.domain.event.models import WorldEvent, EventType
from app.domain.character.personality import PersonalityTraits

class SubjectType(str, Enum):
    CHARACTER = "CHARACTER"
    FACTION = "FACTION"
    GOVERNMENT = "GOVERNMENT"
    ECONOMIC_CONDITION = "ECONOMIC_CONDITION"
    EVENT = "EVENT"

class Belief(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    character_id: uuid.UUID
    subject_id: Optional[uuid.UUID] = None
    subject_type: SubjectType
    belief_type: str 
    value: float = Field(ge=-1.0, le=1.0) 
    confidence: float = Field(ge=0.0, le=1.0)
    
    model_config = ConfigDict(frozen=True)

class BeliefUpdateEngine:
    """
    Updates beliefs based on observations, memories, rumors, interactions, and events.
    Two characters observing the same event can develop different beliefs based on their personality traits.
    Beliefs are imperfect and subjective.
    """
    def __init__(self):
        self.learning_rate = 0.2

    def process_event(
        self, 
        event: WorldEvent, 
        character_id: uuid.UUID, 
        personality: PersonalityTraits, 
        current_beliefs: List[Belief]
    ) -> List[Belief]:
        
        new_beliefs = []
        
        # Divergent interpretation of a TRADE event based on personality
        if event.type == EventType.TRADE:
            amount = event.payload.get("amount", 0)
            
            if event.actor_id and event.actor_id != character_id:
                # Greedy characters perceive large traders as "wealthy"
                if amount > 500 and personality.greed > 0.6:
                    new_beliefs.append(Belief(
                        character_id=character_id,
                        subject_id=event.actor_id,
                        subject_type=SubjectType.CHARACTER,
                        belief_type="wealthy",
                        value=0.8,
                        confidence=0.5
                    ))
                    
            if event.target_id and event.actor_id:
                # Cynical/Aggressive characters without empathy might assume dishonesty
                if personality.empathy < 0.4 and personality.aggression > 0.6:
                    new_beliefs.append(Belief(
                        character_id=character_id,
                        subject_id=event.actor_id,
                        subject_type=SubjectType.CHARACTER,
                        belief_type="dishonest",
                        value=0.6,
                        confidence=0.3
                    ))
                # Empathetic characters might assume honesty in trade
                elif personality.empathy > 0.7:
                    new_beliefs.append(Belief(
                        character_id=character_id,
                        subject_id=event.actor_id,
                        subject_type=SubjectType.CHARACTER,
                        belief_type="honest",
                        value=0.6,
                        confidence=0.4
                    ))
                    
        # Divergent interpretation of CONFLICT
        elif event.type == EventType.CONFLICT:
            if event.actor_id and event.actor_id != character_id:
                if personality.risk_tolerance < 0.4:
                    # Risk-averse characters see conflict instigators as dangerous
                    new_beliefs.append(Belief(
                        character_id=character_id,
                        subject_id=event.actor_id,
                        subject_type=SubjectType.CHARACTER,
                        belief_type="dangerous",
                        value=0.9,
                        confidence=0.8
                    ))
                elif personality.aggression > 0.7:
                    # Aggressive characters might admire them as strong
                    new_beliefs.append(Belief(
                        character_id=character_id,
                        subject_id=event.actor_id,
                        subject_type=SubjectType.CHARACTER,
                        belief_type="strong",
                        value=0.8,
                        confidence=0.7
                    ))
                    
        # Economic beliefs
        elif event.type == EventType.RESOURCE_SHORTAGE:
            if personality.risk_tolerance < 0.5:
                new_beliefs.append(Belief(
                    character_id=character_id,
                    subject_id=event.city_id,
                    subject_type=SubjectType.ECONOMIC_CONDITION,
                    belief_type="unstable",
                    value=0.8,
                    confidence=0.6
                ))
            elif personality.ambition > 0.7:
                # Highly ambitious people see a shortage as an opportunity
                new_beliefs.append(Belief(
                    character_id=character_id,
                    subject_id=event.city_id,
                    subject_type=SubjectType.ECONOMIC_CONDITION,
                    belief_type="opportunity",
                    value=0.7,
                    confidence=0.6
                ))

        # Political beliefs
        elif event.type == EventType.POLITICAL_CHANGE:
            if personality.political_alignment < 0.3:
                # Conservative alignment might view change negatively
                new_beliefs.append(Belief(
                    character_id=character_id,
                    subject_id=event.faction_id,
                    subject_type=SubjectType.GOVERNMENT,
                    belief_type="favorable",
                    value=-0.5,
                    confidence=0.5
                ))
            elif personality.political_alignment > 0.7:
                # Progressive alignment might view change favorably
                new_beliefs.append(Belief(
                    character_id=character_id,
                    subject_id=event.faction_id,
                    subject_type=SubjectType.GOVERNMENT,
                    belief_type="favorable",
                    value=0.6,
                    confidence=0.5
                ))

        # Merge newly formed beliefs with existing beliefs
        merged_beliefs = list(current_beliefs)
        for nb in new_beliefs:
            existing = next((b for b in merged_beliefs if b.subject_id == nb.subject_id and b.belief_type == nb.belief_type), None)
            if existing:
                merged_beliefs.remove(existing)
                # Weighted update of belief value
                total_conf = existing.confidence + nb.confidence
                if total_conf > 0:
                    new_val = (existing.value * existing.confidence + nb.value * nb.confidence) / total_conf
                    new_conf = min(1.0, existing.confidence + nb.confidence * self.learning_rate)
                else:
                    new_val = nb.value
                    new_conf = nb.confidence
                    
                merged_beliefs.append(Belief(
                    id=existing.id,
                    character_id=existing.character_id,
                    subject_id=existing.subject_id,
                    subject_type=existing.subject_type,
                    belief_type=existing.belief_type,
                    value=new_val,
                    confidence=new_conf
                ))
            else:
                merged_beliefs.append(nb)
                
        return merged_beliefs
