# PCI DSS v4.0 Control Mapping
## Risk Assessment System (RAS) — Payment Card Industry Compliance

```yaml
document:       docs/compliance/pci_dss_controls.md
version:        1.0.0
owner:          James Whitfield (@james) — Head of Risk & Compliance
reviewers:      "@priya · @marcus · @darius · @sofia · @aisha"
standard:       PCI DSS v4.0 (March 2022)
assessment_type: SAQ-D (Service Provider)
qsa_target:     Q3 2024
last_updated:   Sprint 3
status:         In Progress — 3 controls open
classification: Internal — RESTRICTED — Legal Privilege
```

---

## 1. Scope Statement

### 1.1 Cardholder Data Environment (CDE)

The RAS Cardholder Data Environment includes all system components that store, process, or transmit cardholder data (CHD) or sensitive authentication data (SAD), and all systems that could impact the security of those components.

```
IN SCOPE (CDE):
  ┌─────────────────────────────────────────────────────┐
  │  Scoring API (FastAPI)     — processes BIN + card   │
  │  PostgreSQL (primary)      — stores tokenized CHD   │
  │  Cassandra (event log)     — stores decision audit  │
  │  Redis (velocity/cache)    — processes card signals │
  │  Kong API Gateway          — transmits CHD in flight│
  │  Kafka (risk.decisions)    — transmits decisions    │
  │  BentoML inference server  — processes card features│
  │  Admin API                 — manages rule engine    │
  │  Case Management API       — displays masked CHD    │
  └─────────────────────────────────────────────────────┘

CONNECTED-TO (in scope — could impact CDE security):
  ┌─────────────────────────────────────────────────────┐
  │  Flink pipeline            — processes txn stream   │
  │  Feast feature store       — processes card features│
  │  Kubernetes control plane  — manages CDE pods       │
  │  Istio control plane       — manages mTLS certs     │
  │  HashiCorp Vault           — manages CDE secrets    │
  │  AWS KMS                   — manages encryption keys│
  │  Keycloak                  — manages CDE access     │
  └─────────────────────────────────────────────────────┘

OUT OF SCOPE:
  ┌─────────────────────────────────────────────────────┐
  │  Snowflake (warehouse)     — no CHD, pseudonymised  │
  │  Neo4j (graph)             — no CHD                 │
  │  Elasticsearch             — masked data only       │
  │  ML training pipeline      — pseudonymised features │
  │  Frontend dashboard        — masked data only       │
  └─────────────────────────────────────────────────────┘
```

> *@james:* "Scope reduction is the primary objective of CDE architecture. Every component not in scope saves assessment time, reduces risk surface, and lowers compliance cost. The decision to tokenize PANs at the point of entry — before they reach the scoring API — was made specifically to minimise CDE scope. If the scoring API never sees a raw PAN, it processes tokens only, and PCI scope is significantly reduced."

### 1.2 Assessment Approach

RAS is assessed as a **Service Provider** under **SAQ-D** — the most comprehensive self-assessment questionnaire, applicable to service providers that store, process, or transmit cardholder data. The target is a full **Report on Compliance (ROC)** by a Qualified Security Assessor (QSA) in Q3 2024.

---

## 2. PCI DSS v4.0 Requirements — Control Mapping

PCI DSS v4.0 contains 12 requirements and 64 sub-requirements. The following table maps each requirement to its RAS control owner, implementation, and current compliance status.

**Status key:**
- ✅ **Compliant** — control implemented and evidence available
- ⚠️ **Partial** — control partially implemented; gap documented
- ❌ **Open** — control not yet implemented; remediation in progress
- 🔵 **N/A** — requirement not applicable to RAS scope

---

### Requirement 1: Install and Maintain Network Security Controls

