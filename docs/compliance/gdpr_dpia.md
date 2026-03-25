# Data Protection Impact Assessment (DPIA)
## Risk Assessment System (RAS) — GDPR Article 35

```yaml
document:           docs/compliance/gdpr_dpia.md
version:            1.0.0
owner:              James Whitfield (@james) — Head of Risk & Compliance
reviewers:          "@priya · @marcus · @sofia · @yuki · @elena"
legal_review:       External DPO — not yet engaged
standard:           GDPR Article 35 · ICO DPIA Guidance (2018)
dpo_consulted:      Yes — @james is CIPP/E certified; external DPO to be engaged for sign-off
status:             Draft — pending external DPO sign-off (PRR blocker B-003)
last_updated:       Pre-development
classification:     Internal — RESTRICTED — Legal Privilege
distribution:       DPO · CISO · Engineering leads · Supervisory authority (if required)
```

---

## 1. Introduction & Legal Basis for DPIA

### 1.1 Why a DPIA Is Required

GDPR Article 35(1) requires a DPIA where processing is likely to result in a high risk to the rights and freedoms of natural persons. Article 35(3) specifies three categories that **always** require a DPIA:

> *Article 35(3)(a):* "A systematic and extensive evaluation of personal aspects relating to natural persons which is based on automated processing, including profiling, and on which decisions are based that produce legal or similarly significant effects concerning the natural person."

RAS meets this criterion on all three elements:

| Element | RAS Evidence |
|---|---|
| Systematic and extensive evaluation | Every transaction by every customer is evaluated in real time via ML model + rule engine |
| Based on automated processing including profiling | XGBoost model uses 47 features including behavioural history, velocity, and device patterns |
| Decisions producing legal or similarly significant effects | A DECLINE decision prevents a customer from completing a financial transaction — a legally significant effect under EDPB Guidelines 04/2022 |

> *@james:* "There is no ambiguity here. RAS is a textbook Article 35(3)(a) system. A DPIA is not optional — it is mandatory before the first production transaction is processed. Failure to complete a DPIA before going live is an ICO enforcement trigger. Maximum fine: €10 million or 2% of global annual turnover under GDPR Article 83(4)."

### 1.2 Supervisory Authority Pre-Consultation

GDPR Article 36 requires prior consultation with the supervisory authority (ICO for UK operations, relevant lead DPA for EU operations) if the DPIA concludes that the processing would result in a high residual risk that cannot be mitigated. Section 7 of this document contains the residual risk assessment. If residual risk remains HIGH after all mitigations, ICO consultation is mandatory before processing commences.

---

## 2. Processing Description

### 2.1 Purpose of Processing

| Purpose | Legal Basis | Article 6 Basis |
|---|---|---|
| Real-time fraud detection and prevention | Legitimate interests | Art. 6(1)(f) — LIA documented in `docs/compliance/lia.md` |
| AML transaction monitoring | Legal obligation | Art. 6(1)(c) — BSA / 4AMLD compliance |
| Case management and human review | Legal obligation + Legitimate interests | Art. 6(1)(c) + 6(1)(f) |
| Model training and improvement | Legitimate interests | Art. 6(1)(f) — LIA documented |
| Regulatory audit trail | Legal obligation | Art. 6(1)(c) — PCI DSS Req 10, AML retention |

> *@james:* "Consent is not an appropriate legal basis for fraud detection processing. EDPB Opinion 06/2014 on the notion of legitimate interests confirms that fraud prevention constitutes a legitimate interest of the controller. More importantly, consent must be freely given — it is not freely given when refusal means the customer cannot complete a transaction. We rely on Article 6(1)(f) for fraud detection and 6(1)(c) for AML/regulatory obligations."

### 2.2 Data Categories Processed

