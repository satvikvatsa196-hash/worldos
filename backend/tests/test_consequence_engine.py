import pytest
import uuid
from app.domain.event.models import WorldEvent, EventType
from app.domain.event.consequence import ConsequenceEngine, ConsequenceRule
from typing import Any, List

class FoodShortageRule(ConsequenceRule):
    name = "FoodShortageRule"
    cooldown_ticks = 0

    def match(self, event: WorldEvent, state: Any) -> bool:
        return event.type == EventType.RESOURCE_SHORTAGE and event.payload.get("resource") == "food"

    def generate(self, event: WorldEvent, state: Any) -> List[WorldEvent]:
        return [
            WorldEvent(
                world_id=event.world_id,
                tick=event.tick,
                type=EventType.PROTEST,
                city_id=event.city_id,
                payload={"reason": "hunger"}
            )
        ]

class ProtestRule(ConsequenceRule):
    name = "ProtestRule"
    cooldown_ticks = 0

    def match(self, event: WorldEvent, state: Any) -> bool:
        return event.type == EventType.PROTEST

    def generate(self, event: WorldEvent, state: Any) -> List[WorldEvent]:
        return [
            WorldEvent(
                world_id=event.world_id,
                tick=event.tick,
                type=EventType.POLITICAL_CHANGE,
                city_id=event.city_id,
                payload={"tension_increase": 10}
            )
        ]

class InfiniteLoopRule(ConsequenceRule):
    name = "InfiniteLoopRule"
    cooldown_ticks = 0

    def match(self, event: WorldEvent, state: Any) -> bool:
        return event.type == EventType.WORLD_TICK

    def generate(self, event: WorldEvent, state: Any) -> List[WorldEvent]:
        # Generates another WORLD_TICK to cause an infinite loop if depth limit fails
        # Using a slightly different payload to bypass duplicate suppression
        return [
            WorldEvent(
                world_id=event.world_id,
                tick=event.tick,
                type=EventType.WORLD_TICK,
                payload={"depth_marker": event.payload.get("depth_marker", 0) + 1}
            )
        ]

class DuplicateGeneratingRule(ConsequenceRule):
    name = "DuplicateGeneratingRule"
    cooldown_ticks = 0

    def match(self, event: WorldEvent, state: Any) -> bool:
        return event.type == EventType.FACTION_ACTION

    def generate(self, event: WorldEvent, state: Any) -> List[WorldEvent]:
        # Generates two identical events to test duplicate suppression
        ev = WorldEvent(
            world_id=event.world_id,
            tick=event.tick,
            type=EventType.RELATIONSHIP_CHANGED,
            payload={"change": -5}
        )
        return [ev, ev]


@pytest.fixture
def engine():
    return ConsequenceEngine(max_depth=3)

@pytest.fixture
def world_id():
    return uuid.uuid4()

@pytest.fixture
def city_id():
    return uuid.uuid4()

def test_simple_consequence(engine, world_id, city_id):
    engine.register_rule(FoodShortageRule())
    
    root_event = WorldEvent(
        world_id=world_id,
        tick=10,
        type=EventType.RESOURCE_SHORTAGE,
        city_id=city_id,
        payload={"resource": "food"}
    )
    
    consequences = engine.process(root_event)
    
    assert len(consequences) == 1
    assert consequences[0].type == EventType.PROTEST
    assert consequences[0].parent_event_id == root_event.id
    assert consequences[0].city_id == city_id

def test_multi_step_cascade(engine, world_id, city_id):
    engine.register_rule(FoodShortageRule())
    engine.register_rule(ProtestRule())
    
    root_event = WorldEvent(
        world_id=world_id,
        tick=10,
        type=EventType.RESOURCE_SHORTAGE,
        city_id=city_id,
        payload={"resource": "food"}
    )
    
    consequences = engine.process(root_event)
    
    assert len(consequences) == 2
    # First level consequence
    protest_event = consequences[0]
    assert protest_event.type == EventType.PROTEST
    assert protest_event.parent_event_id == root_event.id
    
    # Second level consequence
    tension_event = consequences[1]
    assert tension_event.type == EventType.POLITICAL_CHANGE
    assert tension_event.parent_event_id == protest_event.id

def test_cascade_depth_limit(world_id):
    # Set a small max_depth to test limit
    engine = ConsequenceEngine(max_depth=2)
    engine.register_rule(InfiniteLoopRule())
    
    root_event = WorldEvent(
        world_id=world_id,
        tick=1,
        type=EventType.WORLD_TICK,
        payload={"depth_marker": 0}
    )
    
    consequences = engine.process(root_event)
    
    # depth=0: root
    # depth=1: generated 1 (consequences[0])
    # depth=2: generated 2 (consequences[1])
    # depth=3: blocked by limit
    assert len(consequences) == 2
    assert consequences[0].payload["depth_marker"] == 1
    assert consequences[1].payload["depth_marker"] == 2

def test_duplicate_suppression(engine, world_id):
    engine.register_rule(DuplicateGeneratingRule())
    
    root_event = WorldEvent(
        world_id=world_id,
        tick=5,
        type=EventType.FACTION_ACTION
    )
    
    consequences = engine.process(root_event)
    
    # The rule returns 2 identical events, but suppression should ensure only 1 is processed
    assert len(consequences) == 1
    assert consequences[0].type == EventType.RELATIONSHIP_CHANGED

def test_parent_child_event_graph(engine, world_id, city_id):
    engine.register_rule(FoodShortageRule())
    engine.register_rule(ProtestRule())
    
    root_event = WorldEvent(
        world_id=world_id,
        tick=1,
        type=EventType.RESOURCE_SHORTAGE,
        city_id=city_id,
        payload={"resource": "food"}
    )
    
    consequences = engine.process(root_event)
    
    # Build a lookup for easy graph traversal
    events_by_id = {e.id: e for e in consequences}
    events_by_id[root_event.id] = root_event
    
    assert len(consequences) == 2
    protest = consequences[0]
    political_change = consequences[1]
    
    assert protest.parent_event_id == root_event.id
    assert political_change.parent_event_id == protest.id
    
    # Verify we can traverse backwards
    curr = political_change
    curr = events_by_id[curr.parent_event_id]
    assert curr == protest
    curr = events_by_id[curr.parent_event_id]
    assert curr == root_event
    assert curr.parent_event_id is None
