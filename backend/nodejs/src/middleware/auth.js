/**
 * Auth middleware — extracts and validates the Bearer JWT token.
 * Mirrors FastAPI's get_current_user dependency.
 */

const pool = require("../config/db");
const { verifyToken } = require("../utils/auth");

async function requireAuth(req, res, next) {
  const authHeader = req.headers["authorization"] || "";
  const token = authHeader.startsWith("Bearer ") ? authHeader.slice(7) : null;

  if (!token) {
    return res.status(401).json({
      detail: "Invalid or expired token",
    });
  }

  let payload;
  try {
    payload = verifyToken(token);
  } catch {
    return res.status(401).json({ detail: "Invalid or expired token" });
  }

  const username = payload.sub;
  if (!username) {
    return res.status(401).json({ detail: "Invalid or expired token" });
  }

  const [rows] = await pool.execute(
    "SELECT * FROM users WHERE username = ?",
    [username]
  );

  if (!rows.length) {
    return res.status(401).json({ detail: "Invalid or expired token" });
  }

  req.currentUser = rows[0];
  next();
}

module.exports = requireAuth;
