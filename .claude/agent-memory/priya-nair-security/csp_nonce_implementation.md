---
name: CSP Nonce Implementation Fix
description: Root cause of CSP blocking inline scripts was middleware collision; fixed by merging NextAuth + CSP nonce into single root middleware.ts
type: project
---

Next.js 14 CSP nonce middleware was dead code due to middleware collision (root middleware.ts shadows src/middleware.ts). Fixed 2026-03-25.

**Why:** The root middleware.ts exported only NextAuth auth, while the CSP nonce logic lived in src/middleware.ts which never executed. Browser enforced `script-src 'self'` without nonces, blocking all Next.js hydration/RSC inline scripts.

**How to apply:**
- Next.js allows exactly ONE middleware file; root takes precedence over src/
- The unified middleware at `frontend/middleware.ts` now chains NextAuth `auth()` wrapper with CSP nonce generation
- Nonce uses `crypto.getRandomValues(new Uint8Array(16))` for 128-bit entropy (OWASP minimum)
- CSP includes `'strict-dynamic'` so nonced scripts can load child scripts
- `style-src 'unsafe-inline'` is a reviewed exception for Tailwind CSS -- documented in hardening_standards.md
- Layout at `frontend/src/app/layout.tsx` reads nonce from `headers().get("x-nonce")`
- In Next.js 14, `headers()` is synchronous (becomes async in Next.js 15)
- `object-src 'none'`, `base-uri 'self'`, `form-action 'self'` added as defense-in-depth directives beyond the original spec
