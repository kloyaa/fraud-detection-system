# HashiCorp Vault Setup Guide
## Risk Assessment System (RAS) — Secrets Management

```yaml
document:       docs/security/vault_setup.md
version:        1.0.0
owner:          Priya Nair (@priya) — Principal Security Engineer
reviewers:      "@darius · @sofia · @marcus"
last_updated:   Pre-development
status:         Planned
vault_version:  1.15+
deployment:     Kubernetes (HCP Vault or self-hosted)
classification: Internal — RESTRICTED — Security Sensitive
```

---

## 1. Overview

HashiCorp Vault is the single secrets management plane for RAS. No secret — database credential, API key, signing key, or certificate — exists outside Vault in production.

### 1.1 What Vault Manages

| Secret Type | Vault Engine | TTL | Consumers |
|---|---|---|---|
| PostgreSQL credentials | Database secrets engine | 1 hour | All app services |
| Cassandra credentials | Database secrets engine | 1 hour | Scoring API, Flink |
| Redis credentials | Database secrets engine | 1 hour | Scoring API, Feature service |
| Kafka SASL credentials | KV v2 (rotated manually) | 90 days | All Kafka producers/consumers |
| AWS KMS access | AWS secrets engine | 1 hour | Scoring API (encryption) |
| JWT signing key reference | KV v2 | Manual rotation | Keycloak |
| Webhook secrets (per merchant) | KV v2 | On request | Scoring API |
| TLS certificates (internal) | PKI secrets engine | 24 hours | Istio (sidecar) |
| API keys (third-party) | KV v2 | 90 days | Enrichment service |

> *@priya:* "Vault dynamic secrets are the primary security control for credential exposure. A PostgreSQL credential that expires in 1 hour limits the blast radius of any compromise to that 1-hour window. Static passwords that live for years are pre-issued breach keys."

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────┐
│                 HashiCorp Vault                      │
│                                                      │
│  Auth Methods:                                       │
│    Kubernetes auth  ──► service accounts (pods)      │
│    OIDC auth        ──► human operators (Keycloak)   │
│    AppRole          ──► CI/CD pipelines              │
│                                                      │
│  Secrets Engines:                                    │
│    database/        ──► PostgreSQL, Cassandra, Redis │
│    aws/             ──► KMS, IAM credentials         │
│    pki/             ──► TLS cert issuance            │
│    kv/              ──► static secrets (KV v2)       │
│    transit/         ──► encryption as a service      │
│                                                      │
│  Policies:                                           │
│    ras-scoring-api  ──► scoped to scoring paths only │
│    ras-flink        ──► scoped to pipeline paths     │
│    ras-admin        ──► scoped to admin paths        │
│    ras-operator     ──► SRE break-glass access       │
└─────────────────────────────────────────────────────┘
         │                          │
         │ Vault Agent Sidecar      │ Direct API
         │ (pods)                   │ (operators)
         ▼                          ▼
  ┌─────────────┐          ┌────────────────┐
  │  App Pods   │          │  SRE / @priya  │
  │  (no Vault  │          │  (MFA via      │
  │   SDK call) │          │   Keycloak)    │
  └─────────────┘          └────────────────┘
```

---

## 3. Authentication Methods

### 3.1 Kubernetes Auth (Pods)

Every pod authenticates to Vault using its Kubernetes ServiceAccount JWT. Vault validates the JWT against the Kubernetes API and issues a Vault token scoped to that service's policy.

```hcl
# terraform/vault/auth/kubernetes.tf

resource "vault_auth_backend" "kubernetes" {
  type = "kubernetes"
  path = "kubernetes"
}

resource "vault_kubernetes_auth_backend_config" "config" {
  backend            = vault_auth_backend.kubernetes.path
  kubernetes_host    = var.kubernetes_host
  kubernetes_ca_cert = var.kubernetes_ca_cert
}

# One role per service — least privilege
resource "vault_kubernetes_auth_backend_role" "scoring_api" {
  backend                          = vault_auth_backend.kubernetes.path
  role_name                        = "ras-scoring-api"
  bound_service_account_names      = ["ras-scoring-sa"]
  bound_service_account_namespaces = ["risk"]
  token_policies                   = ["ras-scoring-api"]
  token_ttl                        = 3600    # 1 hour
  token_max_ttl                    = 86400   # 24 hours max
}
```

### 3.2 Vault Agent Sidecar (Recommended Pattern)

Application pods never call the Vault API directly. The Vault Agent sidecar handles authentication, secret fetching, and renewal. Secrets are written to a shared in-memory volume — the application reads files, not Vault.

```yaml
# k8s/scoring-api/deployment.yaml (relevant sections)

