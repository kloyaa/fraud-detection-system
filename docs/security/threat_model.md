# Threat Model
## Risk Assessment System (RAS) — Security Threat Analysis
<!-- filepath: docs/security/threat_model.md -->

```yaml
document:       docs/security/threat_model.md
version:        1.0.0
owner:          Priya Nair (@priya) — Principal Security Engineer
reviewers:      "@marcus · @james · @darius · @sofia"
methodology:    STRIDE + PASTA (Process for Attack Simulation and Threat Analysis)
last_updated:   Pre-development
status:         Approved — pending external pentest validation (B-002)
classification: Internal — RESTRICTED — Security Sensitive
```

---

## 1. Purpose & Scope

This document defines the threat model for the Risk Assessment System. It enumerates the attack surface, identifies threats using the STRIDE methodology, assigns risk ratings, and maps mitigating controls to each threat.

The threat model is a living document. It is updated:
- Before every Production Readiness Review (PRR)
- After every security incident or near-miss
- When new services, external dependencies, or data categories are added
- Annually as a scheduled security review

**Scope:** All components of RAS within the Cardholder Data Environment (CDE) and systems that could impact the security of cardholder data. This includes the Scoring API, Case Management API, Admin API, ML Inference Service, Kafka brokers, PostgreSQL, Cassandra, Redis, Neo4j, and all network paths between them.

**Out of Scope:** Merchant client-side implementations, end-user browsers, and third-party enrichment providers (covered by vendor risk assessments).

---

## 2. Assets & Trust Boundaries

### 2.1 Critical Assets

| Asset | Classification | Location | Sensitivity |
|---|---|---|---|
| Cardholder PAN (tokenized) | Restricted | PostgreSQL (encrypted) | PCI DSS Scope |
| Risk scoring models (weights) | Confidential | BentoML / MLflow | IP — adversarial misuse risk |
| Rule engine definitions | Confidential | PostgreSQL | IP — evasion risk if disclosed |
| SHAP feature attributions | Confidential | Cassandra | Adversarial intelligence if disclosed |
| API signing keys (HMAC) | Restricted | HashiCorp Vault | Forgery risk |
| JWT signing key (RS256 private) | Restricted | HashiCorp Vault / Keycloak | Token forgery risk |
| Database credentials | Restricted | HashiCorp Vault (dynamic) | Lateral movement |
| Audit log | Restricted | Cassandra (immutable) | Tamper = PCI DSS violation |
| Customer PII | Confidential | PostgreSQL (encrypted PII fields) | GDPR / PCI DSS |
| ML training data | Confidential | Snowflake | Privacy, model inversion |

### 2.2 Trust Boundaries

```
BOUNDARY 0: Internet → Cloudflare WAF
  All external traffic crosses here first.
  Untrusted by default.

BOUNDARY 1: Cloudflare → Kong API Gateway
  Rate limiting, JWT validation, WAF rules enforced here.
  Partially trusted after JWT validation.

BOUNDARY 2: Kong → Internal Services (Istio mTLS)
  mTLS peer authentication. All east-west traffic encrypted.
  Service identity verified by Istio CA certificate.
  Trusted for service-to-service — NOT trusted for data content.

BOUNDARY 3: Application → Data Stores
  Application credentials issued by Vault (dynamic, short-lived).
  Parameterized queries only. No direct DB access from outside boundary.

BOUNDARY 4: Internal Services → Kafka
  SASL/SCRAM authentication. TLS in transit. Schema registry enforcement.
  Producers and consumers authenticated per service identity.

BOUNDARY 5: RAS → External Enrichment APIs
  Outbound only. Allowlisted IP egress. TLS 1.3.
  Responses treated as untrusted input — validated before use.
```

---

## 3. STRIDE Threat Analysis

STRIDE categories: **S**poofing · **T**ampering · **R**epudiation · **I**nformation Disclosure · **D**enial of Service · **E**levation of Privilege

Risk rating: **CRITICAL** · **HIGH** · **MEDIUM** · **LOW**

---

### 3.1 Spoofing Threats

