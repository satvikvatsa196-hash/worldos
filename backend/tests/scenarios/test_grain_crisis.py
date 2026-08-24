import pytest
import uuid
import asyncio
import json
from typing import Dict, Any, Optional

from app.agents.scheduler import AgentScheduler
from app.domain.event.bus import EventBus
from app.domain.event.models import WorldEvent, EventType
from app.agents.engine import CharacterDecisionEngine
from app.agents.models import AgentAction, ActionType, AgentContext
from app.agents.executor import ActionExecutionEngine, ExecutionStatus, ActionExecutionResult
from app.llm.provider import LLMProvider
from app.llm.models import LLMResponse, LLMDecisionOutput, LLMActionSchema, LLMMetadata

class ScenarioEventBus(EventBus):
    def __init__(self):
        super().__init__()
        self.published_events = []
        
    async def publish(self, event: WorldEvent) -> None:
        self.published_events.append(event)
        await super().publish(event)

class ScenarioActionExecutor(ActionExecutionEngine):
    def __init__(self):
        self.executed_actions = []

    async def execute(self, action: AgentAction, world_id: uuid.UUID, current_tick: int) -> ActionExecutionResult:
        self.executed_actions.append(action)
        events = []
        if action.action_type == ActionType.PROTEST:
            events.append(WorldEvent(world_id=world_id, tick=current_tick, type=EventType.PROTEST, actor_id=action.actor_id))
        elif action.action_type == ActionType.FUND_PROTEST:
            events.append(WorldEvent(world_id=world_id, tick=current_tick, type=EventType.FACTION_ACTION, actor_id=action.actor_id, payload={"action": "FUND_PROTEST"}))
        elif action.action_type == ActionType.DEPLOY_SECURITY:
            events.append(WorldEvent(world_id=world_id, tick=current_tick, type=EventType.POLITICAL_CHANGE, actor_id=action.actor_id, payload={"action": "DEPLOY_SECURITY"}))
        elif action.action_type == ActionType.SELL_RESOURCE:
            events.append(WorldEvent(world_id=world_id, tick=current_tick, type=EventType.PRICE_CHANGED, actor_id=action.actor_id, payload={"reason": "price_gouging"}))

        return ActionExecutionResult(status=ExecutionStatus.SUCCESS, reason="Simulated", events_generated=events)

