# Sprint 2 — Security Layer + Auth

**Goal:** All security controls from the threat model are active.

**Duration:** 2 weeks  
**Lead:** `@priya`  
**Supporting:** `@darius`, `@sofia`

---

## Authentication

`@priya` leads

```
[ ] Keycloak realm configured — roles, scopes, clients
[ ] JWT RS256 validation middleware (FastAPI)
[ ] All API endpoints require valid JWT
[ ] Merchant API key provisioning flow
```

---

## Authorization

`@priya` leads

```
[ ] RBAC scope enforcement per rbac_matrix.md
[ ] Kong Gateway configured — rate limiting, JWT validation
[ ] OPA Gatekeeper policies deployed to Kubernetes
```

---

## Encryption

`@priya` leads

```
[ ] AWS KMS key created + IAM policy
[ ] FieldEncryptor implemented (app/core/encryption.py)
[ ] PII fields encrypted at rest (per encryption_spec.md §2.3)
[ ] Vault Agent Sidecar — dynamic DB credentials
[ ] ISS-003: Vault rotation wired to app reload
```

---

## Network

`@priya` leads

```
[ ] Istio mTLS STRICT mode on risk namespace
[ ] Kubernetes NetworkPolicy default-deny applied
[ ] Cloudflare WAF rules configured
[ ] TLS 1.3 enforced at Kong
```

---

## HMAC

`@priya` leads

```
[ ] Webhook signing implemented (app/core/webhooks.py)
[ ] Replay attack tests passing
```

---

## Security Testing

`@priya` + `@aisha`

```
[ ] OWASP ZAP scan — zero HIGH/CRITICAL findings
[ ] Bandit + Semgrep — zero HIGH/CRITICAL findings
[ ] Auth bypass test suite passing
[ ] SQL injection test suite passing
[ ] Input fuzzing tests passing
```

---

## Completion Criteria

✅ Sprint 2 done when:
- All API endpoints are authenticated
- PII is encrypted at rest
- mTLS is active between all services
- PRR §4 gates reachable

---

**Owner:** Priya Nair (`@priya`)  
**Status:** ⏳ Not started  
**Created:** 2026-03-25
