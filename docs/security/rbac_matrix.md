# RBAC Matrix
## Risk Assessment System (RAS) — Role-Based Access Control

```yaml
document:       docs/security/rbac_matrix.md
version:        1.0.0
owner:          Priya Nair (@priya) — Principal Security Engineer
reviewers:      "@james · @sofia · @darius · @elena"
last_updated:   Pre-development
status:         Approved
idp:            Keycloak (OIDC/OAuth 2.0)
enforcement:    Kong Gateway (API scopes) · OPA Gatekeeper (K8s) · Vault (secrets)
classification: Internal — RESTRICTED — Security Sensitive
```

---

## 1. Roles & Descriptions

| Role | Handle | Assigned To | Provisioned By |
|---|---|---|---|
| `merchant` | — | Merchant API integrations | Automated onboarding |
| `analyst` | — | Fraud review analysts | Manager approval → Jira ticket |
| `risk_admin` | — | Risk engineering leads | CISO approval |
| `ml_engineer` | — | ML team members | Engineering Manager approval |
| `auditor` | — | Compliance, legal, QSA | @james + CISO approval |
| `sre` | — | SRE / platform engineers | Engineering Manager approval |
| `compliance` | — | @james + legal team | CISO approval |
| `service_account` | — | Internal services (scoring API, Flink, etc.) | Vault dynamic — no human assignment |

---

## 2. API Scope Matrix

Scopes are enforced at **Kong Gateway** on every request. JWT claims are validated against the required scope before the request reaches the application.

### 2.1 Scoring & Risk API (`/v1/risk/*`)

| Scope | merchant | analyst | risk_admin | ml_engineer | auditor | sre | compliance |
|---|---|---|---|---|---|---|---|
| `risk:score` — submit scoring request | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `risk:read_own` — read own decisions | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `risk:read_all` — read any decision | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| `risk:feedback` — submit outcome label | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |

### 2.2 Case Management API (`/v1/cases/*`)

| Scope | merchant | analyst | risk_admin | ml_engineer | auditor | sre | compliance |
|---|---|---|---|---|---|---|---|
| `cases:read` — view queue + case detail | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ |
| `cases:write` — assign, resolve, escalate | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `cases:admin` — batch ops, feedback | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| `cases:compliance` — SAR-flagged cases | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

### 2.3 Admin API (`/v1/rules/*`, `/v1/models/*`)

| Scope | merchant | analyst | risk_admin | ml_engineer | auditor | sre | compliance |
|---|---|---|---|---|---|---|---|
| `rules:read` — list active rules | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `rules:write` — create / update rules | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `models:read` — list model registry | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `models:deploy` — promote model | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |

### 2.4 Data Subject Rights API (`/v1/customers/*`)

| Scope | merchant | analyst | risk_admin | ml_engineer | auditor | sre | compliance |
|---|---|---|---|---|---|---|---|
| `customer:data:read` — DSAR access | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ |
| `customer:data:write` — erasure | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

### 2.5 Audit API (`/v1/audit/*`)

| Scope | merchant | analyst | risk_admin | ml_engineer | auditor | sre | compliance |
|---|---|---|---|---|---|---|---|
| `audit:read` — read audit log | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ |

---

## 3. Infrastructure Access Matrix

### 3.1 Kubernetes

| Resource | merchant | analyst | risk_admin | ml_engineer | auditor | sre | compliance |
|---|---|---|---|---|---|---|---|
| Pod logs (`kubectl logs`) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| Pod exec (`kubectl exec`) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| Deployment scaling | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| Secret read | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Cluster-admin | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

> No human role has `cluster-admin`. Cluster administration is performed via ArgoCD GitOps only — changes go through Git PR, not direct `kubectl apply`.

### 3.2 Databases

| Resource | merchant | analyst | risk_admin | ml_engineer | auditor | sre | compliance |
|---|---|---|---|---|---|---|---|
| PostgreSQL (read) | ❌ | ❌ | ❌ | ❌ | ✅ (read replica, masked) | ✅ (ops only) | ✅ (masked) |
| PostgreSQL (write) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Cassandra (read) | ❌ | ❌ | ❌ | ❌ | ✅ (audit keyspace) | ✅ (ops only) | ✅ |
| Cassandra (write) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Redis | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (ops only) | ❌ |
| Snowflake | ❌ | ❌ | ❌ | ✅ (read) | ✅ (read) | ❌ | ✅ (read) |

> All database credentials are issued by HashiCorp Vault (dynamic, 1-hour TTL). No static database passwords exist. Human database access is via Vault-issued short-lived credentials, audit-logged.

### 3.3 HashiCorp Vault

| Path | merchant | analyst | risk_admin | ml_engineer | auditor | sre | compliance |
|---|---|---|---|---|---|---|---|
| `secret/app/*` (app secrets) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `database/creds/*` (DB creds) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (read, audit-logged) | ❌ |
| `pki/*` (certificates) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| `audit/` (Vault audit log) | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ |
| Vault root token | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

> Vault root token is generated once, used to bootstrap, then revoked. No root token exists in production. Break-glass procedure documented in `docs/runbooks/vault_break_glass.md`.

### 3.4 Observability Stack