| ID | Threat | Target | Risk | Control | Status |
|---|---|---|---|---|---|
| S-001 | Forged JWT token — attacker mints arbitrary claims | Scoring API, Case API | HIGH | RS256 asymmetric signing (private key in Keycloak only). Short expiry (15 min). Public key JWKS endpoint for validation. | ⏳ Planned |
| S-002 | API key theft — stolen merchant API key used to score transactions | Kong Gateway | HIGH | API key rotation on suspected compromise. Per-key rate limiting. Anomaly detection on key usage pattern. | ⏳ Planned |
| S-003 | Service identity spoofing — rogue pod claims to be scoring API | Internal services | HIGH | Istio mTLS STRICT mode. Certificate issued by Istio CA per service account. Peer authentication policy enforced at sidecar. | ⏳ Planned |
| S-004 | Webhook replay — attacker resends a previously captured webhook | Webhook consumers | MEDIUM | HMAC-SHA256 signature with timestamp. Timestamp validated within 300-second window. `hmac.compare_digest` for timing-safe comparison. | ⏳ Planned |
| S-005 | Refresh token theft — stolen refresh token used to maintain access | Keycloak | HIGH | Refresh token rotation on use. Single-use refresh tokens. Revocation on suspicious activity. Short-lived (24h). | ⏳ Planned |

**Deep Dive — S-001 (JWT Forgery):**

> *@priya:* "The reason we use RS256 over HS256 is exactly this threat. With HS256, every service that validates tokens holds the signing key — scoring API, case API, admin API, internal tooling. An attacker who compromises any one validation service obtains the key and can mint tokens with arbitrary claims, including `risk_admin` scope. With RS256, the private key never leaves Keycloak. An attacker who compromises a validation service gets the public key — which is already public. Token forgery is impossible without the private key."

**Residual Risk — S-001:**
Keycloak itself is the private key custodian. Compromise of Keycloak is a catastrophic spoofing event. Mitigations: Keycloak runs in an isolated namespace with restricted network policy. Private key material is stored in HSM-backed AWS KMS via Keycloak's PKCS#11 provider. Keycloak access is MFA-enforced for all administrators.

---

### 3.2 Tampering Threats

| ID | Threat | Target | Risk | Control | Status |
|---|---|---|---|---|---|
| T-001 | Audit log tampering — attacker modifies or deletes scoring decisions | Cassandra | CRITICAL | Cassandra append-only schema (no UPDATE/DELETE operations). Application service account has INSERT-only privileges. Separate read-only account for audit queries. | ⏳ Planned |
| T-002 | Rule tampering — attacker modifies production rules to suppress fraud detection | PostgreSQL rules table | CRITICAL | Rule changes require `rules:write` scope (restricted to risk_admin role). All rule changes versioned and published to Kafka `rules.changed` topic. Rule change audit trail in Cassandra. | ⏳ Planned |
| T-003 | Model weight tampering — attacker substitutes a backdoored ML model | BentoML / MLflow | HIGH | Model artifacts stored in MLflow with SHA-256 content hash. Promotion requires @aisha PRR sign-off. Model integrity verified at BentoML load time against MLflow registry hash. | ⏳ Planned |
| T-004 | Feature store poisoning — attacker injects fraudulent feature values into Feast/Redis | Redis (Feast online store) | HIGH | Redis AUTH + ACL rules (write access restricted to Flink pipeline service account). Feature values include provenance metadata. Anomalous feature value distribution alerts via Evidently AI. | ⏳ Planned |
| T-005 | Database migration tampering — attacker introduces malicious migration | Alembic / PostgreSQL | MEDIUM | Migrations reviewed via PR process. Migration files checked into Git (immutable history). SHA-256 hash of migration files verified in CI before apply. | ⏳ Planned |
| T-006 | In-transit payload modification — MITM modifies scoring request in flight | Network | HIGH | TLS 1.3 on all external paths. Istio mTLS on all internal paths. Certificate pinning for high-value internal service calls. | ⏳ Planned |

**Deep Dive — T-001 (Audit Log Tampering):**

