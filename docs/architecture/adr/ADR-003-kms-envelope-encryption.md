# ADR-003: Encryption Key Management — AWS KMS Envelope Encryption

```yaml
id:         ADR-003
title:      Encryption Key Management Strategy
status:     Accepted
date:       2024-01-08  (Sprint 1)
author:     Marcus Chen (@marcus)
reviewers:  "@priya · @james"
deciders:   "@priya · @marcus"
supersedes: —
superseded_by: —
```

## Context

RAS processes and stores PII (customer identifiers, IP addresses) and payment data (BIN, last four, card metadata). PCI DSS v4.0 Requirement 3.5.1 mandates strong cryptography for stored PAN. GDPR Article 32 mandates appropriate technical measures for personal data security.

Requirements:
- AES-256 encryption for all PII and card data fields at rest
- Key rotation without re-encrypting all ciphertext (operational requirement at 150B records/year)
- No raw key material in application code, environment variables, or Kubernetes Secrets
- Hardware Security Module (HSM) backing for key encryption keys
- Auditable key usage (PCI DSS Req 3.7.1)

Candidates: **AWS KMS (envelope encryption)**, **HashiCorp Vault Transit engine**, **Application-managed keys**, **PostgreSQL pgcrypto**

## Decision

**Use AWS KMS envelope encryption for all PII and card data field encryption.**

```
Key Hierarchy:
  AWS KMS (HSM-backed)
    └── Key Encryption Key (KEK) — never leaves KMS
          └── Data Encryption Key (DEK) — generated per record
                └── Encrypted field value (AES-256-GCM)

Storage per encrypted field:
  {
    "ciphertext": "<base64 AES-256-GCM ciphertext>",
    "nonce":      "<base64 12-byte GCM nonce>",
    "enc_dek":    "<base64 KMS-encrypted DEK>",
    "key_version": "arn:aws:kms:us-east-1:...:key/...:1"
  }
```

## Rationale

**Envelope encryption** separates the concern of key management (AWS KMS, HSM-backed) from the concern of data encryption (application layer, AES-256-GCM). Benefits:

1. **Key rotation without re-encryption:** When the KEK is rotated in KMS, existing ciphertext remains valid — it uses the old DEK (still decryptable via KMS with the old key version). New records use a new DEK encrypted with the new KEK. Re-encryption of existing records is a background job, not a blocking migration.

2. **No key material in application:** The application never holds the KEK. It calls `kms:GenerateDataKey` to get a plaintext DEK for encryption and `kms:Decrypt` to recover it for decryption. The plaintext DEK exists in memory only for the duration of the operation.

3. **HSM backing:** AWS KMS uses FIPS 140-2 Level 3 HSMs. The KEK never exists in plaintext outside the HSM. This satisfies PCI DSS Req 3.7.1 requirement for key custodian procedures.

4. **Audit trail:** Every KMS API call is logged to AWS CloudTrail — who decrypted what, when. This is the PCI DSS Req 3.7.8 key usage log.

**Why not Vault Transit:**
Vault Transit is a valid alternative and is already used for dynamic database credentials. However, at 100k TPS with per-record DEK generation, Vault Transit would become a bottleneck — it is a network call per DEK operation. AWS KMS is also a network call, but DEK caching (in-memory, 5-minute TTL, per-key-id) reduces KMS API calls by ~99% in practice — most records reuse a cached DEK, calling KMS only for the initial generation.

**AES-256-GCM over AES-CBC:**
GCM provides authenticated encryption with associated data (AEAD). The authentication tag detects ciphertext tampering — a CBC ciphertext can be silently modified. GCM is immune to padding oracle attacks (POODLE, BEAST) that affect CBC. (@priya, CISSP — this is non-negotiable.)

## Consequences

**Positive:**
- Zero key material in application code or Kubernetes Secrets
- Key rotation with zero downtime
- HSM-backed KEK satisfies PCI DSS hardware security requirements
- CloudTrail audit log for all key usage

**Negative:**
- KMS API latency: ~1ms per call (mitigated by DEK caching)
- AWS vendor lock-in on key management (GCP KMS migration path exists but is non-trivial)
- Increased storage per field (nonce + enc_dek + ciphertext vs. raw value)

*ADR Directory Version: 1.0.0*
*Owner: Marcus Chen — Chief Risk Architect*
*Format: MADR (Markdown Architectural Decision Records)*
*Review: New ADRs require Architecture Review Board approval*
*Classification: Internal — Engineering Confidential*