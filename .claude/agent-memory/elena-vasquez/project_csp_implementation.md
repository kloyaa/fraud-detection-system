---
name: CSP Nonce Implementation
description: Content Security Policy with per-request nonce -- consolidated middleware, NonceContext, reviewed with @priya 2026-03-25
type: project
---

CSP nonce injection is implemented in `frontend/middleware.ts` (the single root middleware file).

Architecture:
- `middleware.ts` generates 128-bit nonce via `crypto.getRandomValues(new Uint8Array(16))` + base64
- Nonce is injected as `x-nonce` request header (Next.js 14 reads this automatically for its inline hydration scripts)
- CSP header is set on both the request (for downstream components) and the response (for browser enforcement)
- NextAuth `auth()` wrapper handles session protection in the same middleware
- Root layout (Server Component) reads nonce via `headers().get("x-nonce")` and passes to `<Providers nonce={nonce}>`
- `Providers` exposes nonce via `NonceContext` -- client components access it with `useNonce()` hook for `<Script nonce={nonce}>`

CSP directives (reviewed by @priya 2026-03-25):
- `script-src 'self' 'nonce-...' 'strict-dynamic'` -- no unsafe-inline, ever
- `style-src 'self' 'unsafe-inline'` -- Tailwind compromise, reviewed exception
- `font-src 'self'` -- Inter self-hosted via next/font
- `connect-src 'self'` -- BFF pattern, all API calls same-origin
- `frame-ancestors 'none'` -- clickjacking defense-in-depth with X-Frame-Options DENY
- `object-src 'none'`, `base-uri 'self'`, `form-action 'self'`, `upgrade-insecure-requests`

Previous bug: `src/middleware.ts` had CSP nonce logic but was dead code because Next.js 14 only runs one middleware file (root takes precedence). Now deleted; all logic consolidated in root `middleware.ts`.

**Why:** XSS prevention is non-negotiable per @priya and hardening_standards.md section 6.2. Nonce-based CSP is required because Next.js inline scripts cannot use static hashes (content changes per SSR render).

**How to apply:** Any new `<Script>` component must use `useNonce()` from `@/app/providers`. Any third-party script addition requires @priya review. Never add `unsafe-inline` to script-src.
