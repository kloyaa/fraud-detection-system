# Feature Catalog
## Risk Assessment System (RAS) — ML Feature Definitions

```yaml
document:       docs/ml/feature_catalog.md
version:        1.0.0
owner:          Dr. Yuki Tanaka (@yuki) — Lead ML / Risk Scientist
reviewers:      "@james · @priya · @sofia · @marcus"
last_updated:   Pre-development
status:         ⏳ Planned
compliance:     GDPR Art. 5(1)(c) · ECOA / Reg B · SR 11-7
classification: Internal — Confidential — Model Governance
```

---

## 1. Purpose

This catalog is the authoritative definition of every feature used in RAS ML models. It serves three purposes:

1. **Data minimisation compliance** — every feature must have a documented fraud detection purpose (GDPR Art. 5(1)(c))
2. **Training-serving parity** — Feast feature definitions are derived from this catalog
3. **Regulatory audit** — SR 11-7 requires documentation of all model inputs; ECOA requires proof that no prohibited basis is used

> *@james:* "Every feature in this catalog has been reviewed for ECOA / Reg B compliance. Any new feature added to a model must go through compliance review before being registered in Feast. This is not optional."

---

## 2. Feature Categories

| Category | Count | Computation | Store |
|---|---|---|---|
| Velocity | 6 | Flink real-time | Feast / Redis |
| Historical | 5 | PySpark batch (6h) | Feast / Redis |
| Graph | 4 | Neo4j → Flink async | Feast / Redis |
| Enriched | 4 | Enrichment service (inline) | Real-time only |
| Derived | 6 | Scoring API (inline) | Real-time only |
| Temporal | 3 | Scoring API (inline) | Real-time only |
| Merchant | 3 | PySpark batch (6h) | Feast / Redis |
| Device | 3 | Device fingerprint service | Feast / Redis |
| **Total** | **34** | — | — |

---

## 3. Feature Definitions

### 3.1 Velocity Features

Computed by Apache Flink from `risk.decisions` Kafka stream. Written to Feast online store (Redis) per transaction.

| Feature | Type | Window | Description | Fraud Signal | ECOA Review |
|---|---|---|---|---|---|
| `txn_count_60s` | `Int64` | 60 seconds | Number of transactions by this customer in the last 60 seconds | High velocity = automated fraud tool | ✅ Approved |
| `txn_count_1h` | `Int64` | 1 hour | Transaction count per customer in last hour | Sustained velocity | ✅ Approved |
| `txn_amount_1h` | `Float32` | 1 hour | Total transaction amount per customer in last hour | Amount accumulation | ✅ Approved |
| `txn_declined_24h` | `Int64` | 24 hours | Number of declined transactions in last 24 hours | Prior declines = fraud signal | ✅ Approved |
| `distinct_merchants_24h` | `Int64` | 24 hours | Unique merchants transacted with in last 24 hours | Card testing pattern | ✅ Approved |
| `txn_count_device_5m` | `Int64` | 5 minutes | Transactions from this device fingerprint in last 5 min | Device-level velocity | ✅ Approved |

```python
# ml/features/velocity_features.py — Feast feature view definition
from feast import FeatureView, Field, PushSource
from feast.types import Int64, Float32

customer_velocity_fv = FeatureView(
    name="customer_velocity",
    entities=["customer"],
    ttl=timedelta(hours=2),
    schema=[
        Field(name="txn_count_60s",        dtype=Int64),
        Field(name="txn_count_1h",         dtype=Int64),
        Field(name="txn_amount_1h",        dtype=Float32),
        Field(name="txn_declined_24h",     dtype=Int64),
        Field(name="distinct_merchants_24h", dtype=Int64),
    ],
    source=PushSource(name="velocity_push"),
    online=True,
    offline=False,   # Real-time only — no offline store
)
```

---

### 3.2 Historical Features

Computed by PySpark batch jobs every 6 hours from Snowflake. Written to Feast online store (Redis) via `materialize_incremental`.

| Feature | Type | Lookback | Description | Fraud Signal | ECOA Review |
|---|---|---|---|---|---|
| `customer_avg_amount_30d` | `Float32` | 30 days | Average transaction amount for this customer | Baseline for amount spike detection | ✅ Approved |
| `customer_age_days` | `Int64` | Account lifetime | Days since customer account was created | New accounts = higher risk | ✅ Approved — account tenure, NOT person age |
| `txn_count_30d` | `Int64` | 30 days | Total transactions in last 30 days | Activity baseline | ✅ Approved |
| `chargeback_rate_90d` | `Float32` | 90 days | Ratio of chargebacks to total transactions | Direct fraud history | ✅ Approved |
| `distinct_merchants_30d` | `Int64` | 30 days | Unique merchants in last 30 days | Behavioural baseline | ✅ Approved |