| Data Category | Examples | Sensitivity | Retention |
|---|---|---|---|
| Transaction data | Amount, currency, timestamp, merchant | Standard personal data | 90 days hot / 7 years cold (AML) |
| Payment instrument | BIN (6 digits), last four, card network | Financial data | 90 days hot / 7 years cold |
| Device data | Fingerprint ID, user agent, screen resolution | Standard personal data | 90 days hot |
| Network data | IP address (masked after scoring), proxy score | Standard personal data | 30 days |
| Behavioural features | Transaction velocity, amount patterns, device history | Inferred / profiling data | 90 days hot / 7 years cold |
| Risk scores | 0–1000 fraud score, decision, SHAP attributions | Inferred / profiling data | 90 days hot / 7 years cold |
| Case management data | Analyst notes, resolution decision, contestation records | Standard personal data | 7 years (regulatory) |

**Special category data (Article 9):** RAS does **not** process special category data (race, ethnicity, health, religion, political opinion, biometric data for identification purposes). The BISG proxy used in fairness audits is used solely for post-hoc bias measurement — it is never a model input feature and never stored in the operational database. (@yuki — documented in model card §4.3.)

### 2.3 Data Subjects

| Category | Estimated Volume | Location |
|---|---|---|
| Cardholders (end consumers) | 15M+ at Q2 2025 | US, EU, APAC |
| Merchants (as entities) | 50+ at Q2 2025 | Global |

### 2.4 Data Flow Diagram

```
[Customer] ──transaction──► [Merchant POS/Website]
                                      │
                                      │ API call (TLS 1.3)
                                      ▼
                             [Kong API Gateway]
                                      │ mTLS
                                      ▼
                             [Scoring API]
                             ┌─────────────────────────────────┐
                             │  Enrichment (IP geo, BIN)       │
                             │  Feature fetch (Feast/Redis)    │
                             │  Rule evaluation                │
                             │  ML scoring (BentoML)           │
                             │  Decision assembly              │
                             └──────────┬──────────────────────┘
                                        │
               ┌────────────────────────┼──────────────────┐
               ▼                        ▼                  ▼
    [PostgreSQL]               [Cassandra]            [Kafka]
    Decisions (encrypted)      Audit log              Event bus
    Cases                      (immutable)
               │                                           │
               ▼                                           ▼
    [Case Management API]                        [Flink Pipeline]
    [Analyst Dashboard]                          [Feast Feature Store]
               │                                           │
               ▼                                      [Snowflake]
    [Analyst resolves case]                        ML training data
               │                                   (pseudonymised)
               ▼
    [Customer notified if declined]
    FCRA adverse action notice
    GDPR Art. 22(3) contestation right
```

**Data transfers outside EEA:**
- Processing in `us-east-1` (Virginia, USA) — Standard Contractual Clauses (SCCs) in place with AWS. Transfer Impact Assessment completed.
- Confluent Cloud (Kafka) — SCCs in place. Data residency: EU data processed in `eu-west-1` only (Kafka MirrorMaker2 replicates decisions, not raw transaction data).
- Snowflake — SCCs in place. EU customer data processed in Snowflake EU region only.

---

## 3. Necessity & Proportionality Assessment

### 3.1 Is the Processing Necessary?

| Processing Activity | Necessity Justification | Alternative Considered |
|---|---|---|
| Real-time ML scoring of every transaction | Fraud detection requires real-time evaluation — batch scoring would allow fraud to complete before detection | Batch scoring rejected — not fit for purpose |
| 47-feature model including behavioural history | High-accuracy fraud detection requires contextual features — fewer features reduce model performance by est. 34% AUC-PR (ablation study) | Minimal feature set evaluated — insufficient accuracy |
| Device fingerprinting | Device linkage is a primary fraud signal — 47% of fraud cases involve a new or shared device | Optional device fingerprinting rejected — reduces detection capability |
| 90-day retention of transaction data (hot) | Model retraining requires labelled outcome data; AML monitoring requires 90-day lookback | Shorter retention evaluated — insufficient for AML compliance |
| 7-year retention (cold — Snowflake) | BSA/AML legal obligation under 31 U.S.C. § 5318. GDPR Art. 17(3)(c) exempts this retention | Cannot be reduced — legal obligation |

### 3.2 Proportionality — Data Minimisation (Article 5(1)(c))