class EmergentLLMProvider(LLMProvider):
    def __init__(self, agent_states: Dict[uuid.UUID, Dict[str, Any]], event_bus: ScenarioEventBus):
        self.agent_states = agent_states
        self.event_bus = event_bus

    async def get_decision(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        context = json.loads(user_prompt.split("Context: ")[1])
        agent_id_str = context["character_state"].get("agent_id")
        
        if not agent_id_str:
            return self._fallback()
            
        agent_id = uuid.UUID(agent_id_str)
        state = self.agent_states.get(agent_id, {})
        role = state.get("role")
        wealth = state.get("wealth", 0)
        
        recent_event_types = [e.type for e in self.event_bus.published_events[-5:]]
        
        action_type = ActionType.DO_NOTHING
        reason = "Observing the situation."
        
        if role == "merchant" and EventType.RESOURCE_SHORTAGE in recent_event_types:
            action_type = ActionType.SELL_RESOURCE
            reason = "Exploiting grain shortage to raise prices."
            
        elif role == "citizen" and EventType.PRICE_CHANGED in recent_event_types and wealth < 20:
            action_type = ActionType.PROTEST
            reason = "Cannot afford grain, protesting!"
            
        elif role == "faction" and EventType.PROTEST in recent_event_types:
            action_type = ActionType.FUND_PROTEST
            reason = "Supporting unrest to gain political influence."
            
        elif role == "government" and EventType.FACTION_ACTION in recent_event_types:
            action_type = ActionType.DEPLOY_SECURITY
            reason = "Quelling funded protests to maintain order."
            
        decision = LLMDecisionOutput(
            decision_summary=reason,
            action=LLMActionSchema(type=action_type.value, parameters={}),
            confidence=0.9
        )
        return LLMResponse(decision=decision, metadata=LLMMetadata(), is_success=True)
        
    def _fallback(self):
        return LLMResponse(
            decision=LLMDecisionOutput(
                decision_summary="Fallback",
                action=LLMActionSchema(type="DO_NOTHING", parameters={}),
                confidence=1.0
            ),
            metadata=LLMMetadata(),
            is_success=True
        )

class ContextAwareDecisionEngine(CharacterDecisionEngine):
    def __init__(self, llm_provider, validator, store, agent_states):
        super().__init__(llm_provider, validator, store)
        self.agent_states = agent_states

    def _build_context(self, character: Any, world: Any) -> AgentContext:
        agent_id = character
        state = self.agent_states.get(agent_id, {})
        return AgentContext(
            character_state={"agent_id": str(agent_id), **state},
            needs={},
            goals=[],
            relevant_memories=[],
            beliefs=[],
            nearby_entities=[],
            relationships=[],
            current_economic_conditions={},
            recent_events=[]
        )

    async def decide(self, agent_id: uuid.UUID, world_id: uuid.UUID, current_tick: int, character: Any = None, world: Any = None) -> Any:
        return await super().decide(agent_id, world_id, current_tick, character=agent_id, world=world)

@pytest.mark.asyncio
async def test_emergent_grain_crisis():
    world_id = uuid.uuid4()
    city_id = uuid.uuid4()
    
    merchant_id = uuid.uuid4()
    citizen_id = uuid.uuid4()
    faction_id = uuid.uuid4()
    gov_id = uuid.uuid4()
    
    agent_states = {
        merchant_id: {"role": "merchant", "wealth": 10000},
        citizen_id: {"role": "citizen", "wealth": 5},
        faction_id: {"role": "faction", "wealth": 5000},
        gov_id: {"role": "government", "wealth": 50000}
    }
    
    event_bus = ScenarioEventBus()
    executor = ScenarioActionExecutor()
    store = type("MockStore", (), {"save": lambda self, r: asyncio.sleep(0)})()
    validator = type("MockVal", (), {"validate": lambda self, a, c: True})()
    
    llm_provider = EmergentLLMProvider(agent_states, event_bus)
    decision_engine = ContextAwareDecisionEngine(llm_provider, validator, store, agent_states)
    
    scheduler = AgentScheduler(decision_engine, event_bus, action_executor=executor, max_concurrency=10)
    
    for aid, state in agent_states.items():
        state["city_id"] = city_id
        scheduler.register_agent(aid, state)
        
    catalyst = WorldEvent(
        world_id=world_id,
        tick=1,
        type=EventType.RESOURCE_SHORTAGE,
        city_id=city_id,
        payload={"resource": "GRAIN"}
    )
    await event_bus.publish(catalyst)
    
    # Tick 1: Merchant reacts to shortage
    await scheduler.run_tick(world_id, 1)
    
    actions_types = [a.action_type for a in executor.executed_actions]
    print(f"\n[test_grain_crisis] Executed Actions: {actions_types}", flush=True)
    assert any(a.action_type == ActionType.SELL_RESOURCE for a in executor.executed_actions), f"Expected SELL_RESOURCE, got {actions_types}"
    
    # Simulate event listeners waking up specific cohorts
    scheduler.schedule_agent(citizen_id, priority=1, urgency=10, reason="PRICE_CHANGED")
    
    # Tick 2: Citizen reacts to price gouging
    await scheduler.run_tick(world_id, 2)
    assert any(a.action_type == ActionType.PROTEST for a in executor.executed_actions)
    
    # Tick 3: Faction reacts to the resulting protest
    scheduler.schedule_agent(faction_id, priority=1, urgency=10, reason="PROTEST")
    await scheduler.run_tick(world_id, 3)
    assert any(a.action_type == ActionType.FUND_PROTEST for a in executor.executed_actions)
    
    # Simulate event listener for government
    scheduler.schedule_agent(gov_id, priority=1, urgency=10, reason="FACTION_ACTION")
    
    # Tick 4: Government reacts to faction interference
    await scheduler.run_tick(world_id, 4)
    assert any(a.action_type == ActionType.DEPLOY_SECURITY for a in executor.executed_actions)
    
    # Validate the full cascade length
    assert len(executor.executed_actions) >= 4
    
    timeline = []
    for e in event_bus.published_events:
        timeline.append(f"Tick {e.tick}: Event {e.type.name} Triggered by {e.actor_id or 'World'}")
        
    with open("grain_crisis_timeline.txt", "w") as f:
        f.write("\n".join(timeline))
