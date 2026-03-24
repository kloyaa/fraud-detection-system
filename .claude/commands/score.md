# Command: /score
## Risk Scoring Pipeline — Development & Debugging Command

```yaml
command:        /score
file:           .claude/commands/score.md
version:        1.0.0
category:       Development · Debugging · Testing
primary_agent:  "@sofia (API layer) · @yuki (ML scoring) · @marcus (pipeline architecture)"
support_agents: "@priya (security validation) · @darius (infra/latency) · @aisha (test coverage)"
triggers:
  - /score
  - /score debug
  - /score trace <request_id>
  - /score test
  - /score benchmark
  - /score explain <request_id>
  - /score rules
  - /score simulate
```

---

## Purpose

The `/score` command is the primary development and debugging interface for the RAS scoring pipeline. It provides structured access to scoring request construction, pipeline tracing, rule engine inspection, ML score explanation, latency benchmarking, and test scenario simulation.

Use `/score` when you are:
- Building or debugging a scoring request payload
- Tracing why a specific transaction received a particular decision
- Inspecting which rules fired and in what order
- Understanding the ML model's contribution to a score
- Benchmarking scoring latency against SLA targets
- Generating test payloads for specific fraud scenarios

---

## Subcommands

### `/score` — Construct a Scoring Request

**Invocation:** `/score`

**Behaviour:** Interactively construct a valid `RiskScoreRequest` payload. Claude acts as `@sofia`, walking through each required field with validation guidance, then outputs a complete curl command and Python SDK call ready for execution.

**Output format:**
```
### Scoring Request Builder (@sofia)

Fields required: merchant_id, customer_id, session_id, amount, currency,
                 payment_method, device

[Interactive field construction with Pydantic v2 validation rules per field]

--- Generated Payload ---
{
  "idempotency_key": "<uuid>",
  "merchant_id": "...",
  ...
}

--- curl ---
curl -X POST https://api.ras.internal/v1/risk/score \
  -H "Authorization: Bearer $RAS_TOKEN" \
  -H "Idempotency-Key: $(uuidgen)" \
  -H "Content-Type: application/json" \
  -d '<payload>'

--- Python SDK ---
from ras_client import RASClient
client = RASClient(api_key=os.environ["RAS_API_KEY"])
decision = await client.score(request)
```

---

### `/score debug` — Full Pipeline Debug Mode

**Invocation:** `/score debug`

**Behaviour:** Activates verbose pipeline tracing for the next scoring request. Outputs the full decision trace including: enrichment result, feature extraction values, rule evaluation sequence, ML score components, and final decision assembly. Agents `@sofia`, `@yuki`, and `@marcus` each annotate their layer of the pipeline.

**Output format:**
```
### /score debug — Pipeline Trace

[1] ENRICHMENT LAYER (@sofia)
    IP Geolocation:       US / New York / AS14618 (AWS)
    IP Proxy Score:       0.12 (MaxMind)
    BIN Lookup:           Visa / US Issuer / Credit / Consumer
    Device Fingerprint:   fp_a1b2c3d4 — first seen: false (seen 14 days ago)
    Enrichment latency:   8ms

[2] FEATURE EXTRACTION (@yuki)
    txn_count_60s:        2         [normal — threshold: 5]
    txn_amount_1h:        $340.00   [normal — avg: $287]
    device_account_count: 1         [normal]
    ip_country_mismatch:  false
    bin_country_mismatch: false
    amount_vs_avg_ratio:  1.18      [normal — threshold: 10.0]
    Feature latency:      4ms (Feast Redis online store)

[3] RULE ENGINE (@marcus / @sofia)
    R001 Blocked Country:       SKIP  — US not in blocklist
    R002 Velocity Exceeded:     SKIP  — count=2, threshold=5
    R003 Amount Spike:          SKIP  — ratio=1.18, threshold=10.0
    R004 New Device High Value: SKIP  — device known (14 days)
    Rule outcome:               SCORE (pass to ML)
    Rule latency:               1ms

[4] ML SCORING (@yuki)
    XGBoost fraud score:        187 / 1000
    Behavioral embedding sim:   0.91 (high similarity to known-good patterns)
    Device risk score:          142 / 1000
    Ensemble score:             172 / 1000
    ML latency:                 18ms (BentoML adaptive batch)

[5] POST-ML OVERLAY (@marcus)
    Score 172 < 200 → APPROVE
    Requires review: false
    Challenge type:  none

[6] DECISION ASSEMBLY (@sofia)
    request_id:      rsk_01HNQZ8T...
    score:           172
    decision:        approve
    processing_ms:   34ms   ✅ within P50 target (35ms)

TOTAL PIPELINE LATENCY: 34ms
SLA STATUS: ✅ P50 (35ms) ✅ P95 (100ms)
```

