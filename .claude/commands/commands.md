# Command: /ppr
## Production Readiness Review — Gated Deployment Command

```yaml
command:        /ppr
file:           .claude/commands/ppr.md
version:        1.0.0
category:       Quality · Deployment · Compliance · Governance
primary_agent:  "@aisha (PRR owner · go/no-go authority)"
support_agents: "@marcus · @priya · @yuki · @darius · @sofia · @james (all sections)"
triggers:
  - /ppr
  - /ppr run
  - /ppr run --section <1-6>
  - /ppr status
  - /ppr gate <section> <pass|fail|block> --evidence <url> --note "<text>"
  - /ppr sign-off
  - /ppr history
  - /ppr report
  - /ppr unblock <issue_id>
auth_scope:     ppr:read (status, history, report)
                ppr:write (gate, run sections)
                ppr:approve (sign-off — @aisha only)
```

---

## Purpose

The Production Readiness Review (`/ppr`) is the mandatory quality and compliance gate that every service must pass before deploying to production. It is owned exclusively by `@aisha` (Aisha Patel, Principal QA Engineer), who holds unconditional go/no-go authority.

The PRR is not a ceremony. It is a structured verification that the system behaves correctly, securely, reliably, and compliantly under the conditions it will actually face in production. Every checklist item represents either a failure mode that has caused a real incident at a previous company, or a regulatory obligation that carries legal liability.

**No deployment to production occurs without a PRR sign-off.**

### When a Full PRR Is Required

| Trigger | PRR Type |
|---|---|
| New service going to production | Full PRR (all 6 sections) |
| New external dependency added | Full PRR |
| New data category processed | Full PRR |
| Major feature (> 20% code change in critical paths) | Full PRR |
| Post-incident recovery | Full PRR |
| Routine deployment (< 20% change, no new deps) | Deployment Sub-Checklist only |
| Model promotion to production | Model PRR (Sections 1, 2, 4, 6) |
| Infrastructure change only | Infra PRR (Sections 2, 3, 5) |

---

## Subcommands

### `/ppr` or `/ppr status` — Current PRR Status

**Invocation:** `/ppr` or `/ppr status`

**Behaviour:** `@aisha` renders the current PRR status across all 6 sections. Shows each gate's pass/fail/blocked state, evidence links, blockers, and the overall go/no-go verdict. All agents annotate their owned sections.

**Output format:**
```
### /ppr status — Production Readiness Review (@aisha)

SERVICE:  ras-scoring-api
VERSION:  1.0.0-rc.3
TARGET:   production
PRR OWNER: Aisha Patel (@aisha)
STARTED:   2024-03-10
UPDATED:   2024-03-15T15:30:00Z

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OVERALL VERDICT:  ⛔ NO-GO  (3 sections blocked)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SECTION SUMMARY

  §1 Code Quality        ⚠️  IN PROGRESS  (8/10 gates passed)
  §2 Performance         ✅  PASS         (9/9 gates passed)
  §3 Reliability/Chaos   ⛔  BLOCKED      (ISS-005 — Cassandra chaos gate)
  §4 Security            ⛔  BLOCKED      (pentest not yet completed)
  §5 Observability       ⚠️  IN PROGRESS  (6/7 gates passed)
  §6 Compliance          ⛔  BLOCKED      (GDPR DPIA not completed)

BLOCKERS  (must be resolved before sign-off)

  🔴 B-001  §3.4  Cassandra node failure chaos experiment not run
            Owner:    @darius
            Blocks:   ISS-005 — Cassandra runbook missing
            ETA:      Sprint 4 (2 weeks)
            Action:   /ppr unblock B-001 once ISS-005 resolved

  🔴 B-002  §4.2  External penetration test not completed
            Owner:    @priya
            Blocks:   §4 Security sign-off
            ETA:      Q2 (pentest vendor booked)
            Action:   /ppr gate 4 pass --evidence <pentest_report_url>

  🔴 B-003  §6.4  GDPR Data Protection Impact Assessment not completed
            Owner:    @james
            Blocks:   §6 Compliance sign-off
            ETA:      Sprint 4
            Action:   /ppr gate 6 pass --evidence <dpia_doc_url>

OPEN ITEMS  (not blocking — must be resolved before conditional GO expires)

  🟡 O-001  §1.2  Branch coverage on ML fallback path: 72% (target: 85%)
            Owner:    @sofia
            Action:   Cover lines 91–98 in scoring_service.py

  🟡 O-002  §5.1  Missing runbook: Cassandra node failure alert
            Owner:    @darius
            Note:     Linked to B-001 — resolves together

PASSED GATES: 23 / 37  (62%)
BLOCKED GATES: 3
OPEN GATES: 11

ESTIMATED READINESS DATE: Sprint 4 completion (~2 weeks)
```

