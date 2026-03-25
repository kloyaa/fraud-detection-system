# Data Retention Schedule
## Risk Assessment System (RAS) — Regulatory Retention Requirements

```yaml
document:       docs/compliance/retention_schedule.md
version:        1.0.0
owner:          James Whitfield (@james) — Head of Risk & Compliance
reviewers:      "@priya · @darius · @sofia · @marcus"
last_updated:   Pre-development
status:         ⏳ Planned
compliance:     GDPR Art. 5(1)(e) · BSA 31 CFR §1020.410 · PCI DSS Req 10.5
                FCRA §605 · 4AMLD Art. 40
classification: Internal — RESTRICTED — Legal Privilege
```

---

## 1. Guiding Principles

| Principle | Source | Application |
|---|---|---|
| **Storage limitation** | GDPR Art. 5(1)(e) | Personal data kept no longer than necessary for its purpose |
| **Legal obligation override** | GDPR Art. 17(3)(b) | AML / BSA obligations override right-to-erasure requests |
| **Minimum retention** | BSA / PCI DSS | Some data must be retained for a minimum period |
| **Purpose limitation** | GDPR Art. 5(1)(b) | Data retained for one purpose cannot be repurposed |

> *@james:* "The tension in this schedule is between GDPR's storage limitation principle and the AML / BSA minimum retention obligations. GDPR says 'keep no longer than necessary.' BSA says 'keep for at least 5 years.' Both are law. The resolution: retain the minimum required by the most demanding applicable law, document the legal basis, and pseudonymise where possible after the primary purpose expires."

---

## 2. Retention Schedule by Data Category

### 2.1 Transaction & Scoring Data

| Data Element | Hot Retention | Cold Retention | Total | Legal Basis | Store |
|---|---|---|---|---|---|
| Risk decisions (score, decision, rules) | 90 days | 7 years | 7 years | BSA 31 CFR §1020.410 — AML records | Cassandra → Snowflake |
| SHAP feature values | 90 days | 7 years | 7 years | FCRA §615 — adverse action evidence | Cassandra → Snowflake |
| Transaction metadata (amount, currency, merchant) | 90 days | 7 years | 7 years | BSA / AML | Cassandra → Snowflake |
| Adverse action notices issued | 90 days | 7 years | 7 years | FCRA §615 record-keeping | PostgreSQL → Snowflake |
| IP subnet (/24 masked) | 30 days | None | 30 days | Fraud detection — GDPR Art. 6(1)(f) | PostgreSQL TTL |
| Device fingerprint ID | 90 days | None | 90 days | Fraud detection — GDPR Art. 6(1)(f) | Cassandra TTL |

### 2.2 Case Management Data

| Data Element | Hot Retention | Cold Retention | Total | Legal Basis | Store |
|---|---|---|---|---|---|
| Case records (analyst notes, decision) | 12 months | 7 years | 7 years | PCI DSS Req 10.5 + BSA | PostgreSQL → Snowflake |
| Analyst identity (who resolved case) | 12 months | 7 years | 7 years | PCI DSS Req 10.2.1 — audit trail | PostgreSQL → Snowflake |
| Contestation records (GDPR Art. 22) | 12 months | 7 years | 7 years | Legal claims defence — GDPR Art. 17(3)(e) | PostgreSQL → Snowflake |
| SAR investigation records | None (no hot limit) | 5 years from filing | 5 years | BSA 31 CFR §1020.320(d) | Cassandra SAR keyspace (no TTL) → Snowflake |

### 2.3 Audit & Security Logs

| Data Element | Hot Retention | Cold Retention | Total | Legal Basis | Store |
|---|---|---|---|---|---|
| Application audit log (all decisions) | 90 days | 7 years | 7 years | PCI DSS Req 10.5.1 (12 months minimum) | Cassandra → Snowflake |
| Security event logs (Falco, WAF) | 12 months | 3 years | 3 years | PCI DSS Req 10.5.1 + ISO 27001 | Loki → S3 |
| Access logs (API, DB, Vault) | 12 months | 3 years | 3 years | PCI DSS Req 10.2.1 | Loki → S3 |
| Authentication events (Keycloak) | 12 months | 3 years | 3 years | PCI DSS Req 10.2.1(e) | Keycloak → Loki → S3 |
| Infrastructure change logs (ArgoCD) | 12 months | 3 years | 3 years | PCI DSS Req 10.2.1(g) | ArgoCD → Loki |

### 2.4 ML & Model Data

| Data Element | Hot Retention | Cold Retention | Total | Legal Basis | Store |
|---|---|---|---|---|---|
| Model artifacts (weights, params) | Per promotion | 2 years post-archival | 2 years min | SR 11-7 — model risk management | MLflow → S3 |
| Training datasets | None (Snowflake only) | 2 years | 2 years | SR 11-7 — model reproducibility | Snowflake |
| Experiment runs (MLflow) | Indefinite | — | Indefinite | SR 11-7 — audit trail | MLflow |
| Feature values (Feast offline) | 6 months | 2 years | 2 years | SR 11-7 — model validation | Snowflake |
| Fairness audit reports | Per model version | 2 years post-deprecation | 2 years min | ECOA / Reg B examination | Compliance vault |

### 2.5 Customer PII

| Data Element | Retention | Legal Basis | Erasure Eligible | Store |
|---|---|---|---|---|
| Customer pseudonymous ID | 7 years | BSA AML | No — AML exemption | PostgreSQL → Snowflake |
| Email hash (SHA-256) | 90 days | Fraud detection | Yes — after 90 days | PostgreSQL TTL |
| Name (if collected) | Not collected | N/A — not required | N/A | N/A |
| Date of birth | Not collected | N/A — not required | N/A | N/A |
| Full IP address | Not stored | N/A — masked at ingestion | N/A | N/A |