| Sub-Req | Description | Control | Owner | Status |
|---|---|---|---|---|
| 1.2.1 | Network security controls (NSC) restrict inbound and outbound traffic | Kubernetes NetworkPolicy (default-deny) + Istio mTLS STRICT | `@priya` / `@darius` | ✅ |
| 1.2.2 | All allowed traffic is defined and justified | NetworkPolicy allowlist per service (see §4.2 of threat model) | `@priya` | ✅ |
| 1.2.3 | NSCs are installed between all wireless networks and CDE | N/A — no wireless networks in RAS infrastructure | — | 🔵 |
| 1.3.1 | Inbound traffic to CDE restricted to that which is necessary | Kong API Gateway allowlist routing — only `/v1/risk/*` exposed | `@priya` | ✅ |
| 1.3.2 | Outbound traffic from CDE restricted to that which is necessary | Kubernetes egress NetworkPolicy — allowlisted external APIs only | `@priya` | ✅ |
| 1.3.3 | NSCs prevent the CDE from being directly accessible from the internet | No CDE component has a public IP. All traffic via Kong → Istio → CDE | `@darius` | ✅ |
| 1.4.1 | NSCs between trusted and untrusted networks | Cloudflare WAF (internet → Kong) + NetworkPolicy (Kong → CDE) | `@priya` | ✅ |
| 1.5.1 | Security controls on devices connecting to both untrusted and CDE networks | N/A — no split-tunnel or BYOD access to CDE | — | 🔵 |

**Evidence:** `k8s/network-policies/` · Istio PeerAuthentication STRICT policy · Kong route config

---

### Requirement 2: Apply Secure Configurations to All System Components

| Sub-Req | Description | Control | Owner | Status |
|---|---|---|---|---|
| 2.1.1 | All default passwords changed | Vault-issued dynamic credentials — no static defaults | `@priya` | ✅ |
| 2.2.1 | System configuration standards documented | Hardening standards defined in `docs/security/hardening_standards.md` | `@priya` | ⚠️ Document in progress |
| 2.2.2 | Vendor default accounts disabled or removed | PostgreSQL `postgres` superuser disabled. Cassandra default user removed. Redis AUTH enforced | `@darius` | ✅ |
| 2.2.3 | Primary functions with different security levels on separate systems | ML inference (BentoML) on separate node pool from scoring API | `@darius` | ✅ |
| 2.2.7 | All non-console administrative access encrypted | All admin access via mTLS + Vault. No Telnet, no plain HTTP | `@priya` | ✅ |
| 2.3.1 | Wireless environments use industry best practices | N/A | — | 🔵 |

**Evidence:** Vault dynamic credential config · PostgreSQL hardening config · Node pool separation in Terraform

---

### Requirement 3: Protect Stored Account Data

| Sub-Req | Description | Control | Owner | Status |
|---|---|---|---|---|
| 3.2.1 | SAD not retained after authorisation | CVV, full track data, PIN never stored. Application-layer rejection at Pydantic validation | `@sofia` | ✅ |
| 3.3.1 | SAD not retained post-authorisation (technical enforcement) | PostgreSQL schema has no column for SAD. Application INSERT statements validated in code review | `@sofia` | ✅ |
| 3.4.1 | PAN masked when displayed | Last four digits only in all UI displays and API responses. `****-****-****-XXXX` format enforced in Pydantic serializer | `@sofia` / `@elena` | ✅ |
| 3.5.1 | PAN protected wherever stored | AES-256-GCM + AWS KMS envelope encryption (ADR-003). Encrypted at application layer before PostgreSQL write | `@priya` | ✅ |
| 3.6.1 | Key management procedures for cryptographic keys | AWS KMS key rotation policy: 90-day automatic rotation. Key custodian: @priya. Key usage audit: CloudTrail | `@priya` | ✅ |
| 3.7.1 | Key management: key generation in secure environment | AWS KMS HSM-backed key generation (FIPS 140-2 Level 3). No key material generated in application code | `@priya` | ✅ |
| 3.7.2 | Secure key distribution | Envelope encryption — DEK encrypted by KMS KEK. DEK never stored or transmitted in plaintext | `@priya` | ✅ |
| 3.7.5 | Key retirement and replacement at cryptoperiod end | KMS automatic rotation every 90 days. Old key versions retained for decryption of existing ciphertext | `@priya` | ✅ |

