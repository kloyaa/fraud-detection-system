# Model Card
## XGBoost Fraud Scoring Model — Risk Assessment System (RAS)

```yaml
document:           docs/ml/model_card.md
model_id:           xgb-fraud-scorer
version:            v3.2.1 (champion) · v3.3.0-rc (challenger — shadow mode)
owner:              Dr. Yuki Tanaka (@yuki) — Lead ML / Risk Scientist
reviewers:          "@james (regulatory) · @priya (PII) · @aisha (PRR) · @marcus (pipeline)"
framework:          XGBoost 2.0
serving:            BentoML 1.3 (adaptive batching)
registry:           MLflow — Production stage
last_trained:       2024-02-28
last_evaluated:     2024-03-01
training_data:      2023-01-01 → 2024-01-31 (13 months)
status:             Production Champion
classification:     Internal — Confidential — Model Governance
regulatory_scope:   FCRA Section 615 · ECOA / Reg B · SR 11-7 · GDPR Article 22
```

---

## 1. Model Overview

### 1.1 Purpose

The XGBoost Fraud Scoring Model is a gradient-boosted classification model that produces a calibrated fraud probability score (0–1000) for every financial transaction evaluated by the Risk Assessment System. The score is the primary input to the automated approve / challenge / decline decision.

This model is a **regulated model** under:
- **FCRA Section 615** — adverse action reason codes are derived from this model's SHAP attributions
- **ECOA / Regulation B** — the model must not produce disparate impact on protected classes
- **Federal Reserve SR 11-7** — model risk management obligations: documentation, independent validation, ongoing monitoring
- **GDPR Article 22** — the model produces automated decisions with legal effects; human review rights apply

### 1.2 Model Summary

| Property | Value |
|---|---|
| **Model Type** | Gradient Boosted Decision Tree (XGBoost DART booster) |
| **Output** | Calibrated fraud probability → scaled to integer 0–1000 |
| **Input Features** | 47 features (see Feature Catalog §4) |
| **Training Period** | 2023-01-01 → 2024-01-31 (13 months, temporal split) |
| **Class Distribution** | 0.12% fraud (positive), 99.88% legitimate (negative) |
| **Class Weight** | `scale_pos_weight = 832` (negative/positive ratio) |
| **Calibration** | Platt scaling (isotonic regression validated equivalent) |
| **Ensemble Role** | Primary scorer (60% weight in ensemble) |
| **Decision Thresholds** | APPROVE < 200 · CHALLENGE 200–600 · DECLINE > 600 |
| **Latency (P95)** | 22ms (BentoML adaptive batch, batch window 1ms) |
| **Model Size** | 18.4 MB (serialized) |
| **Git Commit** | `a3f7c2d` |
| **Training Dataset Hash** | `sha256:9b8e1f...` |

---

## 2. Intended Use

### 2.1 Intended Use Cases

- Real-time fraud scoring of financial transactions at point-of-sale and e-commerce
- Input to automated approve / challenge / decline decisions
- Source of SHAP-based adverse action reason codes for FCRA compliance
- Input to human analyst review for challenged and declined transactions
- Training signal source for model iteration via analyst feedback labels

### 2.2 Out-of-Scope Use Cases

The following uses are **explicitly prohibited** without a separate model validation and compliance review:

| Prohibited Use | Reason |
|---|---|
| Credit underwriting decisions | Different regulatory framework (FCRA Section 604, ECOA) — this model is not validated for creditworthiness |
| Identity verification | Model does not evaluate identity — it evaluates transaction risk |
| Account-level risk scoring (KYC) | Transaction-level features are not appropriate for account-level risk |
| Real-time scoring of non-financial events | Model trained exclusively on transaction data — out-of-distribution |
| Any use where GDPR Article 9 (special category) data is involved | Model does not process and must not process special category data |

---

## 3. Performance Metrics

