"""Cassandra audit log client — INSERT-only writes to risk_events table (ADR-002).

Design:
- cassandra-driver is synchronous; wrapped with asyncio.to_thread() for async compat
- INSERT-only: audit log is append-only and immutable
- DLQ: failed writes buffered in-memory deque (maxlen=10_000) for retry
- Schema: risk_events table in ras_dev keyspace (see CREATE_TABLE_CQL below)

Per ADR-002 rationale:
  Cassandra is chosen for write throughput, TTL, and immutability of the event log.
  The risk_events table uses a partition key of (customer_id, date) so data for a
  customer within a day lives on the same node — supporting time-range queries.
"""

import asyncio
from collections import deque
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from cassandra.cluster import Cluster, Session
from cassandra.policies import DCAwareRoundRobinPolicy

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# CREATE TABLE statement — run once during keyspace initialisation
CREATE_KEYSPACE_CQL = """
CREATE KEYSPACE IF NOT EXISTS {keyspace}
  WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}};
"""

CREATE_TABLE_CQL = """
CREATE TABLE IF NOT EXISTS {keyspace}.risk_events (
    customer_id  text,
    event_date   date,
    event_id     uuid,
    request_id   text,
    merchant_id  text,
    amount_cents bigint,
    currency     text,
    score        int,
    decision     text,
    rules_triggered list<text>,
    processing_ms int,
    region       text,
    occurred_at  timestamp,
    PRIMARY KEY ((customer_id, event_date), event_id)
) WITH CLUSTERING ORDER BY (event_id DESC)
  AND default_time_to_live = 7776000;
"""

INSERT_EVENT_CQL = """
INSERT INTO {keyspace}.risk_events (
    customer_id, event_date, event_id, request_id, merchant_id,
    amount_cents, currency, score, decision, rules_triggered,
    processing_ms, region, occurred_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
"""

# In-memory DLQ for failed Cassandra writes — bounded to prevent OOM
_dlq: deque = deque(maxlen=10_000)

_cluster: Optional[Cluster] = None
_session: Optional[Session] = None
_insert_stmt = None  # Prepared statement — cache after first prepare


def _connect() -> None:
    """Synchronous connect — called once via asyncio.to_thread()."""
    global _cluster, _session, _insert_stmt

    hosts = [h.strip() for h in settings.cassandra_hosts.split(",")]
    _cluster = Cluster(
        contact_points=hosts,
        port=settings.cassandra_port,
        load_balancing_policy=DCAwareRoundRobinPolicy(local_dc="datacenter1"),
        connect_timeout=10,
    )
    _session = _cluster.connect()

    # Ensure keyspace exists
    _session.execute(CREATE_KEYSPACE_CQL.format(keyspace=settings.cassandra_keyspace))
    _session.set_keyspace(settings.cassandra_keyspace)

    # Ensure table exists
    _session.execute(CREATE_TABLE_CQL.format(keyspace=settings.cassandra_keyspace))

    # Prepare insert statement for performance
    _insert_stmt = _session.prepare(
        INSERT_EVENT_CQL.format(keyspace=settings.cassandra_keyspace)
    )

    logger.info(
        "cassandra_connected",
        hosts=hosts,
        keyspace=settings.cassandra_keyspace,
    )


def _close() -> None:
    """Synchronous close — called via asyncio.to_thread()."""
    global _cluster, _session
    if _cluster is not None:
        _cluster.shutdown()
        _cluster = None
        _session = None
    logger.info("cassandra_disconnected")


async def init_cassandra() -> None:
    """Start Cassandra connection. Called once in app lifespan."""
    await asyncio.to_thread(_connect)


async def close_cassandra() -> None:
    """Close Cassandra connection. Called in app lifespan shutdown."""
    await asyncio.to_thread(_close)


def _write_event_sync(
    customer_id: str,
    request_id: str,
    merchant_id: str,
    amount_cents: int,
    currency: str,
    score: int,
    decision: str,
    rules_triggered: list,
    processing_ms: int,
    region: str,
    occurred_at: datetime,
) -> None:
    """Synchronous Cassandra write — run via asyncio.to_thread()."""
    if _session is None or _insert_stmt is None:
        raise RuntimeError("Cassandra session not initialised")

    import uuid
    from cassandra.util import Date

    event_date = Date(occurred_at.date())
    _session.execute(
        _insert_stmt,
        (
            customer_id,
            event_date,
            uuid.uuid4(),
            request_id,
            merchant_id,
            amount_cents,
            currency,
            score,
            decision,
            rules_triggered,
            processing_ms,
            region,
            occurred_at,
        ),
    )


async def write_risk_event(
    customer_id: str,
    request_id: str,
    merchant_id: str,
    amount_cents: int,
    currency: str,
    score: int,
    decision: str,
    rules_triggered: list[str],
    processing_ms: int,
    region: str = "us-east-1",
) -> None:
    """Async write to the Cassandra risk_events audit table.

    On failure, the event is buffered in the in-memory DLQ.
    The DLQ is flushed by the background retry task (see flush_dlq()).
    """
    occurred_at = datetime.now(timezone.utc)
    try:
        await asyncio.to_thread(
            _write_event_sync,
            customer_id,
            request_id,
            merchant_id,
            amount_cents,
            currency,
            score,
            decision,
            rules_triggered,
            processing_ms,
            region,
            occurred_at,
        )
        logger.info("cassandra_event_written", request_id=request_id)
    except Exception as e:
        logger.error(
            "cassandra_write_failed",
            request_id=request_id,
            error=str(e),
            dlq_size=len(_dlq),
        )
        _dlq.append(
            {
                "customer_id": customer_id,
                "request_id": request_id,
                "merchant_id": merchant_id,
                "amount_cents": amount_cents,
                "currency": currency,
                "score": score,
                "decision": decision,
                "rules_triggered": rules_triggered,
                "processing_ms": processing_ms,
                "region": region,
                "occurred_at": occurred_at,
            }
        )


async def flush_dlq() -> int:
    """Retry all buffered DLQ events. Returns number of events successfully flushed."""
    flushed = 0
    retries = []
    while _dlq:
        event = _dlq.popleft()
        try:
            await asyncio.to_thread(
                _write_event_sync,
                event["customer_id"],
                event["request_id"],
                event["merchant_id"],
                event["amount_cents"],
                event["currency"],
                event["score"],
                event["decision"],
                event["rules_triggered"],
                event["processing_ms"],
                event["region"],
                event["occurred_at"],
            )
            flushed += 1
        except Exception:
            retries.append(event)

    for event in retries:
        _dlq.append(event)

    if flushed:
        logger.info("cassandra_dlq_flushed", flushed=flushed, remaining=len(_dlq))
    return flushed


def dlq_size() -> int:
    return len(_dlq)
