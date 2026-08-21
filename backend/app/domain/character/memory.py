from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
import uuid
from typing import List, Optional, Any
from abc import ABC, abstractmethod

from app.domain.event.models import WorldEvent, EventType
from app.domain.interfaces import IMemoryRepository
from app.agents.models import AgentContext

class MemoryType(str, Enum):
    EVENT = "EVENT"
    INTERACTION = "INTERACTION"
    TRANSACTION = "TRANSACTION"
    OBSERVATION = "OBSERVATION"
    BELIEF = "BELIEF"
    GOAL = "GOAL"

class CharacterMemory(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    character_id: uuid.UUID
    type: MemoryType
    summary: str
    importance: float = Field(ge=0.0, le=1.0)
    tick: int
    related_entities: List[uuid.UUID] = Field(default_factory=list)
    source_event_id: Optional[uuid.UUID] = None

    model_config = ConfigDict(frozen=True)

class MemoryManager:
    """
    Evaluates events and determines if they should be stored as memories.
    """
    def __init__(self, importance_threshold: float = 0.5):
        self.importance_threshold = importance_threshold
        
    def evaluate_event(self, event: WorldEvent, character_id: uuid.UUID) -> Optional[CharacterMemory]:
        """
        Evaluate if a world event is significant enough for the character to remember.
        """
        is_actor = event.actor_id == character_id
        is_target = event.target_id == character_id
        is_involved = is_actor or is_target
        
        importance = 0.0
        summary = ""
        memory_type = MemoryType.EVENT
        related_entities = []

        if event.target_id:
            related_entities.append(event.target_id)
        if event.actor_id:
            related_entities.append(event.actor_id)

        # High importance examples logic
        if event.type == EventType.TRADE and is_involved:
            amount = event.payload.get("amount", 0)
            if amount > 1000:
                importance = 0.9
                summary = f"Engaged in a large financial trade of {amount}."
            else:
                importance = 0.6
                summary = f"Engaged in a successful trade of {amount}."
            memory_type = MemoryType.TRANSACTION
            
        elif event.type == EventType.RESOURCE_SHORTAGE:
            importance = 0.8
            memory_type = MemoryType.OBSERVATION
            summary = f"Experienced a major resource shortage of {event.payload.get('resource_type', 'resources')}."
            
        elif event.type == EventType.CONFLICT and is_involved:
            memory_type = MemoryType.INTERACTION
            if event.payload.get("betrayal"):
                importance = 1.0
                summary = "Was betrayed during a conflict."
            else:
                importance = 0.8
                summary = "Was involved in a political or physical conflict."
                
        elif event.type == EventType.DEATH:
            if is_involved:
                importance = 1.0
                summary = "Died."
            elif str(event.target_id) in event.payload.get("important_relationships", []):
                importance = 0.9
                summary = f"Death of important relationship."
            else:
                importance = 0.6
                summary = "Witnessed a death."
                
        elif event.type == EventType.FACTION_ACTION and is_involved:
            action = event.payload.get("action")
            if action == "RECRUITMENT":
                importance = 0.8
                summary = "Participated in faction recruitment."
            elif action == "ARREST":
                importance = 0.9
                summary = "Involved in an arrest."
            else:
                importance = 0.5
                summary = f"Involved in faction action: {action}"
                
        elif event.type == EventType.POLITICAL_CHANGE:
            importance = 0.8
            memory_type = MemoryType.OBSERVATION
            summary = "Observed a major political change or conflict."
            
        elif event.type == EventType.RELATIONSHIP_CHANGED and is_involved:
            memory_type = MemoryType.INTERACTION
            trust_change = event.payload.get("trust_change", 0)
            if trust_change < -0.5:
                importance = 0.9
                summary = "Experienced a severe betrayal of trust."
            else:
                importance = 0.5
                summary = "Experienced a change in relationship."
                
        if importance >= self.importance_threshold:
            # Clean up related entities list (remove self and None)
            clean_entities = list(set([e for e in related_entities if e != character_id and e is not None]))
            return CharacterMemory(
                character_id=character_id,
                type=memory_type,
                summary=summary,
                importance=importance,
                tick=event.tick,
                related_entities=clean_entities,
                source_event_id=event.id
            )
            
        return None

class MemoryRetriever(ABC):
    @abstractmethod
    async def retrieve_relevant_memories(
        self, 
        character_id: uuid.UUID, 
        context: AgentContext,
        limit: int = 5
    ) -> List[CharacterMemory]:
        pass

class PostgresMemoryRetriever(MemoryRetriever):
    """
    PostgreSQL backed memory retrieval. 
    Maintains abstraction for future vector search implementation.
    """
    def __init__(self, repository: IMemoryRepository):
        self.repository = repository
        
    def _calculate_relevance(self, memory: Any, context: AgentContext) -> float:
        score = memory.importance
        
        # Entity overlap scoring
        context_entities = set()
        for entity in context.nearby_entities:
            if "id" in entity:
                try:
                    context_entities.add(uuid.UUID(str(entity["id"])))
                except (ValueError, TypeError):
                    pass
        for rel in context.relationships:
            if "target_id" in rel:
                try:
                    context_entities.add(uuid.UUID(str(rel["target_id"])))
                except (ValueError, TypeError):
                    pass
                    
        # Parse memory related entities
        memory_entities = []
        for e in memory.related_entities:
            try:
                memory_entities.append(uuid.UUID(str(e)))
            except (ValueError, TypeError):
                pass
                
        overlap = set(memory_entities).intersection(context_entities)
        score += len(overlap) * 0.3
        
        return score

    async def retrieve_relevant_memories(
        self, 
        character_id: uuid.UUID, 
        context: AgentContext,
        limit: int = 5
    ) -> List[CharacterMemory]:
        
        # Fetch memories from DB
        db_memories = await self.repository.get_by_character_id(character_id)
        
        # Score and rank memories based on relevance to current context
        scored_memories = []
        for db_mem in db_memories:
            score = self._calculate_relevance(db_mem, context)
            scored_memories.append((score, db_mem))
            
        # Rank descending
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        
        # Map back to domain model
        result = []
        for _, db_mem in scored_memories[:limit]:
            try:
                mem_type = MemoryType(db_mem.type)
            except ValueError:
                mem_type = MemoryType.EVENT
                
            related_ids = []
            for e in db_mem.related_entities:
                try:
                    related_ids.append(uuid.UUID(str(e)))
                except (ValueError, TypeError):
                    pass
            
            result.append(
                CharacterMemory(
                    id=db_mem.id,
                    character_id=db_mem.character_id,
                    type=mem_type,
                    summary=db_mem.summary,
                    importance=db_mem.importance,
                    tick=db_mem.tick,
                    related_entities=related_ids,
                    source_event_id=db_mem.source_event_id
                )
            )
            
        return result
