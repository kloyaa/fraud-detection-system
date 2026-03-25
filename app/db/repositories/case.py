"""Repository for Case (investigation workflow)."""

from typing import Optional, Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Case
from app.db.repositories.base import BaseRepository


class CaseRepository(BaseRepository[Case]):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Case)

    async def get_by_case_id(self, case_id: str) -> Optional[Case]:
        result = await self.session.execute(
            select(Case).where(Case.case_id == case_id)
        )
        return result.scalar_one_or_none()

    async def get_open_by_customer(self, customer_id: str) -> Sequence[Case]:
        result = await self.session.execute(
            select(Case)
            .where(Case.customer_id == customer_id, Case.status == "OPEN")
            .order_by(Case.created_at.desc())
        )
        return result.scalars().all()

    async def get_by_priority(self, priority: str, status: str = "OPEN") -> Sequence[Case]:
        result = await self.session.execute(
            select(Case)
            .where(Case.priority == priority, Case.status == status)
            .order_by(Case.sla_deadline.asc())
        )
        return result.scalars().all()

    async def update_status(self, case_id: str, status: str) -> None:
        await self.session.execute(
            update(Case).where(Case.case_id == case_id).values(status=status)
        )
