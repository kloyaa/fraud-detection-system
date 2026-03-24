# ADR-004: ML Serving Framework — BentoML over TorchServe / Seldon

```yaml
id:         ADR-004
title:      ML Model Serving Framework
status:     Accepted
date:       2024-01-09  (Sprint 1)
author:     Marcus Chen (@marcus)
reviewers:  "@yuki · @darius"
deciders:   "@yuki · @marcus"
supersedes: —
superseded_by: —
```

## Context

RAS requires a model serving framework to host the XGBoost fraud scorer, LightGBM device risk model, and PyTorch behavioral embedding model. Requirements:

- Sub-25ms P95 inference latency per request
- Adaptive micro-batching (batch multiple concurrent requests for GPU/CPU efficiency)
- Multi-framework support: XGBoost, LightGBM, PyTorch in a single serving runtime
- Champion-challenger traffic splitting for A/B model promotion
- MLflow model registry integration
- Kubernetes-native deployment with HPA support

Candidates: **BentoML 1.3**, **TorchServe**, **Seldon Core**, **Ray Serve**, **Triton Inference Server**

## Decision

**Use BentoML 1.3 as the ML serving framework.**

## Rationale

| Criterion | BentoML | TorchServe | Seldon Core | Ray Serve |
|---|---|---|---|---|
| Multi-framework (XGB + PyTorch) | ✅ Native | ❌ PyTorch only | ✅ Via custom servers | ✅ Native |
| Adaptive micro-batching | ✅ Native | ⚠️ Manual config | ❌ Limited | ✅ Native |
| MLflow registry integration | ✅ Native | ❌ Manual | ⚠️ Plugin | ⚠️ Plugin |
| Champion-challenger (runners) | ✅ Native Runner API | ❌ Manual | ✅ SeldonDeployment | ⚠️ Manual |
| Operational complexity | ✅ Low | ⚠️ Medium | ❌ High (Istio dependency) | ⚠️ Medium |
| Kubernetes HPA | ✅ Prometheus metrics | ✅ | ✅ | ✅ |

**Adaptive micro-batching** is the decisive feature at 100k TPS. BentoML's `@bentoml.service(traffic={"max_batch_size": 64, "max_latency_ms": 1})` batches concurrent inference requests dynamically. At 50k TPS with 1ms batch window, ~50 requests batch together — reducing XGBoost inference overhead from ~12ms × 50 = 600ms of CPU time to ~18ms for the batch. Throughput multiplier: ~8x.

**Multi-framework in a single BentoService** allows the ensemble (XGBoost + LightGBM + PyTorch) to be served as a single deployment unit, sharing the request context and eliminating inter-service latency within the ensemble.

**ISS-001 (cold-start latency > 300ms)** was caused by BentoML's JIT compilation on first inference. Resolution: Kubernetes readiness probe configured to run 1,000 warmup inferences before pod joins load balancer. BentoML's `on_startup` hook handles this. (@yuki owns warmup logic, @darius owns readiness probe gate.)

## Consequences

**Positive:**
- ~8x CPU throughput improvement via adaptive batching vs. individual inference
- Single serving runtime for all three model frameworks
- Native MLflow integration — promote model versions via registry stage change
- Champion-challenger via BentoML Runner traffic percentage split

**Negative:**
- Cold-start latency (mitigated by warmup — ISS-001 resolved Sprint 3)
- BentoML is less mature than TorchServe/Triton for very large models (not a concern at our model sizes: 18–22 MB)
- GPU node pool required (@darius) — additional infrastructure cost

*ADR Directory Version: 1.0.0*
*Owner: Marcus Chen — Chief Risk Architect*
*Format: MADR (Markdown Architectural Decision Records)*
*Review: New ADRs require Architecture Review Board approval*
*Classification: Internal — Engineering Confidential*