---

### `/score trace <request_id>` — Historical Decision Trace

**Invocation:** `/score trace rsk_01HNQZ8T...`

**Behaviour:** Retrieves a historical scoring decision from the Cassandra event log and reconstructs the full pipeline trace. Useful for debugging merchant disputes, analyst case review, and regulatory inquiries. Invokes `@sofia` (API retrieval), `@yuki` (feature reconstruction), and `@james` (compliance context if flagged).

**Data sources:**
- Cassandra `risk.events` — raw decision event
- PostgreSQL `risk_decisions` — structured decision record
- Feast offline store — feature values at decision time (point-in-time correct)
- MLflow — model version and SHAP values at inference time

**Output format:**
```
### /score trace rsk_01HNQZ8T... — Historical Decision

DECISION RECORD
  request_id:       rsk_01HNQZ8T...
  timestamp:        2024-03-15T14:23:07.441Z
  merchant_id:      merch_9921
  customer_id:      cust_448821
  amount:           $1,240.00
  currency:         USD
  score:            634
  decision:         challenge
  challenge_type:   3ds
  processing_ms:    67ms
  model_version:    xgb-fraud-v3.2.1

RULES TRIGGERED
  R004 NEW_DEVICE_HIGH_VALUE  → CHALLENGE

FEATURE VALUES (point-in-time)
  [Feature values as stored at decision time via Feast offline store]

ML EXPLANATION (SHAP — @yuki)
  Top 4 contributors to score 634:
  1. device_first_seen = true        +287 pts  "New or unrecognized device"
  2. txn_count_60s = 8               +142 pts  "Elevated transaction velocity"
  3. amount_vs_avg_ratio = 4.3       +89 pts   "Amount significantly above average"
  4. ip_country_mismatch = true      +67 pts   "IP location differs from card country"

ADVERSE ACTION REASON CODES (@james)
  [If applicable — FCRA Section 615 compliant plain-language reasons]

CASE STATUS
  Case ID:    case_00291
  Status:     resolved
  Analyst:    sofia.m
  Decision:   approved (customer verified via 3DS)
  Resolved:   2024-03-15T14:25:12Z
```

---

### `/score test` — Run Scoring Test Suite

**Invocation:** `/score test [unit|integration|contract|all]`

**Behaviour:** Invokes `@aisha` to run the relevant test suite against the scoring pipeline and report coverage, failures, and gaps. Outputs a test run summary with direct links to failing tests and coverage gaps.

**Output format:**
```
### /score test — Test Suite Execution (@aisha)

Running: pytest tests/unit/test_scoring_service.py
         pytest tests/unit/test_rule_engine.py
         pytest tests/integration/test_scoring_api.py
         pytest tests/contract/provider/verify_scoring_provider.py

RESULTS
  Unit tests:        147 passed / 3 failed / 2 skipped
  Integration tests:  34 passed / 1 failed
  Contract tests:     12 passed / 0 failed

FAILURES
  ❌ tests/unit/test_rule_engine.py::test_rule_R003_amount_spike_zero_avg
     AssertionError: avg_txn_amount_30d = 0 should not trigger AMOUNT_SPIKE
     → Rule condition: `return avg > 0 and ctx["amount"] > avg * 10`
     → Test expected SCORE, got BLOCK. Bug: zero-division guard not in test.

COVERAGE GAPS (@aisha)
  app/engines/rule_engine.py     — 88% (missing: exception handler line 47)
  app/services/scoring_service.py — 82% (missing: ML fallback path lines 91–98)
  ⚠️  ML fallback path uncovered — HIGH RISK for PRR Section 1.2

RECOMMENDATION
  Fix failing tests before next PR merge.
  Cover ML fallback path (lines 91–98) — PRR blocker.
```

---

### `/score benchmark` — Latency Benchmark

**Invocation:** `/score benchmark [--tps <n>] [--duration <seconds>]`

**Behaviour:** Invokes `@darius` and `@aisha` to run a focused latency benchmark against the scoring endpoint. Reports P50/P95/P99 against SLA targets, highlights bottlenecks per pipeline stage, and flags any SLA breach.