> *@yuki:* "Accuracy is not reported for this model. On a 0.12% fraud rate, a model predicting 'not fraud' for every transaction achieves 99.88% accuracy. This metric is meaningless. We evaluate on AUC-PR, KS Statistic, and calibration — the metrics that reflect production performance."

### 3.1 Holdout Evaluation (Test Set: 2024-02-01 → 2024-02-28)

| Metric | Value | Notes |
|---|---|---|
| **AUC-PR** | **0.847** | Primary metric. Holdout test set, temporal split. |
| **AUC-ROC** | 0.961 | Reported for completeness — not decision metric |
| **KS Statistic** | 0.71 | Maximum separation between fraud/legit score distributions |
| **Brier Score** | 0.0009 | Calibration quality (lower = better) |
| **Log Loss** | 0.0041 | — |

### 3.2 Operating Threshold Performance

| Threshold | Decision | Precision | Recall | F1 | FPR |
|---|---|---|---|---|---|
| Score < 200 | APPROVE | — | — | — | — |
| Score 200–600 | CHALLENGE | 0.31 | 0.78 | 0.44 | 4.2% |
| Score > 600 | DECLINE | 0.71 | 0.52 | 0.60 | 1.1% |
| **Combined** | All | **0.58** | **0.81** | **0.68** | **2.8%** |

**Threshold selection rationale (@yuki):**

> "The decline threshold of 600 was set by a joint review with the CFO and Head of Risk in Sprint 1. The cost matrix: a false positive (declined legitimate transaction) costs approximately $47 in lost revenue and customer churn risk. A false negative (approved fraud) costs approximately $280 in chargebacks and reputational damage. At threshold 600, the model operates at a 6:1 cost ratio that matches the business cost matrix. The challenge threshold of 200 was set conservatively — below 200, the model is highly confident in legitimacy. The 3DS friction of a challenge at 200–600 costs approximately $3 in conversion loss, which is acceptable given the risk profile."

### 3.3 Calibration

The model output is Platt-scaled to produce calibrated probabilities. The reliability diagram (actual vs. predicted fraud rate per decile) shows well-calibrated outputs across all score ranges.

```
Calibration (reliability diagram — test set):
Score Decile   Predicted P(fraud)   Actual P(fraud)   Calibration
0–100          0.001                0.001             ✅ excellent
100–200        0.008                0.009             ✅ excellent
200–300        0.021                0.023             ✅ good
300–400        0.058                0.061             ✅ good
400–500        0.142                0.139             ✅ excellent
500–600        0.341                0.328             ✅ good
600–700        0.581                0.573             ✅ good
700–800        0.762                0.748             ✅ good
800–900        0.891                0.882             ✅ good
900–1000       0.964                0.951             ✅ excellent

Maximum calibration error (MCE): 0.013  ✅ within acceptable range
```

### 3.4 Champion vs. Challenger Comparison

| Metric | Champion v3.2.1 | Challenger v3.3.0-rc | Delta |
|---|---|---|---|
| AUC-PR | 0.847 | 0.861 | +0.014 ✅ |
| KS Statistic | 0.71 | 0.73 | +0.02 ✅ |
| False Positive Rate | 2.8% | 2.4% | -0.4% ✅ |
| False Negative Rate | 19% | 17% | -2% ✅ |
| P95 Inference Latency | 22ms | 24ms | +2ms ⚠️ |
| Model Size | 18.4 MB | 21.2 MB | +2.8 MB |
| Shadow Mode Status | — | 36h (target: 48h) | ⏳ |

> *@yuki:* "v3.3.0-rc is materially better on AUC-PR and false positive rate. The +2ms P95 latency increase is within the stage budget (25ms allocated). I will promote once shadow mode reaches 48 hours and fairness audit clears. Promotion blocked until @aisha PRR sign-off and @james SHAP reason code review."

---

## 4. Feature Catalog

### 4.1 Feature Importance (SHAP — Top 20)

