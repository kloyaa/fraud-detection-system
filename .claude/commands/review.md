# Command: /review
## Case Management & Analyst Review Command

```yaml
command:        /review
file:           .claude/commands/review.md
version:        1.0.0
category:       Case Management · Analyst Workflow · Compliance
primary_agent:  "@james (compliance context) · @yuki (ML explanation) · @sofia (API layer)"
support_agents: "@priya (security flags) · @marcus (pipeline context) · @aisha (test coverage)"
triggers:
  - /review
  - /review queue
  - /review case <case_id>
  - /review assign <case_id> <analyst>
  - /review resolve <case_id> <approve|decline>
  - /review escalate <case_id>
  - /review stats
  - /review rules
  - /review feedback <request_id> <outcome>
  - /review sla
auth_scope:     cases:read (queue, stats, sla) · cases:write (assign, resolve, escalate)
                cases:admin (rules, feedback batch)
```

---

## Purpose

The `/review` command is the analyst-facing interface for the RAS case management system. It provides structured access to the review queue, individual case investigation, analyst assignment, resolution workflows, SLA monitoring, and outcome feedback collection.

The case management system is the operational implementation of three regulatory obligations:

| Obligation | Regulation | Implementation |
|---|---|---|
| Human review of automated decisions | GDPR Article 22(3) | Case queue + analyst resolution |
| Adverse action contestability | FCRA Section 615 | Dispute workflow in `/review case` |
| AML investigator review | BSA / 4AMLD | Escalation path to compliance |

Use `/review` when you are:
- An analyst working the review queue
- A risk manager monitoring SLA compliance
- A compliance officer investigating a flagged transaction
- A developer testing the case management API
- An engineer debugging case creation or resolution logic

---

## Subcommands

### `/review queue` — Open Case Queue

**Invocation:** `/review queue [--status <open|in_review|all>] [--priority <p1|p2|p3>] [--merchant <id>] [--limit <n>]`

**Behaviour:** Invokes `@sofia` to query the case management API and renders the current analyst review queue. Cases are sorted by SLA deadline (ascending — most urgent first). Each case shows the decision summary, score, triggered rules, and SLA status. `@james` annotates any cases with compliance flags (SAR indicators, GDPR erasure requests, regulatory holds).

**Required scope:** `cases:read`

**Output format:**
```
### /review queue — Open Cases (@sofia / @james)

QUEUE SUMMARY
  Open:        47 cases
  In Review:   12 cases
  SLA Breached: 2 cases  ⚠️
  SLA < 1 hour: 8 cases  ⚠️

┌──────────────────┬──────────────┬────────┬───────────┬─────────────────┬──────────────┐
│ Case ID          │ Request ID   │ Score  │ Decision  │ SLA Deadline    │ Status       │
├──────────────────┼──────────────┼────────┼───────────┼─────────────────┼──────────────┤
│ case_00312  🔴   │ rsk_01HNQ... │ 847    │ decline   │ BREACHED +14min │ open         │
│ case_00309  🔴   │ rsk_01HNP... │ 782    │ decline   │ BREACHED +3min  │ open         │
│ case_00318  🟡   │ rsk_01HNR... │ 634    │ challenge │ 47 min          │ open         │
│ case_00301  🟡   │ rsk_01HNN... │ 712    │ decline   │ 1h 12min        │ in_review    │
│ case_00287  🟢   │ rsk_01HNK... │ 608    │ challenge │ 3h 44min        │ open         │
│ ...              │ ...          │ ...    │ ...       │ ...             │ ...          │
└──────────────────┴──────────────┴────────┴───────────┴─────────────────┴──────────────┘

⚠️  COMPLIANCE FLAGS (@james)
  case_00312 — AML indicator: txn pattern matches FinCEN Advisory FIN-2024-A001
               Requires compliance review before analyst resolution
               Do NOT contact customer — potential SAR obligation

  case_00301 — GDPR Article 22(3): customer has submitted contestation request
               Human review response required within 30 days of request date
               Contestation received: 2024-03-10 → deadline: 2024-04-09

ACTIONS
  Assign to self:  /review assign <case_id> <your_username>
  Open case:       /review case <case_id>
  SLA report:      /review sla
```

