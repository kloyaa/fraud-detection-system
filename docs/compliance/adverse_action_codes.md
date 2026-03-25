# Adverse Action Reason Code Library
## Risk Assessment System (RAS) — FCRA Section 615 Compliance

```yaml
document:       docs/compliance/adverse_action_codes.md
version:        1.0.0
owner:          James Whitfield (@james) — Head of Risk & Compliance
reviewers:      "@yuki · @sofia · @elena"
last_updated:   Pre-development
status:         ⏳ Planned
compliance:     FCRA §615 · ECOA / Reg B · GDPR Art. 22(3)
classification: Internal — Confidential — Legal Privilege
```

---

## 1. Legal Basis

### 1.1 FCRA Section 615

When RAS produces a DECLINE decision and that decision is based wholly or partly on information that functions as a consumer report, **FCRA Section 615(a)** requires:

1. Notification of the adverse action
2. The name, address, and phone of any consumer reporting agency whose data was used
3. The consumer's right to obtain a free copy of their report within 60 days
4. The consumer's right to dispute the accuracy or completeness of any information

**Reason codes are how RAS satisfies obligation #1** — they tell the consumer, in plain language, the principal reasons for the adverse action.

### 1.2 GDPR Article 22(3)

For EU data subjects, GDPR Art. 22(3) additionally requires:
- The right to obtain human intervention
- The right to express their point of view
- The right to contest the decision

Adverse action notices must include instructions for exercising these rights.

### 1.3 ECOA / Regulation B

Under ECOA, adverse action notices must state specific reasons. Vague or general statements ("does not meet our standards") are non-compliant. Reason codes must be specific enough for the applicant to understand what factors to address.

> *@james:* "A reason code of 'risk score too high' is not compliant. It tells the customer nothing actionable. FCRA and ECOA require the **specific factors** that most significantly contributed to the adverse action. That is exactly what SHAP values give us — the top-4 features that drove the decline score. Our job is to translate those feature names into plain-language reasons a consumer can understand and act on."

---

## 2. Code-to-Feature Mapping

Each code maps a Feast feature name (from `docs/ml/feature_catalog.md`) to a plain-language consumer notice. The top-4 SHAP features driving a DECLINE decision are mapped to codes AA01–AA15 using this table.

### 2.1 Primary Reason Codes (AA01–AA15)

| Code | Feature | Plain-Language Reason | Consumer Action |
|---|---|---|---|
| **AA01** | `device_first_seen` | Unrecognized or new device used for this transaction | Use a previously recognized device or contact support to register your new device |
| **AA02** | `txn_count_60s` | Unusually high number of transactions in a short period | Wait before attempting additional transactions |
| **AA03** | `amount_vs_avg_ratio` | Transaction amount is significantly higher than your recent transaction history | Contact your card issuer if this is a legitimate large purchase |
| **AA04** | `ip_proxy_score` | Transaction appears to originate from a proxy, VPN, or anonymizing network | Disable VPN or proxy and retry from your normal network |
| **AA05** | `device_account_count_7d` | Multiple accounts associated with this device in a short period | Contact support if this device is legitimately shared |
| **AA06** | `txn_amount_1h` | High total transaction volume in the past hour | Wait before attempting additional transactions |
| **AA07** | `linked_fraud_ring_score` | Activity associated with accounts linked to prior fraudulent activity | Contact support for account review |
| **AA08** | `ip_country_mismatch` | Transaction location does not match your card's country of issue | Contact your card issuer to confirm travel or location |
| **AA09** | `customer_age_days` | Insufficient account history to assess transaction risk | Build account history with smaller transactions over time |
| **AA10** | `merchant_fraud_rate_30d` | Elevated fraud activity recently detected at this merchant | Contact the merchant directly or use an alternative payment method |
| **AA11** | `txn_declined_24h` | Multiple declined transactions in the past 24 hours | Contact your card issuer or wait before retrying |
| **AA12** | `bin_country_mismatch` | Card-issuing country does not match the transaction location | Contact your card issuer to verify your card is enabled for this location |
| **AA13** | `distinct_merchants_24h` | Transactions at an unusually high number of merchants in a short period | Contact support if this activity is legitimate |
| **AA14** | `email_domain_risk` | Email address associated with elevated risk patterns | Contact support to verify your account email |
| **AA15** | `shared_device_accounts` | Device has been used by multiple accounts | Contact support if this device is legitimately shared |

### 2.2 Secondary Reason Codes (AA16–AA20)

Used when velocity or graph features dominate but a more specific primary code is not applicable.

| Code | Feature | Plain-Language Reason | Consumer Action |
|---|---|---|---|
| **AA16** | `txn_count_1h` | High transaction frequency in the past hour | Wait before attempting additional transactions |
| **AA17** | `chargeback_rate_90d` | Recent history of disputed transactions on your account | Contact your card issuer to resolve outstanding disputes |
| **AA18** | `ip_shared_accounts_1h` | Multiple accounts active from your network in a short period | Contact support if this activity is expected |
| **AA19** | `device_account_switches_7d` | Frequent account switching from this device | Contact support to verify account activity |
| **AA20** | `velocity_ratio_60s_30d` | Current transaction rate significantly exceeds your normal pattern | Wait and retry, or contact support |

---

## 3. Notice Generation Rules

### 3.1 Code Selection

