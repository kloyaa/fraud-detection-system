# Engineering Governance Framework

Non-negotiable rules for the Risk Assessment System (RAS) engineering team.

---

## Purpose

This document enforces mandatory engineering standards across all code changes, deployments, and operational decisions. All rules are binary (pass/fail) and enforceable. No exceptions without explicit authority escalation.

---

## Non-Negotiable Rules

| Rule | Enforcer | Consequence |
|------|----------|------------|
| No feature complete without QA validation | @aisha | Feature blocked for staging/prod |
| No deployment without PRR GO decision | @aisha | Deployment blocked |
| No API change without contract test update | @aisha | PR rejected |
| No frontend change without accessibility validation | @elena | PR rejected |
| No security-sensitive change without security review | @priya | PR rejected, security gate fails |
| No schema change without rollback validation | @sofia | PR rejected |
| No compliance-impacting change without approval | @james | PR rejected, compliance gate fails |
| No external integration without chaos test | @darius | Deployment blocked |

---

## Merge Gates (Pre-Merge Requirements)

**All must pass before merge:**

- ✅ Unit tests: 100% execution on changed code
- ✅ Integration tests: Testcontainers used for data store dependencies (no mocks)
- ✅ Contract tests: All pact expectations passing in CI
- ✅ Line coverage: ≥90% on changed code, ≥80% codebase baseline
- ✅ Branch coverage: ≥85% on critical paths (scoring engine, rule engine, fallback paths)
- ✅ Mutation score: ≥70% on scoring engine
- ✅ Lint: Zero warnings (eslint, ruff, bandit)
- ✅ Type safety: Zero errors (mypy strict mode, tsconfig strict)
- ✅ Security scan: Zero CRITICAL/HIGH findings (Semgrep, Bandit, ZAP)
- ✅ Migration safety: Rollback function defined and tested (if schema change)
- ✅ No merge conflicts
- ✅ All review comments resolved
- ✅ PR description includes test evidence (links to CI run)

**Enforcement:** GitHub Actions gates required before merge. No manual override.

---

## Deployment Gates (Pre-Production)

**All must be completed and passed:**

| Gate | Owner | Requirements | Evidence |
|------|-------|--------------|----------|
| **PRR Completion** | @aisha | All 6 PRR sections evaluated | PRR document signed off with GO decision |
| **Load Test SLA** | @darius | P50 <35ms, P95 <100ms, P99 <250ms @2x peak; error <0.1% | Locust HTML report + Grafana screenshot |
| **Rollback Verification** | @darius | Rollback executed successfully; CI log timestamp provided | Timestamped rollback test log |
| **Observability** | @darius | P1 alerts have runbooks; Grafana dashboards live; traces valid | Prometheus/Grafana verification + runbook links |
| **Security Sign-off** | @priya | Zero CRITICAL/HIGH findings; HMAC/JWT/encryption tested | ZAP report + test execution log |
| **Compliance Sign-off** | @james | Audit log complete; DPIA done; retention implemented | Compliance checklist completed |
| **Blockers Cleared** | @aisha | No open P0/P1 blockers; all ISS issues resolved or deferred with approval | Issue tracker status snapshot |

**Enforcement:** Cannot proceed to production without GO from all gate owners.

---

## Hard Blocks (Automatic Deployment Prevention)

**If any condition is true, deployment is blocked immediately:**

- 🛑 Security vulnerability CRITICAL/HIGH exists
- 🛑 Compliance requirement not met (PCI, GDPR, SOC 2, FCRA)
- 🛑 PRR section marked BLOCKED (not CONDITIONAL GO with VP approval)
- 🛑 Rollback plan missing or untested
- 🛑 External integration not chaos-tested
- 🛑 Load test P95 >100ms or error rate >0.1%
- 🛑 Migration rollback function not defined
- 🛑 P0 incident open and unresolved
- 🛑 Required security testing incomplete (pentest deferred without VP sign-off)
- 🛑 Coverage below thresholds without waiver

**Override Protocol:** Only VP Engineering can approve override. Requires documented risk assessment + remediation timeline.

---

## Merge Review Authority