---

### `/review case <case_id>` — Full Case Investigation

**Invocation:** `/review case case_00318`

**Behaviour:** Opens a full case investigation view. All relevant agents contribute their domain perspective: `@sofia` provides the transaction and decision record, `@yuki` provides the SHAP ML explanation, `@james` provides the regulatory context and adverse action codes, `@priya` flags any security concerns, and `@marcus` provides pipeline context if relevant. The analyst sees everything they need to make an informed resolution decision in a single view.

**Required scope:** `cases:read`

**Output format:**
```
### /review case case_00318 — Full Investigation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CASE RECORD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Case ID:          case_00318
  Status:           open
  Priority:         P2
  SLA Deadline:     2024-03-15T16:10:00Z  (47 min remaining)  ⚠️
  Created:          2024-03-15T14:10:00Z
  Assigned To:      unassigned

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TRANSACTION RECORD (@sofia)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Request ID:       rsk_01HNR...
  Merchant:         merch_4421 (Acme Electronics)
  Customer:         cust_88234
  Session:          sess_x9k2m1
  Amount:           $1,240.00 USD
  Payment Method:   Visa ****4821 (US-issued, Consumer Credit)
  BIN:              424242 (Bank of America, US)
  Timestamp:        2024-03-15T14:09:51Z

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEVICE & NETWORK (@priya)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Device FP:        fp_a1b2c3d4 — FIRST SEEN  ⚠️
  IP Address:       [masked — analyst view only]
  IP Country:       US / Texas / Houston
  IP Proxy Score:   0.71  ⚠️  HIGH — possible VPN/proxy
  User Agent:       Chrome 122 / Windows 11
  Screen:           1920×1080 / UTC-6

  🔐 SECURITY NOTE (@priya):
  IP proxy score 0.71 is above the 0.6 alert threshold.
  This does not indicate fraud conclusively — legitimate
  corporate proxies and privacy VPNs produce similar scores.
  Consider in context of other signals.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RISK DECISION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Score:            634 / 1000
  Decision:         CHALLENGE (3DS)
  3DS Result:       PASSED ✅ (customer authenticated)
  Requires Review:  true — score > 600 post-challenge
  Rules Triggered:  R004 NEW_DEVICE_HIGH_VALUE
  Model Version:    xgb-fraud-v3.2.1
  Processing Time:  67ms

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ML EXPLANATION (@yuki)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Base score:       142 (population baseline)
  Final score:      634

  SHAP Contributions:
  ┌────────────────────────────┬──────────┬────────┬──────────────────────────┐
  │ Feature                    │ Value    │  SHAP  │ Direction                │
  ├────────────────────────────┼──────────┼────────┼──────────────────────────┤
  │ device_first_seen          │ true     │  +287  │ ↑ New device             │
  │ ip_proxy_score             │ 0.71     │  +142  │ ↑ Proxy/VPN detected     │
  │ amount_vs_avg_ratio        │ 4.3      │  +89   │ ↑ Above average spend    │
  │ txn_count_60s              │ 3        │  +31   │ ↑ Moderate velocity      │
  │ customer_age_days          │ 312      │  -28   │ ↓ Established customer   │
  │ merchant_fraud_rate_30d    │ 0.003    │  -21   │ ↓ Low-risk merchant      │
  │ bin_country_mismatch       │ false    │  -18   │ ↓ Card matches location  │
  └────────────────────────────┴──────────┴────────┴──────────────────────────┘

  MODEL NOTE (@yuki): 3DS authentication PASSED. Customer correctly entered
  the OTP sent to their registered mobile. This is a strong positive signal.
  Recommend: approve unless other investigation reveals contradicting evidence.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CUSTOMER HISTORY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Account age:      312 days
  Total txns:       47 (lifetime)
  Chargebacks:      0
  Prior declines:   1 (6 months ago — velocity, resolved)
  Avg txn amount:   $287
  Last txn:         2024-03-12 ($340, approved)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REGULATORY CONTEXT (@james)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  GDPR Article 22: ✅ Human review in progress (this case)
  FCRA Status:     No adverse action yet — challenge was issued
  AML Flag:        None
  SAR Obligation:  None at this time

  ADVERSE ACTION CODES (if declined):
    AA01 — Unrecognized or new device used for this transaction
    AA02 — Transaction originating from a proxy or VPN network
    AA03 — Transaction amount significantly higher than your recent average

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANALYST ACTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Assign to self:  /review assign case_00318 <your_username>
  Approve:         /review resolve case_00318 approve --note "<reason>"
  Decline:         /review resolve case_00318 decline --note "<reason>"
  Escalate:        /review escalate case_00318 --to compliance
  Request info:    /review resolve case_00318 request_info --note "<what>"
```

