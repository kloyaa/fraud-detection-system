"""Generic async repository base class."""

from typing import Generic, Optional, Sequence, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Base async repository providing common CRUD operations."""

    def __init__(self, session: AsyncSession, model: Type[T]) -> None:
        self.session = session
        self.model = model

    async def get_by_id(self, record_id: int) -> Optional[T]:
        return await self.session.get(self.model, record_id)

    async def get_all(self, limit: int = 100) -> Sequence[T]:
        result = await self.session.execute(select(self.model).limit(limit))
        return result.scalars().all()

    async def create(self, instance: T) -> T:
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def delete(self, instance: T) -> None:
        await self.session.delete(instance)
        await self.session.flush()