| Data Element | Collected | Purpose | Minimisation Applied |
|---|---|---|---|
| Full PAN | ❌ Never collected | N/A | Tokenised at merchant point of entry — RAS never sees raw PAN |
| CVV / CVC | ❌ Never collected | N/A | Rejected at Pydantic validation layer |
| Full IP address | ⚠️ Collected, then masked | Geolocation + proxy detection | Masked to /24 subnet after enrichment. Full IP not stored. |
| BIN (first 6 digits) | ✅ Collected | Card issuer identification | Only first 6 digits — not sufficient to reconstruct PAN |
| Last four digits | ✅ Collected | Transaction verification | Not sufficient to reconstruct PAN |
| Customer name | ❌ Not collected | N/A | Not required for risk scoring |
| Email address | ⚠️ Hash only | Email domain risk feature | SHA-256 hash of domain only — not reversible to full email |
| Date of birth | ❌ Not collected | N/A | Not required for risk scoring |

> *@priya:* "The full IP address is the only PII element where minimisation required architectural work. We collect the full IP for MaxMind geolocation and IPQualityScore proxy detection at enrichment time, then immediately replace it with a masked /24 subnet in the decision record stored to PostgreSQL and Cassandra. The full IP exists only in memory during the scoring request — it is never written to any persistent store. @sofia implemented this in the scoring pipeline as a mandatory data masking step."

---

## 4. Risk Assessment

### 4.1 Risk Identification

| Risk ID | Risk | Likelihood | Impact | Risk Level |
|---|---|---|---|---|
| R-001 | **Unfair automated decline** — legitimate customer incorrectly declined due to model bias or rule miscalibration | Medium | High | 🔴 HIGH |
| R-002 | **Profiling without awareness** — customer unaware that behavioural profiling underlies decline decisions | High | Medium | 🔴 HIGH |
| R-003 | **Data breach — scoring data** — unauthorised access to transaction history and risk profiles | Low | Very High | 🔴 HIGH |
| R-004 | **Feature leakage — sensitive proxies** — model inadvertently learns proxies for protected characteristics | Low | Very High | 🔴 HIGH |
| R-005 | **Excessive retention** — data retained beyond necessity | Low | Medium | 🟡 MEDIUM |
| R-006 | **Data subject rights failure** — erasure or access request not fulfilled within statutory deadline | Medium | High | 🔴 HIGH |
| R-007 | **Cross-border transfer risk** — US processing of EU data without adequate safeguards | Low | Very High | 🔴 HIGH |
| R-008 | **SAR confidentiality breach** — AML investigation details disclosed to data subject | Very Low | Very High | 🟡 MEDIUM |
| R-009 | **Model drift — degraded accuracy** — stale model produces systematically incorrect scores | Medium | High | 🔴 HIGH |
| R-010 | **Lack of meaningful human review** — case management process insufficient for Art. 22(3) | Low | Very High | 🔴 HIGH |

### 4.2 Risk Mitigation Measures

#### R-001: Unfair Automated Decline

| Control | Implementation | Residual Risk |
|---|---|---|
| Human review for all high-score declines | Case management system — every score > 600 creates a review case | Low |
| Fairness audit before model promotion | ECOA / Reg B disparate impact analysis — DIR threshold 0.80 | Low |
| FCRA adverse action notices | Top-4 SHAP features → plain-language reason codes | Low |
| Contestation right | GDPR Art. 22(3) — customer can request human review via case system | Low |
| Model recalibration | Analyst false-positive feedback → retraining pipeline | Low |

**Residual risk after controls: LOW**

#### R-002: Profiling Without Awareness

| Control | Implementation | Residual Risk |
|---|---|---|
| Privacy notice (Art. 13/14) | Published at merchant checkout — informs of automated scoring | Low |
| Transparency in decline notice | Adverse action notice explains that automated scoring was used | Low |
| Art. 22 rights disclosure | Customer informed of right to human review and contestation | Low |

**Residual risk after controls: LOW**

#### R-003: Data Breach — Scoring Data