```python
# app/services/adverse_action.py

from app.schemas.risk import RiskDecision
from app.compliance.adverse_action_codes import FEATURE_TO_CODE

FEATURE_TO_CODE: dict[str, str] = {
    "device_first_seen":          "AA01",
    "txn_count_60s":              "AA02",
    "amount_vs_avg_ratio":        "AA03",
    "ip_proxy_score":             "AA04",
    "device_account_count_7d":    "AA05",
    "txn_amount_1h":              "AA06",
    "linked_fraud_ring_score":    "AA07",
    "ip_country_mismatch":        "AA08",
    "customer_age_days":          "AA09",
    "merchant_fraud_rate_30d":    "AA10",
    "txn_declined_24h":           "AA11",
    "bin_country_mismatch":       "AA12",
    "distinct_merchants_24h":     "AA13",
    "email_domain_risk":          "AA14",
    "shared_device_accounts":     "AA15",
    "txn_count_1h":               "AA16",
    "chargeback_rate_90d":        "AA17",
    "ip_shared_accounts_1h":      "AA18",
    "device_account_switches_7d": "AA19",
    "velocity_ratio_60s_30d":     "AA20",
}

def get_adverse_action_codes(
    shap_top4: list[dict],   # [{feature: str, shap_value: float}, ...]
) -> list[str]:
    """
    Maps top-4 SHAP features to FCRA-compliant reason codes.
    Returns up to 4 codes, sorted by SHAP magnitude descending.
    Only includes features with positive SHAP values (risk-increasing).
    """
    codes = []
    for item in shap_top4:
        feature = item["feature"]
        shap    = item["shap_value"]
        if shap > 0 and feature in FEATURE_TO_CODE:
            codes.append(FEATURE_TO_CODE[feature])
    return codes[:4]   # Maximum 4 reason codes per FCRA guidance
```

### 3.2 Notice Delivery

| Channel | Trigger | SLA | Owner |
|---|---|---|---|
| In-API response | Any DECLINE decision | Synchronous | `@sofia` |
| Merchant webhook | Any DECLINE decision | < 5 seconds | `@sofia` |
| Consumer portal notice | Customer contest request | < 30 days | `@elena` |
| Written notice (post) | Customer written request | 30 days (FCRA §615) | `@james` |

### 3.3 Notice Template

```
Subject: Transaction Decision Notice

We were unable to complete your transaction at [merchant_name]
on [date] for [masked_amount].

Principal reasons for this decision:

  1. [AA01 plain-language text]
  2. [AA03 plain-language text]
  3. [AA08 plain-language text]
  4. [AA12 plain-language text]

You have the right to:
  • Request human review of this decision at [contest_url]
  • Obtain a free copy of any consumer report used within 60 days
  • Dispute the accuracy of information used in this decision

To request human review or for questions:
  [merchant_support_url] or [ras_support_email]

This decision was made by an automated system. You have the right
to request that a human review your case.
[GDPR Art. 22(3) — EU customers only]
```

---

## 4. Compliance Constraints

### 4.1 What Is Not Permitted

| Prohibited | Reason |
|---|---|
| "Does not meet our risk standards" | Too vague — FCRA requires specific factors |
| "High risk score" | Does not identify the specific reasons — non-compliant |
| Feature technical names (e.g., `txn_count_60s`) | Not plain language — consumer cannot understand |
| More than 4 reason codes | FCRA guidance limits to principal reasons — 4 maximum |
| Codes that reveal SAR investigation | 31 U.S.C. §5318(g)(2) — SAR confidentiality absolute |
| Protected class references | ECOA §202.9 — reason codes must not reference or imply protected class |

### 4.2 SAR Confidentiality

If a DECLINE is triggered by an AML rule (prefix `AML_*`) or the case is escalated to compliance:

```python
# Never disclose SAR-related reason — use generic code instead
if "AML_" in decision.rules_triggered or decision.sar_flagged:
    # Use generic reason code that does not reveal SAR investigation
    codes = ["AA02"]   # Generic velocity / risk reason
    # Do NOT include any AML or compliance-related explanation
```

### 4.3 Reason Code Audit Trail

Every adverse action notice is logged with:
- `request_id` — links to the scoring decision
- `codes_issued` — list of codes AA01–AA20
- `shap_values` — raw SHAP values that generated the codes
- `issued_at` — timestamp
- `channel` — how notice was delivered

Retained for 7 years (FCRA record-keeping requirement).

---

## 5. Code Review & Maintenance

### 5.1 When Codes Must Be Updated

| Trigger | Action | Owner |
|---|---|---|
| New feature added to model | Add corresponding reason code | `@james` + `@yuki` |
| Feature renamed in catalog | Update `FEATURE_TO_CODE` mapping | `@sofia` |
| Feature removed from model | Deprecate code — keep in registry (historical decisions) | `@james` |
| Regulatory guidance changes | Review all plain-language descriptions | `@james` |
| Model fairness audit (§3.2) | Confirm no code disproportionately affects protected group | `@james` + `@yuki` |

### 5.2 Annual Review

`@james` conducts an annual review of all reason codes against:
- Current CFPB adverse action guidance
- FCRA amendment history
- Fair lending examination findings at comparable institutions
- Internal false positive analysis (are codes misleading legitimate customers?)

---

## 6. Related Documents

| Document | Location |
|---|---|
| Feature Catalog | `docs/ml/feature_catalog.md` |
| Fairness Audit | `docs/ml/fairness_audit.md` |
| Model Card (SHAP) | `docs/ml/model_card.md` |
| GDPR DPIA (Art. 22) | `docs/compliance/gdpr_dpia.md` |
| SAR Procedure | `docs/compliance/sar_procedure.md` |
| Case Management (`/review`) | `.claude/commands/review.md` |

---

*Document Version: 1.0.0*
*Owner: James Whitfield — Head of Risk & Compliance*
*Review Cycle: Annual · On any model feature change*
*Classification: Internal — Confidential — Legal Privilege*