---

### `/review assign <case_id> <analyst>` — Assign Case

**Invocation:** `/review assign case_00318 sofia.m`

**Behaviour:** Assigns a case to the specified analyst, updates status to `in_review`, and records the assignment timestamp in the Cassandra audit log. If the case is within 30 minutes of SLA breach, `@james` emits a compliance warning. If the analyst has > 20 open cases, `@sofia` emits a capacity warning.

**Required scope:** `cases:write`

**Output format:**
```
### /review assign — Case Assigned (@sofia)

  case_00318  →  assigned to: sofia.m
  Status:         open → in_review
  SLA Deadline:   47 min remaining  ⚠️  Prioritise — SLA tight
  Assignment logged to audit trail: ✅

  Analyst queue for sofia.m: 8 open cases (within capacity)

  Next step: /review case case_00318
```

---

### `/review resolve <case_id> <decision>` — Resolve Case

**Invocation:**
- `/review resolve case_00318 approve --note "Customer passed 3DS. Device explained by new laptop purchase. Approved."`
- `/review resolve case_00318 decline --note "IP proxy score 0.71, new device, no satisfactory explanation. Declined."`

**Behaviour:** Records the analyst decision, closes the case, writes the resolution to PostgreSQL and the immutable Cassandra audit log, and triggers downstream actions. `@james` validates the resolution note meets regulatory minimum documentation standards. `@sofia` triggers the outcome webhook to the merchant. `@yuki` marks this case as a feedback label for the next model training cycle.

**Required scope:** `cases:write`

**Downstream actions on resolution:**

| Decision | Downstream Action |
|---|---|
| `approve` | Merchant notified via webhook · SHAP label `false_positive` added to training queue · Customer risk profile updated |
| `decline` | Merchant notified via webhook · FCRA adverse action notice queued (if applicable) · SHAP label `true_positive` added · Velocity counters maintained |
| `request_info` | Merchant notified to contact customer · Case SLA extended 24h · Status → `pending_info` |

**Output format:**
```
### /review resolve — Case Resolved (@sofia / @james / @yuki)

RESOLUTION RECORDED
  Case ID:          case_00318
  Analyst:          sofia.m
  Decision:         approve
  Note:             "Customer passed 3DS. Device explained by new laptop
                     purchase confirmed via customer service notes. Approved."
  Resolved At:      2024-03-15T15:58:22Z
  SLA Status:       ✅ Resolved within SLA (12 min remaining)

AUDIT TRAIL (@james)
  ✅ Decision logged to Cassandra (immutable)
  ✅ Resolution note meets minimum documentation standard
  ✅ GDPR Article 22(3) obligation satisfied — human review completed
  ✅ No FCRA adverse action required (approve decision)

DOWNSTREAM ACTIONS (@sofia)
  ✅ Merchant webhook sent: POST /webhooks/case_resolved
  ✅ Customer risk profile updated: false_positive flag added
  ✅ Training label queued: rsk_01HNR... → false_positive

MODEL FEEDBACK (@yuki)
  ✅ False positive label added to training queue
  ✅ SHAP feature `device_first_seen` flagged for threshold review
  ℹ️  This is the 47th false positive in 30 days where device_first_seen
     was the #1 SHAP contributor. Recommend: review R004 threshold with
     @marcus — new device alone may be over-weighted for established customers.

CASE CLOSED ✅
```

---

### `/review escalate <case_id>` — Escalate to Compliance

**Invocation:** `/review escalate case_00318 --to compliance --reason "Possible AML — transaction pattern matches typology"`

