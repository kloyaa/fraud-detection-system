# Sprint 4 — ML Pipeline + Feature Store

**Goal:** ML model scores transactions. Feast feature store is live.

**Duration:** 3 weeks  
**Lead:** `@yuki`  
**Supporting:** `@darius`, `@aisha`

---

## Feature Store

`@yuki` leads

```
[ ] Feast repository initialized (ml/features/)
[ ] All 34 feature view definitions (per feature_catalog.md)
[ ] Feast online store — Redis configured
[ ] Feast offline store — Snowflake configured
```

---

## Flink Pipeline

`@yuki` leads

```
[ ] Velocity aggregation job (txn_count_60s, txn_amount_1h)
[ ] Graph feature trigger (async Neo4j → Feast)
[ ] Flink checkpointing — RocksDB + S3
[ ] Consumer group ras-flink-velocity live
```

---

## PySpark Batch Jobs

`@yuki` leads

```
[ ] customer_history_features job (6h schedule)
[ ] merchant_features job (6h schedule)
[ ] graph_feature_snapshot job (4h schedule)
```

---

## Model Training

`@yuki` leads

```
[ ] Training dataset built from Snowflake
[ ] XGBoost DART model trained (GPU)
[ ] Platt scaling calibration
[ ] Fairness audit completed — DIR all ≥ 0.80
[ ] Model registered in MLflow (Staging)
```

---

## BentoML Serving

`@yuki` leads

```
[ ] BentoML service defined (ml/serving/)
[ ] ISS-001: Warmup hook implemented
[ ] Champion model deployed to staging
[ ] Scoring API wired to BentoML (circuit breaker + fallback)
```

---

## Model Monitoring

`@yuki` leads

```
[ ] Evidently AI — PSI drift detection configured
[ ] Score distribution alerts in Grafana
```

---

## Infrastructure Support

`@darius` supports

```
[ ] GPU node pool provisioned (Karpenter)
[ ] BentoML Kubernetes deployment + HPA
[ ] Flink cluster on EKS
[ ] ISS-001: BentoML readiness probe gates warmup
```

---

## Completion Criteria

✅ Sprint 4 done when:
- Transactions are scored by the ML ensemble
- Feast serves features in < 5ms
- BentoML P95 < 25ms
- ISS-001 resolved

---

**Owner:** Dr. Yuki Tanaka (`@yuki`)  
**Status:** ⏳ Not started  
**Created:** 2026-03-25
