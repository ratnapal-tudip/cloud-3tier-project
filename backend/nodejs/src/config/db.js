/**
 * MySQL connection pool — mirrors the FastAPI pooling.MySQLConnectionPool.
 * Uses mysql2/promise for async/await support.
 */

const mysql = require("mysql2/promise");

const pool = mysql.createPool({
  host: process.env.MYSQL_HOST,
  port: parseInt(process.env.MYSQL_PORT),
  user: process.env.MYSQL_USER,
  password: process.env.MYSQL_PASSWORD,
  database: process.env.MYSQL_DATABASE,
  connectionLimit: 5,           // same pool_size as FastAPI
  waitForConnections: true,
  queueLimit: 0,
});

module.exports = pool;
