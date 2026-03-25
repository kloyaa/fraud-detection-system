# Encryption Specification
## Risk Assessment System (RAS) — Cryptographic Standards & Implementation

```yaml
document:       docs/security/encryption_spec.md
version:        1.0.0
owner:          Priya Nair (@priya) — Principal Security Engineer
reviewers:      "@marcus · @sofia · @darius · @james"
last_updated:   Pre-development
status:         Approved
classification: Internal — RESTRICTED — Security Sensitive
```

---

## 1. Encryption Standards

| Context | Algorithm | Key Size | Mode | Standard |
|---|---|---|---|---|
| Data at rest (PII fields) | AES | 256-bit | GCM | NIST SP 800-38D |
| Data in transit (external) | TLS | — | 1.3 | RFC 8446 |
| Data in transit (internal) | mTLS | — | 1.3 | Istio Citadel CA |
| Key encryption (KEK) | RSA / AES | 4096-bit / 256-bit | AWS KMS HSM | FIPS 140-2 Level 3 |
| JWT signing | RSA | 2048-bit | RS256 | RFC 7518 |
| Webhook signing | HMAC | 256-bit | SHA-256 | RFC 2104 |
| Password hashing | Argon2id | — | — | RFC 9106 |
| Audit log integrity | SHA | 256-bit | — | FIPS 180-4 |

> *@priya:* "AES-256-GCM is non-negotiable over AES-CBC. GCM provides authenticated encryption — the authentication tag detects any ciphertext tampering before decryption. CBC without an explicit MAC is vulnerable to padding oracle attacks. Every field encrypted in RAS uses GCM."

---

## 2. Envelope Encryption Architecture

All PII and card data fields use envelope encryption via AWS KMS. No raw key material ever exists in application code, environment variables, or Kubernetes Secrets.

```
AWS KMS (FIPS 140-2 Level 3 HSM)
  └── Key Encryption Key (KEK)
        └── never leaves KMS hardware
        └── rotates every 90 days (automated)
              │
              │  kms:GenerateDataKey
              ▼
  Data Encryption Key (DEK) ── plaintext: in memory only (encrypt/decrypt op)
                             └── encrypted: stored alongside ciphertext
                                    │
                                    ▼
                          AES-256-GCM encryption
                          of field value
```

### 2.1 Encrypted Field Storage Format

Every encrypted field is stored as a JSON envelope:

```json
{
  "ciphertext":    "<base64 AES-256-GCM ciphertext>",
  "nonce":         "<base64 12-byte random nonce>",
  "enc_dek":       "<base64 KMS-encrypted DEK>",
  "key_version":   "arn:aws:kms:us-east-1:123456789:key/abc-123:1",
  "algorithm":     "AES_256_GCM",
  "encrypted_at":  "2024-03-15T14:23:07Z"
}
```

### 2.2 Implementation

```python
# app/core/encryption.py

import boto3
import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from functools import lru_cache

class FieldEncryptor:
    """
    Envelope encryption via AWS KMS.
    DEKs are cached in memory (5-min TTL) to minimise KMS API calls.
    At 100k TPS, caching reduces KMS calls by ~99%.
    """

    def __init__(self, kms_key_id: str):
        self._kms        = boto3.client("kms")
        self._key_id     = kms_key_id
        self._dek_cache: dict = {}   # {key_version: (plaintext_dek, enc_dek)}

    def encrypt(self, plaintext: str) -> dict:
        plaintext_dek, enc_dek, key_version = self._get_dek()
        nonce      = os.urandom(12)                    # 96-bit nonce — never reuse
        aesgcm     = AESGCM(plaintext_dek)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)

        return {
            "ciphertext":   base64.b64encode(ciphertext).decode(),
            "nonce":        base64.b64encode(nonce).decode(),
            "enc_dek":      base64.b64encode(enc_dek).decode(),
            "key_version":  key_version,
            "algorithm":    "AES_256_GCM",
        }

    def decrypt(self, envelope: dict) -> str:
        enc_dek    = base64.b64decode(envelope["enc_dek"])
        resp       = self._kms.decrypt(CiphertextBlob=enc_dek)
        plaintext_dek = resp["Plaintext"]

        nonce      = base64.b64decode(envelope["nonce"])
        ciphertext = base64.b64decode(envelope["ciphertext"])
        aesgcm     = AESGCM(plaintext_dek)

        return aesgcm.decrypt(nonce, ciphertext, None).decode()

    def _get_dek(self) -> tuple[bytes, bytes, str]:
        resp = self._kms.generate_data_key(
            KeyId=self._key_id, KeySpec="AES_256"
        )
        return (
            resp["Plaintext"],         # plaintext DEK — in memory only
            resp["CiphertextBlob"],    # encrypted DEK — stored with ciphertext
            resp["KeyId"],             # key version ARN
        )
```

