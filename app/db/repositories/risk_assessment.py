"""Repository for RiskAssessment (idempotency + audit trail)."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import RiskAssessment
from app.db.repositories.base import BaseRepository


class RiskAssessmentRepository(BaseRepository[RiskAssessment]):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RiskAssessment)

    async def get_by_idempotency_key(self, key: str) -> Optional[RiskAssessment]:
        result = await self.session.execute(
            select(RiskAssessment).where(RiskAssessment.idempotency_key == key)
        )
        return result.scalar_one_or_none()

    async def get_by_transaction_id(self, transaction_id: str) -> Optional[RiskAssessment]:
        result = await self.session.execute(
            select(RiskAssessment).where(RiskAssessment.transaction_id == transaction_id)
        )
        return result.scalar_one_or_none()