| Control | Implementation | Residual Risk |
|---|---|---|
| Encryption at rest | AES-256-GCM + AWS KMS envelope encryption (ADR-003) | Low |
| Encryption in transit | TLS 1.3 (external) + Istio mTLS STRICT (internal) | Low |
| Access control | RBAC scopes + Vault dynamic credentials + NetworkPolicy default-deny | Low |
| Breach detection | Falco runtime monitoring + Prometheus anomaly alerts | Low |
| 72-hour breach notification | Incident response playbook — GDPR Art. 33 72-hour ICO notification | Low |

**Residual risk after controls: LOW**

#### R-004: Feature Leakage — Sensitive Proxies

| Control | Implementation | Residual Risk |
|---|---|---|
| Prohibited basis exclusion list | ZIP code, name, DOB, gender, race explicitly excluded from feature catalog | Low |
| Fairness audit (BISG proxy) | Post-hoc disparate impact measurement — never a model input | Low |
| Feature catalog review (@james) | Every new feature requires compliance review before Feast registration | Low |
| Leakage detection in training | Great Expectations validation + manual review of features with solo AUC > 0.85 | Low |

**Residual risk after controls: LOW**

#### R-005: Excessive Retention

| Control | Implementation | Residual Risk |
|---|---|---|
| Retention schedule | Cassandra TTL 90 days. Snowflake 7 years (AML legal obligation) | Low |
| Right-to-erasure endpoint | Pseudonymisation + data category exemption mapping (Art. 17(3)) | Low |
| Annual retention review | Scheduled Q4 — @james | Low |

**Residual risk after controls: LOW**

#### R-006: Data Subject Rights Failure

| Control | Implementation | Residual Risk |
|---|---|---|
| DSAR handling procedure | 30-day response SLA. Tracked in case management system | Medium |
| Erasure endpoint | `DELETE /v1/customers/{id}/data` — pseudonymisation + exemption mapping | Medium |
| Access endpoint | `GET /v1/customers/{id}/data` — returns all stored data in portable format | Medium |
| Rights register | All DSAR requests logged with receipt date and response date | Medium |

**Residual risk after controls: MEDIUM** — SLA adherence at scale (15M+ customers) requires automated tooling not yet built. Remediation: automated DSAR intake and response system — Q3 roadmap.

#### R-007: Cross-Border Transfer Risk

| Control | Implementation | Residual Risk |
|---|---|---|
| SCCs with AWS (US processing) | Standard Contractual Clauses — Module 2 (controller to processor) | Low |
| Transfer Impact Assessment | Completed for US, reviewed for APAC. EU-US data flows documented | Low |
| Data residency for EU data | EU customer data processed in `eu-west-1` only. MirrorMaker2 replication of decisions only (pseudonymised) | Low |
| Snowflake EU region | EU training data remains in Snowflake EU (Frankfurt) region | Low |

**Residual risk after controls: LOW**

#### R-008: SAR Confidentiality Breach

| Control | Implementation | Residual Risk |
|---|---|---|
| SAR segregation | SAR-related cases in separate Cassandra keyspace — not accessible via standard DSAR endpoint | Low |
| Access restriction | Compliance-only access to SAR keyspace. Standard `cases:read` scope cannot access | Low |
| Decline notice sanitisation | No reference to SAR in any customer-facing communication (@sofia — implemented) | Low |

**Residual risk after controls: LOW**

#### R-009: Model Drift — Degraded Accuracy

| Control | Implementation | Residual Risk |
|---|---|---|
| Evidently AI drift monitoring | PSI per feature, score distribution monitoring, calibration error | Low |
| Retraining triggers | Automated alerts → quarterly minimum retraining cycle | Low |
| Champion-challenger | New model validates against champion before production | Low |
| Fairness audit per promotion | DIR re-evaluated on every model version | Low |

**Residual risk after controls: LOW**

#### R-010: Insufficient Human Review (Art. 22(3))

| Control | Implementation | Residual Risk |
|---|---|---|
| Case management system | Every decline score > 600 creates a human review case | Low |
| SLA enforcement | P1: 2h, P2: 4h, P3: 24h. PagerDuty breach alerts | Low |
| Contestation endpoint | Customer can formally contest a decision via merchant portal | Low |
| Analyst training | All case reviewers trained on Art. 22(3) obligations | Low |
| GDPR Art. 22 notice | Decline notice informs customer of contestation right | Low |

