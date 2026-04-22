-- ============================================================
-- Cloud 3-Tier Project — Database Initialization Script
-- This file is auto-executed by MySQL on first container start
-- via /docker-entrypoint-initdb.d/
-- ============================================================

-- Create database (if not already created via MYSQL_DATABASE env var)
CREATE DATABASE IF NOT EXISTS mydb;
USE mydb;

-- ============================================================
-- Users table
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
