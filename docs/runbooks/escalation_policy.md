# On-Call Escalation Policy

**Owner:** `@darius` · **PagerDuty:** https://pagerduty.ras.internal

## On-Call Rotation

| Tier | Role | Responds To | Escalates To |
|---|---|---|---|
| L1 | SRE On-Call | All P1/P2 alerts | L2 after 15 min no resolution |
| L2 | Senior SRE / Service Owner | L1 escalation | L3 after 30 min |
| L3 | Engineering Lead (`@marcus` / `@sofia`) | L2 escalation | CISO / VP Eng after 1 hour |
| Security | `@priya` | Any security alert | CISO immediately |
| Compliance | `@james` | Breach / SAR / regulatory | Legal + CISO immediately |

## Alert Routing by Service

| Alert | Primary | Secondary | Escalate If |
|---|---|---|---|
| Scoring API latency P1 | `@darius` | `@sofia` | Not resolved in 15 min |
| ML service down | `@darius` | `@yuki` | Fallback not active in 5 min |
| Cassandra node down | `@darius` | `@marcus` | Quorum lost |
| Security incident | `@priya` | `@james` | Immediately |
| SAR deadline at risk | `@james` | CISO | Immediately |
| Regional failover | `@darius` | `@marcus` | 30 min post-failover |
| PRR blocker discovered in prod | `@aisha` | All leads | Immediately |

## Response Time SLAs

| Severity | Acknowledge | First Update | Resolution Target |
|---|---|---|---|
| P1 | 5 min | 15 min | 1 hour |
| P2 | 15 min | 30 min | 4 hours |
| P3 | 30 min | 2 hours | 24 hours |

## Communication Protocol

```
P1 Incident Open:
  1. Acknowledge in PagerDuty
  2. Open #incident-YYYYMMDD-<service> Slack channel
  3. Post status every 15 min until resolved
  4. Notify @james if merchant SLA impact (> 5 min P1)

P1 Incident Resolved:
  1. Resolve in PagerDuty
  2. Post resolution summary in incident channel
  3. Schedule post-mortem within 48 hours
  4. File post-mortem in docs/postmortems/

Merchant Communication:
  Any P1 lasting > 5 minutes → @james notifies affected merchants
  per contractual SLA obligations
```

## Handoff Protocol (Shift Change)

```
Outgoing on-call must:
  1. Document all active incidents in PagerDuty
  2. List any degraded services or known issues
  3. Hand off any open investigation to incoming on-call
  4. Confirm handoff acknowledged in #on-call Slack channel
```