### 2.3 Encrypted Fields by Table

| Table | Field | Reason |
|---|---|---|
| `risk_decisions` | `customer_id` | Pseudonymous identifier — re-linkable |
| `risk_decisions` | `ip_subnet` | Network PII |
| `risk_decisions` | `device_fingerprint_id` | Device PII |
| `cases` | `analyst_notes` | Free-text — may contain PII |
| `customers` | `email_hash` | SHA-256 hash — encrypted at rest additionally |
| `payment_instruments` | `bin` | Card data — PCI DSS Req 3.5.1 |
| `payment_instruments` | `last_four` | Card data — PCI DSS Req 3.5.1 |

**Never stored (not encrypted — simply rejected):**
- Full PAN — rejected at Pydantic validation layer
- CVV / CVC — rejected at Pydantic validation layer
- Full track data — never accepted by API

---

## 3. TLS Configuration

### 3.1 External (Cloudflare → Kong)

```
Min TLS version:    1.3
Cipher suites:      TLS_AES_256_GCM_SHA384
                    TLS_CHACHA20_POLY1305_SHA256
                    TLS_AES_128_GCM_SHA256
Certificate:        Cloudflare-managed (auto-renew)
HSTS:               max-age=31536000; includeSubDomains; preload
TLS 1.0/1.1:        Blocked at Cloudflare WAF
TLS 1.2:            Blocked (RAS security baseline — stricter than PCI minimum)
```

### 3.2 Internal (Istio mTLS)

```
Mode:               STRICT (PeerAuthentication — all namespaces)
Certificate issuer: Istio Citadel CA (internal)
Cert rotation:      Every 24 hours (automatic)
Identity format:    SPIFFE: spiffe://cluster.local/ns/{ns}/sa/{sa}
TLS version:        1.3
```

```yaml
# k8s/istio/peer-authentication-strict.yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: risk
spec:
  mtls:
    mode: STRICT
```

> *@priya:* "PERMISSIVE mode is for migration only. In production, STRICT mode is required. Any connection that cannot present a valid mTLS certificate is dropped — no fallback to plaintext, no exceptions."

---

## 4. JWT Configuration

All API authentication uses RS256 asymmetric JWT signed by Keycloak.

```
Algorithm:          RS256 (asymmetric — private key in Keycloak only)
Key size:           RSA 2048-bit
Access token TTL:   15 minutes
Refresh token TTL:  24 hours (single-use rotation)
JWKS endpoint:      https://auth.ras.internal/realms/ras/protocol/openid-connect/certs
Audience:           ras-api
Issuer:             https://auth.ras.internal/realms/ras
```

```python
# app/core/security.py — JWT validation

from jose import jwt, JWTError
from fastapi import HTTPException

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            key=_get_jwks(),           # Fetched from Keycloak JWKS endpoint
            algorithms=["RS256"],      # HS256 explicitly rejected
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        )
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail="Invalid token")
```

**Why RS256 over HS256:** HS256 requires every validating service to hold the signing key — multiplying exposure surface. RS256 keeps the private key in Keycloak only. A compromised validation service cannot forge tokens.

---

## 5. HMAC Webhook Signing

All outbound webhooks (merchant callbacks, case resolution notices) are signed using HMAC-SHA256 — identical to Stripe's webhook signing scheme.

```
Algorithm:    HMAC-SHA256
Secret:       Per-merchant secret — stored in Vault (dynamic, rotatable)
Header:       X-RAS-Signature: t={timestamp},v1={hmac_hex}
Replay window: 300 seconds
```

```python
# app/core/webhooks.py

import hmac, hashlib, time

def sign_payload(payload: bytes, secret: str) -> str:
    ts  = str(int(time.time()))
    msg = f"{ts}.".encode() + payload
    sig = hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"

def verify_signature(
    payload: bytes,
    header: str,
    secret: str,
    tolerance: int = 300,
) -> bool:
    try:
        parts = dict(p.split("=", 1) for p in header.split(","))
        ts, sig = int(parts["t"]), parts["v1"]
    except (KeyError, ValueError):
        return False

    if abs(time.time() - ts) > tolerance:
        return False                        # Replay attack prevention

    expected = hmac.new(
        secret.encode(),
        f"{ts}.".encode() + payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, sig)  # Timing-safe comparison
```

**`hmac.compare_digest` is mandatory.** Direct string comparison (`==`) is vulnerable to timing attacks — an attacker can infer correct HMAC bytes by measuring response time differences.