| Rank | Feature | SHAP (mean |value|) | Type | Feast Store |
|---|---|---|---|---|---|
| 1 | `device_first_seen` | 287.4 | Boolean | Redis (online) |
| 2 | `txn_count_60s` | 241.8 | Velocity | Redis (online) |
| 3 | `amount_vs_avg_ratio` | 198.3 | Derived | Real-time |
| 4 | `ip_proxy_score` | 167.2 | Enriched | Real-time |
| 5 | `device_account_count_7d` | 142.1 | Graph | Redis (online) |
| 6 | `txn_amount_1h` | 118.6 | Velocity | Redis (online) |
| 7 | `linked_fraud_ring_score` | 104.3 | Graph | Redis (online) |
| 8 | `ip_country_mismatch` | 98.7 | Derived | Real-time |
| 9 | `customer_age_days` | 87.4 | Historical | Redis (online) |
| 10 | `merchant_fraud_rate_30d` | 76.2 | Aggregated | Redis (online) |
| 11 | `txn_declined_24h` | 71.8 | Velocity | Redis (online) |
| 12 | `bin_country_mismatch` | 68.4 | Derived | Real-time |
| 13 | `distinct_merchants_24h` | 61.2 | Velocity | Redis (online) |
| 14 | `email_domain_risk` | 54.7 | Enriched | Real-time |
| 15 | `hour_of_day` | 48.3 | Temporal | Real-time |
| 16 | `shared_device_accounts` | 44.1 | Graph | Redis (online) |
| 17 | `card_present_flag` | 38.6 | Boolean | Real-time |
| 18 | `weekend_flag` | 31.2 | Temporal | Real-time |
| 19 | `shipping_billing_mismatch` | 28.4 | Derived | Real-time |
| 20 | `customer_avg_amount_30d` | 24.7 | Historical | Redis (online) |

### 4.2 Feature Engineering Notes

**`device_first_seen` (Rank 1 — highest SHAP):**
> *@yuki:* "This feature is the single strongest predictor of fraud in our dataset and also our highest-volume false positive source — 47 false positives in 30 days where a legitimate customer used a new device (new laptop, phone upgrade). The feature is correct: new devices are genuinely higher risk. But for established customers (age > 90 days, zero chargebacks), the risk is materially lower. v3.3.0-rc introduces a `device_first_seen_x_customer_tenure` interaction term that reduces false positives on this feature by an estimated 23% without reducing true positive rate."

**Leakage audit (@yuki):**
All features were audited for temporal leakage prior to training. The following features were considered and rejected:
- `chargeback_flag` — post-transaction outcome, not available at scoring time ❌
- `dispute_status` — post-transaction outcome ❌
- `auth_response_code` — set by the issuer after scoring, creates circular dependency ❌
- `settlement_amount` — not available at authorisation time ❌

### 4.3 Features Explicitly Excluded (ECOA / Reg B)

The following attributes are **never used as model features**, directly or as proxies, per ECOA Regulation B and internal fair lending policy:

| Attribute | Reason |
|---|---|
| Race / ethnicity | Prohibited basis (ECOA) |
| Gender / sex | Prohibited basis (ECOA) |
| National origin | Prohibited basis (ECOA) |
| Religion | Prohibited basis (ECOA) |
| Age (direct) | Prohibited basis (ECOA) — `customer_age_days` is account tenure, not person age |
| Marital status | Prohibited basis (ECOA) |
| ZIP code (direct) | Prohibited proxy — correlated with race/ethnicity |
| Name | Prohibited proxy — correlated with gender/national origin |

> *@james:* "The ZIP code exclusion is worth noting explicitly. ZIP codes are a well-documented proxy for race in US lending data. They are excluded as direct features. Geographic signals are captured via IP-country-mismatch and BIN-country-mismatch, which reflect behavioural anomaly rather than location demographics."

---

## 5. Training Data

### 5.1 Dataset Specification

