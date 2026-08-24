import uuid
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from app.agents.models import AgentAction, AgentContext, ActionType
from app.agents.interfaces import ActionValidator
from app.llm.provider import LLMProvider
from app.core.telemetry import TraceLogger, metrics
import time

logger = TraceLogger(__name__)

class DecisionRecord(BaseModel):
    decision_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    agent_id: uuid.UUID
    world_id: uuid.UUID
    tick: int
    decision_summary: str
    action: AgentAction
    confidence: float
    latency: float
    token_usage: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(frozen=True)

class IDecisionStore:
    """Interface for persisting agent decisions."""
    async def save(self, record: DecisionRecord) -> None:
        pass

class CharacterDecisionEngine:
    """
    Engine responsible for orchestrating the character decision loop:
    Character -> PerceptionBuilder -> MemoryRetriever -> GoalEvaluator -> AgentContext -> LLMProvider -> AgentDecision -> ActionValidator -> validated action
    """
    def __init__(
        self, 
        llm_provider: LLMProvider, 
        validator: ActionValidator,
        store: IDecisionStore
    ):
        self.llm_provider = llm_provider
        self.validator = validator
        self.store = store
        self._last_decision_tick: Dict[uuid.UUID, int] = {}

    def should_run(self, agent_id: uuid.UUID, current_tick: int, priority: str = "NORMAL") -> bool:
        """
        Determines if the agent should make a decision based on configured frequency.
        Assuming 1 tick = 1 hour:
        - HIGH: ~2 ticks (1-3 hours)
        - NORMAL: ~9 ticks (6-12 hours)
        - LOW: ~18 ticks (12-24 hours)
        """
        last_tick = self._last_decision_tick.get(agent_id, -999)
        cooldowns = {
            "HIGH": 2,    
            "NORMAL": 9,  
            "LOW": 18     
        }
        cooldown = cooldowns.get(priority.upper(), 9)
        return (current_tick - last_tick) >= cooldown

    def _build_context(self, character: Any, world: Any) -> AgentContext:
        """
        Builds the agent context by orchestrating the sub-components.
        (Mocked implementations for now, but shows the architectural flow).
        """
        perception = PerceptionBuilder().build(character, world)
        memories = MemoryRetriever().retrieve(character)
        goals = GoalEvaluator().evaluate(character)
        
        return AgentContext(
            character_state=perception,
            needs={"food": 0.5, "rest": 0.2}, # Mocked
            goals=goals,
            relevant_memories=memories,
            beliefs=[],
            nearby_entities=[],
            relationships=[],
            current_economic_conditions={},
            recent_events=[]
        )

    def _create_fallback_action(self, agent_id: uuid.UUID, reason: str) -> AgentAction:
        return AgentAction(
            action_type=ActionType.DO_NOTHING,
            actor_id=agent_id,
            justification_summary=reason,
            confidence=1.0,
            parameters={}
        )

    async def decide(
        self, 
        agent_id: uuid.UUID, 
        world_id: uuid.UUID, 
        current_tick: int, 
        character: Any = None,
        world: Any = None
    ) -> Tuple[Optional[AgentAction], DecisionRecord]:
        
        # 1. Perception & Context Generation
        context = self._build_context(character, world)
        
        system_prompt = "You are an autonomous character in a simulated world. Decide your next action."
        user_prompt = f"Context: {context.model_dump_json()}"
        
        # 2. LLM Invocation
        response = await self.llm_provider.get_decision(system_prompt, user_prompt)
        
        # 3. Handle Failure & Malformed Response deterministically
        if not response.is_success or not response.decision:
            error_msg = response.metadata.error if response.metadata else "Unknown LLM failure"
            metrics.inc_counter("llm_failures")
            logger.error(f"Agent decision failed", world_id=str(world_id), tick=current_tick, agent_id=str(agent_id), error=error_msg)
            
            action = self._create_fallback_action(agent_id, f"Fallback due to LLM provider failure: {error_msg}")
            decision_summary = f"LLM failure fallback: {error_msg}"
            confidence = 1.0
            usage_dict = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "error": error_msg}
            latency = response.metadata.latency_ms if response.metadata else 0.0
        else:
            decision = response.decision
            
            # Map LLM schema to AgentAction
            try:
                action_type = ActionType(decision.action.type)
            except ValueError:
                action_type = ActionType.DO_NOTHING
                
            action = AgentAction(
                action_type=action_type,
                actor_id=agent_id,
                parameters=decision.action.parameters,
                justification_summary=decision.decision_summary,
                confidence=decision.confidence
            )
            decision_summary = decision.decision_summary
            confidence = decision.confidence
            usage_dict = response.metadata.usage.model_dump()
            latency = response.metadata.latency_ms
        
        # 4. Action Validation
        if not self.validator.validate(action, context):
            logger.warning(f"Agent {agent_id} proposed invalid action {action.action_type}. Using fallback.")
            action = self._create_fallback_action(agent_id, "Proposed action was invalid for current context.")
            decision_summary = "Validation failure fallback"
            usage_dict["error"] = "Validation failure"

        # 5. Metadata & Persistence
        record = DecisionRecord(
            agent_id=agent_id,
            world_id=world_id,
            tick=current_tick,
            decision_summary=decision_summary,
            action=action,
            confidence=confidence,
            latency=latency,
            token_usage=usage_dict
        )
        
        await self.store.save(record)
        
        # 6. Update Cooldown tracking
        self._last_decision_tick[agent_id] = current_tick
        
        is_fallback = "fallback" in action.justification_summary.lower()
        logger.info(
            "Agent decision generated",
            world_id=str(world_id),
            tick=current_tick,
            agent_id=str(agent_id),
            decision_id=str(record.decision_id),
            action_type=action.action_type.value,
            fallback=is_fallback
        )
        
        return action, record

