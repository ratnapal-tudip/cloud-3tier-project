/**
 * Cloud 3-Tier Node.js/Express Backend
 * =====================================
 * Drop-in equivalent of the Python FastAPI backend.
 * Same endpoints, same response shapes, same MySQL schema.
 *
 * Endpoints:
 *   GET  /                  → root
 *   GET  /health            → basic health check
 *   GET  /health/ready      → readiness probe (DB check)
 *   GET  /health/live       → liveness probe
 *   POST /api/auth/signup   → register new user
 *   POST /api/auth/login    → login → JWT token
 *   GET  /api/me            → current user profile  [protected]
 *   GET  /api/dashboard     → dashboard data        [protected]
 */

require("express-async-errors"); // must be first so async route errors propagate

const express = require("express");
const cors = require("cors");
const morgan = require("morgan");

const healthRoutes = require("./routes/health");
const authRoutes = require("./routes/auth");
const userRoutes = require("./routes/user");

const PORT = process.env.PORT || 3000;

const app = express();

// ---------------------------------------------------------------------------
// Middleware
// ---------------------------------------------------------------------------

// Request logger — prints: METHOD /path STATUS response-time ms
app.use(morgan("dev"));

// CORS — mirrors FastAPI CORSMiddleware(allow_origins=["*"])
app.use(cors({ origin: "*", credentials: true }));

// Parse JSON bodies
app.use(express.json());

// Parse URL-encoded bodies (for OAuth2 form submissions: username + password)
app.use(express.urlencoded({ extended: false }));

// ---------------------------------------------------------------------------
// Routes
// ---------------------------------------------------------------------------
app.use("/", healthRoutes);          // GET /, /health, /health/ready, /health/live
app.use("/api/auth", authRoutes);    // POST /api/auth/signup, /api/auth/login
app.use("/api", userRoutes);         // GET /api/me, /api/dashboard

// ---------------------------------------------------------------------------
// Global error handler — converts unhandled errors to JSON responses
// ---------------------------------------------------------------------------
// eslint-disable-next-line no-unused-vars
app.use((err, req, res, next) => {
  console.error(err);
  res.status(err.status || 500).json({
    detail: err.message || "Internal server error",
  });
});

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------
app.listen(PORT, "0.0.0.0", () => {
  console.log(`Cloud 3-Tier Node.js API running on http://0.0.0.0:${PORT}`);
});
