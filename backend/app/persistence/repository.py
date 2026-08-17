from typing import TypeVar, Generic, Type, Optional, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import contextlib

T = TypeVar("T")  # SQLAlchemy Model
K = TypeVar("K")  # Primary Key Type

class BaseRepository(Generic[T, K]):
    def __init__(self, session: AsyncSession, model_class: Type[T]):
        self.session = session
        self.model_class = model_class

    async def get_by_id(self, id: K) -> Optional[T]:
        return await self.session.get(self.model_class, id)

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        stmt = select(self.model_class).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    def add(self, entity: T) -> None:
        self.session.add(entity)

    async def delete(self, entity: T) -> None:
        await self.session.delete(entity)

class UnitOfWork:
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self._session: Optional[AsyncSession] = None

    async def __aenter__(self):
        self._session = self.session_factory()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        else:
            await self.commit()
        await self._session.close()
        self._session = None

    async def commit(self):
        if self._session:
            await self._session.commit()

    async def rollback(self):
        if self._session:
            await self._session.rollback()

    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("Session is not initialized. Use UnitOfWork as a context manager.")
        return self._session

    # Repositories can be instantiated here dynamically or accessed as needed
    def repository(self, model_class: Type[T]) -> BaseRepository[T, Any]:
        return BaseRepository(self.session, model_class)