# Simple mock stubs for the pipeline components
class PerceptionBuilder:
    def build(self, character: Any, world: Any) -> Dict[str, Any]:
        return {"health": 100, "wealth": 50}

class MemoryRetriever:
    def retrieve(self, character: Any, max_memories: int = 5) -> List[Dict[str, Any]]:
        start_time = time.time()
        
        if not hasattr(character, 'memories') or not character.memories:
            return []
            
        memories = list(character.memories)
        
        # Relevant-memory retrieval: sort by importance and recency
        memories.sort(key=lambda m: (getattr(m, 'importance', 0), getattr(m, 'tick', 0)), reverse=True)
        
        # Context minimization: Limit context window size
        top_memories = memories[:max_memories]
        
        # Memory summarization: extract only minimal semantic content
        summarized = []
        for mem in top_memories:
            summarized.append({
                "type": getattr(mem, "type", "event"),
                "summary": getattr(mem, "summary", str(mem)),
                "age": getattr(character, "world", None).current_tick - getattr(mem, "tick", 0) if hasattr(character, "world") else getattr(mem, "tick", 0)
            })
            
        latency_ms = (time.time() - start_time) * 1000.0
        metrics.observe_latency("memory_retrieval_latency", latency_ms)
        
        return summarized

class GoalEvaluator:
    def evaluate(self, character: Any) -> List[Dict[str, Any]]:
        return [{"type": "survival", "priority": 1}]

class FactionDecisionEngine(CharacterDecisionEngine):
    """
    Engine responsible for orchestrating the faction decision loop.
    Inherits from CharacterDecisionEngine to reuse the exact same architecture, 
    but modifies the context building to represent a faction.
    """
    
    def _build_context(self, faction: Any, world: Any) -> AgentContext:
        """
        Builds the agent context for a faction.
        """
        # Mocked perception for faction
        # In reality, this would pull from Faction properties (wealth, power, influence, members, etc.)
        perception = {
            "wealth": getattr(faction, "wealth", 1000),
            "power": getattr(faction, "power", 50),
            "influence": getattr(faction, "influence", 50),
            "ideology": getattr(faction, "ideology", "neutral"),
            "member_count": len(getattr(faction, "members", [])),
        }
        
        # Factions use the exact same AgentContext, we map faction goals/needs here
        return AgentContext(
            character_state=perception, # reusing character_state as the agent's state
            needs={"funds": 0.5, "recruits": 0.8},
            goals=[{"type": "expand_influence", "priority": 1}],
            relevant_memories=[], 
            beliefs=[], 
            nearby_entities=[],
            relationships=[], # Faction relationships
            current_economic_conditions={},
            recent_events=[]
        )
        
    async def decide(
        self, 
        agent_id: uuid.UUID, 
        world_id: uuid.UUID, 
        current_tick: int, 
        faction: Any = None,
        world: Any = None
    ) -> Tuple[Optional[AgentAction], DecisionRecord]:
        
        context = self._build_context(faction, world)
        
        system_prompt = "You are a faction in a simulated world. Decide your next organizational action."
        user_prompt = f"Context: {context.model_dump_json()}"
        
        response = await self.llm_provider.get_decision(system_prompt, user_prompt)
        
        if not response.is_success or not response.decision:
            error_msg = response.metadata.error if response.metadata else "Unknown LLM failure"
            metrics.inc_counter("llm_failures")
            logger.error(f"Faction decision failed", world_id=str(world_id), tick=current_tick, agent_id=str(agent_id), error=error_msg)
            
            action = self._create_fallback_action(agent_id, f"Fallback due to LLM provider failure: {error_msg}")
            decision_summary = f"LLM failure fallback: {error_msg}"
            confidence = 1.0
            usage_dict = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "error": error_msg}
            latency = response.metadata.latency_ms if response.metadata else 0.0
        else:
            decision = response.decision
            try:
                action_type = ActionType(decision.action.type)
            except ValueError:
                action_type = ActionType.DO_NOTHING
                
            action = AgentAction(
                action_type=action_type,
                actor_id=agent_id,
                parameters=decision.action.parameters,
                justification_summary=decision.decision_summary,
                confidence=decision.confidence
            )
            decision_summary = decision.decision_summary
            confidence = decision.confidence
            usage_dict = response.metadata.usage.model_dump()
            latency = response.metadata.latency_ms
        
        if not self.validator.validate(action, context):
            logger.warning(f"Faction {agent_id} proposed invalid action {action.action_type}. Using fallback.")
            action = self._create_fallback_action(agent_id, "Proposed action was invalid for current context.")
            decision_summary = "Validation failure fallback"
            usage_dict["error"] = "Validation failure"

        record = DecisionRecord(
            agent_id=agent_id,
            world_id=world_id,
            tick=current_tick,
            decision_summary=decision_summary,
            action=action,
            confidence=confidence,
            latency=latency,
            token_usage=usage_dict
        )
        
        await self.store.save(record)
        self._last_decision_tick[agent_id] = current_tick
        
        is_fallback = "fallback" in action.justification_summary.lower()
        logger.info(
            "Faction decision generated",
            world_id=str(world_id),
            tick=current_tick,
            agent_id=str(agent_id),
            decision_id=str(record.decision_id),
            action_type=action.action_type.value,
            fallback=is_fallback
        )
        
        return action, record
