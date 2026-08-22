import pytest
import uuid
import asyncio

from app.agents.scheduler import AgentScheduler
from app.domain.event.bus import EventBus
from app.domain.event.models import WorldEvent, EventType
from app.agents.engine import CharacterDecisionEngine
from app.agents.models import AgentAction, ActionType
from app.agents.mock import MockActionValidator
from app.llm.mock import MockLLMProvider
from app.llm.models import LLMResponse, LLMDecisionOutput, LLMActionSchema, LLMMetadata
from app.agents.executor import ActionExecutionEngine, ExecutionStatus, ActionExecutionResult

class MockDecisionStore:
    async def save(self, record):
        pass

class MockActionExecutor(ActionExecutionEngine):
    def __init__(self):
        self.executed_actions = []

    async def execute(self, action: AgentAction, world_id: uuid.UUID, current_tick: int) -> ActionExecutionResult:
        self.executed_actions.append(action)
        return ActionExecutionResult(status=ExecutionStatus.SUCCESS, reason="Mock success")

@pytest.fixture
def store():
    return MockDecisionStore()

@pytest.fixture
def event_bus():
    return EventBus()

@pytest.fixture
def decision_engine(store):
    llm = MockLLMProvider()
    validator = MockActionValidator(accept_all=True)
    return CharacterDecisionEngine(llm, validator, store)

@pytest.fixture
def scheduler(decision_engine, event_bus):
    return AgentScheduler(decision_engine, event_bus, action_executor=MockActionExecutor(), max_concurrency=5)

@pytest.mark.asyncio
async def test_scheduler_event_driven_wakeup(scheduler, event_bus):
    world_id = uuid.uuid4()
    
    citizen_id = uuid.uuid4()
    unrelated_id = uuid.uuid4()
    
    scheduler.register_agent(citizen_id, {"role": "citizen", "city_id": world_id})
    scheduler.register_agent(unrelated_id, {"role": "hermit", "city_id": world_id})
    
    event = WorldEvent(
        world_id=world_id,
        tick=1,
        type=EventType.RESOURCE_SHORTAGE,
        city_id=world_id,
        payload={"resource": "FOOD"}
    )
    
    await event_bus.publish(event)
    
    assert citizen_id in scheduler.queued_agents
    assert unrelated_id not in scheduler.queued_agents
    assert len(scheduler.queue) == 1
    
    task = scheduler.queue[0]
    assert task.agent_id == citizen_id
    assert task.wakeup_reason == "FOOD_SHORTAGE"

@pytest.mark.asyncio
async def test_scheduler_cooldown_and_skip(scheduler):
    world_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    
    scheduler.schedule_agent(agent_id, priority=5, urgency=1, reason="ROUTINE")
    
    scheduler.last_decision_tick[agent_id] = 1
    
    await scheduler.run_tick(world_id, 2)
    
    assert scheduler.metrics["agents_skipped"] == 1
    assert scheduler.metrics["agents_evaluated"] == 0
    assert agent_id not in scheduler.queued_agents 

@pytest.mark.asyncio
async def test_scheduler_execution_and_metrics(store, event_bus):
    world_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    
    decision = LLMDecisionOutput(
        decision_summary="Working",
        action=LLMActionSchema(type="WORK", parameters={}),
        confidence=0.9
    )
    response = LLMResponse(decision=decision, metadata=LLMMetadata(), is_success=True)
    llm = MockLLMProvider(response=response)
    validator = MockActionValidator(accept_all=True)
    engine = CharacterDecisionEngine(llm, validator, store)
    
    executor = MockActionExecutor()
    scheduler = AgentScheduler(engine, event_bus, action_executor=executor)
    
    scheduler.schedule_agent(agent_id, priority=1, urgency=10, reason="TEST")
    
    await scheduler.run_tick(world_id, 1)
    
    assert scheduler.metrics["agents_evaluated"] == 1
    assert scheduler.metrics["llm_calls"] == 1
    assert scheduler.metrics["decisions_executed"] == 1
    assert scheduler.metrics["actions_rejected"] == 0
    
    assert scheduler.last_decision_tick[agent_id] == 1
    assert len(executor.executed_actions) == 1
    assert executor.executed_actions[0].actor_id == agent_id

