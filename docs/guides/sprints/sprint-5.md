# Sprint 5 — Frontend: Analyst Dashboard

**Goal:** Analysts can review cases through the web UI.

**Duration:** 2 weeks  
**Lead:** `@elena`  
**Supporting:** `@sofia`, `@aisha`

---

## Authentication

`@elena` leads

```
[ ] NextAuth.js — Keycloak OIDC login flow
[ ] Role-aware navigation (rbac_matrix.md §4)
[ ] httpOnly session cookie — no JWT in localStorage
[ ] BFF Route Handlers — all API calls server-side
```

---

## Case Queue (/dashboard/queue)

`@elena` leads

```
[ ] Server Component — initial queue render
[ ] Client Component — SWR 5s polling for live updates
[ ] SLA badge colours — P1 🔴 / P2 🟡 / P3 🟢
[ ] Parallel routes — @queue + @case slots
```

---

## Case Investigation (/dashboard/cases/[id])

`@elena` leads

```
[ ] Full case detail — transaction, device, network
[ ] SHAP chart — D3.js horizontal bar chart
      (accessible: role=img, aria-label with full explanation)
[ ] Customer history timeline
[ ] Compliance context panel (@james GDPR Art. 22)
[ ] Action buttons — Approve / Decline / Escalate
      (Client Component — optimistic UI + error recovery)
```

---

## Analyst Actions

`@elena` leads

```
[ ] Resolve case — POST via Route Handler
[ ] Assign case — PATCH via Route Handler
[ ] Escalate to compliance — POST via Route Handler
[ ] Contestation response flow (GDPR Art. 22(3))
```

---

## Testing

`@aisha` writes

```
[ ] Playwright E2E — case queue load + resolve flow
[ ] axe-core accessibility — zero violations
[ ] React Testing Library — component unit tests
[ ] Bundle size check — queue page < 150KB
```

---

## Completion Criteria

✅ Sprint 5 done when:
- Analyst can log in, see the queue, open a case
- Review the SHAP explanation
- Resolve it
- Accessible
- No JWT in localStorage

---

**Owner:** Elena Vasquez (`@elena`)  
**Status:** ⏳ Not started  
**Created:** 2026-03-25