**Output format:**
```
### /score benchmark — Latency Profile (@darius / @aisha)

Configuration:  500 TPS · 120 seconds · multi-class traffic model
Environment:    staging-us-east-1 · 5 scoring API pods · 3 BentoML replicas

LATENCY RESULTS
  P50:   31ms   ✅ target < 35ms
  P95:   88ms   ✅ target < 100ms
  P99:  198ms   ✅ target < 250ms
  P999: 412ms   ⚠️  no target defined — monitor

STAGE BREAKDOWN (median)
  Enrichment:       7ms
  Feature fetch:    4ms  (Feast Redis)
  Rule engine:      1ms
  ML inference:    16ms  (BentoML batch)
  DB write:         3ms  (Cassandra async)
  Total:           31ms

BOTTLENECK ANALYSIS (@darius)
  ML inference (16ms / 52% of total) — dominant stage.
  BentoML adaptive batching window: 1ms.
  Recommendation: evaluate increasing batch window to 2ms at higher TPS.

ERROR RATE: 0.02%  ✅ target < 0.1%
THROUGHPUT: 498 RPS actual vs 500 RPS target  ✅

SLA VERDICT: ✅ PASS — all targets met at 500 TPS
Next gate: run at 2x peak (1,000 TPS) for PRR Section 2 sign-off.
```

---

### `/score explain <request_id>` — ML Decision Explanation

**Invocation:** `/score explain rsk_01HNQZ8T...`

**Behaviour:** Invokes `@yuki` to generate a full SHAP-based explanation for a specific scoring decision. Outputs technical SHAP values for engineers plus plain-language adverse action reason codes compliant with FCRA Section 615 for compliance/legal use.

**Output format:**
```
### /score explain rsk_01HNQZ8T... — ML Explanation (@yuki)

MODEL: xgb-fraud-v3.2.1
BASE SCORE: 142 (population average fraud probability)
FINAL SCORE: 634

SHAP FEATURE CONTRIBUTIONS
  Feature                     Value        SHAP     Direction
  ─────────────────────────────────────────────────────────
  device_first_seen           true         +287     ↑ increases risk
  txn_count_60s               8            +142     ↑ increases risk
  amount_vs_avg_ratio         4.3          +89      ↑ increases risk
  ip_country_mismatch         true         +67      ↑ increases risk
  merchant_fraud_rate_30d     0.008        +31      ↑ increases risk
  customer_age_days           12           +28      ↑ increases risk
  bin_country_mismatch        false        -28      ↓ decreases risk
  email_domain_risk           0.11         -14      ↓ decreases risk
  card_present_flag           false        -12      ↓ decreases risk
  ─────────────────────────────────────────────────────────
  TOTAL SHAP DELTA:           +490 from base → score 634

FCRA ADVERSE ACTION REASON CODES (@james)
  (Plain-language — FCRA Section 615 compliant)

  Code  SHAP Rank  Reason
  ────  ─────────  ──────────────────────────────────────────────────
  AA01  1          Unrecognized or new device used for this transaction
  AA02  2          Higher than normal number of recent transactions
  AA03  3          Transaction amount significantly higher than your recent average
  AA04  4          Transaction location does not match card-issuing country

CALIBRATED FRAUD PROBABILITY: 0.63  (63% probability of fraud)
MODEL CALIBRATION: ✅ Platt-scaled, reliability diagram current
```

---

### `/score rules` — Rule Engine Inspector

**Invocation:** `/score rules [--active] [--triggered <request_id>] [--test <rule_id>]`

**Behaviour:** Invokes `@marcus` and `@sofia` to inspect the current production rule set. Lists all active rules with priority, action, and trigger rate. Optionally shows which rules fired for a specific request or runs a test evaluation against a synthetic payload.

**Output format:**
```
### /score rules — Rule Engine Inspector (@marcus)

ACTIVE RULES (8 rules, sorted by priority)

Pri  ID    Name                    Action     Trigger Rate  Last 24h
───  ────  ──────────────────────  ─────────  ────────────  ────────
1    R001  Blocked Country         BLOCK      0.02%         127
2    R002  Velocity Exceeded       BLOCK      0.08%         504
3    R010  Known Fraud Device      BLOCK      0.01%         63
4    R011  Consortium Block        BLOCK      0.03%         189
5    R003  Amount Spike            CHALLENGE  0.31%         1,958
6    R004  New Device High Value   CHALLENGE  1.24%         7,832
7    R012  Cross-Border High Value CHALLENGE  0.89%         5,621
8    R020  Low-Risk Merchant       ALLOW      12.4%         78,234

RULE ENGINE STATS (last 24h)
  Evaluations:  631,204
  BLOCK:        883    (0.14%)
  CHALLENGE:    15,411 (2.44%)
  ALLOW:        78,234 (12.4%)
  SCORE:        536,676 (85.0% → passed to ML)

PENDING RULE CHANGES
  R013 — "High-Risk BIN Country" — DRAFT — author: marcus — review: @priya
  R021 — "Trusted Merchant Bypass" — REVIEW — author: sofia — review: @james
```