| Property | Value |
|---|---|
| **Training period** | 2023-01-01 → 2024-01-31 (13 months) |
| **Validation period** | 2024-02-01 → 2024-02-14 (temporal, no shuffle) |
| **Test period** | 2024-02-15 → 2024-02-28 (temporal, no shuffle) |
| **Total records** | 847,241,088 transactions |
| **Positive class (fraud)** | 1,016,689 (0.12%) |
| **Negative class (legit)** | 846,224,399 (99.88%) |
| **Geographic coverage** | US (67%), EU (21%), APAC (8%), Other (4%) |
| **Merchant categories** | E-commerce (44%), In-person (31%), Marketplace (15%), Other (10%) |
| **Data source** | Snowflake data warehouse — `risk.training_transactions` |
| **Dataset hash** | `sha256:9b8e1f2c...` |

### 5.2 Label Definition

A transaction is labelled **fraud (positive class)** if any of the following occurred within 180 days of authorisation:

1. Chargeback filed with reason code indicating fraud (MC 4853, Visa 10.4, 10.5)
2. Merchant confirmed fraud via API feedback endpoint
3. Law enforcement referral linked to this transaction
4. SAR filed with FinCEN referencing this transaction ID

A transaction is labelled **legitimate (negative class)** if:
1. No chargeback or dispute filed within 180 days, AND
2. No fraud confirmation from merchant, AND
3. Customer account remains in good standing

**Selection bias note (@yuki):**
> "The training labels contain selection bias from the previous risk system's decisions. Transactions that were declined by the prior system are absent from the training data — we have no outcome labels for them. This is the classic 'reject inference' problem in credit and fraud modelling. We mitigate via: (1) including challenged transactions that were approved post-3DS (with their outcomes), (2) applying reject inference reweighting on a sample of historically declined transactions with subsequent manual review outcomes, (3) monitoring for distribution shift on the declined population in production. A full reject inference model is on the Q3 roadmap."

### 5.3 Data Preprocessing

```python
# Feature preprocessing pipeline
# app/ml/training/preprocessing.py

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler
from sklearn.impute import SimpleImputer

NUMERIC_FEATURES = [
    "txn_count_60s", "txn_amount_1h", "amount_vs_avg_ratio",
    "customer_age_days", "merchant_fraud_rate_30d", "ip_proxy_score",
    # ... 40 more features
]

BOOLEAN_FEATURES = [
    "device_first_seen", "ip_country_mismatch",
    "bin_country_mismatch", "card_present_flag",
    "weekend_flag", "shipping_billing_mismatch",
]

# Robust scaler handles outliers in transaction amounts
# (high-value transactions are legitimate but statistically extreme)
numeric_pipeline = Pipeline([
    ("impute",  SimpleImputer(strategy="median")),   # Feast miss → median
    ("scale",   RobustScaler()),                     # IQR-based — outlier robust
])

# Boolean features: no scaling, 0/1 integer encoding
# Missing boolean = False (conservative assumption)
```

---

## 6. Model Architecture

### 6.1 XGBoost Configuration

```python
# app/ml/training/train_fraud_scorer.py

import xgboost as xgb

MODEL_PARAMS = {
    # Booster
    "booster":              "dart",           # DART: Dropout Additive Regression Trees
    "n_estimators":         800,
    "max_depth":            7,
    "learning_rate":        0.05,
    "subsample":            0.8,
    "colsample_bytree":     0.7,

    # Class imbalance — core parameter
    "scale_pos_weight":     832,              # ~negative/positive ratio

    # DART-specific (dropout regularisation)
    "rate_drop":            0.1,
    "skip_drop":            0.5,

    # Regularisation
    "reg_alpha":            0.1,              # L1
    "reg_lambda":           1.0,              # L2
    "min_child_weight":     50,               # Prevents overfitting on rare fraud

    # Objective
    "objective":            "binary:logistic",
    "eval_metric":          ["aucpr", "logloss"],

    # Reproducibility
    "seed":                 42,
    "deterministic_histogram": True,

    # Hardware
    "device":               "cuda",           # GPU training (A10G)
    "tree_method":          "hist",
}

# Post-training calibration
from sklearn.calibration import CalibratedClassifierCV
calibrated_model = CalibratedClassifierCV(
    xgb_model, method="sigmoid", cv="prefit"
)
```