**Evidence:** ADR-003 · `app/core/encryption.py` · AWS KMS key policy · CloudTrail key usage log

---

### Requirement 4: Protect Cardholder Data with Strong Cryptography During Transmission

| Sub-Req | Description | Control | Owner | Status |
|---|---|---|---|---|
| 4.2.1 | Strong cryptography for CHD in transit | TLS 1.3 for all external traffic. Istio mTLS (STRICT) for all internal east-west traffic | `@priya` / `@darius` | ✅ |
| 4.2.1.1 | Inventory of trusted keys/certificates | Istio certificates: 24-hour rotation, Citadel CA managed. External certs: Cloudflare managed, 90-day rotation | `@priya` | ✅ |
| 4.2.2 | TLS termination policies documented | TLS 1.3 minimum at Cloudflare edge. TLS 1.2 blocked. TLS 1.0/1.1 blocked at WAF layer | `@priya` | ✅ |

**Evidence:** Istio PeerAuthentication STRICT config · Cloudflare TLS settings · `docs/security/encryption_spec.md`

---

### Requirement 5: Protect All Systems and Networks from Malicious Software

| Sub-Req | Description | Control | Owner | Status |
|---|---|---|---|---|
| 5.2.1 | Anti-malware solution deployed | Falco runtime security monitoring (syscall anomaly detection) on all CDE nodes | `@darius` | ✅ |
| 5.2.3 | Systems not at risk from malware evaluated periodically | Container images scanned by Trivy on every build. Zero CRITICAL CVE gate in CI | `@priya` / `@darius` | ✅ |
| 5.3.1 | Anti-malware solutions kept current | Falco rule updates automated. Trivy DB updated on every CI run | `@darius` | ✅ |
| 5.3.3 | Removable media encrypted | N/A — no removable media in RAS infrastructure | — | 🔵 |
| 5.4.1 | Phishing protection in place | Google Workspace phishing protection for engineering team. Not a direct CDE control | — | ⚠️ Out of scope for ROC — covered by corporate security policy |

**Evidence:** Falco deployment config · Trivy CI scan reports · Snyk SCA reports

---

### Requirement 6: Develop and Maintain Secure Systems and Software

| Sub-Req | Description | Control | Owner | Status |
|---|---|---|---|---|
| 6.2.1 | All software developed per secure coding guidelines | OWASP Top 10 addressed in code review checklist. Bandit + Semgrep SAST on every PR | `@priya` / `@sofia` | ✅ |
| 6.2.4 | Attacks prevented via software engineering techniques | Pydantic v2 strict validation (injection prevention). SQLAlchemy parameterized queries (SQL injection). HMAC verification (request forgery) | `@sofia` | ✅ |
| 6.3.1 | Security vulnerabilities identified and addressed | Snyk SCA + Dependabot on every PR. CRITICAL CVE = pipeline failure | `@priya` | ✅ |
| 6.3.3 | All software components protected from known vulnerabilities | Dependency pinning + hash verification. Trivy container scan. Monthly dependency review | `@priya` | ✅ |
| 6.4.1 | WAF deployed for public-facing web applications | Cloudflare WAF + AWS WAF. OWASP Core Rule Set enabled | `@priya` | ✅ |
| 6.4.2 | WAF operating in active blocking mode | Cloudflare WAF: block mode. AWS WAF: block mode for OWASP rules | `@priya` | ✅ |
| 6.4.3 | All payment page scripts managed and authorised | N/A — RAS is a backend API, not a payment page | — | 🔵 |
| 6.5.1 | Change control process exists for CDE software | GitHub PR + code review required. ArgoCD GitOps — no direct kubectl apply. ADR for architectural changes | `@darius` / `@marcus` | ✅ |
| 6.5.4 | Roles and functions separated between production and development | Production cluster isolated from staging. Separate AWS accounts. No developer access to production Vault | `@priya` / `@darius` | ✅ |
| 6.5.6 | Test data and accounts removed before production | Factory data (factory_boy) only in test environments. CI enforces no test accounts in production DB | `@aisha` | ✅ |

