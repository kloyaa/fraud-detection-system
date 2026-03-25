# Sprint 3 — Rule Engine + Case Management

**Goal:** Rules fire correctly. Analysts can review and resolve cases.

**Duration:** 2 weeks  
**Lead:** `@sofia` + `@marcus`  
**Supporting:** `@james`, `@aisha`

---

## Rule Engine

`@sofia` + `@marcus` lead

```
[ ] RuleEngine class — priority-ordered evaluation
[ ] 10 production rules implemented (R001–R010)
[ ] Rule cache (in-process) with Kafka refresh (ADR-008)
[ ] ISS-006: Kafka rule distribution live
[ ] RuleCacheRefresher — startup load + continuous consume
[ ] Readiness probe gates on rule cache ready
```

---

## Case Management

`@sofia` + `@marcus` lead

```
[ ] POST /v1/cases — case creation on score > 600
[ ] GET /v1/cases — analyst queue with SLA sorting
[ ] PATCH /v1/cases/{id} — resolve / assign / escalate
[ ] SLA deadline calculation + PagerDuty alerts
[ ] GDPR Art. 22(3) contestation endpoint
[ ] SAR escalation path — compliance scope + lock
```

---

## Admin API

`@sofia` + `@marcus` lead

```
[ ] GET/POST /v1/rules — rule management
[ ] Rule versioning + rollback (per ADR-008)
[ ] Rule change → Kafka rules.changed publish
```

---

## Compliance Review

`@james` reviews

```
[ ] SAR confidentiality controls — case segregation
[ ] Adverse action notice pipeline (FCRA §615)
[ ] Reason code mapping (AA01–AA20) wired to SHAP
```

---

## Testing

`@aisha` writes

```
[ ] Rule engine unit tests — all 10 rules + edge cases
[ ] Case management integration tests
[ ] Contract tests — case service consumer (Pact)
[ ] SAR escalation tests — confirm tipping-off prevention
```

---

## Completion Criteria

✅ Sprint 3 done when:
- A declined transaction creates a case
- Analyst can resolve it
- Rules fire in correct priority order
- Kafka rule distribution < 500ms

---

**Owner:** Sofia Martínez (`@sofia`)  
**Status:** ⏳ Not started  
**Created:** 2026-03-25
