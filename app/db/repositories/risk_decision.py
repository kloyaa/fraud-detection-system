"""Repository for RiskDecision (Kafka-aligned analytics record)."""

from typing import Optional, Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import RiskDecision
from app.db.repositories.base import BaseRepository


class RiskDecisionRepository(BaseRepository[RiskDecision]):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RiskDecision)

    async def get_by_request_id(self, request_id: str) -> Optional[RiskDecision]:
        result = await self.session.execute(
            select(RiskDecision).where(RiskDecision.request_id == request_id)
        )
        return result.scalar_one_or_none()

    async def get_by_customer_id(self, customer_id: str, limit: int = 50) -> Sequence[RiskDecision]:
        result = await self.session.execute(
            select(RiskDecision)
            .where(RiskDecision.customer_id == customer_id)
            .order_by(RiskDecision.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def mark_published(self, decision_id: int, kafka_offset: Optional[int] = None) -> None:
        await self.session.execute(
            update(RiskDecision)
            .where(RiskDecision.id == decision_id)
            .values(published_to_kafka=True, kafka_offset=kafka_offset)
        )