**Evidence:** Bandit/Semgrep CI reports · SQLAlchemy parameterised query patterns · WAF rule configs · ArgoCD audit log

---

### Requirement 7: Restrict Access to System Components and Cardholder Data by Business Need to Know

| Sub-Req | Description | Control | Owner | Status |
|---|---|---|---|---|
| 7.2.1 | Access control model defined and implemented | RBAC via Keycloak scopes. Roles: merchant, analyst, risk_admin, auditor. Scope matrix documented in `docs/security/rbac_matrix.md` | `@priya` | ✅ |
| 7.2.2 | Access granted based on least privilege | Merchant: `risk:score` only. Analyst: `cases:read/write`. Admin: `rules:write`. Auditor: read-only. No cross-role escalation | `@priya` | ✅ |
| 7.2.3 | Required approvals for access | New analyst access requires manager approval in Jira. Admin role requires CISO approval | `@james` | ✅ |
| 7.2.5 | Application and system accounts managed and their access restricted | Vault dynamic credentials scoped per service. No shared service accounts | `@priya` | ✅ |
| 7.3.1 | Access control system enforced | Kong Gateway enforces JWT scope validation on every request. OPA Gatekeeper for Kubernetes RBAC | `@priya` | ✅ |

**Evidence:** Keycloak realm config · Kong JWT plugin config · Vault policy definitions · `docs/security/rbac_matrix.md`

---

### Requirement 8: Identify Users and Authenticate Access to System Components

| Sub-Req | Description | Control | Owner | Status |
|---|---|---|---|---|
| 8.2.1 | All users assigned a unique ID | Keycloak user accounts — one account per person. No shared login credentials | `@priya` | ✅ |
| 8.3.1 | All user access authenticated with at least one factor | JWT RS256 bearer token. Password + TOTP for Keycloak console access | `@priya` | ✅ |
| 8.3.6 | MFA for all non-console access into CDE | MFA enforced for all admin console access (Keycloak admin, Vault UI, ArgoCD, Grafana) | `@priya` | ✅ |
| 8.3.9 | Password/passphrase change every 90 days | Enforced via Keycloak password policy. Vault dynamic credentials expire in 1 hour | `@priya` | ✅ |
| 8.4.2 | MFA for all non-console access into CDE (service provider) | All service provider staff with CDE access use MFA. Enforced at Keycloak IdP level | `@priya` | ✅ |
| 8.6.1 | System/application accounts managed by policies | Vault dynamic credentials — no static system passwords. Automated rotation | `@priya` | ✅ |
| 8.6.3 | Passwords for application and system accounts protected against misuse | No static passwords stored. Vault-issued credentials only. No hardcoded credentials in code (Semgrep rule) | `@priya` | ✅ |

**Evidence:** Keycloak password policy config · MFA enrollment records · Vault dynamic creds config · Semgrep credential detection rules

---

### Requirement 9: Restrict Physical Access to Cardholder Data

| Sub-Req | Description | Control | Owner | Status |
|---|---|---|---|---|
| 9.x | Physical access controls | RAS runs entirely in AWS (us-east-1, eu-west-1, ap-southeast-1). AWS SOC 2 and PCI DSS Level 1 certified data centres. Physical access controlled by AWS. AWS Shared Responsibility Model applies. | AWS / `@james` | ✅ (AWS responsibility) |