| Domain | Authority | Veto Power | Sign-off Required |
|--------|-----------|-----------|-------------------|
| **Code Quality** | @aisha | Yes | Must approve for merge |
| **Security** | @priya | Yes | Must approve for merge |
| **Backend Implementation** | @sofia | Yes | Must approve for merge |
| **Frontend Implementation** | @elena | Yes | Must approve for merge |
| **Architecture** | @marcus | Yes | Can request changes; delays merge |
| **ML Model** | @yuki | Yes | Must approve for changes to model serving |
| **Compliance** | @james | Yes | Must approve for data/regulatory changes |
| **Infrastructure** | @darius | Yes | Must approve for infra changes |

**Rule:** PRs cannot merge without approval from domain owner. Multiple approvals required if PR spans domains.

---

## Deployment Authority

| Gate | Authority | Veto Power | Conditions |
|------|-----------|-----------|-----------|
| **QA/PRR** | @aisha | Yes | Cannot deploy without PRR GO |
| **Security** | @priya | Yes | Cannot deploy with CRITICAL/HIGH findings |
| **Compliance** | @james | Yes | Cannot deploy with compliance blockers |
| **Infrastructure** | @darius | Yes | Cannot deploy with infra issues; can rollback immediately if SLO breached |

**Rule:** Each authority must explicitly approve deployment in their domain. No implicit approvals.

---

## Violation Handling

### Merge Violation (Failed Gate)

**Action:**
1. PR automatically rejected by GitHub Actions
2. Developer must fix root cause (test, coverage, security, type check)
3. Re-run CI; all gates must pass
4. Resubmit for review

**Escalation:** If gate appears incorrect, escalate to domain owner (@aisha for QA gates, @priya for security, etc.)

---

### Deployment Violation (Hard Block Triggered)

**Action:**
1. Deployment halted immediately
2. Blocking condition must be resolved
3. Root cause documented
4. Retest and re-validate
5. Resubmit deployment request

**Escalation:** If blocker cannot be resolved, escalate to VP Engineering for risk acceptance decision.

---

### Policy Violation (Rule Ignored)

**Action:**
1. Change rolled back immediately
2. Responsible party notified
3. Post-mortem scheduled (if production impact)
4. Rule reinforcement session (team)
5. Monitor for repeat violations

**Consequence:** Repeated violations → escalation to team lead/manager.

---

## Testing Requirements by Change Type

### Backend API Change
- ✅ Contract test added (Pact)
- ✅ Integration test with real database (Testcontainers)
- ✅ Fallback path tested (if applicable)
- ✅ Idempotency tested (if state-modifying)
- ✅ Error cases tested

### Database Schema Change
- ✅ Migration forward tested
- ✅ Migration rollback tested (rollback() function)
- ✅ Zero-downtime verified (no blocking locks)
- ✅ Data consistency verified post-migration
- ✅ Rollback timestamp logged

### Security-Sensitive Code
- ✅ Code review by @priya required
- ✅ Threat model updated (if attack surface changes)
- ✅ Integration test covers security requirement
- ✅ No hardcoded secrets (Semgrep check)
- ✅ SAST findings zero CRITICAL/HIGH

### ML Model Change
- ✅ Leakage analysis completed by @yuki
- ✅ Feature importance evaluated
- ✅ Fairness audit (ECOA compliance)
- ✅ Shadow mode >30h completed
- ✅ Champion-challenger statistical test completed

### Frontend Component
- ✅ WCAG 2.1 AA accessibility tested (@elena review)
- ✅ TypeScript strict mode passing
- ✅ Component story documented
- ✅ Mobile responsive verified
- ✅ No JavaScript errors in browser console

---

## Continuous Accountability

**Weekly Audit (Every Monday 9 AM):**
- Coverage metrics reviewed (target: ≥90% line, ≥85% branch)
- Security scan results reviewed (target: zero CRITICAL/HIGH)
- Open P0/P1 issues tracked (target: zero P0 >4h old)
- PRR status reviewed (deployment readiness)
- Compliance checklist status (GDPR, PCI, SOC 2)

**Monthly Review (Last Friday of month):**
- False-positive rate in security/coverage gates
- Gate effectiveness (blocked bugs vs. false positives)
- Policy violations (recurring patterns)
- Updated risk register

---

## Exemptions and Appeals

**Request Exemption:** Contact @aisha + responsible authority for that domain.

**Exemption Criteria:**
- Business-critical blocker
- Documented risk assessment
- Remediation timeline committed
- VP Engineering approval required

**No exemptions granted for:**
- Security vulnerabilities (CRITICAL/HIGH)
- Compliance violations
- Rollback procedures
- Load test failures
- Coverage thresholds (without data-driven waiver)

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-25 | Initial governance framework |
