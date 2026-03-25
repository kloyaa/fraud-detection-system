---
name: data-testid Naming Convention
description: Convention agreed with @aisha for Playwright test selectors -- format is [component]-[element]
type: project
---

All interactive components use `data-testid` attributes for @aisha's Playwright E2E tests. The naming convention is `[component]-[element]`.

Established test IDs as of frontend scaffold (2026-03-25):
- `risk-badge-level`, `decision-badge-action`
- `case-queue-table`, `case-queue-row`, `case-queue-header-*`
- `case-queue-cell-transaction`, `case-queue-cell-score`, `case-queue-cell-level`, `case-queue-cell-decision`
- `risk-score-gauge`
- `login-form`, `login-email`, `login-password`, `login-submit`, `login-error`
- `skeleton-loader`, `case-queue-skeleton`
- `dashboard-error`, `dashboard-error-retry`
- `case-detail-page`, `case-detail-fields`, `case-detail-reason-codes`
- `nav-logo`, `nav-case-queue`, `nav-rules`, `nav-models`, `nav-env-badge`

**Why:** Consistent naming lets @aisha build page object models without guessing. The convention is simple enough that new components follow it naturally.

**How to apply:** Every new interactive or data-displaying component MUST have data-testid attributes following this convention. Add new IDs to this list when created.