**Evidence:** AWS PCI DSS Attestation of Compliance (AoC) — obtained from AWS Artifact

---

### Requirement 10: Log and Monitor All Access to System Components and Cardholder Data

| Sub-Req | Description | Control | Owner | Status |
|---|---|---|---|---|
| 10.2.1 | Audit logs capture all required events | Cassandra immutable event log + Loki structured logs. See §10.2.1 detail table below | `@marcus` / `@darius` | ⚠️ **Partial — gap documented** |
| 10.2.2 | Audit logs protected from destruction | Cassandra INSERT-only service account. No DELETE/UPDATE privilege. S3 log archive (immutable bucket policy) | `@priya` | ✅ |
| 10.3.1 | Audit logs protected from unauthorised modifications | Cassandra write-once schema. Log files on S3 with object lock (WORM) | `@priya` / `@darius` | ✅ |
| 10.3.2 | Audit log files backed up to secure central location | Loki → S3 (30-day retention). Cassandra → Snowflake (7-year). MirrorMaker2 cross-region Kafka replication | `@darius` | ✅ |
| 10.4.1 | Automated audit log review daily | Grafana alerts + Loki log anomaly detection. PagerDuty escalation on security events | `@darius` | ✅ |
| 10.5.1 | Audit log history retained for at least 12 months | Loki: 12 months. Cassandra: 90 days hot + Snowflake 7 years cold. Meets 12-month minimum | `@darius` / `@james` | ✅ |
| 10.6.3 | Time synchronisation settings protected | AWS NTP (169.254.169.123) for all EKS nodes. NTP settings enforced via Terraform. Cannot be modified by application | `@darius` | ✅ |
| 10.7.1 | Failures of critical security controls detected and reported | Falco alerts on security control failures. PagerDuty P1 for audit log write failures | `@darius` / `@priya` | ✅ |

#### 10.2.1 Required Event Categories — Gap Analysis

PCI DSS v4.0 Requirement 10.2.1 mandates logging of 8 specific event categories. Current status:

| Category | Requirement | RAS Control | Status |
|---|---|---|---|
| 10.2.1(a) | All individual user access to CHD | Cassandra `risk.events` — all scoring decisions with customer_id | ✅ |
| 10.2.1(b) | All actions by root/administrator | Keycloak audit log + Vault audit log + CloudTrail | ✅ |
| 10.2.1(c) | All access to audit trails | Cassandra access control log. Elasticsearch query audit | ⚠️ **Gap: Elasticsearch query audit not yet enabled** |
| 10.2.1(d) | Invalid logical access attempts | Kong 401/403 responses logged to Loki with source IP | ✅ |
| 10.2.1(e) | Use of identification and authentication mechanisms | Keycloak login/logout events. JWT issuance events | ✅ |
| 10.2.1(f) | Initialisation / stopping / pausing of audit logs | Loki pod lifecycle events. Cassandra node events | ✅ |
| 10.2.1(g) | Creation and deletion of system-level objects | Kubernetes audit log (API server). Rule changes via `rules.changed` Kafka topic (ADR-008) | ✅ |
| 10.2.1(h) | All actions by individuals with root/admin | CloudTrail + Vault audit log + Keycloak admin events | ✅ |

**Gap — 10.2.1(c):** Elasticsearch query audit logging is not yet enabled. Any analyst accessing the audit search index via Elasticsearch is not logged. Remediation: enable Elasticsearch audit logging, route to Loki. Owner: `@darius`. Target: Sprint 4.

**Evidence:** Cassandra schema (INSERT-only) · Loki log pipeline config · Keycloak audit log config · CloudTrail config

---

### Requirement 11: Test Security of Systems and Networks Regularly

