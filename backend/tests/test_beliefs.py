import pytest
import uuid
from app.domain.character.personality import PersonalityTraits
from app.domain.character.belief import BeliefUpdateEngine, Belief, SubjectType
from app.domain.event.models import WorldEvent, EventType

def test_divergent_beliefs():
    engine = BeliefUpdateEngine()
    
    # Same event observed by two characters
    target_merchant_id = uuid.uuid4()
    
    trade_event = WorldEvent(
        world_id=uuid.uuid4(),
        tick=10,
        type=EventType.TRADE,
        actor_id=target_merchant_id,
        target_id=uuid.uuid4(),
        payload={"amount": 800}
    )
    
    # Character A: Greedy, low empathy, high aggression (cynical)
    char_a_id = uuid.uuid4()
    char_a_personality = PersonalityTraits(
        greed=0.9,
        empathy=0.2,
        aggression=0.8,
        risk_tolerance=0.5
    )
    
    # Character B: Empathetic, low greed, low aggression
    char_b_id = uuid.uuid4()
    char_b_personality = PersonalityTraits(
        greed=0.1,
        empathy=0.9,
        aggression=0.1,
        risk_tolerance=0.5
    )
    
    # Process event for Char A
    beliefs_a = engine.process_event(
        event=trade_event,
        character_id=char_a_id,
        personality=char_a_personality,
        current_beliefs=[]
    )
    
    # Process event for Char B
    beliefs_b = engine.process_event(
        event=trade_event,
        character_id=char_b_id,
        personality=char_b_personality,
        current_beliefs=[]
    )
    
    # Char A should believe the merchant is wealthy (due to greed) and dishonest (due to low empathy/high aggression)
    assert any(b.belief_type == "wealthy" for b in beliefs_a)
    assert any(b.belief_type == "dishonest" for b in beliefs_a)
    
    # Char B should not think the merchant is wealthy (not greedy enough to care) 
    # but should think they are honest (due to high empathy)
    assert not any(b.belief_type == "wealthy" for b in beliefs_b)
    assert any(b.belief_type == "honest" for b in beliefs_b)
    assert not any(b.belief_type == "dishonest" for b in beliefs_b)


def test_divergent_beliefs_resource_shortage():
    engine = BeliefUpdateEngine()
    city_id = uuid.uuid4()
    
    shortage_event = WorldEvent(
        world_id=uuid.uuid4(),
        tick=11,
        type=EventType.RESOURCE_SHORTAGE,
        city_id=city_id,
        payload={"resource": "food"}
    )
    
    # Char C: Risk-averse
    char_c_id = uuid.uuid4()
    char_c_personality = PersonalityTraits(
        risk_tolerance=0.2,
        ambition=0.3
    )
    
    # Char D: Ambitious and risk-tolerant
    char_d_id = uuid.uuid4()
    char_d_personality = PersonalityTraits(
        risk_tolerance=0.8,
        ambition=0.9
    )
    
    beliefs_c = engine.process_event(shortage_event, char_c_id, char_c_personality, [])
    beliefs_d = engine.process_event(shortage_event, char_d_id, char_d_personality, [])
    
    assert any(b.belief_type == "unstable" for b in beliefs_c)
    assert not any(b.belief_type == "opportunity" for b in beliefs_c)
    
    assert any(b.belief_type == "opportunity" for b in beliefs_d)
    assert not any(b.belief_type == "unstable" for b in beliefs_d)
