from abc import ABC, abstractmethod
from typing import List, Dict, Set, Any, Optional
import uuid

from app.domain.event.models import WorldEvent

class ConsequenceRule(ABC):
    name: str = "BaseRule"
    cooldown_ticks: int = 0
    
    @abstractmethod
    def match(self, event: WorldEvent, state: Any) -> bool:
        """Returns True if this rule applies to the given event."""
        pass
        
    @abstractmethod
    def generate(self, event: WorldEvent, state: Any) -> List[WorldEvent]:
        """Generates the consequence events.
        The engine will automatically set the correct parent_event_id.
        """
        pass

class ConsequenceEngine:
    def __init__(self, max_depth: int = 5):
        self.max_depth = max_depth
        self.rules: List[ConsequenceRule] = []
        # Track cooldowns: rule.name -> tick when it can be used again
        self._cooldowns: Dict[str, int] = {}
        
    def register_rule(self, rule: ConsequenceRule):
        self.rules.append(rule)
        
    def clear_cooldowns(self):
        self._cooldowns.clear()

    def _get_event_signature(self, event: WorldEvent) -> str:
        # Create a unique signature for an event to prevent duplicates in a single cascade
        payload_tuple = tuple(sorted((str(k), str(v)) for k, v in event.payload.items()))
        return f"{event.type.value}:{event.actor_id}:{event.target_id}:{event.city_id}:{event.faction_id}:{hash(payload_tuple)}"

    def process(self, root_event: WorldEvent, state: Any = None) -> List[WorldEvent]:
        all_generated_events: List[WorldEvent] = []
        
        # We will use a queue to process events level by level (BFS)
        # queue stores tuples of (event_to_process, current_depth)
        queue = [(root_event, 0)]
        
        # Track signatures of generated events to suppress duplicates in this cascade
        generated_signatures: Set[str] = set()

        while queue:
            current_event, depth = queue.pop(0)
            
            if depth >= self.max_depth:
                continue
                
            for rule in self.rules:
                # Check cooldown
                next_allowed_tick = self._cooldowns.get(rule.name, 0)
                if current_event.tick < next_allowed_tick:
                    continue
                    
                if rule.match(current_event, state):
                    new_events = rule.generate(current_event, state)
                    
                    for new_event in new_events:
                        # Enforce parent_event_id preservation to build the graph
                        # Create a new immutable copy with the parent_event_id set
                        # to the current_event.id
                        event_kwargs = new_event.model_dump()
                        event_kwargs['parent_event_id'] = current_event.id
                        # Don't carry over the old id, let a new one be generated or use the one provided
                        if 'id' in event_kwargs and event_kwargs['parent_event_id'] != current_event.id:
                            event_kwargs.pop('id') # To ensure fresh id if we copied an existing event mistakenly
                            
                        # Re-instantiate to enforce frozen and constraints
                        # We use model_copy with update if new_event already has an ID, but let's just make sure
                        # the parent_event_id is set correctly.
                        final_event = new_event.model_copy(update={'parent_event_id': current_event.id})
                        
                        signature = self._get_event_signature(final_event)
                        
                        if signature not in generated_signatures:
                            generated_signatures.add(signature)
                            all_generated_events.append(final_event)
                            queue.append((final_event, depth + 1))
                            
                    # Apply cooldown if this rule generated something
                    if new_events and rule.cooldown_ticks > 0:
                        self._cooldowns[rule.name] = current_event.tick + rule.cooldown_ticks

        return all_generated_events