**Why DART booster (@yuki):**
> "Standard XGBoost with gradient boosting can overfit to specific fraud patterns that are well-represented in training data while underperforming on novel fraud typologies. DART (Dropout Additive Regression Trees — Rashmi & Gilad-Bachrach, 2015) applies dropout regularisation during boosting — each tree is randomly dropped with probability `rate_drop` during training. This forces the ensemble to not rely too heavily on any single tree, improving generalisation to unseen fraud patterns. At Affirm, switching from standard GBT to DART improved AUC-PR on out-of-time test data by 3.1 points."

### 6.2 Ensemble Architecture

```
Transaction Features (47 dimensions)
          │
          ├──► XGBoost Fraud Scorer    weight: 0.60  → score_xgb
          ├──► Behavioral Embedding    weight: 0.25  → score_behavioral
          └──► Device Risk LightGBM   weight: 0.15  → score_device
                          │
                          ▼
          Weighted Average Ensemble
          score_ensemble = 0.60 × score_xgb
                         + 0.25 × score_behavioral
                         + 0.15 × score_device
                          │
                          ▼
                  Scale to 0–1000 (integer)
                          │
                          ▼
                  Final Risk Score
```

**Ensemble weight rationale (@yuki):**
> "XGBoost receives the highest weight (0.60) because it performs best on the structured tabular features that dominate our feature set (velocity, amounts, geography). The behavioral embedding model (0.25) captures sequential patterns in a customer's transaction history — it performs particularly well on account takeover scenarios where transaction-level features look normal but the sequence is anomalous. The device risk model (0.15) is a lightweight LightGBM trained specifically on device and network signals — it adds signal on device-centric fraud patterns that XGBoost partially captures but doesn't specialise in."

---

## 7. Fairness & Bias Evaluation

> *@james:* "ECOA and Regulation B prohibit credit decisions that have a disparate impact on protected classes without a business necessity justification. Because RAS decline decisions affect access to services, we are required to evaluate the model for disparate impact before every promotion to production."

### 7.1 Disparate Impact Analysis (v3.2.1 — Test Set)

**Methodology:** Protected class proxies are constructed from ZIP code (Bayesian Improved Surname Geocoding — BISG for race/ethnicity proxy) and first name (gender proxy). These proxies are used exclusively for post-hoc audit — they are **never** model features.

**Disparate Impact Ratio (DIR):** Proportion of group receiving adverse action (score > 600) divided by the proportion in the reference group. DIR < 0.80 triggers mandatory review under the 80% rule (EEOC Uniform Guidelines).

| Protected Class | Group | Decline Rate | DIR vs. Reference | Status |
|---|---|---|---|---|
| Race/Ethnicity | White (reference) | 1.8% | 1.00 | ✅ |
| Race/Ethnicity | Black / African American | 2.1% | 0.86 | ✅ (above 0.80) |
| Race/Ethnicity | Hispanic / Latino | 2.3% | 0.78 | ⚠️ Review required |
| Race/Ethnicity | Asian | 1.6% | 1.13 | ✅ |
| Gender | Male (reference) | 1.9% | 1.00 | ✅ |
| Gender | Female | 1.7% | 1.12 | ✅ |
| Account Tenure | < 30 days | 8.4% | — | Higher risk — not a protected class |

**Hispanic / Latino DIR = 0.78 — Review Finding (@james):**

> "A DIR of 0.78 is below the 0.80 threshold, which triggers mandatory review under ECOA. After analysis, the elevated decline rate for this group is driven primarily by two features: `ip_country_mismatch` (higher rate of US-Hispanic customers transacting with VPNs routing through Latin American IPs) and `device_first_seen` (higher rate of new device usage correlated with smartphone upgrade cycles in this demographic).