---

### `/score simulate` — Fraud Scenario Simulator

**Invocation:** `/score simulate [scenario]`

**Available scenarios:**
- `velocity_attack` — simulates a velocity fraud pattern (rapid transactions)
- `account_takeover` — simulates ATO indicators (new device, changed behavior)
- `card_testing` — simulates card testing pattern (low-amount probes)
- `friendly_fraud` — simulates friendly fraud profile (legitimate customer behavior)
- `new_customer` — simulates a legitimate new customer first transaction
- `high_risk_merchant` — simulates transaction on a high-fraud-rate merchant
- `custom` — interactive payload builder for custom scenario

**Behaviour:** Invokes `@yuki` to generate a realistic synthetic transaction payload matching the requested fraud scenario, then runs it through the full scoring pipeline in debug mode. Useful for testing rule sensitivity, ML model response to known patterns, and building test fixtures for `@aisha`'s test suite.

**Output format:**
```
### /score simulate velocity_attack (@yuki)

SCENARIO: Velocity Attack
Description: Automated fraud tool submitting rapid low-value transactions
             on a small pool of customer IDs to stay under per-transaction
             detection thresholds.

SYNTHETIC PAYLOAD (transaction 6 of 8 in simulated sequence)
  customer_id:    cust_sim_0042      ← recycled from small pool
  amount:         $47.99             ← below typical velocity thresholds
  device:         fp_new_unknown     ← unrecognized fingerprint
  ip_address:     185.220.101.x      ← Tor exit node range
  txn_count_60s:  6                  ← exceeds R002 threshold of 5

PIPELINE RESULT
  Rule R002 VELOCITY_EXCEEDED:  BLOCK ✅ (correctly caught)
  Rule R001 BLOCKED_COUNTRY:    also triggered (Tor exit → blocked jurisdiction)
  Score: N/A (blocked pre-ML)
  Decision: BLOCK

SCENARIO ASSESSMENT (@yuki)
  ✅ Rule engine correctly intercepts this pattern before ML scoring
  ✅ R002 threshold of 5 txn/60s is well-calibrated for this scenario
  ⚠️  If attacker distributes across 3 customer IDs (2 txn each), R002 bypassed
  Recommendation: add R014 — shared device velocity (cross-customer, same device)

FIXTURE GENERATED
  Saved to: tests/unit/fixtures/velocity_attack_scenario.json
  Usage: factory_boy VelocityAttackFactory in tests/conftest.py
```

---

## Agent Dispatch Reference

| Subcommand | Primary Agent | Secondary Agents |
|---|---|---|
| `/score` | `@sofia` | — |
| `/score debug` | `@sofia`, `@marcus`, `@yuki` | `@darius` (latency) |
| `/score trace` | `@sofia`, `@yuki` | `@james` (if compliance flagged) |
| `/score test` | `@aisha` | `@sofia` (fix guidance) |
| `/score benchmark` | `@darius`, `@aisha` | `@yuki` (ML latency) |
| `/score explain` | `@yuki` | `@james` (FCRA codes) |
| `/score rules` | `@marcus` | `@sofia`, `@priya` |
| `/score simulate` | `@yuki` | `@aisha` (fixture generation) |

---

## Environment Configuration

```bash
# Required environment variables for /score commands
export RAS_API_KEY="rk_live_..."          # Merchant API key
export RAS_TOKEN="eyJ..."                 # JWT bearer token
export RAS_BASE_URL="https://api.ras.internal"
export RAS_ENV="staging"                  # staging | production

# Optional debug flags
export RAS_SCORE_VERBOSE=true            # Enable pipeline debug output
export RAS_SCORE_DRY_RUN=true            # Construct payload without submitting
```

---

## Related Commands

| Command | Description |
|---|---|
| `/review` | Case management — review, assign, and resolve flagged decisions |
| `/ppr` | Production Readiness Review — run full PRR checklist |

---

## Security Notes (@priya)

> ⚠️ `/score trace` retrieves records containing enriched customer data. Access requires `risk:read_all` scope. Do not run in environments where terminal output is logged to shared systems. Cassandra audit log access is controlled — any `/score trace` invocation is itself logged.

> ⚠️ `/score simulate` generates synthetic payloads that trigger real rule evaluations in staging. Do not use `RAS_ENV=production` with `/score simulate` — this will generate real scoring decisions against production data.

> ⚠️ SHAP values from `/score explain` contain feature-level detail that may be commercially sensitive. Do not share externally without compliance review from `@james`.

---

*Command File Version: 1.0.0*
*Project: Risk Assessment System*
*Classification: Internal — Engineering Confidential*