# RAS Development Sprints — Complete Index

```yaml
document:       docs/guides/sprints/
version:        1.0.0
status:         ⏳ Sprint 0 — Pre-Development
current_state:  Individual sprint files created
target:         All sprints ✅ COMPLETED by 2026-09-30
```

---

## Quick Links — All Sprints

| Sprint | Title | Duration | Lead | Status |
|--------|-------|----------|------|--------|
| [Sprint 0](sprint-0.md) | Infrastructure & DevOps Foundation | 2 weeks | `@darius` | ⏳ |
| [Sprint 1](sprint-1.md) | Backend Core | 2 weeks | `@sofia` | ⏳ |
| [Sprint 2](sprint-2.md) | Security Layer + Auth | 2 weeks | `@priya` | ⏳ |
| [Sprint 3](sprint-3.md) | Rule Engine + Case Management | 2 weeks | `@sofia` + `@marcus` | ⏳ |
| [Sprint 4](sprint-4.md) | ML Pipeline + Feature Store | 3 weeks | `@yuki` | ⏳ |
| [Sprint 5](sprint-5.md) | Frontend: Analyst Dashboard | 2 weeks | `@elena` | ⏳ |
| [Sprint 6](sprint-6.md) | Frontend: Admin UI + ML Monitor | 2 weeks | `@elena` | ⏳ |
| [Sprint 7](sprint-7.md) | Integration, Load Testing, Chaos | 2 weeks | `@darius` + `@aisha` | ⏳ |
| [Sprint 8](sprint-8.md) | Security Hardening + Compliance | 3 weeks | `@priya` + `@james` | ⏳ |
| [Sprint 9](sprint-9.md) | Production Readiness Review | 2 weeks | `@aisha` | ⏳ |
| [Sprint 10](sprint-10.md) | Production Launch | 1 week | `@darius` | ⏳ |

---

## Complete Timeline

```
Sprint 0   2 weeks   Infrastructure + DevOps foundation
Sprint 1   2 weeks   Scoring API + Databases
Sprint 2   2 weeks   Security layer + Auth
Sprint 3   2 weeks   Rule engine + Case management
Sprint 4   3 weeks   ML pipeline + Feature store
Sprint 5   2 weeks   Frontend — Analyst dashboard
Sprint 6   2 weeks   Frontend — Admin + ML monitor
Sprint 7   2 weeks   Load testing + Chaos
Sprint 8   3 weeks   Security hardening + Compliance
Sprint 9   2 weeks   PRR
Sprint 10  1 week    Production launch
           ────────
           23 weeks  (~6 months)
```

---

## Team Ownership Matrix

| Sprint | Lead | Supporting |
|--------|------|---|
| 0 | `@darius` SRE | `@sofia` Backend, `@elena` Frontend |
| 1 | `@sofia` Backend | `@marcus` Arch, `@aisha` QA |
| 2 | `@priya` Security | `@darius` SRE, `@sofia` Backend |
| 3 | `@sofia` Backend + `@marcus` Arch | `@james` Compliance, `@aisha` QA |
| 4 | `@yuki` ML | `@darius` SRE, `@aisha` QA |
| 5 | `@elena` Frontend | `@sofia` Backend, `@aisha` QA |
| 6 | `@elena` Frontend | `@yuki` ML, `@aisha` QA |
| 7 | `@darius` SRE + `@aisha` QA | All |
| 8 | `@priya` Security + `@james` Compliance | `@darius` SRE |
| 9 | `@aisha` QA | All agents |
| 10 | `@darius` SRE | All agents |

---

## Progress Tracking

### Current Sprint: Sprint 0 — Infrastructure

**Start Date:** 2026-03-25  
**End Date:** 2026-04-08  
**Lead:** Darius Okafor (`@darius`)

**Key Milestones:**
- [ ] `make dev` starts full stack locally
- [ ] CI/CD pipeline live and passing
- [ ] All engineers can run tests

---

## Next Immediate Actions

### TODAY:
1. `@darius` → docker-compose.yml — local dev stack
2. `@sofia` → FastAPI health endpoints + DB connection
3. `@elena` → NextAuth.js Keycloak integration
4. `@priya` → Vault + Keycloak staging bootstrap

### THIS WEEK (Sprint 0):
5. `@darius` → Terraform — EKS + RDS + Redis + Kafka staging
6. `@sofia` → Alembic migrations (risk_decisions, cases, rules)
7. `@aisha` → CI pipeline — lint + test + build gates
8. `@marcus` → Review Sprint 1 API contract with `@sofia`

---

## Document References

- **Master Roadmap:** [docs/guides/project_roadmap.md](../project_roadmap.md)
- **PRR Checklist:** [docs/quality/prr_checklist.md](../../quality/prr_checklist.md)
- **Architecture Decisions:** [docs/architecture/adr/](../../architecture/adr/)
- **Runbooks:** [docs/runbooks/](../../runbooks/)

---

## Notes for Sprint Planning

### How to Update Sprint Progress

Each sprint file has a completion criteria section. As work progresses:
1. Mark checklist items `[x]` as they're completed
2. Update the `Status:` field (⏳ In Progress → ✅ Completed)
3. Update the `End Date:` when sprint wraps
4. File a post-mortem link in the sprint file once available

### Escalation & Blockers

If a sprint is blocked:
1. Update the sprint file with a **BLOCKER** section
2. Tag the responsible agent in Slack
3. Reference the blocker in the next standup

### Cross-Sprint Dependencies

- **Sprint 1 depends on Sprint 0:** Backend can't start without docker-compose + CI
- **Sprint 2 depends on Sprint 1:** Auth layer protects scoring API endpoints
- **Sprint 4 depends on Sprint 1:** ML needs PostgreSQL + Cassandra from Sprint 1
- **Sprint 5 depends on Sprint 1 + 2:** Frontend needs authenticated API endpoints
- **Sprint 7 depends on Sprints 1–6:** All components must exist before load testing
- **Sprint 8 depends on Sprints 1–7:** Security audit & compliance verification
- **Sprint 9 depends on Sprints 0–8:** PRR cannot pass until all prerequisites complete

---

**Repository Owner:** Marcus Chen (`@marcus`) — Chief Risk Architect  
**Sprint Owner:** Darius Okafor (`@darius`) — Staff SRE / Platform Engineer  
**Review Cycle:** End of every sprint + daily standup  
**Classification:** Internal — Engineering Confidential

---

*Last Updated:* 2026-03-25  
*Next Review:* 2026-04-08 (end of Sprint 0)