---

### `/ppr run` — Execute PRR Section

**Invocation:** `/ppr run` (all sections) or `/ppr run --section 1`

**Behaviour:** `@aisha` orchestrates a full or partial PRR execution. Each section invokes its owning agent to collect evidence, run automated checks, and report results. Automated checks (test coverage, lint, Trivy scan, contract tests) are run live. Manual checks (pentest, chaos experiments) are verified by evidence URL. Results are written to the PRR evidence repository.

---

#### Section 1 — Code Quality (@sofia / @aisha)

```
### /ppr run --section 1 — Code Quality (@aisha / @sofia)

Running automated quality checks...

  [1.1] Unit test coverage ≥ 90%
        Running: pytest tests/unit/ --cov=app --cov-report=xml
        Result:  91.3% line coverage  ✅
        Report:  https://codecov.io/gh/org/ras/reports/main

  [1.2] Branch coverage ≥ 85% on critical paths
        Running: coverage report --include=app/engines/* app/services/*
        Result:  scoring_service.py: 72%  ❌  (target: 85%)
                 rule_engine.py: 89%       ✅
                 idempotency.py: 94%       ✅
        Gap:     Lines 91–98 (ML fallback path) — uncovered
        Action:  @sofia — add tests for BentoML 503 fallback path

  [1.3] Mutation score ≥ 70%
        Running: mutmut run --paths-to-mutate app/engines/
        Result:  74.2%  ✅
        Report:  ./mutation_report.html

  [1.4] Integration tests passing
        Running: pytest tests/integration/ --tb=short
        Result:  35 passed / 0 failed  ✅

  [1.5] Contract tests passing
        Running: pact-verifier --provider ras-scoring-api
        Result:  12 contracts verified  ✅
        Broker:  https://pactflow.io/org/ras

  [1.6] Ruff: zero lint errors
        Running: ruff check app/
        Result:  0 errors  ✅

  [1.7] mypy strict: zero type errors
        Running: mypy app/ --strict
        Result:  0 errors  ✅

  [1.8] Bandit: zero HIGH/CRITICAL
        Running: bandit -r app/ -ll
        Result:  0 HIGH  0 CRITICAL  ✅  (3 LOW — documented)

  [1.9] Semgrep: zero security findings
        Running: semgrep --config=p/python app/
        Result:  0 findings  ✅

  [1.10] Alembic migrations have rollback
        Checking: all migrations have downgrade() defined
        Result:  9/9 migrations have downgrade()  ✅

SECTION 1 RESULT:  ⚠️  IN PROGRESS — gate 1.2 open
OWNER COMMENT (@aisha):
  "91.3% line coverage passes the floor. Gate 1.2 stays open until the ML
  fallback path (lines 91–98) is covered. This is the code path that runs
  when BentoML returns a 503 — exactly the path that will be exercised
  during the Section 3 chaos experiment. Cover it before chaos runs."
```

---

#### Section 2 — Performance (@aisha / @darius)