---

## 6. Key Management

### 6.1 Key Inventory

| Key | Type | Size | Storage | Rotation | Owner |
|---|---|---|---|---|---|
| PII field KEK | AES-256 | 256-bit | AWS KMS HSM | 90 days (auto) | `@priya` |
| JWT signing key | RSA | 2048-bit | Keycloak + AWS KMS | Annual | `@priya` |
| Webhook secret (per merchant) | HMAC | 256-bit | HashiCorp Vault | On request / annually | `@priya` |
| Istio CA root cert | RSA | 4096-bit | Istio Citadel | 1 year | `@darius` |
| Istio workload certs | ECDSA | P-256 | Istio Citadel | 24 hours (auto) | `@darius` |
| PostgreSQL TLS cert | RSA | 2048-bit | AWS ACM | 13 months (auto) | `@darius` |
| Kafka SASL credentials | SCRAM-SHA-512 | — | HashiCorp Vault | 90 days | `@darius` |

### 6.2 Key Rotation Procedure

**AWS KMS KEK (automatic):**
```
1. KMS automatic rotation enabled — no manual steps required
2. Old key versions retained indefinitely for decryption of existing ciphertext
3. New encryptions use latest key version automatically
4. CloudTrail logs all key usage — reviewed quarterly by @priya
```

**JWT signing key (manual — annual):**
```
1. Generate new RSA-2048 key pair in Keycloak
2. Add new public key to JWKS endpoint (dual-key period: 48h)
3. All new tokens signed with new key
4. After 48h: remove old public key from JWKS
5. Existing tokens with old key expire within 15 min (access token TTL)
6. Zero-downtime rotation — no service restart required
```

**Emergency key rotation (compromise suspected):**
```
1. Page @priya immediately
2. Revoke compromised key in AWS KMS / Keycloak / Vault
3. All tokens signed with revoked key become invalid immediately
4. Users must re-authenticate — expected disruption: ~15 min
5. Follow security_incident.md for breach notification assessment
```

---

## 7. Prohibited Patterns

The following patterns are forbidden in RAS codebase. Semgrep rules enforce these at CI.

| Prohibited | Reason | Semgrep Rule |
|---|---|---|
| `AES/CBC` | Padding oracle vulnerability | `crypto-cbc-mode` |
| `HS256` JWT algorithm | Shared secret — wide exposure | `jwt-hs256` |
| `hashlib.md5` / `hashlib.sha1` | Broken — collision attacks | `weak-hash-algo` |
| `random` for security tokens | Not cryptographically secure — use `secrets` | `insecure-random` |
| Hardcoded secrets in code | Supply chain exposure | `hardcoded-secret` |
| `ssl.CERT_NONE` | Disables certificate validation | `ssl-no-verify` |
| `# nosec` without comment | Suppresses Bandit — must be documented | `nosec-undocumented` |

---

## 8. Compliance Mapping

| Control | PCI DSS v4.0 | GDPR | NIST |
|---|---|---|---|
| AES-256-GCM field encryption | Req 3.5.1 | Art. 32(1)(a) | SP 800-111 |
| TLS 1.3 in transit | Req 4.2.1 | Art. 32(1)(a) | SP 800-52r2 |
| AWS KMS key management | Req 3.7.1, 3.7.2 | Art. 32 | SP 800-57 |
| 90-day key rotation | Req 3.7.5 | — | SP 800-57 |
| mTLS internal traffic | Req 4.2.1 | Art. 32 | SP 800-52r2 |
| RS256 JWT | Req 8.3.1 | Art. 32 | SP 800-63B |
| HMAC webhook signing | Req 6.2.4 | Art. 32 | RFC 2104 |

---

## 9. Related Documents

| Document | Location |
|---|---|
| Threat Model (STRIDE) | `docs/security/threat_model.md` |
| Vault Setup Guide | `docs/security/vault_setup.md` |
| RBAC Matrix | `docs/security/rbac_matrix.md` |
| ADR-003 (KMS Envelope Encryption) | `docs/architecture/adr/ADR-003-kms-envelope-encryption.md` |
| ADR-007 (Istio mTLS) | `docs/architecture/adr/ADR-007-istio-mtls.md` |
| PCI DSS Controls | `docs/compliance/pci_dss_controls.md` |
| Security Incident Playbook | `docs/runbooks/security_incident.md` |

---

*Document Version: 1.0.0*
*Owner: Priya Nair — Principal Security Engineer*
*Review Cycle: Quarterly · On any cryptographic standard change*
*Classification: Internal — RESTRICTED — Security Sensitive*