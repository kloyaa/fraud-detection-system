---
name: Bundle Size Baselines
description: Bundle size budgets and current baselines per route -- to be measured after first production build
type: project
---

Bundle size budgets enforced via `bundlewatch` in `frontend/package.json`:
- Dashboard (case queue): < 150KB JavaScript
- Rule editor (includes CodeMirror): < 300KB JavaScript

**Baselines not yet established.** The first production build (`pnpm build`) will establish the baseline numbers. These will be tracked per-commit in CI once the GitHub Actions pipeline is set up.

**Why:** Performance budgets prevent silent regression. A fraud analyst at 3am on a throttled VPN connection cannot afford a 500KB JavaScript payload.

**How to apply:** After the first `pnpm build`, record the actual bundle sizes here. Any dependency addition must be evaluated for its impact on these budgets.