@pytest.mark.asyncio
async def test_scheduler_retry_on_failure(store, event_bus):
    world_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    
    llm = MockLLMProvider(should_fail=True)
    validator = MockActionValidator(accept_all=True)
    engine = CharacterDecisionEngine(llm, validator, store)
    
    scheduler = AgentScheduler(engine, event_bus, action_executor=MockActionExecutor())
    
    scheduler.schedule_agent(agent_id, priority=1, urgency=10, reason="TEST")
    
    await scheduler.run_tick(world_id, 1)
    
    assert scheduler.metrics["agents_evaluated"] == 1
    assert scheduler.metrics["actions_rejected"] == 1
    assert scheduler.metrics["decisions_executed"] == 0
    
    assert agent_id in scheduler.queued_agents
    assert len(scheduler.queue) == 1
    task = scheduler.queue[0]
    assert task.retries == 1
    assert "Retry" in task.wakeup_reason

@pytest.mark.asyncio
async def test_scheduler_concurrency_limit(decision_engine, event_bus):
    scheduler = AgentScheduler(decision_engine, event_bus, action_executor=MockActionExecutor(), max_concurrency=2)
    world_id = uuid.uuid4()
    
    for i in range(5):
        agent_id = uuid.uuid4()
        scheduler.schedule_agent(agent_id, priority=1, urgency=10, reason="TEST")
        
    assert len(scheduler.queue) == 5
    
    await scheduler.run_tick(world_id, 1)
    
    assert scheduler.metrics["agents_evaluated"] == 2
    assert len(scheduler.queue) == 3

@pytest.mark.asyncio
async def test_scheduler_deterministic_ordering(store, event_bus):
    # Setup multiple agents with different priorities and UUIDs
    world_id = uuid.uuid4()
    
    # We want a deterministic LLM that returns a valid action so it gets executed
    decision = LLMDecisionOutput(
        decision_summary="Working",
        action=LLMActionSchema(type="WORK", parameters={}),
        confidence=0.9
    )
    response = LLMResponse(decision=decision, metadata=LLMMetadata(), is_success=True)
    llm = MockLLMProvider(response=response)
    validator = MockActionValidator(accept_all=True)
    engine = CharacterDecisionEngine(llm, validator, store)
    
    executor = MockActionExecutor()
    scheduler = AgentScheduler(engine, event_bus, action_executor=executor, max_concurrency=10)
    
    # Agent UUIDs sorted deterministically
    agent1 = uuid.UUID('11111111-1111-1111-1111-111111111111')
    agent2 = uuid.UUID('22222222-2222-2222-2222-222222222222')
    agent3 = uuid.UUID('33333333-3333-3333-3333-333333333333')
    
    # Schedule out of order
    # Lower priority number = executed first
    scheduler.schedule_agent(agent3, priority=1, urgency=10, reason="TEST") # Should be first due to priority
    scheduler.schedule_agent(agent2, priority=2, urgency=10, reason="TEST") # Should be second
    scheduler.schedule_agent(agent1, priority=2, urgency=10, reason="TEST") # Tie on priority, so lexicographical by agent_id (agent1 before agent2)
    
    await scheduler.run_tick(world_id, 1)
    
    # Expected order: agent3 (p1), agent1 (p2, lower UUID), agent2 (p2, higher UUID)
    assert len(executor.executed_actions) == 3
    assert executor.executed_actions[0].actor_id == agent3
    assert executor.executed_actions[1].actor_id == agent1
    assert executor.executed_actions[2].actor_id == agent2