```
### /ppr run --section 2 — Performance (@aisha / @darius)

Running load test: 2x peak traffic (1,000 TPS) · 30 min soak · multi-class

  [2.1] P50 latency < 35ms at 2x peak
        Result:  P50 = 31ms  ✅

  [2.2] P95 latency < 100ms at 2x peak
        Result:  P95 = 88ms  ✅

  [2.3] P99 latency < 250ms at 2x peak
        Result:  P99 = 204ms  ✅

  [2.4] Error rate < 0.1% at 2x peak
        Result:  0.02%  ✅

  [2.5] PgBouncer pool not exhausted
        Peak pool utilisation: 73%  ✅  (ISS-002 resolved — pool_size=15)
        Evidence: https://grafana.ras.internal/d/pgbouncer/sprint-3-load-test

  [2.6] Redis connection pool stable
        Peak pool utilisation: 41%  ✅

  [2.7] Kafka consumer lag < 500ms
        Peak lag: 187ms  ✅

  [2.8] BentoML P95 inference < 30ms
        Result: P95 = 22ms  ✅  (ISS-001 resolved — warmup implemented)

  [2.9] No memory leak over 30-min soak
        Memory delta over 30 min: +12MB (within acceptable range)  ✅
        Evidence: https://grafana.ras.internal/d/memory/soak-test

SECTION 2 RESULT:  ✅  PASS — all 9 gates passed
OWNER COMMENT (@aisha):
  "ISS-001 and ISS-002 both resolved before this section ran — good.
  P95 at 88ms gives us 12ms headroom against the 100ms SLO.
  Performance is solid. Section 2 is green."
```

---

#### Section 3 — Reliability & Chaos (@darius / @aisha)

```
### /ppr run --section 3 — Reliability & Chaos (@darius / @aisha)

  [3.1] ✅  ML service kill → rule fallback < 500ms
        Evidence: https://chaos.ras.internal/experiments/ml-kill-sprint2

  [3.2] ✅  Redis primary failure → fail open
        Evidence: https://chaos.ras.internal/experiments/redis-failover-sprint2

  [3.3] ✅  Kafka broker loss → lag < 30s
        Evidence: https://chaos.ras.internal/experiments/kafka-broker-sprint2

  [3.4] ⛔  BLOCKED — Cassandra node failure chaos experiment
        Blocker:  B-001 / ISS-005 — runbook missing
        Owner:    @darius
        Status:   Runbook authoring in Sprint 4

  [3.5] ⏳  BentoML OOM → circuit breaker opens
        Status:   Scheduled Sprint 4

  [3.6] ⏳  Rollback procedure documented AND executed
        Status:   Rollback tested in staging — evidence pending
        Owner:    @darius

  [3.7] ✅  Canary deployment tested in staging
        Evidence: https://argocd.ras.internal/rollouts/sprint-3-canary

  [3.8] ✅  HPA scale-up verified under load
        Evidence: https://grafana.ras.internal/d/hpa/load-test-sprint3

  [3.9] ✅  Liveness/readiness probes validated
        Evidence: https://ci.ras.internal/actions/runs/probe-validation

  [3.10] ✅  Pod Disruption Budget validated
         Evidence: https://ci.ras.internal/actions/runs/pdb-validation

SECTION 3 RESULT:  ⛔  BLOCKED — gate 3.4 (B-001)
OWNER COMMENT (@darius):
  "Everything except Cassandra is green. ISS-005 is on track for Sprint 4.
  The runbook framework is drafted — I need 3 days to complete and test it.
  Once ISS-005 is resolved, I can run the Chaos Mesh experiment same day."

OWNER COMMENT (@aisha):
  "Section 3 does not pass until 3.4 is green. B-001 is a hard blocker.
  Cassandra is the immutable audit log — it is PCI Requirement 10 critical
  infrastructure. I will not sign off on production without knowing what
  happens when a node dies."
```

---

#### Section 4 — Security (@priya / @aisha)

