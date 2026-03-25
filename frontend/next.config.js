/**
 * Next.js configuration for the RAS frontend.
 *
 * Security headers aligned with @priya (CSP nonce-based, no inline scripts).
 * BFF pattern: all API calls go through Route Handlers, never direct to backend.
 * Fonts self-hosted via next/font — no external CDN requests.
 */

// Log frontend service endpoints at server startup
const logServiceInfo = () => {
    console.log("\n" + "=".repeat(80));
    console.log("📊 RISK ASSESSMENT SYSTEM (RAS) — Frontend Service");
    console.log("=".repeat(80));
    console.log("🌐 Frontend URL:        http://localhost:3000");
    console.log("📡 Backend API:         http://localhost:8000");
    console.log("📚 Swagger UI:          http://localhost:8000/docs");
    console.log("📚 ReDoc:               http://localhost:8000/redoc");
    console.log("🔄 OpenAPI JSON:        http://localhost:8000/openapi.json");
    console.log("=".repeat(80) + "\n");
};

// Execute logging when config is loaded (both dev and build time)
logServiceInfo();

const nextConfig = {
    reactStrictMode: true,
    poweredByHeader: false,

    /**
     * Standalone output for Docker production builds.
     * Generates .next/standalone with a minimal Node.js server (server.js)
     * that includes only the dependencies needed at runtime.
     * Required by the multi-stage production Dockerfile.
     */
    output: "standalone",

    /** Redirect image optimization to self-hosted only */
    images: {
        remotePatterns: [],
        formats: ["image/avif", "image/webp"],
    },

    /**
     * Static security headers — coordinated with @priya.
     *
     * Content-Security-Policy is NOT set here. It is set dynamically in
     * middleware.ts (project root) with a per-request nonce so that Next.js inline
     * hydration scripts satisfy `script-src 'self' 'nonce-...'` without
     * requiring `'unsafe-inline'`.
     *
     * All other headers are static and safe to set at the config level.
     */
    async headers() {
        return [
            {
                source: "/(.*)",
                headers: [
                    {
                        key: "X-Frame-Options",
                        value: "DENY",
                    },
                    {
                        key: "X-Content-Type-Options",
                        value: "nosniff",
                    },
                    {
                        key: "Referrer-Policy",
                        value: "strict-origin-when-cross-origin",
                    },
                    {
                        key: "X-DNS-Prefetch-Control",
                        value: "on",
                    },
                    {
                        key: "Strict-Transport-Security",
                        value: "max-age=63072000; includeSubDomains; preload",
                    },
                    {
                        key: "Permissions-Policy",
                        value:
                            "camera=(), microphone=(), geolocation=(), interest-cohort=()",
                    },
                ],
            },
        ];
    },
};

module.exports = nextConfig;
