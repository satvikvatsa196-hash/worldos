from abc import ABC, abstractmethod
from typing import Optional, List, TypeVar, Generic, Any
import uuid

T = TypeVar("T")

class IRepository(ABC, Generic[T]):
    @abstractmethod
    async def get_by_id(self, id: uuid.UUID) -> Optional[T]:
        pass

    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        pass

    @abstractmethod
    def add(self, entity: T) -> None:
        pass

    @abstractmethod
    async def delete(self, entity: T) -> None:
        pass

class IWorldRepository(IRepository[T], ABC):
    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[T]:
        pass

class ICityRepository(IRepository[T], ABC):
    @abstractmethod
    async def get_by_world_id(self, world_id: uuid.UUID) -> List[T]:
        pass

class ICharacterRepository(IRepository[T], ABC):
    @abstractmethod
    async def get_by_city_id(self, city_id: uuid.UUID) -> List[T]:
        pass

class IEventRepository(IRepository[T], ABC):
    @abstractmethod
    async def get_by_world_and_tick(self, world_id: uuid.UUID, tick: int) -> List[T]:
        pass
