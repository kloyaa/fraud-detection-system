# ADR-007: Service Mesh Security — Istio mTLS over Manual Certificate Management

```yaml
id:         ADR-007
title:      Internal Service-to-Service Encryption Strategy
status:     Accepted
date:       2024-01-16  (Sprint 2)
author:     Marcus Chen (@marcus)
reviewers:  "@priya · @darius"
deciders:   "@priya · @marcus · @darius"
supersedes: —
superseded_by: —
```

## Context

PCI DSS v4.0 Requirement 4.2.1 mandates encryption of cardholder data in transit — including internal (east-west) traffic. RAS has 8+ internal services communicating over the cluster network. Without encryption, a compromised pod can intercept all east-west traffic in plaintext.

Requirements:
- Mutual TLS (mTLS) for all service-to-service communication
- Automatic certificate rotation without application restarts
- Zero application code changes for encryption
- Service identity tied to Kubernetes ServiceAccount (not IP address)
- Observable: mTLS status visible in metrics/dashboards

Candidates: **Istio mTLS (STRICT mode)**, **Manual cert management (cert-manager)**, **Linkerd mTLS**, **Application-layer TLS (each service manages certs)**

## Decision

**Use Istio 1.21 with PeerAuthentication policy set to STRICT mTLS for all namespaces containing RAS services.**

```yaml
# k8s/istio/peer-authentication-strict.yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: risk
spec:
  mtls:
    mode: STRICT     # PERMISSIVE is not acceptable in production
```

## Rationale

**Why not manual cert-manager:**
Manual certificate management at 8+ services means: per-service certificate issuance, rotation tracking, application code for TLS handshake in every service, and certificate expiry monitoring for every cert. At Stripe, a manual cert rotation failure caused a 4-hour internal service outage — the certificate expired on a Saturday and no alert fired. Istio's Citadel CA issues, rotates, and renews all certificates automatically, with zero application code changes. Rotation happens every 24 hours by default — applications never see an expired cert.

**STRICT vs PERMISSIVE:**
Istio supports PERMISSIVE mode (both mTLS and plaintext accepted) for migration. PERMISSIVE is not acceptable in production — it silently accepts unencrypted connections, which means a misconfigured service or a pod that bypasses the sidecar could send plaintext traffic. STRICT mode rejects all connections that cannot present a valid mTLS certificate. This is a binary security guarantee.

**Service identity:**
Istio issues certificates bound to Kubernetes ServiceAccount identities (SPIFFE/SPIRE format: `spiffe://cluster.local/ns/risk/sa/ras-scoring-sa`). This means: even if an attacker spoofs a pod's IP address, they cannot present a valid certificate for the scoring API's ServiceAccount identity. Network-layer identity spoofing is insufficient — cryptographic identity is required.

**@priya's security requirement:** "East-west traffic is where attackers pivot after initial pod compromise. mTLS STRICT mode means a compromised enrichment service pod cannot establish a connection to the database service — it does not hold the scoring API's certificate. Combined with NetworkPolicy default-deny, blast radius of a compromised pod is bounded to the compromised service's explicitly allowed peers only."

## Consequences

**Positive:**
- Zero application code changes for internal TLS — transparent to developers
- Automatic cert rotation every 24h — no expiry incidents
- Service identity tied to ServiceAccount — IP spoofing insufficient for impersonation
- mTLS status observable in Kiali and Grafana

**Negative:**
- Envoy sidecar adds ~1ms per request (P50) — acceptable within latency budget
- Istio control plane is an additional operational dependency (@darius)
- STRICT mode requires all services to have Istio sidecar injected — no opt-out

**Operational requirement:** All new Kubernetes namespaces containing RAS services must have `istio-injection: enabled` label and a STRICT PeerAuthentication policy before any pods are deployed. This is a @darius Helm chart standard enforced via OPA Gatekeeper policy.

*ADR Directory Version: 1.0.0*
*Owner: Marcus Chen — Chief Risk Architect*
*Format: MADR (Markdown Architectural Decision Records)*
*Review: New ADRs require Architecture Review Board approval*
*Classification: Internal — Engineering Confidential*