| Sub-Req | Description | Control | Owner | Status |
|---|---|---|---|---|
| 11.3.1 | Internal penetration test at least annually | Internal security review completed Sprint 3. External pentest scheduled Q2 2024 | `@priya` | ⚠️ **External pentest pending — PRR blocker B-002** |
| 11.3.2 | External penetration test by qualified party | Pentest vendor booked. Report expected Q2 2024 | `@priya` | ❌ **Not yet complete** |
| 11.4.1 | Intrusion detection/prevention system | Falco (runtime IDS). Cloudflare WAF (network IDS). Kong anomaly detection | `@priya` / `@darius` | ✅ |
| 11.4.3 | All exploitable vulnerabilities corrected | CI pipeline blocks CRITICAL CVEs. HIGH CVEs require documented exception from @priya. Snyk remediation SLA: CRITICAL 24h, HIGH 7 days | `@priya` | ✅ |
| 11.5.1 | Intrusion detection alerts personnel | Falco → PagerDuty P1 for CRITICAL detections. Cloudflare → Slack + PagerDuty | `@priya` / `@darius` | ✅ |
| 11.6.1 | Change and tamper detection for payment pages | N/A — RAS is a backend API, not a payment page | — | 🔵 |

**Evidence:** Internal security review report (Sprint 3) · Falco alert config · Snyk SLA policy

---

### Requirement 12: Support Information Security with Organisational Policies and Programmes

| Sub-Req | Description | Control | Owner | Status |
|---|---|---|---|---|
| 12.1.1 | Information security policy established | RAS Information Security Policy v1.0 (in progress — @james) | `@james` | ⚠️ In progress |
| 12.3.1 | Risk assessment process exists | Threat model (STRIDE) — `docs/security/threat_model.md`. Updated per sprint | `@priya` | ✅ |
| 12.3.4 | Hardware and software technologies reviewed annually | Technology stack review: quarterly (per this document). ADR process for technology changes | `@marcus` | ✅ |
| 12.5.2 | PCI DSS scope documented and confirmed at least every 12 months | CDE scope diagram in §1 of this document. Reviewed by QSA at assessment | `@james` | ✅ |
| 12.6.1 | Security awareness programme implemented | Mandatory security training for all engineers with CDE access. Tracked in Workday | `@james` | ✅ |
| 12.8.1 | List of all third-party service providers (TPSPs) maintained | Vendor DPA register — `docs/compliance/vendor_dpa_register.md` | `@james` | ✅ |
| 12.8.2 | Written agreements with all TPSPs | DPAs signed with: Confluent, Snowflake, Neo4j (AuraDB), MaxMind, IPQualityScore. 3 of 8 pending | `@james` | ⚠️ 3 DPAs outstanding |
| 12.8.3 | Established process for engaging TPSPs | Vendor onboarding checklist (PCI compliance confirmation required) | `@james` | ✅ |
| 12.8.4 | TPSP PCI DSS compliance status monitored annually | Annual TPSP compliance review scheduled Q4 | `@james` | ✅ |
| 12.10.1 | Incident response plan exists | Security incident playbook — `docs/runbooks/security_incident.md` | `@priya` | ✅ |
| 12.10.2 | Incident response plan tested annually | Tabletop exercise scheduled Q3 (pre-QSA assessment) | `@james` / `@priya` | ⚠️ Not yet run |

**Evidence:** Threat model · Vendor DPA register · Security training completion records · Incident response playbook

---

## 3. Open Gaps & Remediation Plan

| Gap ID | Requirement | Description | Owner | Target | PRR Impact |
|---|---|---|---|---|---|
| PCI-001 | 10.2.1(c) | Elasticsearch query audit logging not enabled | `@darius` | Sprint 4 | Section §6 |
| PCI-002 | 11.3.2 | External penetration test not complete | `@priya` | Q2 2024 | **PRR blocker B-002** |
| PCI-003 | 12.8.2 | 3 vendor DPAs outstanding (Vercel, Checkly, PagerDuty) | `@james` | Sprint 4 | Section §6 |
| PCI-004 | 2.2.1 | Hardening standards document not yet complete | `@priya` | Sprint 4 | None (compensating: Terraform enforced) |
| PCI-005 | 12.10.2 | Incident response tabletop exercise not yet run | `@james` / `@priya` | Q3 2024 | None (pre-QSA) |