> *@priya:* "PCI DSS Requirement 10.3.2 requires that audit logs are protected from destruction and unauthorised modifications. The architectural control here is not application-level access control — application-level controls can be bypassed. The control is the Cassandra schema: the application service account has INSERT privilege only, not UPDATE or DELETE. There is no code path in the application that can modify or delete an existing audit record, regardless of what the application is instructed to do. To tamper with the audit log, an attacker must compromise the Cassandra cluster directly — which is protected by network policy (no external access), mTLS, and AWS VPC isolation."

**Open Gap — T-004:**
Redis ACL rules restrict write access to the Flink pipeline service account. However, the Flink service account has broad write access to all Feast feature keys. A compromised Flink pod could write arbitrary feature values. Compensating control: Evidently AI drift detection alerts on feature distribution anomalies. Full mitigation requires per-feature-key ACL rules in Redis — to be scheduled.

---

### 3.3 Repudiation Threats

| ID | Threat | Target | Risk | Control | Status |
|---|---|---|---|---|---|
| R-001 | Denied scoring decision — merchant claims a decision was not made | Audit trail | HIGH | Every decision written to immutable Cassandra log with timestamp, request payload hash, model version, and decision. Non-repudiable. | ⏳ Planned |
| R-002 | Analyst action denial — analyst denies making a case resolution | Case management | HIGH | Every case action logged with analyst identity (from JWT `sub` claim), timestamp, IP, and full resolution note. Written to Cassandra on commit. | ⏳ Planned |
| R-003 | Rule change denial — admin denies modifying a rule | Rule audit trail | MEDIUM | Rule changes versioned in PostgreSQL with `created_by` (JWT identity), timestamp, and diff. Published to Kafka `rules.changed` with the same identity. | ⏳ Planned |
| R-004 | SAR filing denial — compliance officer denies filing or not filing a SAR | SAR audit trail | CRITICAL | SAR investigation actions logged to a segregated, compliance-only Cassandra keyspace. Access log maintained. @james owns this audit trail. | ⏳ Planned |

**Audit Log Integrity Architecture:**

```
Every auditable event writes to:

  1. PostgreSQL (application record — OLTP)
  2. Cassandra risk.events (immutable audit log — primary)
  3. Kafka risk.events (for downstream consumers)
  4. Elasticsearch (searchable audit index)

The Cassandra write is synchronous with the scoring response.
PostgreSQL and Elasticsearch writes are async (non-blocking).

If Cassandra write fails:
  → Kafka DLQ buffers the event
  → DLQ consumer retries until Cassandra recovers
  → Alert fires: see runbook docs/runbooks/cassandra_write_failure.md
  → Decision is returned to client with audit_flag: "PENDING"
```

---

### 3.4 Information Disclosure Threats

| ID | Threat | Target | Risk | Control | Status |
|---|---|---|---|---|---|
| I-001 | PAN exposure in logs | Log aggregation (Loki) | CRITICAL | Structured log middleware masks all fields matching PAN patterns (regex + Luhn check) before writing. PRR gate 5.5 verifies zero PAN in log sample. | ⏳ Planned |
| I-002 | PII exposure via API response | Scoring API responses | HIGH | API responses never include raw PAN, CVV, or full card number. BIN (6 digits) and last four only. PII fields masked in all error responses. | ⏳ Planned |
| I-003 | Model internals disclosure via API | Scoring API | HIGH | SHAP values not returned in standard API response. Available only via `/score explain` with `risk:read_all` scope. Rule definitions not exposed externally. | ⏳ Planned |
| I-004 | Training data exfiltration via model inversion | ML models | MEDIUM | Models trained on pseudonymised data. No raw PII in training features. Model inversion attack surface reduced by feature abstraction layer. | ⏳ Planned |
| I-005 | East-west traffic sniffing | Internal network | HIGH | Istio mTLS STRICT mode on all service-to-service communication. Unencrypted east-west traffic is impossible when STRICT mode is active. | ⏳ Planned |
| I-006 | Database credential exposure | PostgreSQL, Redis, Cassandra | CRITICAL | HashiCorp Vault dynamic credentials. Time-limited (1-hour TTL). Never stored in environment variables, config files, or Kubernetes Secrets. | ⏳ Planned |
| I-007 | SHAP values as adversarial intelligence | Analyst interface | HIGH | SHAP values accessible only to analysts (cases:read scope). Not exposed via merchant-facing API. SAR-related SHAP values restricted to compliance scope. | ⏳ Planned |
| I-008 | Kafka message interception | Kafka brokers | HIGH | TLS in transit between all Kafka clients and brokers. SASL/SCRAM authentication. Sensitive fields (PAN tokens) encrypted at application layer before publish. | ⏳ Planned |