spec:
  serviceAccountName: ras-scoring-sa
  volumes:
    - name: vault-secrets
      emptyDir:
        medium: Memory    # In-memory only — never written to disk

  initContainers:
    - name: vault-agent-init
      image: hashicorp/vault:1.15
      args: ["agent", "-config=/vault/config/agent.hcl"]
      volumeMounts:
        - name: vault-secrets
          mountPath: /vault/secrets

  containers:
    - name: api
      image: ras-scoring-api:latest
      env:
        # App reads from file — never calls Vault API
        - name: DATABASE_URL_FILE
          value: /vault/secrets/database-url
      volumeMounts:
        - name: vault-secrets
          mountPath: /vault/secrets
          readOnly: true
```

```hcl
# k8s/scoring-api/vault-agent-config.hcl

auto_auth {
  method "kubernetes" {
    mount_path = "auth/kubernetes"
    config = {
      role = "ras-scoring-api"
    }
  }
  sink "file" {
    config = {
      path = "/vault/secrets/.vault-token"
    }
  }
}

template {
  source      = "/vault/templates/database-url.tpl"
  destination = "/vault/secrets/database-url"
  perms       = 0640
}
```

```
{{- with secret "database/creds/ras-scoring-api" -}}
postgresql://{{ .Data.username }}:{{ .Data.password }}@pgbouncer.ras.internal:5432/ras
{{- end }}
```

> *@priya:* "The app reads a file. It never knows Vault exists. When the credential rotates, Vault Agent rewrites the file and sends SIGHUP to the app process — zero-downtime credential rotation with no application code changes."

### 3.3 OIDC Auth (Human Operators)

Human access to Vault is via Keycloak OIDC — same IdP as the RAS API. MFA is enforced at Keycloak for all Vault-accessing roles.

```hcl
resource "vault_jwt_auth_backend" "oidc" {
  type               = "oidc"
  path               = "oidc"
  oidc_discovery_url = "https://auth.ras.internal/realms/ras"
  oidc_client_id     = var.vault_oidc_client_id
  oidc_client_secret = var.vault_oidc_client_secret
  default_role       = "operator"
}

resource "vault_jwt_auth_backend_role" "operator" {
  backend        = vault_jwt_auth_backend.oidc.path
  role_name      = "operator"
  role_type      = "oidc"
  bound_audiences = ["vault"]
  user_claim     = "sub"
  groups_claim   = "groups"
  token_policies = ["ras-operator"]
  token_ttl      = 3600
}
```

---

## 4. Secrets Engines

### 4.1 Database Secrets Engine — PostgreSQL

```hcl
# terraform/vault/engines/database_postgres.tf

resource "vault_database_secret_backend_engine" "postgres" {
  backend = vault_mount.database.path
  name    = "ras-postgres"
  plugin_name = "postgresql-database-plugin"

  connection_url = "postgresql://{{username}}:{{password}}@postgres.ras.internal:5432/ras"

  allowed_roles = [
    "ras-scoring-api",
    "ras-case-service",
    "ras-admin-api",
    "ras-readonly",
  ]

  root_rotation_statements = [
    "ALTER USER \"{{name}}\" WITH PASSWORD '{{password}}';"
  ]
}

resource "vault_database_secret_backend_role" "scoring_api" {
  backend = vault_mount.database.path
  name    = "ras-scoring-api"
  db_name = vault_database_secret_backend_engine.postgres.name

  creation_statements = [
    "CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}';",
    "GRANT INSERT, SELECT ON risk_decisions TO \"{{name}}\";",
    "GRANT INSERT ON risk_events TO \"{{name}}\";",
  ]

  revocation_statements = [
    "REVOKE ALL ON ALL TABLES IN SCHEMA public FROM \"{{name}}\";",
    "DROP ROLE IF EXISTS \"{{name}}\";",
  ]

  default_ttl = "1h"
  max_ttl     = "4h"
}
```

**Per-role database privileges (least privilege):**

| Vault Role | PostgreSQL Grants |
|---|---|
| `ras-scoring-api` | INSERT on `risk_decisions`, `risk_events` · SELECT on `rules`, `customers` |
| `ras-case-service` | INSERT, UPDATE on `cases` · SELECT on `risk_decisions` |
| `ras-admin-api` | INSERT, UPDATE on `rules`, `models` |
| `ras-readonly` | SELECT on all tables (auditor access) |

### 4.2 Database Secrets Engine — Cassandra

```hcl
resource "vault_database_secret_backend_engine" "cassandra" {
  backend     = vault_mount.database.path
  name        = "ras-cassandra"
  plugin_name = "cassandra-database-plugin"

  hosts    = ["cassandra-0.ras.internal", "cassandra-1.ras.internal"]
  username = var.cassandra_root_user
  password = var.cassandra_root_password

  allowed_roles = ["ras-scoring-api", "ras-flink"]
}