> *@james:* "`customer_age_days` refers to **account tenure** — days since the account was created in our system. It does NOT refer to the age of the person. This distinction is critical for ECOA compliance. Age of a person is a prohibited basis under Reg B. Account tenure is a legitimate risk signal."

---

### 3.3 Graph Features

Computed asynchronously by Apache Flink via Neo4j traversal. Written to Feast online store (Redis). Maximum staleness: 1 hour.

| Feature | Type | Description | Fraud Signal | ECOA Review |
|---|---|---|---|---|
| `device_account_count_7d` | `Int64` | Number of distinct customer accounts that used this device in the last 7 days | Shared device = mule account indicator | ✅ Approved |
| `linked_fraud_ring_score` | `Float32` | Proportion of accounts linked to this device that have been flagged for fraud | Direct fraud ring linkage | ✅ Approved |
| `shared_device_accounts` | `Int64` | Total accounts ever associated with this device fingerprint | Device sharing pattern | ✅ Approved |
| `ip_shared_accounts_1h` | `Int64` | Distinct accounts transacting from this IP in last hour | IP-level velocity (shared IPs, NAT) | ✅ Approved |

```cypher
-- Neo4j traversal query (executed by Flink graph trigger)
MATCH (c:Customer {id: $customer_id})
OPTIONAL MATCH (c)-[:USED_DEVICE]->(d:Device)
             <-[:USED_DEVICE]-(c2:Customer)
OPTIONAL MATCH (c2)-[:FLAGGED_FRAUD]->()
RETURN
  count(DISTINCT d)                                    AS device_account_count_7d,
  count(DISTINCT c2)                                   AS shared_device_accounts,
  CASE WHEN count(DISTINCT c2) > 0
       THEN toFloat(count(DISTINCT c2[FLAGGED_FRAUD]))
            / count(DISTINCT c2)
       ELSE 0.0
  END                                                  AS linked_fraud_ring_score
```

---

### 3.4 Enriched Features

Computed inline by the enrichment service during scoring. Not stored in Feast — available in real-time only.

| Feature | Type | Source | Description | Fraud Signal | ECOA Review |
|---|---|---|---|---|---|
| `ip_proxy_score` | `Float32` | IPQualityScore API | Probability (0–1) that IP is a proxy, VPN, or Tor exit node | High proxy score = identity obfuscation | ✅ Approved |
| `ip_country` | `String` | MaxMind GeoIP2 | ISO 3166-1 country code of IP address | Geolocation for mismatch checks | ✅ Approved |
| `bin_country` | `String` | Internal BIN DB | Country where the card was issued | Card/location mismatch | ✅ Approved |
| `bin_card_type` | `String` | Internal BIN DB | Card type: credit / debit / prepaid | Prepaid = higher risk | ✅ Approved |

> *@priya:* "The full IP address is masked to a /24 subnet after enrichment — only `ip_country` and `ip_proxy_score` are retained in the feature vector. The raw IP never enters the feature store or the model. See `docs/security/encryption_spec.md` §2.3."

---

### 3.5 Derived Features

Computed inline in the scoring API from other features. Zero latency — pure arithmetic.

| Feature | Type | Formula | Description | Fraud Signal | ECOA Review |
|---|---|---|---|---|---|
| `amount_vs_avg_ratio` | `Float32` | `amount / customer_avg_amount_30d` | How much this transaction deviates from the customer's average | Spike = unusual behaviour | ✅ Approved |
| `ip_country_mismatch` | `Bool` | `ip_country != bin_country` | IP location differs from card-issuing country | Cross-border fraud signal | ✅ Approved |
| `bin_country_mismatch` | `Bool` | `bin_country != merchant_country` | Card-issuing country differs from merchant country | Cross-border fraud signal | ✅ Approved |
| `velocity_ratio_60s_30d` | `Float32` | `txn_count_60s / (txn_count_30d / 43200)` | Current velocity vs. 30-day average rate | Velocity spike normalised | ✅ Approved |
| `amount_declined_ratio` | `Float32` | `txn_declined_24h / max(txn_count_1h, 1)` | Proportion of recent transactions that were declined | Declined transaction pattern | ✅ Approved |
| `is_high_value` | `Bool` | `amount > 500` | Transaction above high-value threshold | High-value = higher consequence | ✅ Approved |

---

### 3.6 Temporal Features

Computed inline from transaction timestamp. Zero latency.

| Feature | Type | Description | Fraud Signal | ECOA Review |
|---|---|---|---|---|
| `hour_of_day` | `Int64` | Hour of transaction (0–23, UTC) | Off-hours transactions have higher fraud rate | ✅ Approved |
| `is_weekend` | `Bool` | Whether transaction occurs on Saturday or Sunday | Weekend fraud patterns differ | ✅ Approved |
| `days_since_last_txn` | `Int64` | Days since customer's previous transaction | Dormant account reactivation = risk signal | ✅ Approved |

