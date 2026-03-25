# Sprint 8 — Security Hardening + Compliance

**Goal:** All security controls verified. PCI DSS + GDPR evidence complete.

**Duration:** 3 weeks  
**Lead:** `@priya` + `@james`  
**Supporting:** `@darius`

---

## Security

`@priya` leads

```
[ ] External penetration test completed (B-002)
[ ] All pentest findings remediated
[ ] Trivy — zero CRITICAL CVEs in production images
[ ] Falco runtime monitoring active + alerting
[ ] Container hardening per hardening_standards.md
[ ] Kubernetes CIS benchmark — kube-bench passing
```

---

## PCI DSS

`@james` + `@priya` lead

```
[ ] PCI-001: Elasticsearch audit logging enabled
[ ] PCI-003: All vendor DPAs signed (Vercel, Checkly, PagerDuty)
[ ] PCI-004: Hardening standards document complete
[ ] PCI-005: Incident response tabletop exercise run
[ ] Evidence repository complete (docs/compliance/pci_dss_evidence/)
[ ] QSA pre-assessment internal audit complete
```

---

## GDPR

`@james` leads

```
[ ] B-003: GDPR DPIA — external DPO sign-off obtained
[ ] ROPA completed (docs/compliance/ropa.md)
[ ] LIA documented (docs/compliance/lia.md)
[ ] Privacy notice published
[ ] Data subject rights endpoints tested (access + erasure)
[ ] Retention schedule implemented + verified (@darius)
```

---

## Completion Criteria

✅ Sprint 8 done when:
- External pentest passed
- DPIA signed (B-003 cleared)
- PCI evidence package complete
- PRR §4 (Security) passes
- PRR §6 (Compliance) passes

---

**Owner:** Priya Nair (`@priya`) + James Whitfield (`@james`)  
**Status:** ⏳ Not started  
**Created:** 2026-03-25
