# System Hardening Standards
## Risk Assessment System (RAS) — Security Configuration Baselines

```yaml
document:       docs/security/hardening_standards.md
version:        1.0.0
owner:          Priya Nair (@priya) — Principal Security Engineer
reviewers:      "@darius · @sofia · @marcus"
last_updated:   Pre-development
status:         ⏳ Planned
references:     CIS Benchmarks · NIST SP 800-123 · PCI DSS v4.0 Req 2.2
classification: Internal — RESTRICTED — Security Sensitive
```

---

## 1. Purpose

This document defines the minimum security configuration baseline for every system component in the RAS Cardholder Data Environment (CDE). All components must meet these standards before being admitted to production. Compliance is verified during the PRR (Section §4 Security gates) and by quarterly automated scanning.

> *@priya:* "A hardening standard is only useful if it is enforced — not aspirational. Every standard in this document has a corresponding automated check: Trivy, Checkov, kube-bench, or Semgrep. If the check does not exist yet, the standard does not yet count as implemented."

---

## 2. Container & Image Standards

### 2.1 Base Image Requirements

| Standard | Requirement | Enforcement |
|---|---|---|
| Base image | Distroless or Alpine only — no Debian/Ubuntu full images | Trivy `--scanners vuln` in CI |
| Image tag | Pinned SHA digest — no `latest` tag in production | OPA Gatekeeper policy `deny-latest-tag` |
| Non-root user | All containers run as non-root UID ≥ 1000 | Pod Security Standards (Restricted) |
| Read-only root filesystem | `readOnlyRootFilesystem: true` | Pod Security Standards (Restricted) |
| No privileged containers | `privileged: false` always | Pod Security Standards (Restricted) |
| No `hostPID` / `hostNetwork` | Both must be `false` | Pod Security Standards (Restricted) |
| SBOM | Software Bill of Materials generated per build | Syft in CI pipeline |
| Image signing | All production images signed with Cosign | Cosign + Sigstore |

### 2.2 Build Pipeline Standards

| Standard | Requirement | Enforcement |
|---|---|---|
| No secrets in image layers | Secret scanning on every image build | Trivy `--scanners secret` |
| No CRITICAL CVEs | Zero CRITICAL CVEs — pipeline fails | Trivy `--exit-code 1 --severity CRITICAL` |
| HIGH CVEs | Documented exception required from `@priya` | Trivy + manual gate |
| Reproducible builds | Dependency hash pinning (`requirements.txt` + `pnpm-lock.yaml`) | CI hash verification |
| Multi-stage builds | Final image contains only runtime artifacts | Dockerfile review in PR |

```dockerfile
# Compliant Dockerfile pattern
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM gcr.io/distroless/python3-debian12 AS runtime
COPY --from=builder /app /app
USER 1000:1000                        # Non-root
WORKDIR /app
EXPOSE 8000
ENTRYPOINT ["python", "-m", "uvicorn", "app.main:app"]
```

---

## 3. Kubernetes Hardening Standards

### 3.1 Pod Security Standards

All RAS namespaces enforce the `Restricted` Pod Security Standard:

```yaml
# k8s/namespaces/risk.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: risk
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit:   restricted
    pod-security.kubernetes.io/warn:    restricted
```

The `Restricted` profile enforces:
- No privileged escalation (`allowPrivilegeEscalation: false`)
- Read-only root filesystem
- Non-root user and group
- Dropped `ALL` capabilities
- seccomp `RuntimeDefault` or `Localhost` profile

### 3.2 Required Security Context (All Pods)

```yaml
# Required on every RAS pod — enforced by OPA Gatekeeper
securityContext:
  runAsNonRoot:             true
  runAsUser:                1000
  runAsGroup:               1000
  fsGroup:                  1000
  seccompProfile:
    type:                   RuntimeDefault
containers:
  - securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem:   true
      capabilities:
        drop: ["ALL"]
```

### 3.3 Network Policy Standards

