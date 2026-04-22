"""
Cloud 3-Tier Backend API
Simple FastAPI backend with health checks and user authentication.
Uses MySQL with raw queries — no ORM.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import mysql.connector
from mysql.connector import pooling
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from jose import JWTError, jwt
import bcrypt

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-dev-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "root")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "cloud3tier")

# ---------------------------------------------------------------------------
# MySQL Connection Pool
# ---------------------------------------------------------------------------
db_pool = pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=5,
    host=MYSQL_HOST,
    port=MYSQL_PORT,
    user=MYSQL_USER,
    password=MYSQL_PASSWORD,
    database=MYSQL_DATABASE,
)


def get_db():
    """Get a connection from the pool, yield it, then return it to pool."""
    conn = db_pool.get_connection()
    try:
        yield conn
    finally:
        conn.close()



# ---------------------------------------------------------------------------
# Password hashing & JWT helpers
# ---------------------------------------------------------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
class SignupRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str = ""


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    message: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    created_at: datetime


class MessageResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    service: str


# ---------------------------------------------------------------------------
# Auth dependency — get current user from JWT token
# ---------------------------------------------------------------------------
def get_current_user(token: str = Depends(oauth2_scheme), conn=Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()

    if user is None:
        raise credentials_exception
    return user


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Cloud 3-Tier API",
    description="Simple backend with health checks and user authentication",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===========================================================================
#  HEALTH CHECK ENDPOINTS  (for Jenkins CI/CD & Load Balancers)
# ===========================================================================

@app.get("/", response_model=MessageResponse, tags=["Root"])
def root():
    """Root endpoint — confirms the API is reachable."""
    return {"message": "Cloud 3-Tier API is running"}


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    """
    Basic health check.
    Used by load balancers (ALB/NLB) and Jenkins pipeline to verify the service is up.
    Returns 200 if service is healthy.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "service": "python-fastapi",
    }


@app.get("/health/ready", response_model=HealthResponse, tags=["Health"])
def readiness_check(conn=Depends(get_db)):
    """
    Readiness probe — checks that the app AND database are ready.
    Used by Kubernetes / cloud load balancers.
    """
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
    except Exception:
        raise HTTPException(status_code=503, detail="Database not ready")

    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "service": "python-fastapi",
    }


@app.get("/health/live", response_model=MessageResponse, tags=["Health"])
def liveness_check():
    """
    Liveness probe — lightweight check that the process is alive.
    Used by Kubernetes liveness probes.
    """
    return {"message": "alive"}


# ===========================================================================
#  AUTH ENDPOINTS
# ===========================================================================

@app.post("/api/auth/signup", response_model=UserResponse, status_code=201, tags=["Auth"])
def signup(req: SignupRequest, conn=Depends(get_db)):
    """Register a new user."""
    cursor = conn.cursor(dictionary=True)

    # Check if username already exists
    cursor.execute("SELECT id FROM users WHERE username = %s", (req.username,))
    if cursor.fetchone():
        cursor.close()
        raise HTTPException(status_code=400, detail="Username already taken")

    # Check if email already exists
    cursor.execute("SELECT id FROM users WHERE email = %s", (req.email,))
    if cursor.fetchone():
        cursor.close()
        raise HTTPException(status_code=400, detail="Email already registered")

    # Insert user
    cursor.execute(
        "INSERT INTO users (username, email, hashed_password, full_name) VALUES (%s, %s, %s, %s)",
        (req.username, req.email, hash_password(req.password), req.full_name),
    )
    conn.commit()
    new_id = cursor.lastrowid

    # Fetch and return the created user
    cursor.execute("SELECT * FROM users WHERE id = %s", (new_id,))
    user = cursor.fetchone()
    cursor.close()
    return user


@app.post("/api/auth/login", response_model=LoginResponse, tags=["Auth"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), conn=Depends(get_db)):
    """
    Login with username & password.
    Returns a JWT access token.
    """
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username = %s", (form_data.username,))
    user = cursor.fetchone()
    cursor.close()

    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    token = create_access_token(data={"sub": user["username"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user["username"],
        "message": "Login successful",
    }


# ===========================================================================
#  PROTECTED ENDPOINTS  (require login)
# ===========================================================================

@app.get("/api/me", response_model=UserResponse, tags=["User"])
def get_profile(current_user: dict = Depends(get_current_user)):
    """Get the currently logged-in user's profile."""
    return current_user


@app.get("/api/dashboard", tags=["User"])
def dashboard(current_user: dict = Depends(get_current_user)):
    """
    Protected dashboard data — only accessible after login.
    This is what the frontend will call after authentication.
    """
    return {
        "message": f"Welcome back, {current_user['full_name'] or current_user['username']}!",
        "user": {
            "id": current_user["id"],
            "username": current_user["username"],
            "email": current_user["email"],
            "full_name": current_user["full_name"],
        },
        "dashboard_data": {
            "total_projects": 3,
            "recent_activity": "Deployed v1.0.0 to production",
            "server_status": "All systems operational",
        },
    }
