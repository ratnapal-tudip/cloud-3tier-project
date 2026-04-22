/**
 * Auth routes — mirrors FastAPI auth endpoints.
 *
 * POST /api/auth/signup → register a new user
 * POST /api/auth/login  → login, returns JWT
 */

const router = require("express").Router();
const { body, validationResult } = require("express-validator");

const pool = require("../config/db");
const { hashPassword, verifyPassword, createAccessToken } = require("../utils/auth");

// ---------------------------------------------------------------------------
// Helper — format a DB user row to match FastAPI's UserResponse schema
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
// POST /api/auth/signup
// Mirrors: @app.post("/api/auth/signup", response_model=UserResponse, status_code=201)
// ---------------------------------------------------------------------------
router.post(
  "/signup",
  [
    body("username").notEmpty().withMessage("username is required"),
    body("email").isEmail().withMessage("A valid email is required"),
    body("password").notEmpty().withMessage("password is required"),
  ],
  async (req, res) => {
    // Validate request body
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(422).json({ detail: errors.array() });
    }

    const { username, email, password, full_name = "" } = req.body;

    // Check if username already exists
    const [existingUsername] = await pool.execute(
      "SELECT id FROM users WHERE username = ?",
      [username]
    );
    if (existingUsername.length) {
      return res.status(400).json({ detail: "Username already taken" });
    }

    // Check if email already exists
    const [existingEmail] = await pool.execute(
      "SELECT id FROM users WHERE email = ?",
      [email]
    );
    if (existingEmail.length) {
      return res.status(400).json({ detail: "Email already registered" });
    }

    // Insert user with hashed password
    const hashed = await hashPassword(password);
    const [result] = await pool.execute(
      "INSERT INTO users (username, email, hashed_password, full_name) VALUES (?, ?, ?, ?)",
      [username, email, hashed, full_name]
    );

    // Fetch and return the created user (mirrors FastAPI pattern)
    const [rows] = await pool.execute(
      "SELECT * FROM users WHERE id = ?",
      [result.insertId]
    );

    return res.status(201).json(formatUser(rows[0]));
  }
);

// ---------------------------------------------------------------------------
// POST /api/auth/login
// Mirrors: @app.post("/api/auth/login", response_model=LoginResponse)
//
// FastAPI uses OAuth2PasswordRequestForm (form-encoded: username + password).
// We accept BOTH application/x-www-form-urlencoded AND application/json so
// the frontend can use either Content-Type without changes.
// ---------------------------------------------------------------------------
router.post("/login", async (req, res) => {
  // Support both form-encoded (OAuth2 standard) and JSON bodies
  const username = req.body.username;
  const password = req.body.password;

  if (!username || !password) {
    return res.status(422).json({ detail: "username and password are required" });
  }

  const [rows] = await pool.execute(
    "SELECT * FROM users WHERE username = ?",
    [username]
  );
  const user = rows[0];

  if (!user || !(await verifyPassword(password, user.hashed_password))) {
    return res.status(401).json({ detail: "Incorrect username or password" });
  }

  const token = createAccessToken({ sub: user.username });

  return res.json({
    access_token: token,
    token_type: "bearer",
    username: user.username,
    message: "Login successful",
  });
});

module.exports = router;