> *@priya:* "Full IP addresses are never written to any persistent store. The /24 subnet is stored for 30 days for fraud pattern analysis, then TTL-expired. This is a conscious data minimisation decision — see DPIA §3.2."

---

## 3. Retention Implementation

### 3.1 Cassandra TTL Configuration

```cql
-- Standard risk events table (90-day TTL)
CREATE TABLE risk.events (
    customer_id   TEXT,
    occurred_at   TIMEUUID,
    event_type    TEXT,
    payload       TEXT,
    PRIMARY KEY ((customer_id), occurred_at)
) WITH default_time_to_live = 7776000;   -- 90 days in seconds

-- SAR keyspace (no TTL — manual archive after 5 years)
CREATE TABLE sar.investigations (
    case_id       UUID,
    occurred_at   TIMEUUID,
    event_type    TEXT,
    payload       TEXT,
    PRIMARY KEY ((case_id), occurred_at)
) WITH default_time_to_live = 0;          -- No TTL — retained indefinitely
```

### 3.2 PostgreSQL Partition Archival

```sql
-- Monthly partitions archived to Snowflake after 90 days
-- Partition is detached (instant — no lock) then exported

-- Step 1: Export partition to Snowflake (Spark job — scheduled)
-- Step 2: Verify export completeness
-- Step 3: Detach partition (instant DDL — no downtime)
ALTER TABLE risk_decisions
  DETACH PARTITION risk_decisions_2024_01;

-- Step 4: Drop local partition after Snowflake verification
DROP TABLE risk_decisions_2024_01;
```

### 3.3 Snowflake Cold Storage Tiers

```sql
-- Snowflake storage tiers by age
-- Managed via Snowflake Time Travel + Fail-safe policies

-- Hot tier (0–12 months): Standard storage, full query access
-- Warm tier (1–3 years): Standard storage, query access
-- Cold tier (3–7 years): Snowflake Secure Data Sharing — compliance access only
-- Deletion: Automated after maximum retention period

ALTER TABLE risk.decisions
  SET DATA_RETENTION_TIME_IN_DAYS = 365;   -- 12-month Time Travel
```

### 3.4 Loki Log Retention

```yaml
# k8s/loki/retention-config.yaml
limits_config:
  retention_period: 8760h    # 12 months hot retention (PCI DSS minimum)

compactor:
  retention_enabled: true
  retention_delete_delay: 2h
  retention_delete_worker_count: 150
```

---

## 4. Right to Erasure — Retention Interaction

When a data subject submits a GDPR Art. 17 erasure request, retention obligations take precedence:

| Data Category | Erasure Eligible | Exemption | Action |
|---|---|---|---|
| Transaction records | ❌ No | BSA Art. 17(3)(b) — legal obligation | Retain 7 years, pseudonymise PII |
| SAR records | ❌ No | Legal claims Art. 17(3)(e) + BSA | Retain per SAR schedule |
| Fraud evidence (cases) | ❌ No | Legal claims Art. 17(3)(e) | Retain 7 years |
| Security logs | ❌ No | Legal obligation Art. 17(3)(b) | Retain per log schedule |
| Email hash | ✅ Yes | Purpose expired after 90 days | Delete via TTL or on request |
| Device fingerprint | ✅ Partial | Fraud evidence may justify retention | Pseudonymise after 90 days |

**Erasure response process:**
```
1. Identify all data categories for customer_id
2. Apply exemption table above per category
3. For eligible categories: delete or pseudonymise
4. For exempt categories: document legal basis per category
5. Respond within 30 days (GDPR Art. 12(3)) with:
   - Categories erased
   - Categories retained + legal basis for each
```

---

## 5. Retention Review & Governance

| Activity | Frequency | Owner |
|---|---|---|
| Annual retention schedule review | Annual | `@james` |
| Verify TTL configuration in Cassandra | Quarterly | `@darius` |
| Verify Snowflake archival completion | Monthly | `@darius` |
| Verify Loki log retention policy | Quarterly | `@darius` |
| SAR record 5-year archival | As records age | `@james` |
| Regulatory change review | On any BSA/GDPR update | `@james` |
| Retention schedule sign-off | Pre-production | `@james` + CISO |

---

## 6. Non-Compliance Risk

| Violation | Regulatory Consequence |
|---|---|
| Deleting AML records before 5 years | BSA violation — civil penalty up to $1M per violation |
| Retaining PII beyond GDPR schedule | ICO enforcement — up to €20M / 4% global turnover |
| Deleting audit logs before PCI minimum | PCI DSS Req 10.5.1 finding — assessment failure |
| Missing SAR records at FinCEN examination | BSA penalty + potential programme failure designation |
| Retaining data beyond stated purpose | GDPR Art. 5(1)(e) violation — ICO enforcement action |

---

## 7. Related Documents

| Document | Location |
|---|---|
| GDPR DPIA | `docs/compliance/gdpr_dpia.md` |
| SAR Procedure | `docs/compliance/sar_procedure.md` |
| PCI DSS Controls (Req 10) | `docs/compliance/pci_dss_controls.md` |
| AML Programme | `docs/compliance/aml_programme.md` |
| Cassandra Node Failure Runbook | `docs/runbooks/cassandra_node_failure.md` |
| Kafka Topic Design (retention config) | `docs/architecture/kafka_topics.md` |

---

*Document Version: 1.0.0*
*Owner: James Whitfield — Head of Risk & Compliance*
*Review Cycle: Annual · On any regulatory change*
*Classification: Internal — RESTRICTED — Legal Privilege*