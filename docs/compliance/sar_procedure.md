# Suspicious Activity Report (SAR) Procedure
## Risk Assessment System (RAS) — BSA / AML Compliance

```yaml
document:       docs/compliance/sar_procedure.md
version:        1.0.0
owner:          James Whitfield (@james) — Head of Risk & Compliance
reviewers:      "@priya · @marcus · @sofia"
last_updated:   Pre-development
status:         ⏳ Planned
compliance:     BSA 31 U.S.C. §5318(g) · FinCEN SAR Rule 31 CFR §1020.320
                4AMLD / 6AMLD (EU) · UK POCA 2002 §330
classification: Internal — RESTRICTED — Legal Privilege
distribution:   Compliance team · CISO · Legal counsel · MLRO only
```

> ⚠️ **Confidentiality Notice:** The existence of a SAR investigation or a filed SAR must never be disclosed to the subject of the report, their associates, or any other party not listed under Distribution above. Violation of SAR confidentiality is a federal criminal offence under 31 U.S.C. §5318(g)(2).

---

## 1. Legal Framework

### 1.1 Filing Obligations

| Jurisdiction | Law | Obligation | Deadline |
|---|---|---|---|
| United States | BSA / 31 CFR §1020.320 | File SAR when transaction involves ≥ $5,000 and we know, suspect, or have reason to suspect illegal activity | **30 days** from detection date |
| United States (extended) | BSA | Extension available if subject cannot be identified | **60 days** from detection date |
| United Kingdom | POCA 2002 §330 | Report to National Crime Agency (NCA) when suspicion arises — no minimum threshold | **As soon as practicable** |
| European Union | 4AMLD / 6AMLD | Report to Financial Intelligence Unit (FIU) — threshold varies by member state | **As soon as practicable** |

> *@james:* "The SAR clock starts from **detection** — not from when a human analyst reviews the case. If RAS's automated transaction monitoring flags a pattern at 14:09 on March 15, the 30-day window closes at 14:09 on April 14, regardless of when a human sees it. Every AML rule trigger in RAS must timestamp the detection event, not the review completion."

### 1.2 Tipping-Off Prohibition

Under 31 U.S.C. §5318(g)(2), it is unlawful to notify any person involved in a transaction that a SAR has been filed or is being considered. This applies absolutely — no exceptions for:
- Customer service responses
- Decline notices to the customer
- Merchant webhook payloads
- Data subject access requests (DSAR)
- Any API response or log accessible to the subject

---

## 2. SAR Trigger Rules

### 2.1 Automated AML Rules (RAS Rule Engine)

The following rule engine rules prefix `AML_` and trigger SAR investigation workflow automatically:

| Rule ID | Pattern | Threshold | SAR Priority |
|---|---|---|---|
| `AML_001` | Structuring — multiple transactions just below reporting threshold | 3+ txns < $10,000 within 48h, cumulative > $9,000 | High |
| `AML_002` | Round-dollar pattern | 5+ transactions with exact round-dollar amounts in 24h | Medium |
| `AML_003` | Rapid fund movement — in/out pattern | Deposit followed by withdrawal > 80% within 1h | High |
| `AML_004` | High-risk geography | Transaction involving FATF high-risk jurisdiction | Medium |
| `AML_005` | Unusual velocity + high amount | `txn_count_60s > 10` AND `txn_amount_1h > $50,000` | High |
| `AML_006` | Known typology match | Transaction pattern matches current FinCEN advisory | High |

### 2.2 Analyst-Initiated SAR

An analyst may initiate a SAR investigation at any time during case review by:
```
/review escalate <case_id> --to compliance --reason "AML indicator: <description>"
```

This immediately:
1. Locks the case from standard analyst access
2. Notifies `@james` via PagerDuty
3. Starts the SAR clock in the compliance tracking system
4. Applies SAR confidentiality protocol to all related records

---

## 3. SAR Investigation Workflow

```
AML Rule Trigger / Analyst Escalation
          │
          ▼
┌─────────────────────────────────────────────────────┐
│  STEP 1: Detection Timestamp Recorded               │
│  System logs detection_at (immutable — Cassandra)   │
│  30-day window opens                                │
│  Case status: SAR_INVESTIGATION                     │
│  Access: compliance scope only                      │
└─────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────┐
│  STEP 2: Evidence Preservation (Day 1–3)            │
│  @james collects:                                   │
│    - Transaction history (Cassandra audit log)      │
│    - Entity graph snapshot (Neo4j — @marcus)        │
│    - Kafka raw event export (@darius)               │
│    - Scoring decision + SHAP values                 │
│    - KYC / CIP records                              │
│  All evidence locked — no TTL override              │
└─────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────┐
│  STEP 3: Internal Investigation (Day 1–20)          │
│  @james reviews evidence + typology analysis        │
│  Consult legal counsel if needed                    │
│  Document investigation findings                   │
│  Decision: File SAR / No-File / Continue monitoring │
└─────────────────────────────────────────────────────┘
          │
     ┌────┴────┐
     ▼         ▼
  FILE SAR   NO-FILE
     │         │
     ▼         ▼
  Step 4   Document
           rationale
           Close case
```

### Step 4: SAR Filing (FinCEN — US)