**Behaviour:** Escalates a case beyond normal analyst review to the compliance team. Invokes `@james` as primary agent. Triggers SAR investigation workflow if AML indicators are present. Locks the case from standard analyst modification. Records escalation in the immutable audit log.

**Required scope:** `cases:write`

**Escalation targets:**

| Target | Use Case | Notified Agent |
|---|---|---|
| `compliance` | AML/SAR indicators, regulatory inquiry | `@james` |
| `security` | Suspected fraud ring, data breach indicator | `@priya` |
| `senior_analyst` | Complex case requiring senior judgment | Team lead |
| `legal` | Legal hold, litigation indicator, subpoena | General Counsel |

**Output format:**
```
### /review escalate — Case Escalated (@james)

  Case ID:        case_00318
  Escalated to:   Compliance Team
  Reason:         "Possible AML — transaction pattern matches typology"
  Escalated by:   sofia.m
  Escalated at:   2024-03-15T15:12:04Z
  Case status:    locked — standard analyst resolution disabled

⚖️  COMPLIANCE INTAKE (@james)

  Escalation received. Initiating AML review protocol.

  IMMEDIATE ACTIONS:
  1. SAR clock assessment:
     - System detection timestamp: 2024-03-15T14:09:51Z
     - 30-day SAR window closes: 2024-04-14T14:09:51Z
     - Time remaining: 29 days, 22 hours

  2. SAR confidentiality protocol active:
     - Do NOT contact customer
     - Do NOT reference this escalation in any customer communication
     - Case locked from standard analyst access
     - Access restricted to: Compliance, Legal, MLRO

  3. Evidence preservation:
     - Cassandra event log: locked (no TTL override)
     - Kafka raw event: preserved to cold storage
     - Neo4j entity graph: snapshot queued

  NEXT STEP: @james to initiate internal investigation.
  Run: /review case case_00318 --compliance-mode
```

---

### `/review stats` — Queue Analytics & KPIs

**Invocation:** `/review stats [--period <24h|7d|30d>] [--merchant <id>]`

**Behaviour:** Invokes `@sofia` for data retrieval and `@james` for compliance KPI commentary. Provides operational metrics on queue health, SLA compliance, analyst throughput, decision distribution, and model feedback quality.

**Required scope:** `cases:read`

**Output format:**
```
### /review stats — Queue Analytics (Last 7 Days) (@sofia / @james)

VOLUME
  Total decisions:      631,204
  Cases created:        4,218   (0.67% of decisions)
  Cases resolved:       4,071
  Cases open (now):     147

SLA COMPLIANCE (@james)
  Resolved within SLA:  3,891 / 4,071  (95.6%)   ⚠️  target: 98%
  SLA breaches:         180             (4.4%)
  Avg resolution time:  1h 42min
  P95 resolution time:  3h 18min

  ⚠️  SLA compliance at 95.6% is below the 98% target.
  Primary cause: Monday volume spike (312 cases created, 14 analysts on shift).
  Recommendation: review on-call staffing model with EM for Monday coverage.

DECISION DISTRIBUTION
  Analyst Approvals:    2,841  (69.8%)
  Analyst Declines:      891   (21.9%)
  Escalated:             181   (4.4%)    → compliance: 89, security: 47, senior: 45
  Request Info:          158   (3.9%)

MODEL FEEDBACK (@yuki)
  True positives:        891   (analyst confirmed fraud — correct declines)
  False positives:        312  (analyst approved — model over-scored)
  False positive rate:   7.4%  ⚠️  target: < 5%

  ⚠️  False positive rate 7.4% exceeds 5% target.
  Top contributing feature to false positives: device_first_seen (+47 cases)
  Recommendation: @yuki to review R004 threshold and model feature weight.
  Training labels queued: 1,203 (will be included in next model training cycle)

TOP MERCHANTS BY CASE VOLUME
  merch_4421 (Acme Electronics):    312 cases  (7.4%)
  merch_0092 (GlobalShop):          287 cases  (6.8%)
  merch_7731 (TechMart):            201 cases  (4.8%)
```

---

### `/review rules` — Case Creation Rules

**Invocation:** `/review rules [--active] [--edit <rule_id>]`

