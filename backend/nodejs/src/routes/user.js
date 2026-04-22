/**
 * User / protected routes — mirrors FastAPI protected endpoints.
 *
 * GET /api/me        → current user's profile
 * GET /api/dashboard → protected dashboard data
 */

const router = require("express").Router();
const requireAuth = require("../middleware/auth");

// ---------------------------------------------------------------------------
// Helper — serialize a DB user row to match FastAPI's UserResponse schema
// ---------------------------------------------------------------------------
function formatUser(user) {
  return {
    id: user.id,
    username: user.username,
    email: user.email,
    full_name: user.full_name || "",
    created_at: user.created_at instanceof Date
      ? user.created_at.toISOString()
      : user.created_at,
  };
}

// ---------------------------------------------------------------------------
// GET /api/me
// Mirrors: @app.get("/api/me", response_model=UserResponse)
// ---------------------------------------------------------------------------
router.get("/me", requireAuth, (req, res) => {
  res.json(formatUser(req.currentUser));
});

// ---------------------------------------------------------------------------
// GET /api/dashboard
// Mirrors: @app.get("/api/dashboard")
// ---------------------------------------------------------------------------
router.get("/dashboard", requireAuth, (req, res) => {
  const user = req.currentUser;

  res.json({
    message: `Welcome back, ${user.full_name || user.username}!`,
    user: {
      id: user.id,
      username: user.username,
      email: user.email,
      full_name: user.full_name || "",
    },
    dashboard_data: {
      total_projects: 3,
      recent_activity: "Deployed v1.0.0 to production",
      server_status: "All systems operational",
    },
  });
});

module.exports = router;
