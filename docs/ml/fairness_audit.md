# Fairness Audit Report
## Risk Assessment System (RAS) — Model Bias & Disparate Impact Analysis

```yaml
document:       docs/ml/fairness_audit.md
version:        1.0.0
owner:          Dr. Yuki Tanaka (@yuki) — Lead ML / Risk Scientist
co-owner:       James Whitfield (@james) — Head of Risk & Compliance
reviewers:      "@priya · @aisha"
last_updated:   Pre-development
status:         ⏳ Planned — to be completed per model promotion
compliance:     ECOA / Regulation B · FCRA · SR 11-7 · GDPR Art. 22
classification: Internal — Confidential — Legal Privilege
```

---

## 1. Purpose & Legal Basis

This document records the fairness evaluation conducted before each model promotion to production. It demonstrates compliance with:

| Regulation | Obligation |
|---|---|
| **ECOA / Reg B** | Prohibits credit decisions with disparate impact on protected classes without business necessity justification |
| **FCRA §615** | Requires adverse action reason codes — model must be explainable per decision |
| **SR 11-7** | Federal Reserve model risk guidance — requires independent validation including bias assessment |
| **GDPR Art. 22** | Automated decision-making must not discriminate — fairness audit is part of the DPIA obligation |

> *@james:* "A fairness audit is not a box-checking exercise. It is a legal obligation under ECOA and a regulatory expectation under SR 11-7. If this audit identifies a DIR below 0.80 for any protected group, the model cannot be promoted to production until the finding is resolved — either by model remediation or by documented business necessity justification reviewed by legal counsel."

---

## 2. Methodology

### 2.1 Disparate Impact Ratio (DIR)

The primary fairness metric is the **Disparate Impact Ratio (DIR)** per EEOC Uniform Guidelines (29 CFR §1607):

```
DIR = (Adverse action rate for protected group) / (Adverse action rate for reference group)

Threshold:  DIR < 0.80 → Potential disparate impact — mandatory review
            DIR ≥ 0.80 → Acceptable — document and monitor
            DIR > 1.25 → Inverse disparity — also review
```

An "adverse action" in RAS context is a DECLINE decision (score > 600).

### 2.2 Protected Class Proxy Construction

Protected class attributes are **never model features**. They are reconstructed post-hoc for audit purposes only using:

| Protected Class | Proxy Method | Tool |
|---|---|---|
| Race / Ethnicity | Bayesian Improved Surname Geocoding (BISG) — ZIP code + surname | `surgeo` Python library |
| Gender | First name gender inference | `gender-guesser` library |
| National Origin | Surname + ZIP code | BISG |

> *@yuki:* "BISG proxies are probabilistic, not deterministic. They produce a probability distribution across racial/ethnic categories per individual — not a hard classification. We evaluate disparate impact at the group level using these probability weights, not by assigning individuals to categories. This is the standard methodology used by the CFPB and DOJ in fair lending examinations."

> *@priya:* "BISG proxy data is computed solely for audit purposes, held in memory during the audit run, and never written to any database, feature store, or log file. It is never used as a model input."

### 2.3 Evaluation Dataset

```
Dataset:        Held-out test set (temporal split — no training data)
Period:         Last 3 months of available labelled data
Min group size: 500 transactions per group (groups below threshold excluded from DIR)
Outcome:        DECLINE decision (score > 600)
```

### 2.4 Additional Metrics

Beyond DIR, the audit evaluates:

| Metric | Definition | Threshold |
|---|---|---|
| **Equal Opportunity** | True positive rate (fraud catch rate) equal across groups | Difference < 5 percentage points |
| **Predictive Parity** | Precision (PPV) equal across groups | Difference < 5 percentage points |
| **Calibration** | Predicted fraud probability matches actual rate per group | Max calibration error < 0.03 per group |

---

## 3. Audit Template — Per Model Version

> This section is completed for each model version before promotion. The first production audit will be conducted on the initial training run.

### 3.1 Model Information

```yaml
model_id:           xgb-fraud-scorer
version:            ⏳ To be completed at first training run
mlflow_run_id:      ⏳ Pending
training_period:    ⏳ Pending
test_period:        ⏳ Pending
audit_date:         ⏳ Pending
auditor:            Dr. Yuki Tanaka (@yuki)
compliance_review:  James Whitfield (@james)
```

### 3.2 Disparate Impact Results

```
⏳ To be completed at first model training run.

Target format:

Race / Ethnicity — Decline Rate & DIR
─────────────────────────────────────────────────────────────
Group                  Decline Rate    DIR vs. White    Status
─────────────────────────────────────────────────────────────
White (reference)      X.X%            1.00             ✅
Black / African Amer.  X.X%            X.XX             ⏳
Hispanic / Latino      X.X%            X.XX             ⏳
Asian                  X.X%            X.XX             ⏳
Other / Multiracial    X.X%            X.XX             ⏳

Gender — Decline Rate & DIR
─────────────────────────────────────────────────────────────
Group                  Decline Rate    DIR vs. Male     Status
─────────────────────────────────────────────────────────────
Male (reference)       X.X%            1.00             ✅
Female                 X.X%            X.XX             ⏳
```

### 3.3 Equal Opportunity Results

```
⏳ To be completed at first model training run.

True Positive Rate (Fraud Detection Rate) by Group:
  Max group difference target: < 5 percentage points
```

### 3.4 Calibration by Group