> Both features have a clear, documented, and statistically validated fraud detection purpose — they are not proxies for national origin or ethnicity. The relationship is: this demographic exhibits specific behavioural patterns that correlate with features that also correlate with fraud risk. This is a legitimate business necessity justification under ECOA.

> Required actions: (1) document this analysis in the ROPA and the model card, (2) monitor DIR quarterly — if it crosses 0.75, we revisit the feature weights, (3) evaluate whether the `device_first_seen_x_customer_tenure` interaction term in v3.3.0-rc reduces this gap (preliminary analysis shows DIR improvement to 0.82)."

### 7.2 Intersectional Analysis

DIR was also evaluated for intersectional subgroups (race × gender). No subgroup showed DIR < 0.75. Full intersectional analysis available in `docs/ml/fairness_audit.md`.

---

## 8. FCRA Adverse Action Reason Codes

Per FCRA Section 615, when a transaction is declined, the top 4 SHAP features driving the decline are mapped to plain-language reason codes. These are the legally required adverse action reasons.

### 8.1 Reason Code Library

| Code | Feature | Plain-Language Reason |
|---|---|---|
| AA01 | `device_first_seen` | Unrecognized or new device used for this transaction |
| AA02 | `txn_count_60s` | Higher than normal number of recent transactions |
| AA03 | `amount_vs_avg_ratio` | Transaction amount significantly higher than your recent average |
| AA04 | `ip_proxy_score` | Transaction appearing to originate from a proxy or VPN network |
| AA05 | `device_account_count_7d` | Multiple accounts associated with this device |
| AA06 | `txn_amount_1h` | High transaction volume in a short period |
| AA07 | `linked_fraud_ring_score` | Activity associated with accounts linked to prior fraud |
| AA08 | `ip_country_mismatch` | Transaction location does not match card-issuing country |
| AA09 | `customer_age_days` | Insufficient account history to assess transaction risk |
| AA10 | `merchant_fraud_rate_30d` | Recent elevated fraud activity at this merchant |
| AA11 | `txn_declined_24h` | Multiple declined transactions in the past 24 hours |
| AA12 | `bin_country_mismatch` | Card-issuing country does not match transaction location |
| AA13 | `distinct_merchants_24h` | Transactions at an unusually high number of merchants |
| AA14 | `email_domain_risk` | Email address associated with elevated risk patterns |
| AA15 | `shared_device_accounts` | Device shared with multiple accounts |

**Implementation note (@sofia):**
> "The SHAP values from BentoML inference are sorted descending. The top 4 features are mapped to reason codes from this library. The `reasons` field in the `RiskDecision` response contains the AA codes for declined decisions. The case management system surfaces these codes in analyst review. The adverse action notice pipeline (Celery task) formats them into the legally required consumer notice."

---

## 9. Monitoring & Drift Detection

### 9.1 Production Monitoring Metrics

| Metric | Target | Alert Threshold | Tooling |
|---|---|---|---|
| Score distribution (mean) | 187 ± 20 | > ±40 shift over 24h | Evidently AI |
| Approve rate | 78.2% ± 3% | > ±5% shift over 24h | Prometheus |
| Challenge rate | 19.4% ± 2% | > ±4% shift over 24h | Prometheus |
| Decline rate | 2.4% ± 0.5% | > ±1% shift over 24h | Prometheus |
| False positive rate (feedback) | < 5% | > 7.5% over 7 days | MLflow |
| Feature drift (PSI) | < 0.1 per feature | > 0.2 on any top-10 feature | Evidently AI |
| Model calibration error | < 0.02 | > 0.05 | Evidently AI |
| P95 inference latency | < 25ms | > 35ms | Prometheus |

### 9.2 Population Stability Index (PSI) — Current

PSI measures the shift between training feature distributions and current production distributions. PSI > 0.2 on a key feature triggers model review.