```
### /ppr run --section 4 — Security (@priya / @aisha)

  [4.1] ✅  OWASP ZAP scan: zero HIGH/CRITICAL
        Running: zap-cli quick-scan --self-contained --start-options '-config api.key=...'
        Result:  0 HIGH  0 CRITICAL  2 MEDIUM (documented)  ✅
        Report:  https://security.ras.internal/zap/sprint-3-report

  [4.2] ⛔  BLOCKED — External penetration test
        Blocker:  B-002 — pentest vendor booked for Q2
        Owner:    @priya
        ETA:      Q2 (6 weeks)
        Note:     PCI DSS Requirement 11.4.3 — mandatory pre-GA

  [4.3] ✅  HMAC replay attack test passed
        Evidence: pytest tests/security/test_replay_attack.py — 12/12 passed

  [4.4] ✅  JWT expiry and rotation tested
        Evidence: pytest tests/security/test_auth.py — 18/18 passed

  [4.5] ✅  Trivy scan: zero CRITICAL CVEs
        Running: trivy image ras-scoring-api:1.0.0-rc.3
        Result:  0 CRITICAL  3 HIGH (accepted — no fix available)  ✅
        Exceptions documented: https://security.ras.internal/trivy/exceptions

  [4.6] ✅  Input fuzzing: Pydantic boundary tests
        Evidence: pytest tests/security/test_input_fuzzing.py — 44/44 passed

  [4.7] ✅  SQL injection test suite passed
        Evidence: pytest tests/security/test_injection.py — 31/31 passed

  [4.8] ✅  Auth bypass test suite passed
        Evidence: pytest tests/security/test_auth_bypass.py — 22/22 passed

SECTION 4 RESULT:  ⛔  BLOCKED — gate 4.2 (B-002)
OWNER COMMENT (@priya):
  "Internal security testing is clean. ZAP, Trivy, all auth and injection
  tests are green. The external pentest is the only outstanding gate.
  I cannot self-certify the external pentest — that is the definition of
  a QSA requirement. The vendor is booked. This section clears on receipt
  of the pentest report with all critical and high findings closed."

OWNER COMMENT (@aisha):
  "B-002 is a hard blocker. No workaround, no conditional GO on this one.
  PCI DSS Requirement 11.4.3 is explicit. @james confirmed it in the
  compliance review. Pentest report or the service does not ship."
```

---

#### Section 5 — Observability (@darius / @aisha)

```
### /ppr run --section 5 — Observability (@darius / @aisha)

  [5.1] ⏳  All P1 alerts have linked runbooks
        Status:  9/10 P1 alerts have runbooks
        Missing: scoring_api_cassandra_write_failure alert → O-002
        Owner:   @darius

  [5.2] ✅  Grafana dashboard reviewed and accurate
        Evidence: https://grafana.ras.internal/d/ras-scoring/overview
        Sign-off: @darius 2024-03-14

  [5.3] ✅  Distributed traces validated end-to-end
        Evidence: https://jaeger.ras.internal/trace/sample-sprint3
        Trace spans: enrichment → features → rules → ML → DB → response  ✅

  [5.4] ✅  No PII in logs (audit confirmed)
        Running: log-audit-scan --sample 10000 --check pii
        Result:  0 PII fields detected in 10,000 sampled log lines  ✅
        Evidence: https://ci.ras.internal/actions/runs/log-pii-audit

  [5.5] ✅  No PAN/CVV in any log output
        Running: grep -r 'pan\|cvv\|card_number' logs/
        Result:  0 matches  ✅
        Evidence: https://ci.ras.internal/actions/runs/pan-log-audit

  [5.6] ✅  Structured log format validated
        Sample reviewed: all fields present (request_id, customer_id,
        score, decision, processing_ms, model_version)  ✅

  [5.7] ✅  On-call rotation confirmed and trained
        PagerDuty schedule: https://pagerduty.ras.internal/schedules/ras-oncall
        Trained engineers: 6 / 6  ✅

SECTION 5 RESULT:  ⚠️  IN PROGRESS — gate 5.1 (O-002)
OWNER COMMENT (@darius):
  "One alert missing its runbook — the Cassandra write failure alert.
  This resolves alongside ISS-005 (B-001). Same Sprint 4 deliverable."

OWNER COMMENT (@aisha):
  "5.1 is open but not independently blocking — it resolves with B-001.
  When Darius closes ISS-005, both 3.4 and 5.1 clear simultaneously.
  All other observability gates are green. Good work on the PII audit."
```

---

#### Section 6 — Compliance (@james / @aisha)