**Residual risk after controls: LOW**

---

## 5. Overall Residual Risk Summary

| Risk | Pre-Mitigation | Post-Mitigation |
|---|---|---|
| R-001 Unfair automated decline | HIGH | ⏳ Planned |
| R-002 Profiling without awareness | HIGH | ⏳ Planned |
| R-003 Data breach | HIGH | ⏳ Planned |
| R-004 Feature leakage — proxies | HIGH | ⏳ Planned |
| R-005 Excessive retention | MEDIUM | ⏳ Planned |
| R-006 Data subject rights failure | HIGH | ⏳ Planned |
| R-007 Cross-border transfer | HIGH | ⏳ Planned |
| R-008 SAR confidentiality | MEDIUM | ⏳ Planned |
| R-009 Model drift | HIGH | ⏳ Planned |
| R-010 Insufficient human review | HIGH | ⏳ Planned |

**Overall residual risk: MEDIUM** (driven by R-006 — DSAR automation gap)

> *@james:* "One residual MEDIUM risk does not automatically trigger mandatory ICO prior consultation under Article 36. The ICO guidance (August 2018) states that prior consultation is required where residual risk is HIGH or where the controller cannot implement sufficient measures. R-006 is MEDIUM and has a defined remediation timeline (Q3). I am satisfied that prior ICO consultation is not required at this time, but I will re-assess if the DSAR automation is not delivered by Q3 or if transaction volume grows faster than projected."

---

## 6. Data Subject Rights Implementation

### 6.1 Right of Access (Article 15)

```
Endpoint:   GET /v1/customers/{customer_id}/data
Scope:      customer:data:read (requires identity verification)
Response:   All stored data for the customer:
              - Transaction history (90 days)
              - Risk scores and decisions
              - Case management records (excluding SAR-related)
              - Feature values used in scoring
SLA:        30 days (Art. 12(3))
Format:     JSON (machine-readable, portable)
```

### 6.2 Right to Erasure (Article 17)

```
Endpoint:   DELETE /v1/customers/{customer_id}/data
Scope:      customer:data:write

Processing:
  Step 1: Identify all data categories for customer_id
  Step 2: Apply Art. 17(3) exemptions:
            - Transaction records → retained (AML legal obligation, Art. 17(3)(b))
            - Fraud evidence → retained (legal claims, Art. 17(3)(e))
            - Risk scores → pseudonymised (PII replaced with hash)
  Step 3: Delete non-exempt PII fields:
            - PostgreSQL: UPDATE — replace name, email, device_id with hash
            - Cassandra: TTL-based expiry only (no DELETE) — exempt data retained
  Step 4: Log erasure action with exemptions applied
  Step 5: Respond within 30 days with:
            - Categories of data erased
            - Categories of data retained (with legal basis per category)
SLA:        30 days (Art. 12(3))
```

> *@sofia:* "The Cassandra append-only architecture creates a technical constraint for erasure: we cannot DELETE rows from Cassandra (INSERT-only service account — PCI DSS Req 10.3). For data subject erasure, we implement pseudonymisation: the customer_id in Cassandra is a UUID — we delete the mapping between that UUID and the customer's identity from PostgreSQL. The Cassandra records are retained (AML exemption) but are no longer linkable to the individual without the UUID mapping."

### 6.3 Right to Object to Automated Decision-Making (Article 22)

Per Article 22(3), data subjects have the right to:
1. Obtain human intervention
2. Express their point of view
3. Contest the automated decision

**Implementation:**

```
Trigger:    Any automated DECLINE decision
Notice:     Adverse action notice includes:
              - Statement that automated processing was used
              - Right to request human review
              - How to exercise the right (merchant portal)

Contest endpoint:   POST /v1/decisions/{request_id}/contest
Response:           Case created in case management system
                    Priority: P1 (2-hour SLA)
                    Analyst reviews full decision context
                    Customer notified of outcome

Documentation:      All contestation requests and outcomes logged
                    GDPR Art. 22(3) compliance evidence for QSA
```