**Deep Dive — I-003 (Model Internals Disclosure):**

> *@priya:* "If an attacker can query the scoring API and receive SHAP feature attributions in real time, they can reverse-engineer which features drive the fraud score and specifically craft transactions to score below the decline threshold. This is the model evasion attack. The control is straightforward: SHAP values are never included in the standard scoring response. The score and decision are returned — not the reasoning. Reasoning is available only to analysts with `risk:read_all` scope via the case management interface, and only for specific decisions under review. Rule definitions are never exposed externally."

**Open Gap — I-004:**
Model inversion attacks on ML models can sometimes recover approximate training data distributions. Current mitigations: pseudonymised training data, no raw PII in features. Full mitigation requires differential privacy guarantees on the training pipeline — this is a research-grade intervention scheduled for evaluation in Q3.

---

### 3.5 Denial of Service Threats

| ID | Threat | Target | Risk | Control | Status |
|---|---|---|---|---|---|
| D-001 | Volumetric DDoS — flood of scoring requests | Scoring API | HIGH | Cloudflare DDoS protection (L3/L4). Kong rate limiting: 100 req/s per API key, 10 req/s per IP. HPA scales pods under legitimate load. | ⏳ Planned |
| D-002 | Slowloris / connection exhaustion | Kong / FastAPI | MEDIUM | Cloudflare proxy terminates slow connections. Uvicorn connection timeout: 30s. Kong upstream timeout: 5s. | ⏳ Planned |
| D-003 | Algorithmic complexity attack — crafted payloads maximise scoring latency | Scoring pipeline | MEDIUM | Per-request timeout: 500ms hard limit. Complex enrichment calls have 50ms timeout. ML inference has 100ms timeout. Rule engine has no variable complexity. | ⏳ Planned |
| D-004 | Kafka consumer lag DoS — producer flood causes consumer starvation | Kafka consumers | MEDIUM | Consumer lag monitoring (Prometheus). Auto-scaling consumer pods on lag > 1,000 messages. Kafka topic retention: 7 days. DLQ for failed messages. | ⏳ Planned |
| D-005 | Redis memory exhaustion via velocity key flood | Redis Cluster | MEDIUM | All Redis keys have TTL (max 3,600s). Memory threshold alert at 75% capacity. Redis `maxmemory-policy: allkeys-lru` as last resort. | ⏳ Planned |
| D-006 | Scoring API pod OOM via large payload | Scoring API pods | LOW | Pydantic v2 strict mode rejects oversized payloads. Request body size limit: 64KB at Kong. Pod memory limits enforced (Guaranteed QoS class). | ⏳ Planned |

---

### 3.6 Elevation of Privilege Threats

| ID | Threat | Target | Risk | Control | Status |
|---|---|---|---|---|---|
| E-001 | Compromised pod lateral movement | Internal services | CRITICAL | Kubernetes NetworkPolicy default-deny. Pods can only communicate on explicitly allowlisted paths. Istio mTLS — a compromised pod cannot impersonate another service identity. | ⏳ Planned |
| E-002 | Scope escalation — merchant obtains analyst scope | Kong / Keycloak | HIGH | Scopes issued by Keycloak based on client credentials. Merchant clients can only hold `risk:score` and `risk:read_own`. Scope cannot be self-elevated. JWT claims are signed — cannot be tampered. | ⏳ Planned |
| E-003 | Kubernetes RBAC escalation — pod obtains cluster-admin | Kubernetes | HIGH | Service accounts have minimum required RBAC permissions. No `cluster-admin` bindings for application workloads. Pod security standards: Restricted profile. Audit logging of all RBAC changes. | ⏳ Planned |
| E-004 | Vault token escalation — application obtains excessive Vault policies | HashiCorp Vault | HIGH | Vault policies follow least privilege. Each service account has a dedicated Vault policy scoped to its specific secret paths. Token TTL: 1 hour. No root token in production. | ⏳ Planned |
| E-005 | Container escape — attacker breaks out of pod to host | Kubernetes nodes | HIGH | Pod security standards: Restricted (no privileged containers, no hostPID, no hostNetwork). seccomp RuntimeDefault profile. Non-root UID enforced. Falco runtime security monitoring. | ⏳ Planned |
| E-006 | Supply chain attack — compromised dependency introduces malicious code | Application build | HIGH | Snyk SCA on every PR. Dependabot automated security updates. Pinned dependency versions with hash verification. Container image signing (Cosign). SBOM generated per build. | ⏳ Planned |

