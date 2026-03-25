#!/usr/bin/env node

/**
 * Frontend dev server startup script
 * Logs service endpoints for the RAS frontend
 * Usage: node scripts/dev-startup.js [--port 3000]
 */

const { spawn } = require("child_process");

// Parse command line arguments
const args = process.argv.slice(2);
const portIndex = args.indexOf("--port");
const frontendPort = portIndex !== -1 && args[portIndex + 1] ? args[portIndex + 1] : process.env.NEXT_PORT || "3000";

// Extract backend URL from environment or use default
const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";

// Log service information with dynamic ports
const logServiceInfo = (fPort, bUrl) => {
    console.log("\n" + "=".repeat(80));
    console.log("📊 RISK ASSESSMENT SYSTEM (RAS) — Services Starting");
    console.log("=".repeat(80));
    console.log(`🌐 Frontend URL:        http://localhost:${fPort}`);
    console.log(`📡 Backend API:         ${bUrl}`);
    console.log(`📚 Swagger UI:          ${bUrl}/docs`);
    console.log(`📚 ReDoc:               ${bUrl}/redoc`);
    console.log(`🔄 OpenAPI JSON:        ${bUrl}/openapi.json`);
    console.log("=".repeat(80) + "\n");
};

// Start the Next.js dev server
const startDevServer = (port) => {
    const nextDev = spawn("next", ["dev", "--port", port, "--hostname", "0.0.0.0"], {
        stdio: "inherit",
        shell: true,
    });

    nextDev.on("error", (err) => {
        console.error("Failed to start dev server:", err);
        process.exit(1);
    });

    nextDev.on("close", (code) => {
        process.exit(code);
    });
};

logServiceInfo(frontendPort, backendUrl);
startDevServer(frontendPort);