```
### /ppr run --section 6 — Compliance (@james / @aisha)

  [6.1] ✅  PCI DSS CDE scope diagram reviewed
        Evidence: docs/compliance/pci_dss_cde_scope_v2.pdf
        Sign-off: James Whitfield (@james) 2024-03-12

  [6.2] ✅  No PAN in database (confirmed by scan)
        Running: db-scan --table risk_decisions --check pan
        Result:  0 PAN patterns found in 2.1M records  ✅

  [6.3] ✅  Audit log completeness verified (PCI DSS Req 10.2.1)
        All 8 required event categories confirmed present  ✅
        Evidence: docs/compliance/pci_dss_controls.md §10.2.1

  [6.4] ⛔  BLOCKED — GDPR Data Protection Impact Assessment
        Blocker:  B-003 — DPIA in progress
        Owner:    @james
        ETA:      Sprint 4 (legal review underway)
        Note:     GDPR Article 35 — mandatory for high-risk processing

  [6.5] ✅  Adverse action reason codes documented
        Evidence: docs/compliance/adverse_action_codes.md
        Sign-off: James Whitfield (@james) 2024-03-11

  [6.6] ✅  Data retention schedule implemented
        Evidence: k8s/cassandra/ttl-config.yaml (90-day TTL)
                  k8s/loki/retention-config.yaml (1-year)
        Sign-off: @james / @darius 2024-03-13

  [6.7] ✅  Right-to-erasure endpoint tested
        Evidence: pytest tests/integration/test_gdpr_erasure.py — 8/8 passed

SECTION 6 RESULT:  ⛔  BLOCKED — gate 6.4 (B-003)
OWNER COMMENT (@james):
  "GDPR Article 35(3)(a) makes a DPIA mandatory when processing involves
  systematic automated decision-making that produces legal effects. A
  transaction decline is a legal effect. This system requires a DPIA before
  it processes a single production transaction. The DPIA is with legal
  counsel for review — it will be complete by Sprint 4."

OWNER COMMENT (@aisha):
  "B-003 is a hard blocker with no compensating control available.
  James is clear: GDPR Article 35 is not optional. Section 6 clears
  when the DPIA is signed and evidence is submitted."
```

---

### `/ppr gate <section> <result> --evidence <url> --note "<text>"` — Update a Gate

**Invocation:**
```bash
/ppr gate 3 pass \
  --evidence "https://chaos.ras.internal/experiments/cassandra-sprint4" \
  --note "Cassandra node failure experiment passed. Runbook ISS-005 resolved.
          System degraded gracefully — scoring continued at reduced write
          throughput. Audit log caught up within 8 seconds of node return."
```

**Behaviour:** `@aisha` records the gate result with evidence link and note. Validates that evidence URL is accessible and the note meets minimum documentation standards. Updates the overall PRR verdict. If a blocker is resolved, emits a notification to the team.

**Output format:**
```
### /ppr gate — Gate Updated (@aisha)

  Gate:     §3.4 — Cassandra node failure chaos experiment
  Result:   ✅ PASS
  Evidence: https://chaos.ras.internal/experiments/cassandra-sprint4
  Note:     "Cassandra node failure experiment passed..." [truncated]
  Updated:  2024-03-28T11:14:03Z
  By:       darius.o

  BLOCKER RESOLVED: B-001 ✅
  OPEN ITEM RESOLVED: O-002 ✅  (Cassandra runbook alert linked)

  Section 3 status: ⚠️  IN PROGRESS  (gates 3.5, 3.6 still pending)
  Overall blockers remaining: 2  (B-002 pentest, B-003 DPIA)

  📢 TEAM NOTIFICATION: B-001 resolved. Gates §3.4 and §5.1 now passing.
     Remaining blockers: B-002 (@priya), B-003 (@james)
```

---

### `/ppr sign-off` — Final PRR Sign-off

**Invocation:** `/ppr sign-off`

**Behaviour:** `@aisha` performs the final PRR assessment. All sections must be `PASS` with no open blockers. If any blocker remains, sign-off is refused with a specific list of what must be resolved. If all sections pass, `@aisha` issues the GO decision and generates the PRR completion report.

