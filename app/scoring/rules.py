"""Scoring rules engine - implements risk assessment logic.

This is the core business logic for fraud detection.
Placeholder implementation for Sprint 1.

In production:
- Load rules from configuration/database
- Integrate ML model output (BentoML)
- Check entity graph (Neo4j)
- Query velocity counters (Redis)
- Reference historical patterns (Cassandra)
"""

from app.core.logging import get_logger
from app.scoring.schemas import RiskScoreRequest

logger = get_logger(__name__)


class ScoringRulesEngine:
    """Rule-based scoring engine.

    Simple placeholder that applies a few heuristic rules.
    Returns a dict with score, level, and decision.
    """

    def evaluate(self, request: RiskScoreRequest) -> dict:
        """Score a transaction based on rules.

        Args:
            request: Validated scoring request

        Returns:
            Dict with keys:
            - score: float [0.0, 1.0]
            - level: str ("LOW", "MEDIUM", "HIGH", "CRITICAL")
            - decision: str ("APPROVE", "REVIEW", "DECLINE")
            - reason_codes: list[str]
        """
        score = 0.0
        reason_codes = []

        # Rule 1: Amount heuristic
        # Transactions > $5,000 get slight risk bump
        if request.amount_cents > 500_000:  # $5,000
            score += 0.15
            reason_codes.append("LARGE_AMOUNT")

        # Rule 2: High-risk countries
        high_risk_countries = {"NG", "IR", "KP", "SY"}
        if request.merchant_country in high_risk_countries:
            score += 0.30
            reason_codes.append("HIGH_RISK_COUNTRY")

        # Rule 3: Unusual merchant categories
        high_risk_mcc = {"7995", "7994", "6211", "6051", "5962"}  # Gambling, securities, adult, crypto
        if request.merchant_category in high_risk_mcc:
            score += 0.20
            reason_codes.append("HIGH_RISK_MERCHANT_CATEGORY")

        # Rule 4: Test mode bypass (for development)
        if request.customer_id.startswith("TEST_"):
            score = 0.05
            reason_codes = ["TEST_MODE"]
            logger.info("scoring_test_mode", customer_id=request.customer_id)

        # Clamp score to [0.0, 1.0]
        score = min(max(score, 0.0), 1.0)

        # Determine risk level and decision
        if score < 0.10:
            level = "LOW"
            decision = "APPROVE"
        elif score < 0.30:
            level = "MEDIUM"
            decision = "REVIEW"
        elif score < 0.60:
            level = "HIGH"
            decision = "REVIEW"
        else:
            level = "CRITICAL"
            decision = "DECLINE"

        logger.info(
            "scoring_rules_evaluated",
            transaction_id=request.transaction_id,
            score=score,
            level=level,
            reason_codes=reason_codes,
        )

        return {
            "score": score,
            "level": level,
            "decision": decision,
            "reason_codes": reason_codes,
        }