---

## 4. Evidence Repository

All PCI DSS evidence is stored in `docs/compliance/pci_dss_evidence/` with the following structure:

```
docs/compliance/pci_dss_evidence/
├── req_01_network/
│   ├── network_policy_manifests.yaml
│   ├── istio_peer_auth_strict.yaml
│   └── kong_route_config.json
├── req_03_stored_data/
│   ├── encryption_spec.md
│   ├── kms_key_policy.json
│   └── cloudtrail_key_usage_sample.json
├── req_06_secure_software/
│   ├── bandit_scan_sprint3.html
│   ├── semgrep_scan_sprint3.html
│   └── trivy_scan_sprint3.json
├── req_08_authentication/
│   ├── keycloak_password_policy.json
│   └── mfa_enrollment_report.csv
├── req_10_logging/
│   ├── cassandra_schema_insert_only.cql
│   ├── loki_pipeline_config.yaml
│   └── log_audit_sample_sprint3.json
├── req_11_testing/
│   ├── internal_security_review_sprint3.pdf
│   └── owasp_zap_report_sprint3.html
└── req_12_policy/
    ├── vendor_dpa_register.md
    └── security_training_completion.csv
```

**@james:** "Evidence must be collected continuously — not assembled in the week before the QSA arrives. Every sprint, each control owner submits updated evidence to this repository. The QSA will ask for evidence spanning the audit period, not a point-in-time snapshot."

---

## 5. QSA Assessment Preparation Timeline

| Milestone | Date | Owner | Status |
|---|---|---|---|
| CDE scope diagram finalised | Sprint 3 | `@james` | ✅ Done |
| Internal security review complete | Sprint 3 | `@priya` | ✅ Done |
| All open gaps closed (PCI-001 to PCI-005) | Sprint 4 | Per owner | ⚠️ In progress |
| External penetration test complete | Q2 2024 | `@priya` | ❌ Pending |
| Vendor DPAs completed | Sprint 4 | `@james` | ⚠️ 3 outstanding |
| Evidence repository complete | Q2 2024 | `@james` | ⚠️ In progress |
| Pre-assessment internal audit | Q3 2024 | `@james` | ⏳ Not started |
| QSA on-site assessment | Q3 2024 | `@james` | ⏳ Not started |
| ROC (Report on Compliance) issued | Q3 2024 | QSA | ⏳ Not started |
| Attestation of Compliance (AoC) signed | Q3 2024 | `@james` | ⏳ Not started |

---

## 6. Related Documents

| Document | Location | Owner |
|---|---|---|
| Threat Model (STRIDE) | `docs/security/threat_model.md` | `@priya` |
| Encryption Specification | `docs/security/encryption_spec.md` | `@priya` |
| Vault Configuration | `docs/security/vault_setup.md` | `@priya` |
| GDPR DPIA | `docs/compliance/gdpr_dpia.md` | `@james` |
| Vendor DPA Register | `docs/compliance/vendor_dpa_register.md` | `@james` |
| Security Incident Playbook | `docs/runbooks/security_incident.md` | `@priya` |
| ADR-003 (KMS Encryption) | `docs/architecture/adr/ADR-003-kms-envelope-encryption.md` | `@marcus` |
| PRR Checklist (§6 Compliance) | `docs/quality/prr_checklist.md` | `@aisha` |

---

*Document Version: 1.0.0*
*Owner: James Whitfield — Head of Risk & Compliance*
*Review Cycle: Per sprint (gap updates) · Quarterly (full review)*
*Classification: Internal — RESTRICTED — Legal Privilege*
*Distribution: Engineering leads · CISO · QSA auditors only*