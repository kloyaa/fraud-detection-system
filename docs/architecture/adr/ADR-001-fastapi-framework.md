# ADR-001: API Framework — FastAPI over Django REST Framework

```yaml
id:         ADR-001
title:      API Framework Selection
status:     Accepted
date:       2024-01-08  (Sprint 1)
author:     Marcus Chen (@marcus)
reviewers:  "@sofia · @darius · @priya"
deciders:   "@marcus · @sofia"
supersedes: —
superseded_by: —
```

## Context

RAS requires an API framework to serve the scoring endpoint (`POST /v1/risk/score`). The scoring endpoint is the hot path — it must handle 100,000+ requests per second with P95 latency under 100ms. The framework must support:

- Async I/O natively — the scoring pipeline makes multiple concurrent downstream calls (enrichment, Feast, BentoML)
- Automatic OpenAPI documentation
- Strong request validation at the boundary
- Python 3.12 compatibility
- Production-proven at high throughput

Candidates evaluated: **FastAPI**, **Django REST Framework (DRF)**, **Starlette (bare)**, **Flask + marshmallow**, **Litestar**

## Decision

**Use FastAPI 0.111+ as the API framework for all RAS services.**

## Rationale

| Criterion | FastAPI | DRF | Starlette | Flask |
|---|---|---|---|---|
| Async-first | ✅ Native ASGI | ❌ Sync (ASGI adapter only) | ✅ Native | ❌ Sync |
| Pydantic v2 integration | ✅ Native | ❌ Separate serializers | ❌ Manual | ❌ Manual |
| OpenAPI auto-docs | ✅ Automatic | ⚠️ drf-spectacular add-on | ❌ Manual | ❌ Manual |
| Dependency injection | ✅ Native `Depends()` | ❌ Mixins/ViewSets | ❌ Manual | ❌ Manual |
| Type safety | ✅ Full mypy support | ⚠️ Partial | ✅ Full | ⚠️ Partial |
| Production adoption | ✅ Stripe, Netflix, Microsoft | ✅ Instagram, Disqus | ⚠️ Lower adoption | ✅ Broad |

**The key differentiator is async-first architecture.** The scoring pipeline makes 4–6 concurrent downstream calls per request (enrichment, Feast feature fetch, rule engine, BentoML inference, Cassandra write, Kafka publish). Under DRF's synchronous model, these would be sequential — adding 150ms+ to every request. Under FastAPI's native async model, they execute concurrently within the event loop, collapsing to the latency of the slowest call (~25ms for BentoML inference).

**Pydantic v2 native integration** eliminates a separate validation layer. Pydantic v2's Rust-based core provides ~17x faster validation than Pydantic v1, which matters at 100k TPS.

## Consequences

**Positive:**
- Sub-100ms P95 latency achievable with concurrent async downstream calls
- Single validation layer (Pydantic) — no impedance mismatch between framework and validator
- Auto-generated OpenAPI docs reduce API documentation toil
- Native dependency injection enables clean testability (swap real DB for Testcontainers fixture)

**Negative:**
- Blocking calls inside `async def` are invisible bugs — requires discipline and code review enforcement (@sofia owns this)
- CPU-bound tasks must be offloaded to Celery — event loop blocks on computation
- Smaller ecosystem than Django — some Django utilities (admin, ORM) not available

**Mitigations:**
- `ruff` rules enforce no synchronous I/O in async context
- Celery for all background tasks
- SQLAlchemy 2.0 async + asyncpg for fully async ORM


*ADR Directory Version: 1.0.0*
*Owner: Marcus Chen — Chief Risk Architect*
*Format: MADR (Markdown Architectural Decision Records)*
*Review: New ADRs require Architecture Review Board approval*
*Classification: Internal — Engineering Confidential*