```
Platform:   FinCEN BSA E-Filing System (https://bsaefiling.fincen.treas.gov)
Form:       FinCEN Form 114A (SAR)
Deadline:   Day 30 from detection_at (Day 60 with extension if subject unidentified)
Filed by:   @james (designated BSA Officer)

Required fields:
  Part I:   Subject information (if known)
  Part II:  Suspicious activity information
              - Date range of activity
              - Amount involved
              - Type of suspicious activity (checkbox)
              - Narrative description (free text — most important field)
  Part III: Financial institution information
  Part IV:  Contact information (BSA Officer)

Narrative requirements:
  - Who: Subject description (without revealing SAR to subject)
  - What: Specific transactions and amounts
  - When: Date range
  - Where: Geographic locations involved
  - Why: Why activity is suspicious (link to typology)
  - How: Method of suspicious activity
  Minimum length: 150 words
  Maximum length: No formal limit — be thorough
```

### Step 4 (UK): SAR Filing (NCA)

```
Platform:   National Crime Agency — SARs Online
Form:       Suspicious Activity Report
Deadline:   As soon as practicable (POCA §330 — no fixed days)
Filed by:   @james (designated MLRO)
Defence:    Filing provides 'consent defence' — protects from POCA §327/328 liability
```

---

## 4. Confidentiality Protocol

### 4.1 System-Level Controls

| Control | Implementation | Owner |
|---|---|---|
| SAR case segregation | SAR-flagged cases in separate Cassandra keyspace — inaccessible via standard `cases:read` scope | `@priya` / `@sofia` |
| DSAR exclusion | Right-to-access endpoint excludes SAR keyspace — GDPR Art. 17(3)(e) exemption applies | `@sofia` |
| Decline notice sanitisation | AML rule triggers replaced with generic reason code (AA02) in customer-facing notices | `@sofia` |
| Merchant webhook suppression | SAR-related case outcomes not included in merchant webhook payloads | `@sofia` |
| Log access restriction | SAR investigation logs accessible to `compliance` scope only | `@priya` |

### 4.2 Human Protocol

```
All personnel with SAR knowledge must:

  ✅ Treat SAR existence as strictly confidential
  ✅ Discuss only with: @james, legal counsel, CISO, FinCEN examiners
  ✅ Use encrypted channels for all SAR-related communication
  ✅ Log all access to SAR case materials

  ❌ Never mention SAR in any customer communication
  ❌ Never include SAR status in merchant-facing systems
  ❌ Never confirm or deny SAR existence if asked by subject or associates
  ❌ Never discuss SAR via unencrypted email or chat
```

---

## 5. Continuing SARs

If suspicious activity continues after initial filing, a **Continuing SAR** (also called a Supplemental SAR) must be filed:

| Trigger | Deadline |
|---|---|
| Suspicious activity continues for > 90 days after initial SAR | File continuing SAR within 120 days of initial SAR |
| New suspicious activity by same subject | File new SAR within 30 days |
| Law enforcement requests continued reporting | As directed |

---

## 6. Record-Keeping Requirements

Per 31 CFR §1020.320(d), all SAR-related records must be retained for **5 years** from the date of filing:

| Record | Retention | Storage |
|---|---|---|
| Filed SAR (copy) | 5 years | Encrypted compliance vault (`@james`) |
| Supporting documentation | 5 years | Encrypted compliance vault |
| Investigation notes | 5 years | Encrypted compliance vault |
| No-file decision rationale | 5 years | Encrypted compliance vault |
| Detection event log | 5 years | Cassandra SAR keyspace (separate from standard 90-day TTL) |

> *@darius:* "The Cassandra SAR keyspace has **no TTL** — records are retained indefinitely until manually archived to Snowflake cold storage after 5 years. The standard 90-day TTL that applies to the main `risk.events` table does not apply to SAR-flagged records. This is configured via a separate Cassandra table with `default_time_to_live = 0`."

---

## 7. Law Enforcement Requests

If law enforcement presents a subpoena, court order, or National Security Letter related to a SAR:

```
1. Immediately notify legal counsel and CISO
2. Do NOT acknowledge whether a SAR has been filed
   (SAR confidentiality applies even to law enforcement inquiries
    unless the request is specifically about the SAR itself)
3. Respond to the legal demand through proper legal channels only
4. Document all law enforcement contact in the compliance log
5. FinCEN notification may be required — @james determines
```

---

## 8. SAR Metrics & Oversight

`@james` reports the following to the CISO and Board Risk Committee quarterly:

| Metric | Description |
|---|---|
| SARs filed (count) | Total SARs filed in period |
| SARs by typology | Breakdown by AML rule trigger |
| Filing timeliness | % filed within 30-day window |
| No-file decisions | Count + rationale summary |
| Continuing SARs | Active continuing SAR count |
| Law enforcement requests | Count + nature |

---

## 9. Related Documents

| Document | Location |
|---|---|
| AML Programme | `docs/compliance/aml_programme.md` |
| Retention Schedule | `docs/compliance/retention_schedule.md` |
| GDPR DPIA (SAR exemptions) | `docs/compliance/gdpr_dpia.md` |
| Adverse Action Codes (SAR masking) | `docs/compliance/adverse_action_codes.md` |
| Security Incident Playbook | `docs/runbooks/security_incident.md` |
| Case Management (`/review escalate`) | `.claude/commands/review.md` |

---

*Document Version: 1.0.0*
*Owner: James Whitfield — Head of Risk & Compliance (designated BSA Officer / MLRO)*
*Review Cycle: Annual · On any BSA/AML regulatory change*
*Classification: Internal — RESTRICTED — Legal Privilege*
*Distribution: Compliance · CISO · Legal counsel · MLRO only*