---

### 3.7 Merchant Features

Computed by PySpark batch every 6 hours. Written to Feast online store.

| Feature | Type | Lookback | Description | Fraud Signal | ECOA Review |
|---|---|---|---|---|---|
| `merchant_fraud_rate_30d` | `Float32` | 30 days | Proportion of transactions at this merchant confirmed as fraud | High-risk merchant = elevated baseline | ✅ Approved |
| `merchant_txn_count_30d` | `Int64` | 30 days | Total transaction volume at this merchant | New merchant = less history | ✅ Approved |
| `merchant_avg_amount_30d` | `Float32` | 30 days | Average transaction amount at this merchant | Baseline for merchant-level spike detection | ✅ Approved |

---

### 3.8 Device Features

Computed by the device fingerprint service. Written to Feast online store.

| Feature | Type | Description | Fraud Signal | ECOA Review |
|---|---|---|---|---|
| `device_first_seen` | `Bool` | Whether this device fingerprint has been seen before | New device = higher risk | ✅ Approved |
| `device_age_days` | `Int64` | Days since device fingerprint first observed | Very new device = risk signal | ✅ Approved |
| `device_account_switches_7d` | `Int64` | Number of distinct accounts that logged in from this device in 7 days | Account switching = takeover signal | ✅ Approved |

---

## 4. Prohibited Features

The following features are **explicitly prohibited** from use in any RAS model. This list is enforced by the feature compliance review process owned by `@james`.

| Feature | Category | Prohibition Basis |
|---|---|---|
| Race / ethnicity | Protected class | ECOA / Reg B §202.6 |
| Gender / sex | Protected class | ECOA / Reg B §202.6 |
| National origin | Protected class | ECOA / Reg B §202.6 |
| Religion | Protected class | ECOA / Reg B §202.6 |
| Marital status | Protected class | ECOA / Reg B §202.6 |
| ZIP code (direct) | Prohibited proxy | Correlated with race/ethnicity — disparate impact |
| Full name | Prohibited proxy | Correlated with gender and national origin |
| Date of birth (person) | Prohibited proxy | Age discrimination risk (distinct from account age) |
| Email address (full) | PII minimisation | Not required — email domain hash only (SHA-256) |
| Full IP address | PII minimisation | Masked to /24 after enrichment — never stored |
| Full PAN | PCI DSS | Never collected — tokenised at entry point |
| CVV / CVC | PCI DSS | Never collected — rejected at validation layer |

---

## 5. Feature Addition Process

Any new feature must complete the following steps before being used in a model:

```
1. Feature proposal — author documents in this catalog (draft)
   Include: name, type, computation, fraud signal justification

2. Compliance review (@james)
   Checks: ECOA prohibited basis, GDPR minimisation, PII classification

3. Privacy review (@priya)
   Checks: PII handling, encryption requirements, retention classification

4. Technical review (@marcus / @sofia)
   Checks: Feast definition, computation feasibility, latency impact

5. Leakage review (@yuki)
   Checks: temporal correctness, no post-decision data, solo AUC < 0.85

6. Feast registration
   Feature view updated in ml/features/
   PR review required — @yuki approval

7. Catalog update
   This document updated with Approved status
```

---

## 6. Feature Freshness SLAs

| Store | Feature Category | Max Staleness | Alert Threshold |
|---|---|---|---|
| Feast / Redis (Flink) | Velocity | 60 seconds | > 120 seconds |
| Feast / Redis (Flink) | Graph | 1 hour | > 2 hours |
| Feast / Redis (PySpark) | Historical | 6 hours | > 8 hours |
| Feast / Redis (PySpark) | Merchant | 6 hours | > 8 hours |
| Feast / Redis (device service) | Device | 5 minutes | > 15 minutes |
| Real-time (inline) | Enriched / Derived / Temporal | Per request | N/A |

---

## 7. Related Documents

| Document | Location |
|---|---|
| Model Card | `docs/ml/model_card.md` |
| ML Pipeline Architecture | `docs/ml/pipeline_architecture.md` |
| Fairness Audit Report | `docs/ml/fairness_audit.md` |
| GDPR DPIA (data minimisation) | `docs/compliance/gdpr_dpia.md` |
| Adverse Action Codes | `docs/compliance/adverse_action_codes.md` |
| Feast Feature Definitions | `ml/features/` |

---

*Document Version: 1.0.0*
*Owner: Dr. Yuki Tanaka — Lead ML / Risk Scientist*
*Review Cycle: Per model promotion · On any feature addition*
*Classification: Internal — Confidential — Model Governance*