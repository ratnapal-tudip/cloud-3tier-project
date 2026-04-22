"""
auth_app/views.py

Django REST Framework views that mirror every FastAPI endpoint in main.py:

  GET  /                      → root
  GET  /health                → health_check
  GET  /health/ready          → readiness_check
  GET  /health/live           → liveness_check
  POST /api/auth/signup       → signup
  POST /api/auth/login        → login  (OAuth2 form-compatible: username + password)
  GET  /api/me                → get_profile   [JWT required]
  GET  /api/dashboard         → dashboard     [JWT required]

Raw MySQL queries via mysql.connector — no Django ORM for user data.
"""

import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
import mysql.connector
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

# ---------------------------------------------------------------------------
# MySQL connection helper  (no pool — simple per-request connect/close)
# ---------------------------------------------------------------------------

def _get_conn():
    """Return a new MySQL connection using env-var creds from settings."""
    return mysql.connector.connect(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        database=settings.MYSQL_DATABASE,
    )


# ---------------------------------------------------------------------------
# Password hashing & JWT helpers  (identical logic to FastAPI version)
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode['exp'] = expire
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _decode_token(token: str) -> dict | None:
    """Return payload dict or None if token is invalid/expired."""
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


# ---------------------------------------------------------------------------
# Auth dependency helper — extract current user from Bearer token
# ---------------------------------------------------------------------------

def _get_current_user(request):
    """
    Reads 'Authorization: Bearer <token>' header.
    Returns (user_dict, None) on success or (None, Response) on failure.
    """
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        err = Response(
            {'detail': 'Invalid or expired token'},
            status=status.HTTP_401_UNAUTHORIZED,
            headers={'WWW-Authenticate': 'Bearer'},
        )
        return None, err

    token = auth_header.split(' ', 1)[1]
    payload = _decode_token(token)
    if not payload:
        err = Response(
            {'detail': 'Invalid or expired token'},
            status=status.HTTP_401_UNAUTHORIZED,
            headers={'WWW-Authenticate': 'Bearer'},
        )
        return None, err

    username = payload.get('sub')
    if not username:
        err = Response(
            {'detail': 'Invalid or expired token'},
            status=status.HTTP_401_UNAUTHORIZED,
            headers={'WWW-Authenticate': 'Bearer'},
        )
        return None, err

    conn = _get_conn()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user:
        err = Response(
            {'detail': 'Invalid or expired token'},
            status=status.HTTP_401_UNAUTHORIZED,
            headers={'WWW-Authenticate': 'Bearer'},
        )
        return None, err

    return user, None


# ===========================================================================
#  HEALTH CHECK ENDPOINTS  (GET /, /health, /health/ready, /health/live)
# ===========================================================================

@api_view(['GET'])
def root(request):
    """Root endpoint — confirms the API is reachable."""
    return Response({'message': 'Cloud 3-Tier API is running'})


@api_view(['GET'])
def health_check(request):
    """
    Basic health check.
    Used by load balancers (ALB/NLB) and Jenkins pipeline to verify the service is up.
    Returns 200 if service is healthy.
    """
    return Response({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'version': '1.0.0',
        'service': 'python-django',
    })


@api_view(['GET'])
def readiness_check(request):
    """
    Readiness probe — checks that the app AND database are ready.
    Used by Kubernetes / cloud load balancers.
    """
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception:
        return Response({'detail': 'Database not ready'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'version': '1.0.0',
        'service': 'python-django',
    })


@api_view(['GET'])
def liveness_check(request):
    """
    Liveness probe — lightweight check that the process is alive.
    Used by Kubernetes liveness probes.
    """
    return Response({'message': 'alive'})


# ===========================================================================
#  AUTH ENDPOINTS  (POST /api/auth/signup, POST /api/auth/login)
# ===========================================================================

@api_view(['POST'])
def signup(request):
    """
    Register a new user.
    Expects JSON body: { username, email, password, full_name }
    """
    data = request.data
    username  = data.get('username', '').strip()
    email     = data.get('email', '').strip()
    password  = data.get('password', '')
    full_name = data.get('full_name', '').strip()

    # Basic validation
    if not username or not email or not password:
        return Response(
            {'detail': 'username, email, and password are required'},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    conn = _get_conn()
    cursor = conn.cursor(dictionary=True)

    # Check duplicate username
    cursor.execute('SELECT id FROM users WHERE username = %s', (username,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return Response({'detail': 'Username already taken'}, status=status.HTTP_400_BAD_REQUEST)

    # Check duplicate email
    cursor.execute('SELECT id FROM users WHERE email = %s', (email,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return Response({'detail': 'Email already registered'}, status=status.HTTP_400_BAD_REQUEST)

    # Insert new user
    cursor.execute(
        'INSERT INTO users (username, email, hashed_password, full_name) VALUES (%s, %s, %s, %s)',
        (username, email, hash_password(password), full_name),
    )
    conn.commit()
    new_id = cursor.lastrowid

    # Fetch and return the created user
    cursor.execute('SELECT * FROM users WHERE id = %s', (new_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    # Serialize datetime fields
    user['created_at'] = user['created_at'].isoformat() if user.get('created_at') else None
    user.pop('hashed_password', None)
    user.pop('updated_at', None)

    return Response(user, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def login(request):
    """
    Login with username & password.
    Accepts both:
      - JSON body:            { "username": "...", "password": "..." }
      - Form-encoded body:    username=...&password=...  (OAuth2-compatible)
    Returns a JWT access token.
    """
    # Support both JSON and form-encoded (same as FastAPI OAuth2PasswordRequestForm)
    content_type = request.content_type or ''
    if 'application/json' in content_type:
        username = request.data.get('username', '')
        password = request.data.get('password', '')
    else:
        username = request.data.get('username', '')
        password = request.data.get('password', '')

    if not username or not password:
        return Response(
            {'detail': 'username and password are required'},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    conn = _get_conn()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user or not verify_password(password, user['hashed_password']):
        return Response(
            {'detail': 'Incorrect username or password'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    token = create_access_token(data={'sub': user['username']})
    return Response({
        'access_token': token,
        'token_type': 'bearer',
        'username': user['username'],
        'message': 'Login successful',
    })


# ===========================================================================
#  PROTECTED ENDPOINTS  (require JWT Bearer token)
# ===========================================================================

@api_view(['GET'])
def get_profile(request):
    """Get the currently logged-in user's profile."""
    user, err = _get_current_user(request)
    if err:
        return err

    return Response({
        'id': user['id'],
        'username': user['username'],
        'email': user['email'],
        'full_name': user['full_name'],
        'created_at': user['created_at'].isoformat() if user.get('created_at') else None,
    })


@api_view(['GET'])
def dashboard(request):
    """
    Protected dashboard data — only accessible after login.
    This is what the frontend will call after authentication.
    """
    user, err = _get_current_user(request)
    if err:
        return err

    return Response({
        'message': f"Welcome back, {user['full_name'] or user['username']}!",
        'user': {
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'full_name': user['full_name'],
        },
        'dashboard_data': {
            'total_projects': 3,
            'recent_activity': 'Deployed v1.0.0 to production',
            'server_status': 'All systems operational',
        },
    })