| Feature | PSI (last 30 days) | Status |
|---|---|---|
| `txn_count_60s` | 0.04 | ✅ Stable |
| `amount_vs_avg_ratio` | 0.07 | ✅ Stable |
| `device_first_seen` | 0.11 | ✅ Stable |
| `ip_proxy_score` | 0.14 | ✅ Stable (monitoring) |
| `merchant_fraud_rate_30d` | 0.08 | ✅ Stable |
| `linked_fraud_ring_score` | 0.06 | ✅ Stable |

> *@yuki:* "`ip_proxy_score` PSI at 0.14 is elevated — the distribution is shifting toward higher proxy scores in production vs. training. This is consistent with increased consumer VPN adoption trends. It is not yet at the 0.20 alert threshold, but I am watching it. If it crosses 0.20, I will add more recent VPN-usage data to the next training run. v3.3.0-rc was trained on 2023-03-01 → 2024-02-28, which includes more recent VPN-adoption data — this likely accounts for part of the AUC-PR improvement."

### 9.3 Retraining Trigger Criteria

A model retraining is triggered when any of the following occurs:

| Trigger | Threshold | Action |
|---|---|---|
| AUC-PR degradation | Drop > 0.02 from champion baseline | Immediate retraining |
| False positive rate | > 7.5% sustained over 7 days | Retraining initiated |
| Feature PSI | > 0.20 on any top-10 feature | Retraining initiated |
| Score distribution shift | Mean shift > 40 points over 24h | Investigation + possible retraining |
| New fraud typology detected | Analyst-flagged pattern | Feature engineering + retraining |
| Scheduled retraining | Quarterly | Regardless of drift metrics |
| Regulatory change | New ECOA/FCRA guidance | Fairness audit + possible retraining |

---

## 10. Model Governance

### 10.1 Model Lifecycle

```
DATA COLLECTION
  Snowflake: risk.training_transactions
  Label definition: chargeback / merchant feedback / SAR (§5.1)
        │
        ▼
FEATURE ENGINEERING
  Feast offline store backfill (PySpark)
  Temporal split: train / val / test (no shuffle)
  Leakage audit on all features
        │
        ▼
TRAINING
  XGBoost DART (GPU — A10G)
  Hyperparameter tuning: Optuna (200 trials)
  Cross-validation: stratified K-fold (k=5, temporal blocks)
        │
        ▼
EVALUATION
  AUC-PR, KS, calibration on holdout test set
  Fairness audit: disparate impact analysis (BISG proxy)
  SHAP importance — top 20 features reviewed
  Leakage re-audit on final model
        │
        ▼
REGISTRATION
  MLflow: artifact + metrics + parameters logged
  Model card updated (this document)
  Dataset fingerprint recorded
        │
        ▼
STAGING
  BentoML staging deployment
  @aisha integration + contract tests
  @priya model artifact integrity check
        │
        ▼
CHAMPION-CHALLENGER (shadow mode ≥ 48h)
  Challenger serves 0% of traffic
  Challenger scores every request in shadow (no production effect)
  Score distribution comparison vs. champion
  Ground truth comparison as feedback labels arrive
        │
        ▼
PROMOTION GATES (all must pass)
  ✅  AUC-PR ≥ champion on holdout
  ✅  Shadow mode ≥ 48h at production volume
  ✅  Fairness audit: no group DIR < 0.80
  ✅  @james: SHAP reason code review
  ✅  @aisha: PRR sign-off (model section)
  ✅  @priya: model artifact hash verified
        │
        ▼
PRODUCTION (champion)
  BentoML production deployment
  Evidently AI monitoring active
  Quarterly retraining scheduled
        │
        ▼
DEPRECATION
  Champion replaced by new champion
  Model archived in MLflow (Archived stage)
  Minimum 2-year retention (SR 11-7)
  SHAP values retained for adverse action audit trail
```

### 10.2 Independent Validation (SR 11-7)

The Federal Reserve's SR 11-7 guidance requires independent model validation — validation by a party not involved in model development. The validation report for v3.2.1 was completed by the Risk Modelling Validation Team (independent of @yuki's team) on 2024-02-20.