```yaml
# Default-deny all ingress and egress — applied to every namespace
# Explicit allow rules defined per service in k8s/network-policies/
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: risk
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

Explicit allow rules required for every communication path. No wildcard selectors in production.

### 3.4 RBAC Standards

| Standard | Requirement |
|---|---|
| No `cluster-admin` bindings | OPA Gatekeeper rejects any `ClusterRoleBinding` to `cluster-admin` |
| Least-privilege ServiceAccounts | Each pod has a dedicated ServiceAccount with minimum RBAC |
| No default ServiceAccount | `automountServiceAccountToken: false` on all pods that don't need API access |
| No wildcard RBAC rules | `resources: ["*"]` and `verbs: ["*"]` blocked by OPA Gatekeeper |

### 3.5 OPA Gatekeeper Policies

| Policy | Blocks |
|---|---|
| `deny-latest-tag` | Images tagged `:latest` |
| `deny-cluster-admin` | `ClusterRoleBinding` to `cluster-admin` |
| `require-resource-limits` | Pods without CPU/memory `limits` |
| `require-liveness-probe` | Pods without `livenessProbe` |
| `require-readiness-probe` | Pods without `readinessProbe` |
| `deny-privileged` | `privileged: true` containers |
| `require-non-root` | Containers running as root (UID 0) |
| `deny-host-namespaces` | `hostPID`, `hostNetwork`, `hostIPC` |

---

## 4. Operating System & Node Standards

All EKS worker nodes use Amazon Linux 2023 with the following hardening applied via Terraform/Karpenter:

| Standard | Requirement | Basis |
|---|---|---|
| OS patching | Automated via Karpenter node replacement — nodes replaced weekly | CIS Amazon Linux 2023 Benchmark |
| SSH access | Disabled — no SSH to production nodes. Access via `kubectl exec` only (SRE role) | CIS Level 1 |
| Instance metadata service | IMDSv2 required — `http-put-response-hop-limit: 1` | AWS Security Best Practices |
| EBS encryption | All EBS volumes encrypted at rest (AWS KMS) | PCI DSS Req 3.5.1 |
| Audit daemon | `auditd` enabled with CIS ruleset | CIS Level 2 |
| Core dumps | Disabled — `fs.suid_dumpable = 0` | CIS Level 1 |
| Unused services | No unnecessary services running on nodes | CIS Level 1 |

```hcl
# terraform/eks/node_groups.tf — IMDSv2 enforcement
resource "aws_launch_template" "ras_nodes" {
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"    # IMDSv2 only
    http_put_response_hop_limit = 1             # Prevents SSRF via metadata
  }
  block_device_mappings {
    ebs {
      encrypted   = true
      kms_key_id  = var.ebs_kms_key_arn
    }
  }
}
```

---

## 5. Database Hardening Standards

### 5.1 PostgreSQL

| Standard | Requirement |
|---|---|
| Superuser access | `postgres` superuser disabled in production. `pg_hba.conf` rejects superuser login |
| SSL enforcement | `ssl = on`, `ssl_min_protocol_version = TLSv1.3` |
| `log_connections` | `on` — all connection attempts logged |
| `log_disconnections` | `on` |
| `log_statement` | `ddl` — all DDL statements logged (schema changes) |
| `password_encryption` | `scram-sha-256` — no md5 passwords |
| Unused extensions | Only `pgvector` and `pg_stat_statements` enabled |
| Default port | Changed from `5432` to non-standard (via Terraform) |
| Public schema | `REVOKE CREATE ON SCHEMA public FROM PUBLIC` |

### 5.2 Cassandra

| Standard | Requirement |
|---|---|
| Default credentials | `cassandra/cassandra` default user removed. Service accounts only via Vault |
| Client encryption | `enabled: true` in `cassandra.yaml` — TLS 1.3 |
| Internode encryption | `all` — all node-to-node traffic encrypted |
| Authenticator | `PasswordAuthenticator` (not `AllowAllAuthenticator`) |
| Authorizer | `CassandraAuthorizer` (not `AllowAllAuthorizer`) |
| JMX | Disabled on all production nodes |
| `nodetool` | Requires authentication |

### 5.3 Redis

| Standard | Requirement |
|---|---|
| AUTH password | Required — Vault-issued, 64-char random |
| `rename-command` | `FLUSHALL`, `FLUSHDB`, `CONFIG`, `DEBUG` renamed or disabled |
| `bind` | Bound to cluster-internal IPs only — not `0.0.0.0` |
| TLS | `tls-port` enabled, plain port disabled |
| `protected-mode` | `yes` |
| `maxmemory-policy` | `allkeys-lru` — prevents OOM eviction corruption |

---

## 6. Application Hardening Standards

### 6.1 Python / FastAPI

| Standard | Requirement | Enforcement |
|---|---|---|
| Dependency pinning | All deps pinned with hashes in `requirements.txt` | CI hash verification |
| `bandit` | Zero HIGH/CRITICAL findings | CI gate |
| `semgrep` | Zero security findings (p/python ruleset) | CI gate |
| No `eval()` / `exec()` | Never used in application code | Semgrep rule |
| No `pickle` for untrusted data | Only for internal ML model serialization (MLflow managed) | Semgrep rule |
| No `shell=True` in `subprocess` | Always use list form | Semgrep rule |
| `secrets` module | Used for all token/key generation — never `random` | Semgrep rule |
| SQL queries | Parameterised only — no string interpolation | Semgrep + code review |
| Logging | No PII, no secrets in log output | structlog middleware + PRR gate |

### 6.2 Next.js / TypeScript (Frontend)

| Standard | Requirement | Enforcement |
|---|---|---|
| CSP headers | `script-src 'self' 'nonce-{nonce}'` — no `unsafe-inline` | `next.config.ts` headers |
| `X-Frame-Options` | `DENY` | `next.config.ts` headers |
| `X-Content-Type-Options` | `nosniff` | `next.config.ts` headers |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | `next.config.ts` headers |
| No JWT in `localStorage` | Session cookie (httpOnly, Secure, SameSite=Strict) only | NextAuth.js config |
| Dependency audit | `pnpm audit --audit-level high` | CI gate |
| TypeScript strict | `strict: true` + `noUncheckedIndexedAccess` | `tsconfig.json` |
| No `dangerouslySetInnerHTML` | Blocked unless explicitly reviewed | ESLint rule |

```typescript
// next.config.ts — Required security headers
const securityHeaders = [
  { key: "X-Frame-Options",           value: "DENY" },
  { key: "X-Content-Type-Options",    value: "nosniff" },
  { key: "Referrer-Policy",           value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy",        value: "camera=(), microphone=(), geolocation=()" },
  {
    key: "Content-Security-Policy",
    value: [
      "default-src 'self'",
      "script-src 'self' 'nonce-{nonce}'",
      "style-src 'self' 'unsafe-inline'",   // Tailwind requires — reviewed
      "img-src 'self' data:",
      "connect-src 'self'",
      "frame-ancestors 'none'",
    ].join("; "),
  },
];
```

---

## 7. Network & TLS Standards

| Standard | Requirement |
|---|---|
| Minimum TLS version | TLS 1.3 (external) · TLS 1.3 (internal via Istio) |
| TLS 1.0 / 1.1 | Blocked at Cloudflare WAF — hard reject |
| TLS 1.2 | Blocked (RAS baseline is stricter than PCI minimum) |
| Certificate validity | Maximum 90 days (auto-renewed via AWS ACM / Istio Citadel) |
| HSTS | `max-age=31536000; includeSubDomains; preload` |
| Certificate transparency | Enforced via Cloudflare |
| Self-signed certificates | Not permitted in production — Istio Citadel CA or AWS ACM only |
| Cipher suites | TLS_AES_256_GCM_SHA384, TLS_CHACHA20_POLY1305_SHA256 only |

---

## 8. Secrets Management Standards

| Standard | Requirement |
|---|---|
| No secrets in code | Semgrep `hardcoded-secret` rule — CI failure |
| No secrets in env vars | Vault Agent Sidecar injects secrets as in-memory files only |
| No secrets in Kubernetes Secrets | OPA Gatekeeper policy rejects unencrypted K8s Secrets containing known secret patterns |
| No secrets in CI env vars | GitHub OIDC + Vault — short-lived tokens only, no static secrets |
| No secrets in container images | Trivy `--scanners secret` — CI failure |
| No secrets in logs | structlog middleware masks known secret patterns |
| Secret rotation | All secrets rotate on schedule — see `docs/security/encryption_spec.md` §6 |

---

## 9. Compliance Mapping

| Standard | PCI DSS v4.0 | CIS Benchmark | NIST |
|---|---|---|---|
| Container hardening | Req 2.2, 6.3 | CIS Docker 1.6 | SP 800-190 |
| K8s Pod Security | Req 2.2, 7.2 | CIS K8s 1.8 | SP 800-190 |
| OS hardening | Req 2.2 | CIS Amazon Linux 2023 | SP 800-123 |
| DB hardening | Req 2.2, 8.3 | CIS PostgreSQL 16 | SP 800-123 |
| TLS standards | Req 4.2.1 | — | SP 800-52r2 |
| Secrets management | Req 3.7, 8.6 | — | SP 800-57 |
| Application security | Req 6.2, 6.4 | OWASP Top 10 | SP 800-53 |

---

## 10. Verification & Scanning Schedule

| Scan | Tool | Schedule | Gate |
|---|---|---|---|
| Container vulnerability scan | Trivy | Every build | CI failure on CRITICAL |
| K8s config scan | Checkov / kube-bench | Every PR | CI warning → weekly gate |
| OPA policy enforcement | OPA Gatekeeper | Every admission | Hard block |
| Dependency SCA | Snyk + Dependabot | Every PR + daily | CI failure on CRITICAL |
| SAST | Bandit + Semgrep | Every PR | CI failure on HIGH/CRITICAL |
| Secret scanning | Trivy + Gitleaks | Every commit + build | CI failure |
| Runtime anomaly | Falco | Continuous | PagerDuty P1 alert |
| TLS configuration | `testssl.sh` | Weekly | Report to `@priya` |
| CIS benchmark | `kube-bench` | Weekly | Report to `@darius` |

---

## 11. Related Documents

| Document | Location |
|---|---|
| Threat Model | `docs/security/threat_model.md` |
| Encryption Specification | `docs/security/encryption_spec.md` |
| RBAC Matrix | `docs/security/rbac_matrix.md` |
| Vault Setup Guide | `docs/security/vault_setup.md` |
| PCI DSS Controls (Req 2) | `docs/compliance/pci_dss_controls.md` |
| ADR-007 (Istio mTLS) | `docs/architecture/adr/ADR-007-istio-mtls.md` |

---

*Document Version: 1.0.0*
*Owner: Priya Nair — Principal Security Engineer*
*Review Cycle: Quarterly · On any infrastructure or toolchain change*
*Classification: Internal — RESTRICTED — Security Sensitive*