**Deep Dive — E-001 (Lateral Movement):**

> *@priya:* "Assume breach. If an attacker compromises the enrichment service pod, what can they reach? Without network policy: everything on the cluster network — PostgreSQL, Redis, Cassandra, Kafka, the scoring API. With default-deny NetworkPolicy, the enrichment service can only communicate with its explicitly allowed peers: the scoring API (inbound) and external enrichment APIs (outbound). It cannot reach the database, Redis, Kafka, or any other internal service. Istio mTLS adds a second layer: even if the attacker bypasses network policy via a misconfiguration, they cannot present a valid mTLS certificate for the scoring API's service identity. The blast radius of a compromised enrichment pod is the enrichment service — nothing more."

**Open Gap — E-006:**
Dependency hash pinning is implemented for direct dependencies. Transitive dependency hashes are not yet pinned — a compromised transitive dependency (e.g., a sub-dependency of `httpx`) could introduce malicious code without triggering a direct dependency hash mismatch. Full mitigation requires reproducible builds with full dependency tree hash pinning — to be scheduled.

---

## 4. Attack Surface Map

### 4.1 External Attack Surface (Internet-Facing)

```
EXTERNAL ATTACK SURFACE
═══════════════════════

┌─────────────────────────────────────────────────┐
│  EXPOSED ENDPOINTS (via Kong API Gateway)        │
│                                                  │
│  POST /v1/risk/score                             │
│    Auth: Bearer JWT (risk:score scope)           │
│    Rate: 100 req/s per API key                   │
│    Input: RiskScoreRequest (Pydantic validated)  │
│                                                  │
│  GET  /v1/risk/{request_id}                      │
│    Auth: Bearer JWT (risk:read_own scope)        │
│    Rate: 100 req/s per API key                   │
│                                                  │
│  POST /v1/risk/{id}/feedback                     │
│    Auth: Bearer JWT (risk:score scope)           │
│    Rate: 100 req/s per API key                   │
│                                                  │
│  POST /webhooks/inbound                          │
│    Auth: HMAC-SHA256 signature                   │
│    Validated: timestamp within 300s              │
└─────────────────────────────────────────────────┘

AUTHENTICATION ENDPOINTS (Keycloak — separate host)
┌─────────────────────────────────────────────────┐
│  POST /realms/ras/protocol/openid-connect/token  │
│  GET  /realms/ras/protocol/openid-connect/certs  │
└─────────────────────────────────────────────────┘

NOT EXPOSED EXTERNALLY:
  - Admin API (/v1/rules, /v1/models)    → internal only
  - Case Management API (/v1/cases)      → internal only
  - Kafka brokers                        → VPC only
  - All data stores                      → VPC only
  - BentoML inference server             → cluster-internal only
```

### 4.2 Internal Attack Surface (East-West)

```
INTERNAL SERVICE COMMUNICATION MATRIX
══════════════════════════════════════
(✅ = allowed · ✗ = blocked by NetworkPolicy)

                 Scoring  CaseMgmt  Admin  Enrich  BentoML  Kafka  Postgres  Redis  Cassandra
Scoring API        —         ✗        ✗      ✅       ✅       ✅      ✅       ✅       ✅
CaseMgmt API       ✗         —        ✗      ✗        ✗        ✅      ✅       ✗        ✅
Admin API          ✗         ✗        —      ✗        ✗        ✅      ✅       ✗        ✗
Enrichment Svc     ✗         ✗        ✗      —        ✗        ✗       ✗        ✗        ✗
BentoML            ✗         ✗        ✗      ✗        —        ✗       ✗        ✅       ✗
Flink Pipeline     ✗         ✗        ✗      ✗        ✗        ✅      ✗        ✅       ✅
Kong Gateway       ✅        ✅        ✅     ✗        ✗        ✗       ✗        ✗        ✗
```

