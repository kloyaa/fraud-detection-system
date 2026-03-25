"""Repository for Rule (authoritative rule store — ADR-008)."""

from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Rule
from app.db.repositories.base import BaseRepository


class RuleRepository(BaseRepository[Rule]):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Rule)

    async def get_by_rule_id(self, rule_id: str) -> Optional[Rule]:
        result = await self.session.execute(
            select(Rule).where(Rule.rule_id == rule_id)
        )
        return result.scalar_one_or_none()

    async def get_active_rules(self) -> Sequence[Rule]:
        result = await self.session.execute(
            select(Rule).where(Rule.enabled == True).order_by(Rule.id)
        )
        return result.scalars().all()

    async def disable_rule(self, rule_id: str) -> None:
        from sqlalchemy import update
        await self.session.execute(
            update(Rule).where(Rule.rule_id == rule_id).values(enabled=False)
        )