**Behaviour:** Invokes `@marcus` to display and manage the rules that determine when a scored transaction is routed to the analyst review queue (as opposed to being auto-approved or auto-declined). These are distinct from the pre-ML rule engine — they govern post-decision case creation logic.

**Output format:**
```
### /review rules — Case Creation Rules (@marcus)

CASE CREATION TRIGGERS (evaluated after scoring decision)

  ID     Condition                              Action        Owner
  ────   ─────────────────────────────────────  ──────────    ──────
  CR001  score > 600 AND decision = challenge   create_case   @marcus
  CR002  score > 800                            create_case   @marcus
  CR003  rules_triggered CONTAINS 'AML_*'       escalate      @james
  CR004  merchant_fraud_rate_30d > 0.02         create_case   @marcus
  CR005  customer_age_days < 7 AND amount > 200 create_case   @marcus
  CR006  analyst_feedback = false_positive      retrain_flag  @yuki
  CR007  GDPR Article 22 contestation filed     create_case   @james

CASE SLA TARGETS
  P1 cases (score > 800):          2 hours
  P2 cases (score 600–800):        4 hours
  P3 cases (score < 600, flagged): 24 hours
  Compliance escalations:          Per @james protocol (SAR: 30 days)
```

---

### `/review feedback <request_id> <outcome>` — Submit Outcome Label

**Invocation:** `/review feedback rsk_01HNR... true_positive`
**Valid outcomes:** `true_positive` · `false_positive` · `true_negative` · `false_negative`

**Behaviour:** Submits an outcome label for a scoring decision. Used by analysts, merchant integrations, and chargeback workflows to feed ground truth back into the ML training pipeline. Invokes `@yuki` who assesses the label quality and queues it for the next training cycle.

**Required scope:** `cases:admin`

**Output format:**
```
### /review feedback — Outcome Label Submitted (@yuki)

  Request ID:    rsk_01HNR...
  Decision:      approve (score: 172)
  Outcome:       false_negative  ← transaction was actually fraud
  Source:        chargeback_webhook
  Submitted at:  2024-03-15T16:01:44Z

MODEL IMPACT (@yuki)
  ✅ Label queued for next training cycle
  Score 172 → outcome fraud: this is a hard negative for the model
  Feature review: amount_vs_avg_ratio=1.18 — within normal range, no signal
  Feature review: device_first_seen=false — known device used for fraud
     → Adding to known_fraud_device registry for R010 rule update

  PATTERN NOTE (@yuki):
  This is the 8th false negative in 30 days where a known device was used.
  Hypothesis: attacker has compromised a legitimate device.
  Recommendation: add device_compromise_score feature to next model version.
  Flagging for @marcus — may require a new rule R015 (device compromise indicator).
```

---

### `/review sla` — SLA Monitoring Dashboard

**Invocation:** `/review sla [--alert-threshold <minutes>]`

**Behaviour:** Invokes `@darius` for metrics data and `@james` for regulatory SLA obligations. Provides a real-time SLA health view across all open cases, alerts on impending breaches, and maps cases to their regulatory deadline obligations.

**Output format:**
```
### /review sla — SLA Monitor (@darius / @james)

LIVE SLA STATUS  (as of 2024-03-15T15:30:00Z)

  🔴 BREACHED        2 cases   (action required NOW)
  🟡 < 30 min        5 cases   (action required urgently)
  🟡 30 min – 2h    11 cases   (action required today)
  🟢 2h – 24h       94 cases   (on track)
  🟢 > 24h           35 cases  (comfortable)

BREACHED CASES — IMMEDIATE ACTION REQUIRED
  case_00312  (score: 847 · 14 min breached)  → unassigned  ← CRITICAL
  case_00309  (score: 782 · 3 min breached)   → unassigned  ← CRITICAL

REGULATORY DEADLINES (@james)
  GDPR Art 22(3) contestations:
    case_00301 — deadline: 2024-04-09 (25 days)    🟢
    case_00288 — deadline: 2024-03-22 (7 days)     🟡  Prioritise

  Compliance escalations (SAR window):
    case_00295 — SAR deadline: 2024-03-31 (16 days) 🟢
    case_00271 — SAR deadline: 2024-03-20 (5 days)  🟡  Prioritise — @james reviewing

INFRASTRUCTURE HEALTH (@darius)
  Case management API P95:  42ms   ✅
  PostgreSQL replication lag: 8ms  ✅
  Celery worker queue depth: 12    ✅
  PagerDuty alert (SLA breach): ACTIVE  🔴 — check your phone
```

