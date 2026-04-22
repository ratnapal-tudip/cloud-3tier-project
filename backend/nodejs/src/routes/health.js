/**
 * Health check routes — mirrors FastAPI health endpoints.
 *
 * GET /          → root
 * GET /health    → basic health check
 * GET /health/ready → readiness probe (checks DB)
 * GET /health/live  → liveness probe
 */

const router = require("express").Router();
const pool = require("../config/db");

const VERSION = "1.0.0";
const SERVICE = "nodejs-express";

// ---------------------------------------------------------------------------
// GET /
// ---------------------------------------------------------------------------
router.get("/", (req, res) => {
  res.json({ message: "Cloud 3-Tier API is running" });
});

// ---------------------------------------------------------------------------
// GET /health
// Basic health check — used by load balancers & Jenkins CI/CD.
// ---------------------------------------------------------------------------
router.get("/health", (req, res) => {
  res.json({
    status: "healthy",
    timestamp: new Date().toISOString(),
    version: VERSION,
    service: SERVICE,
  });
});

// ---------------------------------------------------------------------------
// GET /health/ready
// Readiness probe — confirms app AND database are ready.
// Returns 503 if DB is unreachable (mirrors FastAPI 503 behaviour).
// ---------------------------------------------------------------------------
router.get("/health/ready", async (req, res) => {
  try {
    const [rows] = await pool.execute("SELECT 1");
    void rows; // just confirming query succeeds
  } catch {
    return res.status(503).json({ detail: "Database not ready" });
  }

  res.json({
    status: "healthy",
    timestamp: new Date().toISOString(),
    version: VERSION,
    service: SERVICE,
  });
});

// ---------------------------------------------------------------------------
// GET /health/live
// Liveness probe — lightweight check that the process is alive.
// ---------------------------------------------------------------------------
router.get("/health/live", (req, res) => {
  res.json({ message: "alive" });
});

module.exports = router;
