import pytest
import uuid
from app.domain.relationship.models import CharacterRelationship
from app.domain.relationship.engine import RelationshipEngine
from app.domain.event.models import WorldEvent, EventType

def test_relationship_trade():
    engine = RelationshipEngine()
    actor_id = uuid.uuid4()
    target_id = uuid.uuid4()
    world_id = uuid.uuid4()
    
    trade_event = WorldEvent(
        world_id=world_id,
        tick=1,
        type=EventType.TRADE,
        actor_id=actor_id,
        target_id=target_id,
        payload={"amount": 100}
    )
    
    rels = []
    updated_rels, generated_events = engine.process_event(trade_event, rels)
    
    assert len(updated_rels) == 2
    assert updated_rels[0].trust == 0.1
    assert updated_rels[0].respect == 0.05
    assert len(generated_events) == 2
    assert generated_events[0].type == EventType.RELATIONSHIP_CHANGED
    assert generated_events[0].payload["trust_change"] == 0.1

def test_relationship_betrayal():
    engine = RelationshipEngine()
    actor_id = uuid.uuid4()
    target_id = uuid.uuid4()
    world_id = uuid.uuid4()
    
    conflict_event = WorldEvent(
        world_id=world_id,
        tick=2,
        type=EventType.CONFLICT,
        actor_id=actor_id,
        target_id=target_id,
        payload={"betrayal": True}
    )
    
    # Pre-existing relationship
    rels = [CharacterRelationship(
        source_character_id=target_id, 
        target_character_id=actor_id,
        trust=0.5,
        friendship=0.5
    )]
    
    updated_rels, generated_events = engine.process_event(conflict_event, rels)
    
    rel = next(r for r in updated_rels if r.source_character_id == target_id)
    assert rel.trust == pytest.approx(-0.3) # 0.5 - 0.8
    assert rel.friendship == pytest.approx(0.0) # 0.5 - 0.5
    assert rel.hostility == pytest.approx(0.6)
    
    assert len(generated_events) == 1
    assert generated_events[0].payload["trust_change"] == -0.8
    assert generated_events[0].payload["hostility_change"] == 0.6

def test_relationship_help_crisis():
    engine = RelationshipEngine()
    actor_id = uuid.uuid4()
    target_id = uuid.uuid4()
    world_id = uuid.uuid4()
    
    help_event = WorldEvent(
        world_id=world_id,
        tick=3,
        type=EventType.CHARACTER_ACTION,
        actor_id=actor_id,
        target_id=target_id,
        payload={"action": "HELP", "crisis": True}
    )
    
    rels = []
    updated_rels, generated_events = engine.process_event(help_event, rels)
    
    rel = updated_rels[0]
    assert rel.trust == 0.5
    assert rel.obligation == 0.6
    assert rel.friendship == 0.4
    
    assert generated_events[0].payload["obligation_change"] == 0.6

def test_relationship_political_disagreement():
    engine = RelationshipEngine()
    actor_id = uuid.uuid4()
    target_id = uuid.uuid4()
    world_id = uuid.uuid4()
    
    disagree_event = WorldEvent(
        world_id=world_id,
        tick=4,
        type=EventType.CHARACTER_ACTION,
        actor_id=actor_id,
        target_id=target_id,
        payload={"action": "POLITICAL_DISAGREEMENT"}
    )
    
    rels = []
    updated_rels, generated_events = engine.process_event(disagree_event, rels)
    
    assert updated_rels[0].respect == -0.2
    assert updated_rels[0].friendship == -0.1
    assert generated_events[0].payload["respect_change"] == -0.2
