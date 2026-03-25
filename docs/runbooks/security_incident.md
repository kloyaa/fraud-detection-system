# Security Incident Response

**Severity:** P1 (all security incidents) · **Owner:** `@priya` · **Escalate to:** `@james`, CISO

## Incident Classification

| Type | Examples | Response Time |
|---|---|---|
| **Critical** | PAN in logs, active breach, credential compromise | Immediate (< 15 min) |
| **High** | Suspicious auth pattern, Falco runtime alert, CRITICAL CVE in production | < 1 hour |
| **Medium** | Anomalous feature distribution, failed pentest finding, DLQ security events | < 4 hours |

## Immediate Actions (All Incidents)

```
1. Do NOT attempt to fix before containing
2. Page @priya + @james immediately
3. Open incident channel: #incident-security-YYYYMMDD in Slack
4. Preserve evidence — do NOT restart pods until forensics complete
5. Activate incident log — record every action with timestamp
```

## Scenario A: PAN Detected in Logs

```bash
# STOP all log shipping immediately
kubectl scale deployment loki-promtail -n monitoring --replicas=0

# Identify affected log stream
kubectl logs -n risk -l app=ras-scoring-api --tail=1000 | \
  grep -E '[0-9]{13,16}'

# Contain: isolate affected pod
kubectl label pod <pod-name> -n risk quarantine=true
kubectl apply -f k8s/network-policies/quarantine-policy.yaml

# Page @james — GDPR Art. 33 breach notification assessment
# 72-hour ICO notification window starts NOW
# Document: timestamp of discovery, estimated records affected
```

## Scenario B: Credential / Key Compromise

```bash
# Immediately revoke compromised credential in Vault
vault lease revoke -prefix <lease-prefix>

# If JWT signing key: rotate in Keycloak
# All existing tokens become invalid immediately (~15 min disruption)
# Page @priya for key rotation procedure

# If AWS KMS key: disable key version in AWS console
# Existing encrypted data requires re-encryption with new key
# Page @marcus for re-encryption scope assessment

# Audit: what was accessed with compromised credential?
vault audit list
# Review CloudTrail for KMS key usage
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=<key-id>
```

## Scenario C: Active Intrusion (Falco Alert)

```bash
# Isolate affected pod immediately
kubectl label pod <pod-name> -n risk quarantine=true
kubectl apply -f k8s/network-policies/quarantine-policy.yaml

# Capture forensic snapshot BEFORE pod restart
kubectl exec -n risk <pod-name> -- ps aux > /tmp/incident-ps.txt
kubectl exec -n risk <pod-name> -- netstat -tulpn > /tmp/incident-netstat.txt
kubectl logs -n risk <pod-name> --previous > /tmp/incident-logs.txt

# Do NOT restart pod until @priya has reviewed forensics

# Check for lateral movement
kubectl get pods -n risk -o wide | grep -v Running
kubectl logs -n risk --all-containers=true --since=1h | \
  grep -i "connection refused\|permission denied\|unauthorized"
```

## Scenario D: Anomalous Scoring Pattern (Model Attack)

```bash
# Check score distribution anomaly
kubectl logs -n risk -l app=ras-scoring-api --tail=1000 | \
  jq '.score' | sort -n | uniq -c

# Check for systematic low scoring (adversarial evasion attempt)
# If mean score shifted > 40 points vs. baseline → page @yuki

# Temporarily lower decline threshold as defensive measure
# (requires @marcus + @james approval — affects merchant SLA)
```

## Regulatory Notifications

| Obligation | Trigger | Deadline | Owner |
|---|---|---|---|
| ICO (UK GDPR Art. 33) | Personal data breach | 72 hours from discovery | `@james` |
| EDPB (EU GDPR Art. 33) | EU resident data affected | 72 hours | `@james` |
| FinCEN (BSA) | Breach affecting AML records | As soon as practicable | `@james` |
| PCI DSS | CHD breach | Immediately + forensics | `@james` + QSA |
| Merchant notification | Any breach affecting merchant data | Per merchant contract SLA | `@james` |

## Post-Incident

```
Within 24h: Incident timeline documented
Within 48h: Root cause identified
Within 72h: Regulatory notifications filed (if required)
Within 7d:  Post-mortem published to #engineering
Within 30d: Preventive controls implemented + verified
```