### 4.3 Third-Party Attack Surface

| Integration | Direction | Auth | Risk | Control |
|---|---|---|---|---|
| MaxMind GeoIP (local DB) | Outbound (DB file) | N/A — local file | LOW | DB file integrity verified on update (SHA-256) |
| IPQualityScore API | Outbound | API key (Vault) | MEDIUM | Allowlisted egress IP. Response validated before use. Timeout 50ms. |
| BIN Database (internal) | Internal | mTLS | LOW | Internal service — standard controls |
| Confluent Cloud (Kafka) | Outbound | SASL/SCRAM + TLS | MEDIUM | VPC peering — traffic does not traverse public internet |
| AWS KMS | Outbound | IAM role | HIGH | Encryption operations — IAM role scoped to KMS key only |
| Snowflake | Outbound | OAuth + IP allowlist | MEDIUM | Read-only role for ML feature backfill. IP allowlist enforced. |

---

## 5. Security Controls Summary

### 5.1 Preventive Controls

| Layer | Control | Implementation |
|---|---|---|
| Network perimeter | DDoS protection | Cloudflare |
| Network perimeter | WAF | Cloudflare WAF + AWS WAF |
| API gateway | Authentication | JWT RS256 (Keycloak) |
| API gateway | Rate limiting | Kong: 100 req/s per key |
| API gateway | Input filtering | Kong request validator |
| Application | Input validation | Pydantic v2 strict mode |
| Application | SQL injection prevention | SQLAlchemy parameterized queries |
| Application | HMAC verification | `hmac.compare_digest` + timestamp |
| Application | Idempotency | Redis SET NX per idempotency key |
| Data | Encryption at rest | AES-256-GCM + AWS KMS envelope |
| Data | Encryption in transit | TLS 1.3 (external) + mTLS (internal) |
| Data | Secrets management | HashiCorp Vault dynamic credentials |
| Infrastructure | Container security | Pod Security Standards (Restricted) |
| Infrastructure | Network segmentation | Kubernetes NetworkPolicy (default-deny) |
| Infrastructure | Service identity | Istio mTLS (STRICT mode) |

### 5.2 Detective Controls

| Layer | Control | Implementation |
|---|---|---|
| Application | Structured audit logging | structlog → Cassandra (immutable) |
| Application | Anomalous feature detection | Evidently AI drift alerts |
| Infrastructure | Runtime security monitoring | Falco (syscall anomaly detection) |
| Infrastructure | Metrics & alerting | Prometheus + Grafana + PagerDuty |
| Infrastructure | Distributed tracing | OpenTelemetry + Jaeger |
| Code | Static analysis (SAST) | Bandit + Semgrep (every PR) |
| Dependencies | Vulnerability scanning | Snyk + Dependabot |
| Container | Image scanning | Trivy (every build) |

### 5.3 Corrective Controls

| Scenario | Control | Recovery Time |
|---|---|---|
| Compromised API key | Key revocation via Keycloak | < 60 seconds |
| Compromised JWT signing key | Keycloak key rotation — all tokens invalid | < 5 minutes |
| Compromised Vault token | Vault lease revocation | Immediate |
| Compromised pod | Pod eviction + network policy isolation | < 30 seconds |
| Audit log integrity breach | Cassandra backup restore + chain-of-custody report | Per RTO |
| Malicious dependency | Dependabot PR + Snyk alert + rollback | Per runbook |

---

## 6. Residual Risk Register

Threats where controls are partial or compensating — not fully mitigated.