---

## Agent Dispatch Reference

| Subcommand | Primary Agent | Secondary Agents |
|---|---|---|
| `/review queue` | `@sofia` | `@james` (compliance flags) |
| `/review case` | `@sofia`, `@yuki`, `@james` | `@priya` (security), `@marcus` (pipeline) |
| `/review assign` | `@sofia` | — |
| `/review resolve` | `@sofia`, `@james` | `@yuki` (feedback label) |
| `/review escalate` | `@james` | `@priya` (security escalations) |
| `/review stats` | `@sofia` | `@james` (compliance KPIs), `@yuki` (model KPIs) |
| `/review rules` | `@marcus` | `@james` (regulatory triggers) |
| `/review feedback` | `@yuki` | `@marcus` (rule updates) |
| `/review sla` | `@darius` | `@james` (regulatory deadlines) |

---

## Data Flow: Case Lifecycle

```
Transaction Scored (score > 600 OR rule CR001–CR007 triggered)
        │
        ▼
Case Created (PostgreSQL `cases` table)
  - decision_id linked
  - SLA deadline set (P1: 2h / P2: 4h / P3: 24h)
  - Event published to Kafka `cases.created`
        │
        ▼
/review queue  ←  Analyst picks up case
        │
        ▼
/review assign  →  Status: open → in_review
        │
        ▼
/review case    →  Full investigation view
        │
  ┌─────┴──────┐
  ▼            ▼
Resolve      Escalate
  │            │
  ▼            ▼
Closed      Compliance
  │          Protocol
  ▼
Feedback label → @yuki training queue
Webhook → Merchant
Audit log → Cassandra (immutable)
FCRA notice → Queued (if decline)
```

---

## Security & Compliance Notes

> ⚠️ **@priya:** `/review case` displays enriched customer data including masked IP and device fingerprint. This requires `cases:read` scope. All case access is logged to the Cassandra audit trail — PCI DSS Requirement 10.2.1(a) mandates logging of all access to cardholder data. Do not screenshot or export case data outside of approved tooling.

> ⚠️ **@james:** Cases with AML escalation (`CR003` trigger) are under SAR confidentiality from the moment of escalation. `31 U.S.C. § 5318(g)(2)` prohibits disclosure to any person that a SAR has been filed or may be filed. Any case marked `compliance_escalated` must not appear in standard merchant-facing reporting or customer data exports.

> ⚠️ **@james:** GDPR Article 22(3) contestation cases (`CR007` trigger) have a hard 30-day response deadline from the date of contestation, not the date of case creation. Monitor with `/review sla` — breach of this deadline is an ICO reportable event.

> ⚠️ **@priya:** `/review resolve decline` triggers the FCRA adverse action notice pipeline. Ensure the `--note` field contains substantive reasoning — it becomes part of the compliance evidence package. Notes of `"looks like fraud"` are not compliant. Minimum standard: reference the SHAP features, the analyst's investigation steps, and the conclusion.

---

## Environment Configuration

```bash
# Required environment variables for /review commands
export RAS_API_KEY="rk_live_..."
export RAS_TOKEN="eyJ..."                 # Requires cases:read or cases:write scope
export RAS_BASE_URL="https://api.ras.internal"
export RAS_ANALYST_ID="sofia.m"           # Set to your analyst username

# Compliance mode (unlocks escalated case access — requires cases:admin)
export RAS_COMPLIANCE_MODE=true
```

---

## Related Commands

| Command | Description |
|---|---|
| `/score trace <request_id>` | Full pipeline trace for the underlying scoring decision |
| `/score explain <request_id>` | Detailed SHAP explanation for a scoring decision |
| `/ppr` | Production Readiness Review — includes case management gates |

---

*Command File Version: 1.0.0*
*Project: Risk Assessment System*
*Classification: Internal — Engineering Confidential*