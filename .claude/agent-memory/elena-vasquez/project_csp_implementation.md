---
name: CSP Implementation
description: Content Security Policy headers agreed with @priya -- script-src self, no inline, nonce pattern planned
type: project
---

CSP headers are defined in `frontend/next.config.ts` in the `headers()` function.

Current baseline CSP:
- `default-src 'self'`
- `script-src 'self'` (no unsafe-inline, no unsafe-eval)
- `style-src 'self' 'unsafe-inline'` (Tailwind injects styles; nonce for styles is a future improvement)
- `img-src 'self' data: blob:`
- `font-src 'self'` (Inter self-hosted via next/font)
- `connect-src 'self'` (BFF pattern means all API calls are same-origin)
- `frame-ancestors 'none'`

Additional security headers: X-Frame-Options DENY, HSTS, X-Content-Type-Options nosniff, strict Referrer-Policy, Permissions-Policy.

**Why:** Agreed with @priya. No inline scripts prevents XSS. No eval prevents code injection. Self-hosted fonts avoid CDN dependency (and CSP would reject Google Fonts CDN). Nonce-based script-src is the next step for dynamic scripts.

**How to apply:** Any third-party script addition requires @priya review. Style `unsafe-inline` is a known compromise for Tailwind -- track the nonce-for-styles improvement.