| ID | Threat | Residual Risk | Mitigation Status | Owner | Target |
|---|---|---|---|---|---|
| T-004 | Feature store poisoning | MEDIUM — per-feature Redis ACL not implemented | Compensating: Evidently AI drift alerts | `@priya` | To be scheduled |
| I-004 | Model inversion attack | LOW — pseudonymised features reduce surface | Compensating: feature abstraction layer | `@yuki` | Q3 eval |
| E-006 | Transitive dependency supply chain | MEDIUM — direct deps pinned, transitive not | Compensating: Snyk transitive scanning | `@priya` | To be scheduled |
| B-002 | Unknown vulnerabilities (pre-pentest) | HIGH — no external validation yet | Compensating: OWASP ZAP + internal review | `@priya` | Q2 pentest |

---

## 7. Incident Response Triggers

The following conditions require immediate activation of the security incident response playbook (`docs/runbooks/security_incident.md`):

| Trigger | Severity | Immediate Action |
|---|---|---|
| PAN detected in any log output | P1 / CRITICAL | Stop logging · Isolate pod · Page @priya + @james |
| Audit log write failure > 60s | P1 / CRITICAL | DLQ review · Page @priya + @darius |
| Anomalous JWT issuance spike | P1 / HIGH | Revoke tokens · Review Keycloak audit · Page @priya |
| Falco runtime anomaly (syscall) | P1 / HIGH | Pod isolation · Forensic snapshot · Page @priya |
| Trivy CRITICAL CVE in production image | P1 / HIGH | Emergency patch · Page @priya + @darius |
| Feature distribution anomaly (Evidently) | P2 / MEDIUM | Investigate · Pause affected model · Page @yuki + @priya |
| Failed auth spike (> 100/min) | P2 / MEDIUM | Review source IPs · Cloudflare block · Page @priya |
| Rule engine modification without ADR | P2 / MEDIUM | Revert change · Audit trail review · Page @priya + @marcus |

---

## 8. Compliance Mapping

| Threat Category | PCI DSS v4.0 Requirement | GDPR Article | SOC 2 Criteria |
|---|---|---|---|
| Spoofing | Req 8 (Identity), Req 4 (Encryption) | Art 32 (Security) | CC6.1 |
| Tampering | Req 10 (Audit logs), Req 6 (Systems security) | Art 32 | CC7.1, CC8.1 |
| Repudiation | Req 10 (Audit trail) | Art 5(2) (Accountability) | CC4.1 |
| Information Disclosure | Req 3 (PAN protection), Req 4 (Transmission) | Art 32, Art 25 | CC6.6, CC6.7 |
| Denial of Service | Req 6.4 (WAF), Req 12.3 (Risk assessment) | Art 32(1)(b) (Availability) | A1.1, A1.2 |
| Elevation of Privilege | Req 7 (Access control), Req 8 (Auth) | Art 32 | CC6.3 |

---

## 9. Threat Model Review Schedule

| Review Type | Frequency | Trigger |
|---|---|---|
| Full STRIDE review | Annually | Scheduled (Q4 each year) |
| Incremental update | Per sprint | New service / dependency / data category |
| Post-incident review | Within 48h | Any P1 security incident |
| Pre-PRR review | Per release | Major version PRR |
| External pentest correlation | Post-pentest (Q2) | Map pentest findings to threat model gaps |

---

## 10. Related Documents

| Document | Location | Owner |
|---|---|---|
| Encryption Specification | `docs/security/encryption_spec.md` | `@priya` |
| Vault Configuration Guide | `docs/security/vault_setup.md` | `@priya` |
| PCI DSS Control Mapping | `docs/compliance/pci_dss_controls.md` | `@james` |
| Network Policy Manifests | `k8s/network-policies/` | `@darius` |
| Security Incident Playbook | `docs/runbooks/security_incident.md` | `@priya` |
| System Architecture Overview | `docs/architecture/system_overview.md` | `@marcus` |
| PRR Security Gates (§4) | `docs/quality/prr_checklist.md` | `@aisha` |

---

*Document Version: 1.0.0*
*Owner: Priya Nair — Principal Security Engineer*
*Review Cycle: Per Sprint (incremental) · Annual (full STRIDE)*
*Classification: Internal — RESTRICTED — Security Sensitive*
*Distribution: Engineering leads, CISO, QSA auditors, SOC 2 auditors only*