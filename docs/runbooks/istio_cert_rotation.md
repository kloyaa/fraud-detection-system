# Istio — Certificate Rotation

**Alert:** `istio_cert_expiry_days < 7`  
**Severity:** P2 · **Owner:** `@darius`

## Overview

Istio Citadel CA rotates workload certificates every 24 hours automatically. This runbook covers manual rotation for the Citadel root CA (annual) and emergency rotation on compromise.

## Verify Current Certificate Status

```bash
# Check workload cert expiry across all pods
istioctl proxy-config secret <pod-name>.<namespace> | \
  grep -E "NAME|VALID"

# Check Citadel CA cert expiry
kubectl get secret -n istio-system istio-ca-secret -o jsonpath=\
  '{.data.ca-cert\.pem}' | base64 -d | \
  openssl x509 -noout -dates
```

## Routine Workload Cert Rotation (Automatic)

Workload certs rotate every 24 hours without intervention. If a pod is showing an expired cert:

```bash
# Force cert refresh by restarting the pod
kubectl rollout restart deployment/<deployment-name> -n risk

# Verify new cert
istioctl proxy-config secret <new-pod>.<namespace> | grep VALID
```

## Root CA Rotation (Annual — Planned)

```bash
# Step 1: Generate new root CA
# (Follow Istio documentation for CA rotation with zero downtime)
# https://istio.io/latest/docs/tasks/security/cert-management/plugin-ca-cert/

# Step 2: Add new CA to trust bundle (dual-CA period)
kubectl create secret generic cacerts -n istio-system \
  --from-file=ca-cert.pem=new-ca-cert.pem \
  --from-file=ca-key.pem=new-ca-key.pem \
  --from-file=root-cert.pem=new-root-cert.pem \
  --from-file=cert-chain.pem=new-cert-chain.pem \
  --dry-run=client -o yaml | kubectl apply -f -

# Step 3: Rolling restart of istiod
kubectl rollout restart deployment/istiod -n istio-system

# Step 4: Rolling restart of all workloads to pick up new certs
for ns in risk kafka; do
  kubectl rollout restart deployment -n $ns
done

# Step 5: Verify all workloads have new cert
istioctl analyze -n risk
```

## Emergency Rotation (Cert Compromise)

```bash
# Immediately revoke all current certs by rotating root CA
# This will cause brief disruption to all internal services (~2 min)
# Page @priya + @marcus before proceeding

# Follow Root CA Rotation procedure above with urgency
# All pods will fail mTLS until they receive new certs
# Karpenter will handle pod restarts
```

## Recovery Criteria
All pods showing valid certs with new CA → resolve alert.