resource "vault_database_secret_backend_role" "cassandra_scoring" {
  backend = vault_mount.database.path
  name    = "ras-cassandra-scoring"
  db_name = vault_database_secret_backend_engine.cassandra.name

  creation_statements = [
    "CREATE USER '{{username}}' WITH PASSWORD '{{password}}' NOSUPERUSER;",
    "GRANT INSERT ON risk.events TO '{{username}}';",
  ]

  default_ttl = "1h"
  max_ttl     = "4h"
}
```

### 4.3 PKI Secrets Engine (Internal TLS)

Used for internal service certificates. Istio uses this as a backend CA for workload certificate issuance.

```hcl
resource "vault_mount" "pki_int" {
  path                      = "pki_int"
  type                      = "pki"
  default_lease_ttl_seconds = 86400     # 24 hours
  max_lease_ttl_seconds     = 2592000   # 30 days
}

resource "vault_pki_secret_backend_role" "ras_service" {
  backend          = vault_mount.pki_int.path
  name             = "ras-service"
  allowed_domains  = ["ras.internal", "risk.svc.cluster.local"]
  allow_subdomains = true
  max_ttl          = "24h"
  key_type         = "ec"
  key_bits         = 256
  require_cn       = false
}
```

### 4.4 KV v2 — Static Secrets

```hcl
# Path structure for KV v2 static secrets

secret/
  ras/
    kafka/
      producer/          ← SASL credentials (90-day rotation)
      consumer/
    enrichment/
      maxmind/           ← MaxMind API key
      ipqualityscore/    ← IPQualityScore API key
    webhooks/
      merchants/
        {merchant_id}/   ← Per-merchant HMAC secret
    jwt/
      keycloak/          ← Keycloak client secret (reference only)
```

---

## 5. Vault Policies

Policies follow least-privilege. Each service can only access its own secret paths.

```hcl
# terraform/vault/policies/ras-scoring-api.hcl

# Database credentials
path "database/creds/ras-scoring-api" {
  capabilities = ["read"]
}

# Cassandra credentials
path "database/creds/ras-cassandra-scoring" {
  capabilities = ["read"]
}

# KMS access (envelope encryption)
path "aws/creds/ras-kms-role" {
  capabilities = ["read"]
}

# Kafka producer credentials
path "secret/data/ras/kafka/producer" {
  capabilities = ["read"]
}

# Enrichment API keys
path "secret/data/ras/enrichment/+" {
  capabilities = ["read"]
}

# Merchant webhook secrets (own merchant only — enforced by app)
path "secret/data/ras/webhooks/merchants/+" {
  capabilities = ["read"]
}

# Explicit deny — scoring API cannot access other services' secrets
path "secret/data/ras/kafka/consumer" {
  capabilities = ["deny"]
}
path "database/creds/ras-admin-api" {
  capabilities = ["deny"]
}
```

---

## 6. Bootstrap Procedure

> ⚠️ **Run once only.** After bootstrap, the root token is revoked. All subsequent access is via auth methods.

```bash
# Step 1: Initialise Vault
vault operator init \
  -key-shares=5 \
  -key-threshold=3 \
  -format=json > vault-init.json

# CRITICAL: Store unseal keys in AWS Secrets Manager (separate account)
# CRITICAL: Store root token temporarily — revoke after bootstrap
aws secretsmanager create-secret \
  --name "ras/vault/unseal-keys" \
  --secret-string "$(cat vault-init.json)"

# Step 2: Unseal (requires 3 of 5 key holders)
vault operator unseal $UNSEAL_KEY_1
vault operator unseal $UNSEAL_KEY_2
vault operator unseal $UNSEAL_KEY_3

# Step 3: Login with root token (bootstrap only)
vault login $ROOT_TOKEN

# Step 4: Enable auth methods
vault auth enable kubernetes
vault auth enable -path=oidc jwt