| Resource | merchant | analyst | risk_admin | ml_engineer | auditor | sre | compliance |
|---|---|---|---|---|---|---|---|
| Grafana (dashboards) | ❌ | ✅ (case SLA only) | ✅ | ✅ (ML dashboards) | ✅ (read) | ✅ | ❌ |
| Grafana (admin) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| Loki (logs) | ❌ | ❌ | ❌ | ❌ | ✅ (masked) | ✅ | ❌ |
| Jaeger (traces) | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ |
| PagerDuty | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| ArgoCD | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |

### 3.5 MLflow Model Registry

| Action | merchant | analyst | risk_admin | ml_engineer | auditor | sre | compliance |
|---|---|---|---|---|---|---|---|
| View experiments + metrics | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Log runs + artifacts | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Promote model (Staging→Production) | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Delete model versions | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## 4. Frontend Access Matrix (Elena's Dashboard)

Applies to the Next.js analyst dashboard and admin UI. Role-based route and component visibility enforced via NextAuth.js session + server-side checks.

| Surface | merchant | analyst | risk_admin | ml_engineer | auditor | compliance |
|---|---|---|---|---|---|---|
| `/dashboard/queue` | ❌ | ✅ | ✅ | ❌ | ✅ (read) | ✅ (read) |
| `/dashboard/cases/[id]` | ❌ | ✅ | ✅ | ❌ | ✅ (read) | ✅ |
| `/admin/rules` | ❌ | ✅ (read) | ✅ | ❌ | ✅ (read) | ❌ |
| `/admin/rules/edit` | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| `/models` | ❌ | ❌ | ✅ | ✅ | ✅ (read) | ❌ |
| `/merchant/reports` | ✅ (own) | ❌ | ✅ | ❌ | ✅ | ❌ |
| `/compliance` | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |

---

## 5. Service Account Scopes

Internal services authenticate via Vault Kubernetes auth (ServiceAccount JWT). Each service gets only the scopes it needs.

| Service | Vault Path | API Scopes | DB Access |
|---|---|---|---|
| `ras-scoring-api` | `k8s/risk/ras-scoring-sa` | `risk:score` | PostgreSQL write, Cassandra insert, Redis write |
| `ras-case-service` | `k8s/risk/ras-case-sa` | `cases:write` | PostgreSQL write, Cassandra insert |
| `ras-admin-api` | `k8s/risk/ras-admin-sa` | `rules:write`, `models:deploy` | PostgreSQL write |
| `ras-flink-pipeline` | `k8s/risk/ras-flink-sa` | — | Redis write (Feast), Cassandra insert |
| `ras-bentoml` | `k8s/risk/ras-bentoml-sa` | — | Redis read (Feast) |
| `ras-ml-training` | `k8s/risk/ras-ml-sa` | — | Snowflake read |
| `snowflake-sink` | `k8s/risk/ras-sink-sa` | `audit:read` | Snowflake write |
| `elasticsearch-sink` | `k8s/risk/ras-es-sa` | `audit:read` | Elasticsearch write |

---

## 6. Access Request & Provisioning

### 6.1 Human Access

```
Role            Approval Required           Process
──────────────────────────────────────────────────────
analyst         Line manager                Jira ITSM ticket → Keycloak group
risk_admin      CISO                        Jira ITSM + CISO email approval
ml_engineer     Engineering Manager         Jira ITSM ticket → Keycloak group
auditor         @james + CISO               Jira ITSM + signed NDA
compliance      CISO                        Jira ITSM + legal sign-off
sre             Engineering Manager         Jira ITSM ticket → Keycloak group
```

### 6.2 Access Review

| Review | Frequency | Owner |
|---|---|---|
| All human access review | Quarterly | `@priya` + `@james` |
| Privileged access (risk_admin, sre) | Monthly | `@priya` |
| Service account scope review | Per deployment | `@priya` (PR review) |
| Orphaned account detection | Weekly (automated) | Keycloak + PagerDuty alert |

---

## 7. Privilege Escalation Controls

| Control | Implementation |
|---|---|
| No shared credentials | Every human and service has a unique identity |
| No scope self-elevation | JWT claims are signed by Keycloak — cannot be self-modified |
| No `cluster-admin` binding | OPA Gatekeeper policy rejects any ClusterRoleBinding to `cluster-admin` |
| No Vault root token | Root token revoked post-bootstrap. Break-glass requires 2-person approval |
| Audit log of all privilege use | CloudTrail (AWS) + Vault audit log + Keycloak event log |
| MFA on all privileged roles | Enforced at Keycloak for `risk_admin`, `sre`, `compliance`, `auditor` |

---

## 8. Related Documents

| Document | Location |
|---|---|
| Encryption Specification | `docs/security/encryption_spec.md` |
| Vault Setup Guide | `docs/security/vault_setup.md` |
| Threat Model | `docs/security/threat_model.md` |
| PCI DSS Controls (Req 7, 8) | `docs/compliance/pci_dss_controls.md` |
| GDPR DPIA (data access) | `docs/compliance/gdpr_dpia.md` |
| Keycloak Config | `k8s/keycloak/` |
| OPA Gatekeeper Policies | `k8s/opa/` |

---

*Document Version: 1.0.0*
*Owner: Priya Nair — Principal Security Engineer*
*Review Cycle: Quarterly (access review) · On role/scope change*
*Classification: Internal — RESTRICTED — Security Sensitive*