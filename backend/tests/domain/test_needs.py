import pytest
import uuid
from pydantic import ValidationError
from app.domain.character.needs import CharacterNeeds, CharacterStateSnapshot, NeedEngine

def test_snapshot_is_immutable():
    needs = CharacterNeeds()
    snapshot = CharacterStateSnapshot(
        character_id=uuid.uuid4(),
        name="Test Char",
        occupation="Tester",
        health=100.0,
        wealth_balance=50.0,
        needs=needs
    )
    
    with pytest.raises(ValidationError):
        snapshot.name = "New Name"

def test_hunger_increases():
    # food value decreasing means hunger increases
    engine = NeedEngine()
    needs = CharacterNeeds(food=100.0)
    snapshot = CharacterStateSnapshot(
        character_id=uuid.uuid4(),
        name="Test Char",
        occupation="Tester",
        health=100.0,
        wealth_balance=50.0,
        needs=needs
    )
    
    new_needs = engine.process_tick(snapshot)
    assert new_needs.food < needs.food

def test_food_consumption_decreases_hunger():
    engine = NeedEngine()
    needs = CharacterNeeds(food=50.0)
    
    # Consuming food should increase the food need value (decrease hunger)
    new_needs = engine.consume_food(needs, nutrition_value=30.0)
    assert new_needs.food == 80.0

def test_needs_remain_within_valid_bounds():
    engine = NeedEngine()
    needs = CharacterNeeds(food=5.0, safety=95.0, wealth=0.0)
    snapshot = CharacterStateSnapshot(
        character_id=uuid.uuid4(),
        name="Test Char",
        occupation="Tester",
        health=100.0,
        wealth_balance=50.0,
        needs=needs,
        in_danger=False, # safety increases
        has_job=False # wealth decreases
    )
    
    # Tick multiple times to hit boundaries
    for _ in range(10):
        new_needs = engine.process_tick(snapshot)
        # Update snapshot for next tick with new needs
        snapshot = CharacterStateSnapshot(
            character_id=snapshot.character_id,
            name=snapshot.name,
            occupation=snapshot.occupation,
            health=snapshot.health,
            wealth_balance=snapshot.wealth_balance,
            needs=new_needs,
            in_danger=snapshot.in_danger,
            has_job=snapshot.has_job
        )
    
    final_needs = snapshot.needs
    
    # Food decreases to 0 but not below
    assert final_needs.food == 0.0
    
    # Wealth decreases to 0 but not below
    assert final_needs.wealth == 0.0
    
    # Safety increases to 100 but not above
    assert final_needs.safety == 100.0
    
    # Consume huge amount of food
    stuffed_needs = engine.consume_food(final_needs, 200.0)
    assert stuffed_needs.food == 100.0

def test_simulation_progression_affects_needs():
    engine = NeedEngine()
    needs = CharacterNeeds(wealth=50.0, safety=100.0, social=100.0)
    
    # Context 1: Has job, safe, not isolated
    snapshot1 = CharacterStateSnapshot(
        character_id=uuid.uuid4(),
        name="Test Char",
        occupation="Tester",
        health=100.0,
        wealth_balance=50.0,
        needs=needs,
        has_job=True,
        in_danger=False,
        is_isolated=False
    )
    
    new_needs1 = engine.process_tick(snapshot1)
    assert new_needs1.wealth > needs.wealth # Job increases wealth
    assert new_needs1.safety == needs.safety # Safety maxed
    assert new_needs1.social < needs.social # Social decays slowly
    
    # Context 2: No job, in danger, isolated
    snapshot2 = CharacterStateSnapshot(
        character_id=uuid.uuid4(),
        name="Test Char",
        occupation="Tester",
        health=100.0,
        wealth_balance=50.0,
        needs=needs,
        has_job=False,
        in_danger=True,
        is_isolated=True
    )
    
    new_needs2 = engine.process_tick(snapshot2)
    assert new_needs2.wealth < needs.wealth # Unemployment decreases wealth
    assert new_needs2.safety < needs.safety # Danger decreases safety significantly
    assert new_needs2.social < new_needs1.social # Isolation decreases social more than normal decay