```
⏳ To be completed at first model training run.

Calibration Error by Group:
  Max calibration error target: < 0.03 per group
```

---

## 4. Finding Classification & Response Protocol

### 4.1 DIR Finding Classification

| DIR | Classification | Required Action |
|---|---|---|
| ≥ 0.80 | ✅ Acceptable | Document + quarterly monitoring |
| 0.75 – 0.79 | ⚠️ Borderline | Enhanced monitoring + @james review + model investigation |
| < 0.75 | 🔴 Disparate Impact | **Block promotion** — remediation or business necessity justification required |
| > 1.25 | ⚠️ Inverse Disparity | Investigate + document |

### 4.2 Business Necessity Justification Process

If DIR < 0.80, promotion is blocked unless business necessity is established:

```
Step 1: @yuki — Identify which features drive the disparity
        (SHAP contribution analysis per group)

Step 2: @yuki — Test feature removal/reweighting impact
        Can disparity be reduced without materially harming fraud detection?
        Document precision/recall trade-off.

Step 3: @james — Legal counsel review
        Is there a legitimate, fraud-risk-based justification for the disparity?
        Document in writing with supporting data.

Step 4: Decision:
        A) Remediate model → re-audit → promote if DIR ≥ 0.80
        B) Accept with justification → document + enhanced monitoring
           (requires CISO + Legal sign-off)
        C) Block model promotion → return to training
```

### 4.3 Known Risk Factors for Disparity

Based on feature analysis, the following features carry the highest risk of producing disparate impact and are monitored closely:

| Feature | Risk | Reason | Mitigation |
|---|---|---|---|
| `device_first_seen` | Medium | Lower device reuse rates in some demographics | Interaction term with `customer_age_days` in v3.3+ |
| `ip_country_mismatch` | Medium | Higher VPN usage + cross-border activity in some communities | Monitor PSI + DIR correlation |
| `ip_proxy_score` | Medium | Consumer VPN adoption increasing — not uniformly distributed | Model v3.3+ trained on more recent VPN data |
| `customer_age_days` | Low | Account tenure not person age — reviewed and approved | Annual re-confirmation of ECOA compliance |

---

## 5. Intersectional Analysis

In addition to single-axis group analysis, the audit evaluates intersectional subgroups (race × gender) with a minimum group size of 200 transactions.

```
⏳ To be completed at first model training run.

Intersectional DIR threshold: < 0.75 triggers mandatory review
(stricter than single-axis 0.80 due to compound disadvantage risk)
```

---

## 6. SHAP-Based Adverse Action Fairness

The top-4 SHAP features used for adverse action reason codes (FCRA §615) must not systematically differ by protected group in a way that reveals protected class membership.

```
⏳ To be completed at first model training run.

Evaluation: For each protected group, compute the frequency with which
each reason code (AA01–AA15) appears in the top-4 SHAP features.

Target: No reason code should appear > 2x more frequently for any
protected group vs. the reference group — this would suggest the
model is systematically using a proxy for protected class membership.
```

---

## 7. Promotion Gate

The fairness audit is a **hard promotion gate**. A model cannot move from `Staging` to `Production` in MLflow without:

```
[ ] All group DIRs ≥ 0.80 OR business necessity documented and signed
[ ] Equal opportunity difference < 5 percentage points across all groups
[ ] Calibration error < 0.03 per group
[ ] Intersectional DIR ≥ 0.75 for all subgroups ≥ 200 transactions
[ ] SHAP reason code distribution reviewed — no prohibited proxy signal
[ ] @james compliance sign-off (documented in this report)
[ ] @aisha PRR acknowledgement (model section)
```

**Sign-off:**
```
Fairness Audit Status:   ⏳ Pending first training run

ML Scientist:            Dr. Yuki Tanaka
Sign-off:                _________________ Date: _________

Compliance Review:       James Whitfield
Sign-off:                _________________ Date: _________
```

---

## 8. Ongoing Monitoring

Post-promotion, fairness metrics are monitored on a rolling basis:

| Check | Frequency | Tool | Alert |
|---|---|---|---|
| DIR per group | Monthly | Evidently AI + custom | DIR drops below 0.80 → P2 alert to `@yuki` + `@james` |
| Equal opportunity | Monthly | Evidently AI | > 5pp difference → review |
| SHAP reason code distribution | Per model retraining | Custom script | > 2x frequency disparity → review |
| Full re-audit | Per model promotion | This document | Mandatory — no exceptions |
| Annual independent validation | Annually | External party | SR 11-7 requirement |

---

## 9. Audit History

| Model Version | Audit Date | Overall Result | DIR Low | Action Taken |
|---|---|---|---|---|
| v1.0.0 (initial) | ⏳ Pending | ⏳ | ⏳ | ⏳ |

---

## 10. Related Documents

| Document | Location |
|---|---|
| Model Card | `docs/ml/model_card.md` |
| Feature Catalog | `docs/ml/feature_catalog.md` |
| Adverse Action Codes | `docs/compliance/adverse_action_codes.md` |
| GDPR DPIA (R-004) | `docs/compliance/gdpr_dpia.md` |
| Training Data Specification | `docs/ml/training_data_spec.md` |

---

*Document Version: 1.0.0*
*Owners: Dr. Yuki Tanaka (@yuki) · James Whitfield (@james)*
*Review Cycle: Per model promotion (mandatory) · Annual independent validation*
*Classification: Internal — Confidential — Legal Privilege*