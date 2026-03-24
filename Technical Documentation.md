# Risk Assessment System (RAS)
### Production-Ready Technical Documentation v1.0.0

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Technology Stack](#2-technology-stack)
3. [Architecture](#3-architecture)
4. [Security Design](#4-security-design)
5. [Risk Engine Design](#5-risk-engine-design)
6. [API Specification](#6-api-specification)
7. [Database Schema](#7-database-schema)
8. [Scalability & Reliability](#8-scalability--reliability)
9. [Observability & Monitoring](#9-observability--monitoring)
10. [Deployment](#10-deployment)
11. [Development Guidelines](#11-development-guidelines)

---

## 1. System Overview

The **Risk Assessment System (RAS)** is a high-performance, real-time fraud and risk evaluation platform inspired by the risk engines powering **PayPal** and **Stripe**. It evaluates transactions, user sessions, and behavioral signals to produce risk scores, enforce policy rules, and trigger automated or human-in-the-loop review workflows.

### Core Capabilities

| Capability | Description |
|---|---|
| **Real-Time Scoring** | Sub-100ms risk score computation per transaction |
| **Rule Engine** | Configurable, versioned rule policies (allow / challenge / block) |
| **ML Scoring** | Gradient-boosted models + neural behavioral embeddings |
| **Device Fingerprinting** | Passive device/browser fingerprint collection and matching |
| **Velocity Checks** | Sliding-window counters for amount, frequency, and geography |
| **Graph Analysis** | Entity relationship graph to detect fraud rings |
| **Case Management** | Analyst review queue with SLA tracking |
| **Adaptive Auth** | Step-up authentication triggers (OTP, biometric) |

---

## 2. Technology Stack

### 2.1 Core Language & Runtime

| Component | Choice | Rationale |
|---|---|---|
| Language | **Python 3.12+** | Async support, ML ecosystem, typing |
| Runtime | **CPython + Uvicorn** | ASGI, high concurrency |
| Package Manager | **uv** | Fast dependency resolution |
| Type Safety | **Pydantic v2** | Runtime validation, serialization |

### 2.2 Web Framework

| Component | Choice | Rationale |
|---|---|---|
| API Framework | **FastAPI** | Async-first, OpenAPI auto-docs, Pydantic integration |
| Background Tasks | **Celery 5 + Redis** | Distributed task queue, retries, scheduling |
| WebSocket | **FastAPI WebSocket** | Real-time dashboard feeds |
| GraphQL (internal) | **Strawberry** | Analyst case query interface |

### 2.3 Databases

| Role | Technology | Rationale |
|---|---|---|
| **Primary OLTP** | PostgreSQL 16 (+ pgvector) | ACID, JSON support, vector similarity search |
| **Time-Series / Events** | Apache Cassandra 5 | High write throughput, event log immutability |
| **Cache / Velocity** | Redis 7 (Redis Stack) | Sliding window counters, bloom filters, pub/sub |
| **Graph Store** | Neo4j 5 (AuraDB) | Fraud ring detection, entity relationship traversal |
| **Search** | Elasticsearch 8 | Full-text audit log search, analyst queries |
| **Data Warehouse** | Snowflake | Batch ML feature engineering, BI reporting |

### 2.4 ML & Feature Engineering

| Component | Technology |
|---|---|
| Feature Store | **Feast** (offline + online) |
| Model Training | **XGBoost**, **LightGBM**, **PyTorch** (behavioral embeddings) |
| Model Serving | **BentoML** (low-latency inference server) |
| Experimentation | **MLflow** |
| Data Pipeline | **Apache Spark** (via PySpark) + **Apache Kafka** |
| Feature Drift | **Evidently AI** |

### 2.5 Message Queue & Streaming

| Role | Technology |
|---|---|
| Event Streaming | **Apache Kafka** (Confluent Cloud) |
| Dead Letter Queue | **Kafka DLQ + Alerting** |
| Schema Registry | **Confluent Schema Registry** (Avro/Protobuf) |
| Stream Processing | **Apache Flink** (real-time feature aggregation) |

### 2.6 Security Infrastructure

| Component | Technology |
|---|---|
| Secret Management | **HashiCorp Vault** |
| mTLS & Service Mesh | **Istio** + **Envoy** |
| API Gateway | **Kong Gateway** (rate limiting, JWT auth) |
| Identity Provider | **Keycloak** (OIDC/OAuth 2.0) |
| WAF | **AWS WAF** / **Cloudflare** |
| HSM / Key Management | **AWS KMS** / **GCP Cloud KMS** |
| Dependency Scanning | **Snyk** + **Dependabot** |
| SAST | **Bandit** + **Semgrep** |

### 2.7 Infrastructure & DevOps

| Component | Technology |
|---|---|
| Container Runtime | **Docker** + **containerd** |
| Orchestration | **Kubernetes 1.30** (EKS / GKE) |
| Service Mesh | **Istio** |
| IaC | **Terraform** + **Helm** |
| CI/CD | **GitHub Actions** + **ArgoCD** |
| Secrets in CI | **GitHub OIDC + Vault** |
| Registry | **AWS ECR** / **GCR** |

### 2.8 Observability

| Component | Technology |
|---|---|
| Metrics | **Prometheus** + **Grafana** |
| Tracing | **OpenTelemetry** + **Jaeger** |
| Logging | **Loki** + **Grafana** (structured JSON logs) |
| Alerting | **PagerDuty** + **Alertmanager** |
| Uptime | **Checkly** |
| Error Tracking | **Sentry** |

---

## 3. Architecture

### 3.1 High-Level System Architecture

```
                        ┌─────────────────────────────┐
                        │        API Clients           │
                        │  (Merchant SDK / Internal)  │
                        └────────────┬────────────────┘
                                     │ HTTPS / mTLS
                        ┌────────────▼────────────────┐
                        │      Kong API Gateway        │
                        │  (Rate Limit · JWT · WAF)   │
                        └────────────┬────────────────┘
                                     │
               ┌─────────────────────┼──────────────────────┐
               │                     │                      │
  ┌────────────▼──────┐  ┌──────────▼──────────┐  ┌───────▼────────────┐
  │  RAS Scoring API  │  │  Case Mgmt API       │  │  Admin / Config    │
  │  (FastAPI / ASGI) │  │  (FastAPI + GQL)     │  │  API (FastAPI)     │
  └────────────┬──────┘  └──────────┬──────────┘  └───────┬────────────┘
               │                    │                      │
               │          ┌─────────▼──────────────────────┤
               │          │     Kafka Event Bus             │
               │          │  (transactions · signals ·     │
               │          │   decisions · audit)            │
               │          └─────────┬──────────────────────┘
               │                    │
     ┌─────────▼──────┐   ┌────────▼──────────┐
     │  Rule Engine   │   │  Flink Stream      │
     │  (Drools DSL   │   │  Processor         │
     │   + Python)    │   │  (velocity feats)  │
     └────────┬───────┘   └────────┬──────────┘
              │                    │
     ┌────────▼───────────────────▼────────────┐
     │            ML Scoring Service            │
     │       (BentoML · XGBoost · PyTorch)      │
     └────────┬──────────────────┬─────────────┘
              │                  │
   ┌──────────▼──────┐  ┌────────▼──────────────┐
   │   Feature Store │  │   Graph Risk Service   │
   │   (Feast/Redis) │  │   (Neo4j traversal)    │
   └──────────┬──────┘  └────────────────────────┘
              │
   ┌──────────▼──────────────────────────────────┐
   │              Data Stores                     │
   │  PostgreSQL · Cassandra · Redis · ES · Neo4j │
   └─────────────────────────────────────────────┘
```

### 3.2 Risk Decision Flow (Inspired by Stripe Radar / PayPal Risk)

```
Transaction Received
        │
        ▼
[1] Data Enrichment (IP geo, BIN lookup, device fp)
        │
        ▼
[2] Feature Extraction (Feast online store)
        │
        ├──► Velocity Counters (Redis sliding window)
        ├──► Historical User Behavior (Cassandra)
        └──► Graph Features (Neo4j — shared devices, accounts)
        │
        ▼
[3] Rule Engine Evaluation (pre-ML gate)
        │
        ├── BLOCK  ──► Decline immediately
        ├── ALLOW  ──► Bypass ML, fast approve
        └── SCORE  ──► Continue to ML
        │
        ▼
[4] ML Ensemble Scoring
        │
        ├── XGBoost fraud score (0–1000)
        ├── Behavioral embedding similarity
        └── Consortium score (shared intelligence)
        │
        ▼
[5] Post-ML Rule Overlay
        │
        ├── Score < 200   ──► APPROVE
        ├── Score 200–600 ──► CHALLENGE (3DS / OTP)
        └── Score > 600   ──► DECLINE / QUEUE REVIEW
        │
        ▼
[6] Decision Published → Kafka
        │
        ├──► Client response (<100ms)
        ├──► Audit log (Cassandra immutable)
        └──► Case queue (if review)
```

---

## 4. Security Design

### 4.1 Authentication & Authorization

```python
# app/core/security.py

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from app.core.config import settings

bearer_scheme = HTTPBearer()

async def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> dict:
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_PUBLIC_KEY,
            algorithms=["RS256"],
            audience=settings.JWT_AUDIENCE,
        )
        return payload
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

def require_scope(scope: str):
    """RBAC scope enforcer — mirrors Stripe's restricted key model."""
    async def _check(claims: dict = Depends(verify_token)):
        if scope not in claims.get("scopes", []):
            raise HTTPException(status_code=403, detail=f"Missing scope: {scope}")
        return claims
    return _check
```

**Roles:**

| Role | Scopes |
|---|---|
| `merchant` | `risk:score`, `risk:read_own` |
| `analyst` | `risk:read_all`, `cases:write` |
| `risk_admin` | `rules:write`, `models:deploy` |
| `auditor` | `audit:read` (read-only, append-only log) |

### 4.2 Encryption

- **Data in Transit:** TLS 1.3 everywhere; mTLS between internal services via Istio.
- **Data at Rest:** AES-256-GCM for PII fields (card number, email) using envelope encryption via AWS KMS.
- **Field-Level Encryption (FLE):** PAN, CVV, SSN encrypted at application layer before DB write.
- **Key Rotation:** Automated 90-day rotation via Vault Dynamic Secrets.

```python
# app/core/encryption.py

import boto3
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

class FieldEncryptor:
    def __init__(self, kms_key_id: str):
        self.kms = boto3.client("kms")
        self.key_id = kms_key_id

    def encrypt(self, plaintext: str) -> dict:
        # Generate data key from KMS (envelope encryption)
        resp = self.kms.generate_data_key(KeyId=self.key_id, KeySpec="AES_256")
        plaintext_key = resp["Plaintext"]
        encrypted_key = resp["CiphertextBlob"]

        nonce = os.urandom(12)
        aesgcm = AESGCM(plaintext_key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)

        return {
            "ciphertext": base64.b64encode(ciphertext).decode(),
            "nonce": base64.b64encode(nonce).decode(),
            "encrypted_key": base64.b64encode(encrypted_key).decode(),
        }

    def decrypt(self, payload: dict) -> str:
        encrypted_key = base64.b64decode(payload["encrypted_key"])
        resp = self.kms.decrypt(CiphertextBlob=encrypted_key)
        plaintext_key = resp["Plaintext"]

        nonce = base64.b64decode(payload["nonce"])
        ciphertext = base64.b64decode(payload["ciphertext"])
        aesgcm = AESGCM(plaintext_key)
        return aesgcm.decrypt(nonce, ciphertext, None).decode()
```

### 4.3 API Security Controls

| Control | Implementation |
|---|---|
| Rate Limiting | Kong: 100 req/s per API key, 10 req/s per IP |
| HMAC Request Signing | Webhook payloads signed with SHA-256 HMAC (Stripe-style) |
| Idempotency Keys | UUID v4 idempotency key on all POST endpoints |
| Input Validation | Pydantic v2 strict mode, allowlist field validation |
| SQL Injection | SQLAlchemy ORM, parameterized queries only |
| SSRF Prevention | Allowlisted outbound IPs for enrichment calls |
| PCI DSS Scope | Card data never logged; masked in all outputs |

### 4.4 HMAC Webhook Verification (Stripe-Inspired)

```python
import hmac, hashlib, time

def verify_webhook(payload: bytes, signature: str, secret: str, tolerance: int = 300) -> bool:
    try:
        parts = dict(p.split("=", 1) for p in signature.split(","))
        timestamp = int(parts["t"])
        sig = parts["v1"]
    except (KeyError, ValueError):
        return False

    if abs(time.time() - timestamp) > tolerance:
        return False  # Replay attack prevention

    expected = hmac.new(
        secret.encode(), f"{timestamp}.".encode() + payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, sig)
```

---

## 5. Risk Engine Design

### 5.1 Risk Score Request Model

```python
# app/schemas/risk.py

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from decimal import Decimal
from datetime import datetime
import uuid

class DeviceInfo(BaseModel):
    fingerprint_id: str
    ip_address: str
    user_agent: str
    screen_resolution: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None

class PaymentMethod(BaseModel):
    type: str  # "card" | "bank_transfer" | "wallet"
    bin: Optional[str] = None           # First 6 digits only
    last_four: Optional[str] = None
    country: Optional[str] = None
    network: Optional[str] = None

class RiskScoreRequest(BaseModel):
    idempotency_key: str = Field(default_factory=lambda: str(uuid.uuid4()))
    merchant_id: str
    customer_id: str
    session_id: str
    amount: Decimal = Field(gt=0, le=Decimal("1000000"))
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    payment_method: PaymentMethod
    device: DeviceInfo
    metadata: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("bin")
    @classmethod
    def mask_sensitive(cls, v):
        # Ensure no full PANs slip through
        if v and len(v) > 8:
            raise ValueError("BIN must be max 8 digits")
        return v

class RiskDecision(BaseModel):
    request_id: str
    score: int = Field(ge=0, le=1000)
    decision: str           # "approve" | "challenge" | "decline"
    reasons: list[str]
    rules_triggered: list[str]
    requires_review: bool
    challenge_type: Optional[str] = None   # "3ds" | "otp" | "biometric"
    processing_ms: int
    model_version: str
```

### 5.2 Rule Engine

```python
# app/engines/rule_engine.py

from dataclasses import dataclass
from typing import Callable, Awaitable
from enum import Enum

class RuleAction(str, Enum):
    BLOCK = "block"
    ALLOW = "allow"
    SCORE = "score"          # Pass to ML
    CHALLENGE = "challenge"

@dataclass
class Rule:
    id: str
    name: str
    priority: int            # Lower = higher priority
    condition: Callable[..., Awaitable[bool]]
    action: RuleAction
    reason_code: str

class RuleEngine:
    def __init__(self, rules: list[Rule]):
        self.rules = sorted(rules, key=lambda r: r.priority)

    async def evaluate(self, ctx: dict) -> tuple[RuleAction, list[str]]:
        triggered = []
        for rule in self.rules:
            if await rule.condition(ctx):
                triggered.append(rule.reason_code)
                if rule.action in (RuleAction.BLOCK, RuleAction.ALLOW):
                    return rule.action, triggered
        return RuleAction.SCORE, triggered

# --- Example Rules (PayPal / Stripe inspired) ---

async def rule_blocked_country(ctx: dict) -> bool:
    BLOCKED = {"KP", "IR", "SY", "CU"}
    return ctx["device"]["ip_country"] in BLOCKED

async def rule_velocity_exceeded(ctx: dict) -> bool:
    # Max 5 txns in 60 seconds per customer
    return ctx["velocity"]["txn_count_60s"] > 5

async def rule_amount_spike(ctx: dict) -> bool:
    # Amount > 10x the customer's 30-day average
    avg = ctx["history"]["avg_txn_amount_30d"]
    return avg > 0 and ctx["amount"] > avg * 10

async def rule_new_device_high_value(ctx: dict) -> bool:
    return (
        ctx["device"]["first_seen"]
        and ctx["amount"] > 500
    )

PRODUCTION_RULES = [
    Rule("R001", "Blocked Country",       1, rule_blocked_country,       RuleAction.BLOCK,     "BLOCKED_COUNTRY"),
    Rule("R002", "Velocity Exceeded",     2, rule_velocity_exceeded,      RuleAction.BLOCK,     "VELOCITY_EXCEEDED"),
    Rule("R003", "Amount Spike",          5, rule_amount_spike,           RuleAction.CHALLENGE, "AMOUNT_SPIKE"),
    Rule("R004", "New Device High Value", 6, rule_new_device_high_value,  RuleAction.CHALLENGE, "NEW_DEVICE_HIGH_VALUE"),
]
```

### 5.3 Velocity Counter (Redis Sliding Window — PayPal-Style)

```python
# app/services/velocity.py

import redis.asyncio as aioredis
import time

class VelocityService:
    def __init__(self, redis: aioredis.Redis):
        self.redis = redis

    async def check_and_increment(
        self,
        key: str,
        window_seconds: int,
        max_count: int,
    ) -> tuple[int, bool]:
        now = time.time()
        window_start = now - window_seconds
        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, window_seconds + 1)
        results = await pipe.execute()
        count = results[2]
        return count, count > max_count

    async def get_customer_velocity(self, customer_id: str) -> dict:
        txn_60s, _ = await self.check_and_increment(
            f"vel:txn:{customer_id}:60", 60, 5
        )
        txn_1h, _ = await self.check_and_increment(
            f"vel:txn:{customer_id}:3600", 3600, 20
        )
        return {"txn_count_60s": txn_60s, "txn_count_1h": txn_1h}
```

---

## 6. API Specification

### 6.1 Endpoints

| Method | Path | Auth Scope | Description |
|---|---|---|---|
| `POST` | `/v1/risk/score` | `risk:score` | Evaluate transaction risk |
| `GET` | `/v1/risk/{request_id}` | `risk:read_own` | Retrieve a decision |
| `POST` | `/v1/risk/{request_id}/feedback` | `risk:score` | Submit outcome feedback |
| `GET` | `/v1/cases` | `cases:read` | List review queue |
| `PATCH` | `/v1/cases/{case_id}` | `cases:write` | Update case decision |
| `GET` | `/v1/rules` | `rules:read` | List active rules |
| `POST` | `/v1/rules` | `rules:write` | Create / update rule |
| `GET` | `/v1/models` | `models:read` | List deployed models |
| `POST` | `/v1/models/{id}/promote` | `models:deploy` | Promote model to production |

### 6.2 Score Endpoint

```
POST /v1/risk/score
Authorization: Bearer <JWT>
Idempotency-Key: <uuid>
Content-Type: application/json

Response 200:
{
  "request_id": "rsk_01HNQZ8T...",
  "score": 287,
  "decision": "challenge",
  "reasons": ["NEW_DEVICE_HIGH_VALUE", "VELOCITY_MODERATE"],
  "rules_triggered": ["R004"],
  "requires_review": false,
  "challenge_type": "3ds",
  "processing_ms": 47,
  "model_version": "xgb-fraud-v3.2.1"
}
```

---

## 7. Database Schema

### 7.1 PostgreSQL — Core Tables

```sql
-- Risk decisions (immutable append-only)
CREATE TABLE risk_decisions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id      TEXT UNIQUE NOT NULL,
    merchant_id     TEXT NOT NULL,
    customer_id     TEXT NOT NULL,
    session_id      TEXT NOT NULL,
    score           SMALLINT NOT NULL CHECK (score BETWEEN 0 AND 1000),
    decision        TEXT NOT NULL CHECK (decision IN ('approve','challenge','decline')),
    model_version   TEXT NOT NULL,
    rules_triggered JSONB NOT NULL DEFAULT '[]',
    reasons         JSONB NOT NULL DEFAULT '[]',
    requires_review BOOLEAN NOT NULL DEFAULT FALSE,
    processing_ms   INT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

CREATE INDEX idx_rd_customer ON risk_decisions (customer_id, created_at DESC);
CREATE INDEX idx_rd_merchant  ON risk_decisions (merchant_id, created_at DESC);
CREATE INDEX idx_rd_score     ON risk_decisions (score) WHERE requires_review = TRUE;

-- Rule definitions (versioned)
CREATE TABLE rules (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_code   TEXT NOT NULL,
    name        TEXT NOT NULL,
    version     INT NOT NULL DEFAULT 1,
    priority    INT NOT NULL,
    action      TEXT NOT NULL,
    definition  JSONB NOT NULL,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_by  TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (rule_code, version)
);

-- Review cases
CREATE TABLE cases (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_id     UUID NOT NULL REFERENCES risk_decisions(id),
    status          TEXT NOT NULL DEFAULT 'open'
                    CHECK (status IN ('open','in_review','resolved')),
    assigned_to     TEXT,
    analyst_decision TEXT CHECK (analyst_decision IN ('approve','decline', NULL)),
    notes           TEXT,
    sla_deadline    TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at     TIMESTAMPTZ
);
```

### 7.2 Cassandra — Event Log

```cql
CREATE KEYSPACE risk WITH replication = {
  'class': 'NetworkTopologyStrategy',
  'us-east-1': 3,
  'eu-west-1': 3
};

CREATE TABLE risk.events (
    customer_id  TEXT,
    occurred_at  TIMEUUID,
    event_type   TEXT,    -- 'txn_scored' | 'rule_triggered' | 'model_scored'
    payload      TEXT,    -- JSON blob
    PRIMARY KEY ((customer_id), occurred_at)
) WITH CLUSTERING ORDER BY (occurred_at DESC)
  AND default_time_to_live = 7776000;   -- 90 days
```

---

## 8. Scalability & Reliability

### 8.1 Scalability Strategy

| Layer | Strategy |
|---|---|
| **API Pods** | HPA: scale on P95 latency > 80ms or CPU > 65% |
| **Rule Engine** | Stateless; horizontally scalable |
| **ML Service** | GPU-backed BentoML replicas behind K8s service |
| **Redis** | Redis Cluster (6 shards, 3 replicas each) |
| **PostgreSQL** | Primary + 2 read replicas (PgBouncer connection pool) |
| **Cassandra** | 6-node ring, RF=3, LOCAL_QUORUM reads/writes |
| **Kafka** | 9 brokers, 24 partitions per topic, 3x replication |

### 8.2 Reliability Patterns

```python
# app/core/resilience.py — Circuit Breaker + Retry

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.1, max=2),
    retry=retry_if_exception_type(httpx.TransientError),
)
async def call_enrichment_service(payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=0.5) as client:
        resp = await client.post("http://enrichment-svc/enrich", json=payload)
        resp.raise_for_status()
        return resp.json()
```

| Pattern | Implementation |
|---|---|
| **Circuit Breaker** | `tenacity` + custom state tracker |
| **Bulkhead** | Separate thread/async pools per dependency |
| **Timeout** | Strict 500ms on all external calls |
| **Fallback** | Score with partial features if enrichment fails |
| **Idempotency** | Redis-backed idempotency key deduplication |
| **Graceful Degradation** | Rule-only scoring if ML service is degraded |

### 8.3 SLA Targets

| Metric | Target |
|---|---|
| Availability | 99.99% (< 52 min/year downtime) |
| P50 Scoring Latency | < 35ms |
| P95 Scoring Latency | < 100ms |
| P99 Scoring Latency | < 250ms |
| RPO (data loss) | < 1 second |
| RTO (recovery) | < 5 minutes |

### 8.4 Multi-Region Active-Active

- **Primary regions:** `us-east-1`, `eu-west-1`, `ap-southeast-1`
- **Traffic routing:** Cloudflare Load Balancer with latency-based routing
- **Data replication:** Cassandra multi-DC, Postgres logical replication
- **Kafka:** MirrorMaker 2 for cross-region topic mirroring

---

## 9. Observability & Monitoring

### 9.1 Structured Logging

```python
# All services emit structured JSON logs

import structlog

log = structlog.get_logger()

log.info(
    "risk_decision_made",
    request_id=request_id,
    customer_id=customer_id,
    score=score,
    decision=decision,
    processing_ms=elapsed_ms,
    model_version=model_version,
    rules_triggered=rules_triggered,
)
```

### 9.2 Key Metrics

| Metric | Type | Labels |
|---|---|---|
| `ras_score_requests_total` | Counter | merchant_id, decision |
| `ras_score_latency_seconds` | Histogram | region, model_version |
| `ras_rule_triggers_total` | Counter | rule_code, action |
| `ras_ml_score_histogram` | Histogram | model_version |
| `ras_fraud_rate` | Gauge | merchant_id, currency |
| `ras_case_queue_depth` | Gauge | status |

### 9.3 Alerting Rules

| Alert | Condition | Severity |
|---|---|---|
| High Decline Rate | `decline_rate > 15%` for 5 min | P1 |
| Scoring Latency | P95 > 200ms for 3 min | P1 |
| ML Service Down | Health check failing > 30s | P1 |
| Fraud Rate Spike | fraud_rate > 2x baseline | P2 |
| Case Queue Depth | > 500 unreviewed cases | P2 |
| Rule Engine Error | error_rate > 0.1% | P2 |

---

## 10. Deployment

### 10.1 Kubernetes Deployment (Example)

```yaml
# k8s/scoring-api/deployment.yaml

apiVersion: apps/v1
kind: Deployment
metadata:
  name: ras-scoring-api
  namespace: risk
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ras-scoring-api
  template:
    metadata:
      labels:
        app: ras-scoring-api
    spec:
      serviceAccountName: ras-scoring-sa
      securityContext:
        runAsNonRoot: true
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: api
          image: gcr.io/my-org/ras-scoring-api:1.0.0
          ports:
            - containerPort: 8000
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: ras-secrets
                  key: database-url
          resources:
            requests:
              cpu: "500m"
              memory: "512Mi"
            limits:
              cpu: "2000m"
              memory: "2Gi"
          livenessProbe:
            httpGet:
              path: /health/live
              port: 8000
            initialDelaySeconds: 10
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 8000
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ras-scoring-api-hpa
  namespace: risk
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ras-scoring-api
  minReplicas: 3
  maxReplicas: 50
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 65
```

### 10.2 CI/CD Pipeline

```
Push to main
    │
    ├──► Static Analysis (Bandit, Semgrep, Ruff)
    ├──► Unit Tests (pytest, 90%+ coverage)
    ├──► Integration Tests (Docker Compose)
    ├──► Container Build & Scan (Trivy)
    ├──► Push to ECR
    └──► ArgoCD Sync
            ├──► Canary Deploy (5% traffic)
            ├──► Monitor metrics (5 min)
            ├──► Promote to 100% or Rollback
            └──► Post-deploy smoke tests
```

---

## 11. Development Guidelines

### 11.1 Project Structure

```
ras/
├── app/
│   ├── api/            # FastAPI routers
│   ├── core/           # Config, security, encryption
│   ├── engines/        # Rule engine, ML orchestration
│   ├── schemas/        # Pydantic models
│   ├── services/       # Velocity, graph, enrichment
│   ├── repositories/   # DB access layer
│   └── workers/        # Celery tasks
├── ml/
│   ├── features/       # Feast feature definitions
│   ├── training/       # Model training scripts
│   └── serving/        # BentoML service definitions
├── k8s/                # Kubernetes manifests
├── terraform/          # Infrastructure as Code
├── tests/
│   ├── unit/
│   ├── integration/
│   └── load/           # Locust load tests
├── pyproject.toml
└── docker-compose.yml
```

### 11.2 Environment Configuration

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
cov_fail_under = 90

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "S", "B", "UP"]

[tool.mypy]
strict = true
```

### 11.3 Compliance Checklist

| Standard | Status |
|---|---|
| **PCI DSS v4.0** | Card data tokenized; no PAN storage |
| **GDPR / CCPA** | Customer data pseudonymized; right-to-erasure supported |
| **SOC 2 Type II** | Audit logging, access controls, encryption |
| **ISO 27001** | Security policies, risk management framework |
| **FIDO2 / WebAuthn** | Step-up authentication for high-risk flows |

---

*Document Owner: Platform Security & Risk Engineering Team*
*Review Cycle: Quarterly*
*Classification: Internal — Confidential*