**Validation findings:**

| Finding | Severity | Status |
|---|---|---|
| Training-serving feature parity confirmed (Feast) | ✅ No issue | Closed |
| Temporal split correctly implemented | ✅ No issue | Closed |
| DART booster parameters within reasonable range | ✅ No issue | Closed |
| Reject inference not implemented | ⚠️ Medium | Open — Q3 roadmap |
| Fairness audit methodology documented | ✅ No issue | Closed |
| Hispanic/Latino DIR requires monitoring | ⚠️ Medium | Open — quarterly monitoring |

### 10.3 Model Versioning Convention

```
xgb-fraud-scorer-v{MAJOR}.{MINOR}.{PATCH}

MAJOR: Breaking change — new feature set, new architecture, label redefinition
MINOR: Significant improvement — new features added, threshold recalibration
PATCH: Hotfix — hyperparameter adjustment, calibration update, bug fix

Current champion:   v3.2.1
Current challenger: v3.3.0-rc  (release candidate — not yet promoted)
```

---

## 11. Known Limitations

| Limitation | Impact | Mitigation |
|---|---|---|
| **Reject inference gap** | Model trained only on approved transactions — no outcome labels for prior declines. May over-score segments historically declined by prior system. | SR 11-7 finding open. Reject inference model on Q3 roadmap. |
| **New merchant cold start** | Merchants with < 30 days history have no `merchant_fraud_rate_30d`. Feature defaults to population median. | Compensated by device and velocity features. Monitored by merchant cohort analysis. |
| **Cross-border transactions** | Model trained on US-heavy data (67%). Performance on APAC transactions (8% of training) may be lower. | Regional model variants planned for Q4. EU model variant in evaluation. |
| **Fraud typology drift** | Novel fraud patterns not seen in training data will score lower than their true risk. | Evidently AI drift detection. Quarterly retraining. Analyst feedback loop. |
| **VPN adoption trend** | `ip_proxy_score` PSI at 0.14 — legitimate consumer VPN adoption increasing. False positive risk on privacy-conscious consumers. | v3.3.0-rc trained on more recent data — monitors this trend. |
| **Account takeover detection** | The behavioral embedding model handles ATO better than XGBoost, but the embedding is 25% weight in the ensemble. ATO may be under-scored relative to card-present fraud. | Behavioral embedding weight increase to 35% under evaluation in v3.4 design. |

---

## 12. Related Documents

| Document | Location | Owner |
|---|---|---|
| Feature Catalog (full) | `docs/ml/feature_catalog.md` | `@yuki` |
| ML Pipeline Architecture | `docs/ml/pipeline_architecture.md` | `@yuki` |
| Fairness Audit Report (v3.2.1) | `docs/ml/fairness_audit.md` | `@yuki` / `@james` |
| Training Data Specification | `docs/ml/training_data_spec.md` | `@yuki` |
| BentoML Service Definition | `ml/serving/fraud_scorer_service.py` | `@yuki` |
| Feast Feature Definitions | `ml/features/` | `@yuki` |
| Adverse Action Reason Code Library | `docs/compliance/adverse_action_codes.md` | `@james` |
| Independent Validation Report | `docs/ml/validation_report_v3.2.1.pdf` | Risk Modelling Validation Team |
| System Architecture Overview | `docs/architecture/system_overview.md` | `@marcus` |
| PRR Model Gates | `docs/quality/prr_checklist.md` | `@aisha` |

---

*Document Version: 1.0.0*
*Model: xgb-fraud-scorer v3.2.1*
*Owner: Dr. Yuki Tanaka — Lead ML / Risk Scientist*
*Review Cycle: Per model promotion · Quarterly scheduled*
*Classification: Internal — Confidential — Model Governance*
*Regulatory: FCRA Section 615 · ECOA / Reg B · SR 11-7 · GDPR Article 22*