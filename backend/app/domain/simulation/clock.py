from enum import Enum
from pydantic import BaseModel

class SimulationStatus(str, Enum):
    PAUSED = "PAUSED"
    RUNNING = "RUNNING"

class SimulationClock(BaseModel):
    current_tick: int = 0
    simulation_status: SimulationStatus = SimulationStatus.PAUSED

    @property
    def day(self) -> int:
        return self.current_tick // 24

    @property
    def hour(self) -> int:
        return self.current_tick % 24

    def advance_one_tick(self) -> int:
        if self.simulation_status != SimulationStatus.RUNNING:
            return self.current_tick
        self.current_tick += 1
        return self.current_tick

    def start(self) -> None:
        self.simulation_status = SimulationStatus.RUNNING

    def pause(self) -> None:
        self.simulation_status = SimulationStatus.PAUSED

    def reset(self) -> None:
        self.current_tick = 0
        self.simulation_status = SimulationStatus.PAUSED
