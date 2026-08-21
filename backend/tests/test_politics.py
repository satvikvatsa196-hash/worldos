import pytest
import uuid
from app.domain.politics.models import Government, Policy, PolicyType
from app.domain.politics.engine import PoliticalEngine
from app.domain.event.models import EventType
from app.agents.models import ActionType

def test_policy_creation_and_effects():
    engine = PoliticalEngine()
    world_id = uuid.uuid4()
    
    gov = Government(
        world_id=world_id,
        approval=0.5,
        stability=0.5,
        active_policies=[
            Policy(name="High Grain Tax", type=PolicyType.TAX, value=0.5), # 0.5 is high
            Policy(name="Low Wages", type=PolicyType.WAGE, value=0.8), # less than 1.0 is low
            Policy(name="Military Build-up", type=PolicyType.MILITARY_SPENDING, value=0.6)
        ]
    )
    
    new_gov, events = engine.evaluate_policies(gov, current_tick=1, economic_indicators={})
    
    # TAX value 0.5: approval -= 0.05 * 0.5 (0.025), stability -= 0.02 * 0.5 (0.01)
    # WAGE value 0.8: approval -= 0.08
    # MILITARY value 0.6: security += 0.03, stability += 0.012, approval -= 0.006
    # Total approval delta = -0.025 - 0.08 - 0.006 = -0.111 -> new approval = 0.389
    # Total stability delta = -0.01 + 0.012 = +0.002 -> new stability = 0.502
    
    assert new_gov.approval < 0.4
    assert new_gov.stability > 0.5
    assert new_gov.security_capacity > 0.5
    
    assert any(e.type == EventType.POLICY_CHANGED for e in events)

def test_protest_generation():
    engine = PoliticalEngine()
    world_id = uuid.uuid4()
    
    gov = Government(
        world_id=world_id,
        approval=0.1, # extremely low approval
        stability=0.5,
        active_policies=[]
    )
    
    new_gov, events = engine.evaluate_policies(gov, current_tick=1, economic_indicators={})
    
    # Protest prob: 0.05 + (1.0 - 0.1) * 0.8 = 0.05 + 0.72 = 0.77.
    # 0.77 > 0.6 -> Protest triggers.
    
    assert any(e.type == EventType.PROTEST for e in events)

def test_faction_pressure_and_protest_effects():
    engine = PoliticalEngine()
    world_id = uuid.uuid4()
    
    gov = Government(
        world_id=world_id,
        approval=0.5,
        stability=0.5,
        security_capacity=0.8
    )
    
    # Factions apply actions
    actions = [
        {"type": ActionType.PROTEST, "actor_id": uuid.uuid4(), "parameters": {"intensity": 1.0}},
        {"type": ActionType.FUND_PROTEST, "parameters": {"amount": 500}},
        {"type": ActionType.OPPOSE_POLICY},
        {"type": ActionType.DEPLOY_SECURITY, "parameters": {"force_level": 0.5}}
    ]
    
    new_gov, events = engine.process_political_actions(gov, actions, current_tick=1)
    
    # PROTEST 1.0: stab -= 0.1, app -= 0.05
    # FUND 500: impact min(0.2, 500/5000) = 0.1. stab -= 0.1
    # OPPOSE: app -= 0.02
    # DEPLOY 0.5: stab += 0.2*0.5 = +0.1, app -= 0.15*0.5 = -0.075
    # Overall stab: 0.5 - 0.1 - 0.1 + 0.1 = 0.4
    # Overall app: 0.5 - 0.05 - 0.02 - 0.075 = 0.355
    
    assert new_gov.stability == pytest.approx(0.4)
    assert new_gov.approval == pytest.approx(0.355)
    
    assert len(events) == 1
    assert events[0].type == EventType.PROTEST
    
