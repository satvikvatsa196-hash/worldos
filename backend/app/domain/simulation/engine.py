import uuid
from typing import List
from pydantic import BaseModel
from app.domain.simulation.clock import SimulationClock, SimulationStatus

class WorldTick(BaseModel):
    world_id: uuid.UUID
    tick: int
    day: int
    hour: int

class SimulationEngine:
    def __init__(self, world_id: uuid.UUID, initial_tick: int = 0, initial_status: str = "PAUSED"):
        self.world_id = world_id
        
        status_enum = SimulationStatus.PAUSED
        if initial_status.upper() == "RUNNING":
            status_enum = SimulationStatus.RUNNING
            
        self.clock = SimulationClock(
            current_tick=initial_tick,
            simulation_status=status_enum
        )
        self.pending_events: List[WorldTick] = []

    def _emit_tick_event(self) -> None:
        event = WorldTick(
            world_id=self.world_id,
            tick=self.clock.current_tick,
            day=self.clock.day,
            hour=self.clock.hour
        )
        self.pending_events.append(event)

    def advance_one_tick(self) -> int:
        if self.clock.simulation_status == SimulationStatus.RUNNING:
            self.clock.advance_one_tick()
            self._emit_tick_event()
        return self.clock.current_tick

    def advance_ticks(self, n: int) -> int:
        if n < 0:
            raise ValueError("Cannot advance negative ticks")
        if self.clock.simulation_status == SimulationStatus.RUNNING:
            for _ in range(n):
                self.clock.advance_one_tick()
                self._emit_tick_event()
        return self.clock.current_tick

    def start(self) -> None:
        self.clock.start()

    def pause(self) -> None:
        self.clock.pause()

    def reset(self) -> None:
        self.clock.reset()
        self.pending_events.clear()
