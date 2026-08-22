import uuid
import asyncio
import heapq
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from app.domain.event.models import WorldEvent, EventType
from app.domain.event.bus import EventBus
from app.agents.engine import CharacterDecisionEngine
from app.agents.models import ActionType, AgentAction
from app.agents.executor import ActionExecutionEngine, ExecutionStatus

@dataclass(order=True)
class WakeupTask:
    priority: int
    agent_id: uuid.UUID = field(compare=False)
    wakeup_reason: str = field(compare=False)
    urgency: int = field(compare=False)
    retries: int = field(default=0, compare=False)

class AgentScheduler:
    def __init__(
        self, 
        decision_engine: CharacterDecisionEngine, 
        event_bus: EventBus, 
        action_executor: Optional[ActionExecutionEngine] = None,
        max_concurrency: int = 10
    ):
        self.decision_engine = decision_engine
        self.event_bus = event_bus
        self.action_executor = action_executor
        self.max_concurrency = max_concurrency
        
        self.queue: List[WakeupTask] = []
        self.queued_agents: Set[uuid.UUID] = set()
        
        # Tracking metrics
        self.metrics = {
            "agents_evaluated": 0,
            "agents_skipped": 0,
            "llm_calls": 0,
            "decisions_executed": 0,
            "actions_rejected": 0
        }
        
        self.last_decision_tick: Dict[uuid.UUID, int] = {}
        
        # Agent metadata cache for filtering relevant agents
        self.agent_metadata: Dict[uuid.UUID, Dict[str, Any]] = {}

        self._setup_event_subscriptions()

    def _setup_event_subscriptions(self):
        if self.event_bus:
            self.event_bus.subscribe(EventType.RESOURCE_SHORTAGE, self.handle_resource_shortage)
            self.event_bus.subscribe(EventType.PROTEST, self.handle_protest)
            self.event_bus.subscribe(EventType.WORLD_TICK, self.handle_world_tick)

    def register_agent(self, agent_id: uuid.UUID, metadata: Dict[str, Any]):
        """Register agent metadata such as role, city_id, etc. to evaluate event relevance."""
        self.agent_metadata[agent_id] = metadata

    async def handle_resource_shortage(self, event: WorldEvent):
        resource = event.payload.get("resource", "FOOD")
        city_id = event.city_id
        
        for agent_id, meta in self.agent_metadata.items():
            role = meta.get("role", "")
            agent_city_id = meta.get("city_id")
            
            # Check proximity
            if agent_city_id != city_id and city_id is not None:
                continue
                
            if role in ["citizen", "merchant", "farmer", "politician", "government", "faction"]:
                self.schedule_agent(
                    agent_id, 
                    priority=1, # Lower number = higher priority
                    urgency=10, 
                    reason=f"{resource}_SHORTAGE"
                )

    async def handle_protest(self, event: WorldEvent):
        city_id = event.city_id
        for agent_id, meta in self.agent_metadata.items():
            role = meta.get("role", "")
            agent_city_id = meta.get("city_id")
            
            if agent_city_id == city_id:
                if role in ["politician", "government", "citizen", "security"]:
                    self.schedule_agent(
                        agent_id, 
                        priority=2, 
                        urgency=8, 
                        reason="PROTEST_OCCURRED"
                    )

    async def handle_world_tick(self, event: WorldEvent):
        # We can occasionally wake up agents that haven't been evaluated in a while
        current_tick = event.tick
        for agent_id, meta in self.agent_metadata.items():
            last_tick = self.last_decision_tick.get(agent_id, -999)
            # Default normal cooldown might be 10 ticks
            if (current_tick - last_tick) > 10:
                self.schedule_agent(
                    agent_id, 
                    priority=5, 
                    urgency=1, 
                    reason="ROUTINE_EVALUATION"
                )

    def schedule_agent(self, agent_id: uuid.UUID, priority: int, urgency: int, reason: str, retries: int = 0):
        if agent_id not in self.queued_agents:
            task = WakeupTask(
                priority=priority, 
                agent_id=agent_id, 
                wakeup_reason=reason, 
                urgency=urgency, 
                retries=retries
            )
            heapq.heappush(self.queue, task)
            self.queued_agents.add(agent_id)

    def can_run(self, agent_id: uuid.UUID, current_tick: int, urgency: int) -> bool:
        last_tick = self.last_decision_tick.get(agent_id, -999)
        # Higher urgency = lower cooldown. Urgency 10 -> cooldown 1
        cooldown = max(1, 11 - urgency)
        return (current_tick - last_tick) >= cooldown

    async def run_tick(self, world_id: uuid.UUID, current_tick: int):
        tasks_to_run = []
        
        while self.queue and len(tasks_to_run) < self.max_concurrency:
            task = heapq.heappop(self.queue)
            self.queued_agents.remove(task.agent_id)
            
            if self.can_run(task.agent_id, current_tick, task.urgency):
                tasks_to_run.append(task)
            else:
                self.metrics["agents_skipped"] += 1
                
        if not tasks_to_run:
            return

        # 1. PERCEPTION -> PARALLEL DECISIONS -> ACTION VALIDATION
        # Run decisions concurrently
        results = await asyncio.gather(*(self.evaluate_agent(task, world_id, current_tick) for task in tasks_to_run))
        
        valid_actions: List[Tuple[WakeupTask, AgentAction]] = []
        
        for task, action, success in results:
            if not success:
                if task.retries < 3:
                    self.schedule_agent(
                        task.agent_id, 
                        priority=task.priority, 
                        urgency=task.urgency, 
                        reason=f"Retry: {task.wakeup_reason}", 
                        retries=task.retries + 1
                    )
            elif action and action.action_type.value != "DO_NOTHING":
                valid_actions.append((task, action))

        # 2. DETERMINISTIC SORTING
        # Ordering by: world tick, agent priority, agent ID (lexicographical fallback to ensure determinism)
        valid_actions.sort(key=lambda item: (current_tick, item[0].priority, str(item[0].agent_id)))
        
        # 3. ORDERED EXECUTION -> EVENT GENERATION -> CONSEQUENCES
        for task, action in valid_actions:
            if self.action_executor:
                exec_result = await self.action_executor.execute(action, world_id, current_tick)
                if exec_result.status == ExecutionStatus.SUCCESS:
                    self.metrics["decisions_executed"] += 1
                    # Event generation and consequence trigger via EventBus
                    for event in exec_result.events_generated:
                        await self.event_bus.publish(event)
                else:
                    self.metrics["actions_rejected"] += 1
            else:
                # If no executor is provided (e.g. in some isolated tests), assume success
                self.metrics["decisions_executed"] += 1

    async def evaluate_agent(self, task: WakeupTask, world_id: uuid.UUID, current_tick: int) -> Tuple[WakeupTask, Optional[AgentAction], bool]:
        self.metrics["agents_evaluated"] += 1
        self.metrics["llm_calls"] += 1
        
        try:
            action = await self.decision_engine.decide(task.agent_id, world_id, current_tick)
            
            self.last_decision_tick[task.agent_id] = current_tick
            
            if not action:
                self.metrics["actions_rejected"] += 1
                return task, None, False
                
            is_fallback = "fallback" in action.justification_summary.lower()
            
            if is_fallback:
                self.metrics["actions_rejected"] += 1
                return task, action, False
            else:
                return task, action, True
                
        except Exception:
            self.metrics["actions_rejected"] += 1
            return task, None, False