### 6.4 Right to Portability (Article 20)

```
Endpoint:   GET /v1/customers/{customer_id}/data/export
Format:     JSON (machine-readable)
Contents:   All data provided by the data subject (transaction data)
            Does NOT include inferred data (risk scores, SHAP values)
            — inferred data is not subject to portability
SLA:        30 days
```

---

## 7. Consultation Record

| Stakeholder | Role | Input | Date |
|---|---|---|---|
| James Whitfield | CIPP/E, Head of Compliance | DPIA author and primary reviewer | Pre-development |
| Priya Nair | Principal Security Engineer | Security controls review — §4.2 | Pre-development |
| Marcus Chen | Chief Risk Architect | Data flow diagram review — §2.4 | Pre-development |
| Dr. Yuki Tanaka | Lead ML Scientist | Feature catalog and model fairness — §4.2 R-004 | Pre-development |
| Sofia Martínez | Senior Backend Engineer | Erasure implementation — §6.2 | Pre-development |
| External DPO | Qualified DPO (external) | Full DPIA review and sign-off | **Pending** |
| ICO Prior Consultation | UK Supervisory Authority | Not required — residual risk MEDIUM | N/A |

---

## 8. DPO Sign-off

```
DPIA Status:    DRAFT — pending external DPO sign-off

PRR Blocker:    B-003 — DPIA must be signed before production processing
                commences (GDPR Article 35(1))

Estimated sign-off date: Pre-development

Upon sign-off, this document will be updated to:
  status: Approved
  signed_by: [External DPO name]
  signed_at: [timestamp]
  next_review: 12 months from sign-off date

DPO Sign-off Block:
  ┌─────────────────────────────────────────────────────┐
  │  DPIA Approved                                      │
  │  Signed: ______________________________             │
  │  Title:  Data Protection Officer                   │
  │  Date:   ______________________________             │
  │  Next Review: ______________________________        │
  └─────────────────────────────────────────────────────┘
```

---

## 9. Review Schedule

| Review Trigger | Action |
|---|---|
| Annual scheduled review | Full DPIA re-assessment |
| New data category added | Section 2 + risk assessment update |
| New processing purpose | Full DPIA re-assessment |
| New cross-border transfer | Section 2.4 + R-007 update |
| Significant model change (new features, architecture) | Section 2.2 + R-004 update |
| Data breach incident | Section 4 risk re-assessment |
| New regulatory guidance from ICO/EDPB | Full review within 30 days |
| Transaction volume > 50M customers | Scale-up review (R-006 DSAR automation urgency) |

---

## 10. Related Documents

| Document | Location | Owner |
|---|---|---|
| Legitimate Interests Assessment | `docs/compliance/lia.md` | `@james` |
| Record of Processing Activities (ROPA) | `docs/compliance/ropa.md` | `@james` |
| Adverse Action Reason Codes | `docs/compliance/adverse_action_codes.md` | `@james` |
| Data Retention Schedule | `docs/compliance/retention_schedule.md` | `@james` |
| Vendor DPA Register | `docs/compliance/vendor_dpa_register.md` | `@james` |
| AML Programme Documentation | `docs/compliance/aml_programme.md` | `@james` |
| Threat Model (STRIDE) | `docs/security/threat_model.md` | `@priya` |
| Encryption Specification | `docs/security/encryption_spec.md` | `@priya` |
| Model Card | `docs/ml/model_card.md` | `@yuki` |
| Fairness Audit Report | `docs/ml/fairness_audit.md` | `@yuki` |
| PRR Checklist (§6 Compliance) | `docs/quality/prr_checklist.md` | `@aisha` |

---

*Document Version: 1.0.0*
*Owner: James Whitfield — Head of Risk & Compliance*
*Review Cycle: Annual · On material processing change*
*Classification: Internal — RESTRICTED — Legal Privilege*
*Distribution: DPO · CISO · Engineering leads · Supervisory authority on request*