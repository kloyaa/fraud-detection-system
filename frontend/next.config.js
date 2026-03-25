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
     * Security headers — coordinated with @priya.
     *
     * CSP: script-src 'self' with nonce injection (Next.js handles nonce via
     * the experimental.serverActions config). No 'unsafe-inline', no 'unsafe-eval'.
     *
     * NOTE: In production, the nonce is injected by Next.js middleware.
     * The static CSP below is the baseline; nonce augmentation happens at runtime.
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
                    {
                        key: "Content-Security-Policy",
                        value: [
                            "default-src 'self'",
                            "script-src 'self'",
                            "style-src 'self' 'unsafe-inline'",
                            "img-src 'self' data: blob:",
                            "font-src 'self'",
                            "connect-src 'self'",
                            "frame-ancestors 'none'",
                            "base-uri 'self'",
                            "form-action 'self'",
                        ].join("; "),
                    },
                ],
            },
        ];
    },
};

module.exports = nextConfig;