**GO Output format:**
```
### /ppr sign-off — Production Readiness Review (@aisha)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRR FINAL ASSESSMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SERVICE:   ras-scoring-api v1.0.0
DATE:      2024-04-14T09:32:00Z

  §1 Code Quality        ✅  PASS
  §2 Performance         ✅  PASS
  §3 Reliability/Chaos   ✅  PASS
  §4 Security            ✅  PASS
  §5 Observability       ✅  PASS
  §6 Compliance          ✅  PASS

  Total gates: 37 / 37  ✅
  Blockers:    0
  Open items:  0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VERDICT:  ✅  GO — APPROVED FOR PRODUCTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PRR Owner:      Aisha Patel
Sign-off Time:  2024-04-14T09:32:00Z
Valid for:      30 days (re-run required if not deployed by 2024-05-14)

DEPLOYMENT INSTRUCTIONS
  1. Confirm on-call engineer is available and briefed: @darius
  2. Deploy via ArgoCD canary — do not use rolling update
  3. Monitor canary at 5% for minimum 10 minutes before promoting
  4. Promotion gates: P95 < 100ms · error rate < 0.1% · decision ratio ±3%
  5. Full promotion or rollback decision within 30 minutes of canary start
  6. Post-deploy smoke tests: /score test --env production --suite smoke
  7. Confirm with @james that first production SAR clock is set correctly

PRR REPORT: /ppr report  (full evidence package for audit purposes)

🎉 Congratulations team. It took 5 weeks and 37 gates.
   Build it right, and it stays right. Ship it.
```

**NO-GO Output format:**
```
### /ppr sign-off — REFUSED (@aisha)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VERDICT:  ⛔  NO-GO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PRR sign-off refused. The following blockers must be resolved:

  B-002  §4.2  External penetration test not completed
               Owner: @priya · ETA: Q2
               Required by: PCI DSS Requirement 11.4.3

  B-003  §6.4  GDPR DPIA not completed
               Owner: @james · ETA: Sprint 4
               Required by: GDPR Article 35

These are not negotiable. There is no compensating control for a missing
external pentest or a missing DPIA on high-risk automated processing.

When blockers are resolved:
  /ppr gate 4 pass --evidence <pentest_report_url> --note "<summary>"
  /ppr gate 6 pass --evidence <dpia_doc_url> --note "<summary>"
  /ppr sign-off

I will re-run sign-off within 24 hours of all blockers being resolved.
```

---

### `/ppr report` — Generate Evidence Package

**Invocation:** `/ppr report [--format pdf|markdown] [--output <path>]`

**Behaviour:** Generates the complete PRR evidence package for audit purposes. Includes all gate results, evidence links, agent sign-offs, and timeline. Used for PCI DSS QSA assessment, SOC 2 Type II evidence collection, and internal audit records.

**Output format:**
```
### /ppr report — Evidence Package (@aisha / @james)

Generating PRR Evidence Package...

PACKAGE CONTENTS
  prr_summary.md              ← Gate results, verdicts, timeline
  section_1_code_quality/     ← Codecov reports, CI run logs
  section_2_performance/      ← Locust HTML reports, Grafana snapshots
  section_3_reliability/      ← Chaos Mesh reports, runbook links
  section_4_security/         ← ZAP report, Trivy output, pentest summary
  section_5_observability/    ← Dashboard screenshots, trace samples
  section_6_compliance/       ← PCI scope diagram, DPIA, audit log sample
  sign_off_certificate.pdf    ← Signed PRR completion certificate

AUDIT NOTES (@james)
  This evidence package satisfies:
  ✅ PCI DSS v4.0 Req 12.3.4 — Security technologies reviewed annually
  ✅ SOC 2 Type II — Change management evidence (CC8.1)
  ✅ ISO 27001:2022 — A.8.32 Change management evidence
  Retention: 3 years (PCI DSS Req 10.7) · stored in: docs/quality/prr_evidence/

Package saved to: docs/quality/prr_evidence/ras-scoring-api-v1.0.0-prr-2024-04-14.zip
Checksum (SHA-256): a3f7c2...
```

---

### `/ppr history` — PRR History

