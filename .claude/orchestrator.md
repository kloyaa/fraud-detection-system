# Agent Orchestration Framework

Central routing logic for the RAS multi-agent system.

**12 Agents:**
- **Domain:** @marcus (architecture), @priya (security), @yuki (ML), @darius (SRE), @sofia (backend), @james (compliance), @aisha (QA), @elena (frontend)
- **Utility:** @optimizer (code review), @doc-integrity (documentation)

---

## Routing by Keywords

| Keywords | Primary | Supporting |
|----------|---------|------------|
| architecture, system design, kafka, microservices, event sourcing, CQRS, trade-off, CAP theorem | @marcus | @sofia, @darius |
| encryption, JWT, mTLS, Vault, WAF, PCI, CVE, threat, zero trust, HMAC, secrets, RBAC, certificate | @priya | @james, @darius |
| model, XGBoost, feature, drift, BentoML, Feast, MLflow, AUC, embedding, bias, FCRA | @yuki | @james, @aisha |
| kubernetes, SRE, SLO, HPA, Terraform, ArgoCD, Prometheus, Grafana, chaos, latency, incident, EKS, Istio, canary | @darius | @aisha, @sofia |
| FastAPI, SQLAlchemy, Pydantic, router, postgres, redis, celery, API, endpoint, idempotency, migration, async, N+1 | @sofia | @marcus, @aisha |
| GDPR, SOC 2, audit, AML, KYC, SAR, compliance, regulation, PCI QSA, retention, erasure, FCRA, adverse action | @james | @priya, @marcus |
| test, pytest, Locust, coverage, contract, chaos, smoke, PRR, regression, load, integration, quality gate | @aisha | All (PRR) |
| Next.js, TypeScript, React, frontend, dashboard, UI, component, Tailwind, bundle, WCAG, Playwright | @elena | @priya (BFF) |

## Routing by Request Type

| Request | Flow | Phase |
|---------|------|-------|
| Feature Design | @marcus → @sofia → @aisha → @james | Design |
| Deployment Readiness | @aisha → @priya → @darius → @james | Pre-Prod |
| Security Incident | @priya → @james → @darius → @marcus | Reactive |
| ML Model Promotion | @yuki → @aisha → @james → @darius | Deployment |
| API Contract Change | @sofia → @elena → @aisha | Design |
| Production Readiness Review | @aisha (orchestrates all) | Gate |
| Performance Regression | @darius → @sofia → @marcus → @aisha | Triage |

---

## Collaboration Patterns

### 1. Feature Design — Lead: @marcus

1. **@marcus** — Service boundaries, scalability, ADR alignment
2. **@sofia** — API contract, migrations, idempotency
3. **@aisha** — Test strategy (unit/integration/contract/load)
4. **@james** — Data residency, retention, audit, GDPR/PCI impact
5. **@priya** (if security-sensitive) — Encryption, secrets, auth/authz, attack surface

### 2. Production Readiness Review (PRR) — Lead: @aisha

**Authority:** @aisha has unconditional GO/NO-GO veto over all agents on quality gates.

**Sections & Ownership:**
- **Code Quality** → @aisha: Line ≥90%, Branch ≥85%, Mutation ≥70%, zero security findings
- **Performance** → @aisha + @darius: P50 <35ms, P95 <100ms, P99 <250ms @2x peak, error <0.1%
- **Chaos & Reliability** → @darius: Fallback <500ms, circuit breaker tested, runbooks complete
- **Security** → @priya: ZAP zero CRITICAL, HMAC/JWT tested
- **Observability** → @darius: Alerts have runbooks, zero PII in logs
- **Compliance** → @james: Audit log complete, DPIA done, right-to-erasure tested

**Gate Rule:** Cannot issue GO with open blockers. Conditional GO only with VP sign-off.

### 3. Security Incident — Lead: @priya

| Level | Trigger | Lead | Action |
|-------|---------|------|--------|
| L1 | CVE reported | @priya | Assess scope, patch priority, CDE impact |
| L2 | Exploit suspected | @priya + @james | Threat model review, compliance notify |
| L3 | Data breach confirmed | @priya + @james + @darius | Forensics, breach notification (SAR/GDPR), incident response |
| L4 | Multi-service impact | All + VP/Legal | Full review, post-mortem, remediation |

**@priya Authority:** Can mandate immediate changes without PRR gate; @darius enforces via infrastructure.

### 4. ML Model Promotion — Lead: @yuki

**Gates (in sequence, all required):**
1. **@yuki** — AUC-PR, leakage analysis, champion-challenger >30h shadow, fairness audit, calibration
2. **@aisha** — Test harness, regression detection, fallback testing, A/B design
3. **@james** — SR 11-7 model card, FCRA reason codes, SHAP explainability, Article 22 notice
4. **@darius** — BentoML P95 <30ms, fallback <500ms, canary params, rollback tested
5. **@sofia** — API integration, Feast store stable, batch scoring working

**Promotion Authority:** @yuki (requires joint sign-off from @aisha, @james, @darius).

### 5. API Contract Change — Lead: @sofia

1. **@sofia** — Schema changes, backward compatibility
2. **@elena** — OpenAPI type regeneration, component updates
3. **@aisha** — Integration test coverage

---

## Invocation Modes

**Sequential (Design Phase)**
```
Request → @marcus → @sofia → @aisha → @james → GO/NO-GO
```
Use for: Feature design, major architecture changes | Duration: 4–8h

**Parallel (Emergency)**
```
Request → (@priya + @darius + @james) → action
```
Use for: Security incident, P0 production incident | Duration: 0–30m

**Linear (Deployment)**
```
Request → @aisha (PRR orchestration) → all agents validate → GO/NO-GO
```
Use for: Production deployment | Duration: 2–4h

**Consultation (Ad-hoc)**
```
Request → router (keyword match) → primary agent + supporting agents
```
Use for: Questions, guidance | Duration: 0–2h

---

## Decision Authority

**Conflicts:** When agents disagree, authority follows this hierarchy:

| Conflict | Authority | Rule |
|----------|-----------|------|
| Quality vs. Schedule | @aisha | Cannot deploy without PRR GO |
| Security vs. Performance | @priya | Cannot deploy with security blockers |
| Compliance vs. Timeline | @james | Cannot deploy with compliance blockers |
| Architecture vs. Implementation | @marcus + @sofia | Negotiate; escalate to VP if stuck |
| ML Model vs. Rules | @yuki + @sofia | Co-own fallback logic; @aisha observes |

---

## Hard Gates (Non-Negotiable)

**No production deployment without:**
- ✅ PRR GO from @aisha
- ✅ Security sign-off from @priya (zero CRITICAL/HIGH findings)
- ✅ Compliance sign-off from @james (GDPR, PCI DSS, SOC 2)
- ✅ Rollback procedure tested and documented
- ✅ P95 latency <100ms validated under 2x peak load
- ✅ Error rate <0.1% under 2x peak load

**Escalation triggers:**
- SLO breach: P95 >250ms or error >1% → @darius can rollback immediately
- Security finding CRITICAL/HIGH → @priya can block deployment
- Compliance blocker → @james can block deployment

