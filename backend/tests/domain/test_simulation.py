import pytest
import uuid
from app.domain.simulation.clock import SimulationClock, SimulationStatus
from app.domain.simulation.engine import SimulationEngine

def test_clock_initialization():
    clock = SimulationClock()
    assert clock.current_tick == 0
    assert clock.simulation_status == SimulationStatus.PAUSED
    assert clock.day == 0
    assert clock.hour == 0

def test_clock_start_pause():
    clock = SimulationClock()
    clock.start()
    assert clock.simulation_status == SimulationStatus.RUNNING
    
    clock.pause()
    assert clock.simulation_status == SimulationStatus.PAUSED

def test_clock_progression():
    clock = SimulationClock()
    clock.start()
    clock.advance_one_tick()
    assert clock.current_tick == 1
    assert clock.hour == 1
    assert clock.day == 0

def test_clock_does_not_advance_when_paused():
    clock = SimulationClock()
    clock.advance_one_tick()
    assert clock.current_tick == 0

def test_clock_hour_rollover():
    clock = SimulationClock()
    clock.start()
    for _ in range(24):
        clock.advance_one_tick()
    assert clock.current_tick == 24
    assert clock.hour == 0
    assert clock.day == 1

def test_clock_day_rollover():
    clock = SimulationClock()
    clock.start()
    for _ in range(49):
        clock.advance_one_tick()
    assert clock.current_tick == 49
    assert clock.hour == 1
    assert clock.day == 2

def test_engine_initialization():
    world_id = uuid.uuid4()
    engine = SimulationEngine(world_id=world_id)
    assert engine.clock.current_tick == 0
    assert engine.clock.simulation_status == SimulationStatus.PAUSED
    assert len(engine.pending_events) == 0

def test_engine_initialization_with_state():
    world_id = uuid.uuid4()
    engine = SimulationEngine(world_id=world_id, initial_tick=10, initial_status="RUNNING")
    assert engine.clock.current_tick == 10
    assert engine.clock.simulation_status == SimulationStatus.RUNNING

def test_engine_advance_one_tick():
    world_id = uuid.uuid4()
    engine = SimulationEngine(world_id=world_id, initial_tick=0, initial_status="RUNNING")
    
    engine.advance_one_tick()
    
    assert engine.clock.current_tick == 1
    assert len(engine.pending_events) == 1
    
    event = engine.pending_events[0]
    assert event.world_id == world_id
    assert event.tick == 1
    assert event.day == 0
    assert event.hour == 1

def test_engine_advance_ticks():
    world_id = uuid.uuid4()
    engine = SimulationEngine(world_id=world_id, initial_tick=0, initial_status="RUNNING")
    
    engine.advance_ticks(5)
    
    assert engine.clock.current_tick == 5
    assert len(engine.pending_events) == 5
    
    last_event = engine.pending_events[-1]
    assert last_event.tick == 5
    assert last_event.hour == 5

def test_engine_reset():
    world_id = uuid.uuid4()
    engine = SimulationEngine(world_id=world_id, initial_tick=10, initial_status="RUNNING")
    
    engine.advance_one_tick()
    assert len(engine.pending_events) == 1
    
    engine.reset()
    assert engine.clock.current_tick == 0
    assert engine.clock.simulation_status == SimulationStatus.PAUSED
    assert len(engine.pending_events) == 0

def test_engine_persistence_after_restart():
    world_id = uuid.uuid4()
    engine = SimulationEngine(world_id=world_id, initial_status="RUNNING")
    engine.advance_ticks(10)
    
    # Simulate restart
    saved_tick = engine.clock.current_tick
    saved_status = engine.clock.simulation_status.value
    
    new_engine = SimulationEngine(world_id=world_id, initial_tick=saved_tick, initial_status=saved_status)
    assert new_engine.clock.current_tick == 10
    assert new_engine.clock.simulation_status == SimulationStatus.RUNNING
    
    new_engine.advance_one_tick()
    assert new_engine.clock.current_tick == 11
    assert len(new_engine.pending_events) == 1