**Invocation:** `/ppr history [--service <name>] [--limit <n>]`

**Output format:**
```
### /ppr history (@aisha)

PRR HISTORY — ras-scoring-api

  Version    Date        Verdict     Duration   Blockers    Owner
  ─────────  ──────────  ──────────  ─────────  ──────────  ─────────
  v1.0.0     2024-04-14  ✅ GO       35 days    3 resolved  @aisha
  v0.9.0     2024-02-01  ⛔ NO-GO    —          2 open      @aisha  ← never shipped
  v0.8.0     2024-01-15  ✅ GO       12 days    1 resolved  @aisha  ← staging only

DEPLOYMENT SUB-CHECKLIST RUNS
  v1.0.1     2024-04-28  ✅ PASS     1 day      0           @aisha
  v1.0.2     2024-05-03  ✅ PASS     1 day      0           @aisha
```

---

### `/ppr unblock <issue_id>` — Resolve a Blocker

**Invocation:** `/ppr unblock B-001 --evidence <url> --note "<resolution summary>"`

**Behaviour:** Marks a PRR blocker as resolved with evidence. `@aisha` validates the resolution against the original blocker criteria. If valid, the associated gate is updated to PASS and the overall PRR status is recalculated.

---

## PRR Decision Matrix

```
All 37 gates ✅ PASS  →  GO
─────────────────────────────────────────────────────
Any gate ❌ FAIL      →  NO-GO (must be resolved)
Any gate ⛔ BLOCKED   →  NO-GO (blocker must be cleared)
─────────────────────────────────────────────────────
⚠️  CONDITIONAL GO: available only with VP Engineering approval,
    documented risk acceptance, and a time-limited remediation plan.
    Cannot be used for security (§4) or compliance (§6) blockers.
    Maximum validity: 14 days.
    Requires @aisha + VP Engineering co-signature.
```

---

## Agent Ownership by Section

| Section | Gates | Primary Owner | Supporting Agents |
|---|---|---|---|
| §1 Code Quality | 1.1–1.10 | `@sofia` | `@aisha` (coverage standards), `@priya` (SAST) |
| §2 Performance | 2.1–2.9 | `@darius`, `@aisha` | `@sofia` (DB pool), `@yuki` (ML latency) |
| §3 Reliability | 3.1–3.10 | `@darius` | `@aisha` (experiment criteria), `@marcus` (blast radius) |
| §4 Security | 4.1–4.8 | `@priya` | `@aisha` (test execution), `@james` (compliance gates) |
| §5 Observability | 5.1–5.7 | `@darius` | `@sofia` (log format), `@priya` (PII audit) |
| §6 Compliance | 6.1–6.7 | `@james` | `@priya` (PCI controls), `@darius` (retention config) |
| **Sign-off** | All | **`@aisha`** | All agents |

---

## Related Commands

| Command | Description |
|---|---|
| `/score test` | Run scoring test suite (feeds §1 code quality gates) |
| `/score benchmark` | Run latency benchmark (feeds §2 performance gates) |
| `/review sla` | Review queue SLA status (feeds §5 observability gates) |

---

## Security & Compliance Notes

> ⚠️ **@priya:** The PRR evidence package contains security test outputs including vulnerability scan results and penetration test summaries. This package is `RESTRICTED` — share only with QSA assessors, SOC 2 auditors, and internal audit under NDA. Do not store in public repositories or share via unencrypted channels.

> ⚠️ **@james:** The PRR sign-off certificate is a controlled document that will be cited in PCI DSS ROC submissions and SOC 2 Type II audit evidence packages. It must be signed by the named PRR owner (Aisha Patel) and archived in the compliance evidence repository with a 3-year minimum retention per PCI DSS Requirement 10.7.

> ⚠️ **@aisha:** A CONDITIONAL GO may never be issued for §4 Security or §6 Compliance blockers. These sections have no compensating control pathway — the requirement is hard. Any pressure to issue a CONDITIONAL GO on these sections should be escalated to the CISO and CCO immediately.

---

*Command File Version: 1.0.0*
*Project: Risk Assessment System*
*Classification: Internal — Engineering Confidential*