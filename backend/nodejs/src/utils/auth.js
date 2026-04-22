/**
 * Auth helpers — mirrors FastAPI's hash_password / verify_password / create_access_token.
 */

const bcrypt = require("bcryptjs");
const jwt = require("jsonwebtoken");

const SECRET_KEY = process.env.SECRET_KEY || "super-secret-dev-key-change-in-production";
const ALGORITHM = "HS256";
const ACCESS_TOKEN_EXPIRE_SECONDS = 60 * 60 * 24; // 24 hours — same as FastAPI

/**
 * Hash a plain-text password (async, bcrypt).
 * Mirrors: bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
 */
async function hashPassword(password) {
  const salt = await bcrypt.genSalt(12);
  return bcrypt.hash(password, salt);
}

/**
 * Verify a plain-text password against a bcrypt hash.
 * Mirrors: bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
 */
async function verifyPassword(plain, hashed) {
  return bcrypt.compare(plain, hashed);
}

/**
 * Create a signed JWT access token.
 * Mirrors: jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
 *
 * @param {object} data - payload data (must include `sub`)
 * @param {number} [expiresInSeconds]
 */
function createAccessToken(data, expiresInSeconds = ACCESS_TOKEN_EXPIRE_SECONDS) {
  const payload = { ...data };
  return jwt.sign(payload, SECRET_KEY, {
    algorithm: ALGORITHM,
    expiresIn: expiresInSeconds,
  });
}

/**
 * Verify and decode a JWT token.
 * Throws if invalid / expired.
 */
function verifyToken(token) {
  return jwt.verify(token, SECRET_KEY, { algorithms: [ALGORITHM] });
}

module.exports = { hashPassword, verifyPassword, createAccessToken, verifyToken };