# Step 5: Enable secrets engines
vault secrets enable -path=database database
vault secrets enable -path=secret -version=2 kv
vault secrets enable pki
vault secrets enable -path=pki_int pki
vault secrets enable aws

# Step 6: Apply all policies (Terraform)
cd terraform/vault && terraform apply

# Step 7: REVOKE root token — no exceptions
vault token revoke $ROOT_TOKEN
echo "Root token revoked. Verify:"
vault token lookup $ROOT_TOKEN   # Should return 403

# Step 8: Verify Kubernetes auth works
vault write auth/kubernetes/login \
  role=ras-scoring-api \
  jwt=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
```

---

## 7. Auto-Unseal

Vault is configured for auto-unseal via AWS KMS — eliminates the need for manual unseal key holders on pod restart.

```hcl
# terraform/vault/main.tf

seal "awskms" {
  region     = "us-east-1"
  kms_key_id = var.vault_unseal_kms_key_id
}
```

> Manual unseal keys (Shamir shares) are still generated and stored in AWS Secrets Manager as a break-glass fallback if KMS becomes unavailable.

---

## 8. Audit Logging

All Vault operations are logged — who accessed what secret, when, from which IP.

```bash
# Enable file audit log (to stdout for log aggregation)
vault audit enable file file_path=stdout

# Enable syslog audit (backup)
vault audit enable syslog
```

Audit log fields:

```json
{
  "time":      "2024-03-15T14:23:07Z",
  "type":      "response",
  "auth": {
    "client_token": "hmac-sha256:...",
    "accessor":     "accessor-id",
    "policies":     ["ras-scoring-api"],
    "entity_id":    "entity-uuid",
    "metadata": {
      "service_account_name":      "ras-scoring-sa",
      "service_account_namespace": "risk"
    }
  },
  "request": {
    "operation": "read",
    "path":      "database/creds/ras-scoring-api",
    "remote_address": "10.0.1.45"
  }
}
```

Audit logs flow: Vault stdout → Loki (log aggregation) → Elasticsearch (searchable) → Snowflake (7-year retention — AML compliance).

**PCI DSS Req 10.2.1(b):** All Vault audit logs satisfy the requirement to log all actions by administrators and privileged accounts.

---

## 9. Break-Glass Procedure

For emergency access when normal auth methods are unavailable.

```
Trigger:    Vault sealed + KMS auto-unseal failed
            OR Kubernetes auth unavailable
            OR OIDC/Keycloak unavailable

Requires:   2-person authorisation (@priya + CISO)
            Jira ITSM emergency ticket
            PagerDuty P1 incident opened

Steps:
  1. Retrieve unseal keys from AWS Secrets Manager
     (requires separate AWS account access — @priya + @darius jointly)
  2. Manually unseal: vault operator unseal (3 of 5 keys)
  3. Use break-glass AppRole credentials (stored in AWS Secrets Manager)
  4. Perform necessary remediation
  5. Rotate ALL break-glass credentials after use
  6. Document all actions in Jira ticket
  7. Post-incident review within 48h

Runbook: docs/runbooks/vault_break_glass.md
```

---

## 10. Monitoring & Alerts

| Alert | Condition | Severity |
|---|---|---|
| Vault sealed | `vault_core_unsealed == 0` | P1 |
| Auth failure spike | `vault_auth_failures > 10/min` | P1 |
| Root token active | `vault_token_lookup{type="root"} > 0` | P1 |
| Lease expiry failures | `vault_expire_num_leases > threshold` | P2 |
| Audit log disabled | `vault_audit_log_request_count == 0` for 5 min | P1 |
| High secret read rate | `vault_secret_kv_read > 10k/min` | P2 |

---

## 11. Related Documents

| Document | Location |
|---|---|
| Encryption Specification | `docs/security/encryption_spec.md` |
| RBAC Matrix | `docs/security/rbac_matrix.md` |
| Threat Model | `docs/security/threat_model.md` |
| ADR-003 (KMS Encryption) | `docs/architecture/adr/ADR-003-kms-envelope-encryption.md` |
| ADR-007 (Istio mTLS) | `docs/architecture/adr/ADR-007-istio-mtls.md` |
| PCI DSS Controls (Req 3, 8) | `docs/compliance/pci_dss_controls.md` |
| Break-Glass Runbook | `docs/runbooks/vault_break_glass.md` |

---

*Document Version: 1.0.0*
*Owner: Priya Nair — Principal Security Engineer*
*Review Cycle: Quarterly · On any Vault version upgrade*
*Classification: Internal — RESTRICTED — Security Sensitive*