# Production Readiness Review (PRR) Checklist
## Risk Assessment System (RAS)

```yaml
document:       docs/quality/prr_checklist.md
version:        1.0.0
owner:          Aisha Patel (@aisha) — Principal QA / Test Engineer
authority:      Unconditional go/no-go on production deployment
reviewers:      "@marcus · @priya · @yuki · @darius · @sofia · @james · @elena"
last_updated:   Pre-development
status:         Template — not yet executed
classification: Internal — Engineering Confidential
```

---

## Overview

The PRR is the mandatory quality and compliance gate before any RAS service deploys to production. Every item requires **evidence** — not assertion. A checkbox without an evidence link is not a passed gate.

**PRR types:**

| Trigger | PRR Type | Sections Required |
|---|---|---|
| New service → production | Full PRR | All 7 sections |
| New external dependency | Full PRR | All 7 sections |
| New data category processed | Full PRR | All 7 sections |
| Major feature (>20% critical path change) | Full PRR | All 7 sections |
| Model promotion to production | Model PRR | §1 · §2 · §4 · §6 · §7 |
| Infrastructure change only | Infra PRR | §2 · §3 · §5 · §6 |
| Routine deployment (<20% change, no new deps) | Deploy Sub-Checklist | `docs/quality/deploy_checklist.md` |

**Status key:**
- `⏳ Planned` — not yet executed
- `🔄 In Progress` — actively being worked
- `✅ Pass` — gate passed with evidence
- `❌ Fail` — gate failed — must be resolved
- `🔴 Blocked` — external dependency blocking gate
- `🔵 N/A` — not applicable to this PRR run

---

## PRR Header

```
Service:          ras-scoring-api
Version:          ____________
Target env:       production
PRR Type:         Full PRR
PRR Owner:        Aisha Patel (@aisha)
PRR Started:      ____________
PRR Completed:    ____________
Overall Verdict:  [ ] GO   [ ] NO-GO   [ ] CONDITIONAL GO
Conditions:       ____________
```

---

## Section 1 — Code Quality
**Owner:** `@sofia` · **Reviewer:** `@aisha`

| # | Gate | Evidence Required | Owner | Status |
|---|---|---|---|---|
| 1.1 | Unit test coverage ≥ 90% (line) | Codecov report URL | `@sofia` | `⏳ Planned` |
| 1.2 | Branch coverage ≥ 85% on critical paths | Codecov branch report URL | `@sofia` | `⏳ Planned` |
| 1.3 | Mutation score ≥ 70% on scoring engine | mutmut HTML report | `@sofia` | `⏳ Planned` |
| 1.4 | All integration tests passing in staging | CI run URL | `@sofia` | `⏳ Planned` |
| 1.5 | Contract tests passing for all consumers | PactFlow dashboard URL | `@aisha` | `⏳ Planned` |
| 1.6 | Ruff: zero lint errors | CI run output | `@sofia` | `⏳ Planned` |
| 1.7 | mypy strict: zero type errors | CI run output | `@sofia` | `⏳ Planned` |
| 1.8 | Bandit: zero HIGH / CRITICAL findings | Bandit report URL | `@priya` | `⏳ Planned` |
| 1.9 | Semgrep: zero security findings | Semgrep report URL | `@priya` | `⏳ Planned` |
| 1.10 | All Alembic migrations have `downgrade()` | Migration code review link | `@sofia` | `⏳ Planned` |
| 1.11 | No `any` type in TypeScript frontend | ESLint report URL | `@elena` | `⏳ Planned` |
| 1.12 | Frontend Playwright E2E tests passing | CI run URL | `@aisha` / `@elena` | `⏳ Planned` |

**Section 1 Result:** `⏳ Planned`

---

## Section 2 — Performance
**Owner:** `@aisha` · `@darius` · **Reviewer:** `@aisha`

> All gates validated at **2x expected peak traffic** with **multi-class Locust traffic model** for minimum **30 minutes**.

| # | Gate | Target | Evidence Required | Owner | Status |
|---|---|---|---|---|---|
| 2.1 | P50 scoring latency | < 35ms | Locust HTML report | `@aisha` | `⏳ Planned` |
| 2.2 | P95 scoring latency | < 100ms | Locust HTML report | `@aisha` | `⏳ Planned` |
| 2.3 | P99 scoring latency | < 250ms | Locust HTML report | `@aisha` | `⏳ Planned` |
| 2.4 | Error rate at 2x peak | < 0.1% | Locust HTML report | `@aisha` | `⏳ Planned` |
| 2.5 | PgBouncer pool utilisation at peak | < 70% | Grafana screenshot | `@sofia` / `@darius` | `⏳ Planned` |
| 2.6 | Redis connection pool stable at peak | < 70% | Redis metrics screenshot | `@sofia` | `⏳ Planned` |
| 2.7 | Kafka consumer lag at peak | < 500ms | Confluent CC screenshot | `@darius` | `⏳ Planned` |
| 2.8 | BentoML P95 inference latency | < 25ms | BentoML metrics report | `@yuki` | `⏳ Planned` |
| 2.9 | No memory leak over 30-min soak | Stable trend | Grafana memory graph | `@darius` | `⏳ Planned` |
| 2.10 | HPA scale-up verified under load | Pods scale within 60s | K8s events log | `@darius` | `⏳ Planned` |
| 2.11 | Frontend Core Web Vitals | LCP < 2.5s · INP < 200ms · CLS < 0.1 | Lighthouse report | `@elena` | `⏳ Planned` |

**Section 2 Result:** `⏳ Planned`

---

## Section 3 — Reliability & Chaos
**Owner:** `@darius` · **Reviewer:** `@aisha`

> Each chaos experiment requires: hypothesis statement, steady-state definition, blast radius documentation, and pass/fail evidence.

| # | Gate | Hypothesis | Evidence Required | Owner | Status |
|---|---|---|---|---|---|
| 3.1 | ML service pod kill | Rule-only fallback activates < 500ms | Chaos Mesh report | `@darius` | `⏳ Planned` |
| 3.2 | Redis primary failure | Velocity checks fail open, scoring continues | Chaos Mesh report | `@darius` | `⏳ Planned` |
| 3.3 | Kafka broker loss (1 of 9) | Consumer lag < 30s, no message loss | Chaos Mesh report | `@darius` | `⏳ Planned` |
| 3.4 | Cassandra node failure | Scoring degrades gracefully, audit log intact | Chaos Mesh report | `@darius` | `⏳ Planned` |
| 3.5 | BentoML OOM kill | Circuit breaker opens, fallback < 200ms | Chaos Mesh report | `@darius` | `⏳ Planned` |
| 3.6 | Enrichment service timeout | Scoring continues with `enrichment_partial=true` | Chaos Mesh report | `@darius` | `⏳ Planned` |
| 3.7 | PostgreSQL primary failover | Read replicas promote, RTO < 5 min | Failover test log | `@darius` | `⏳ Planned` |
| 3.8 | Rollback procedure