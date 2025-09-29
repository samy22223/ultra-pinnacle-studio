"""
Security module for Ultra Pinnacle AI Studio
Implements rate limiting, CORS, security headers, and input validation
"""
import time
import hashlib
import hmac
from typing import Dict, List, Optional, Tuple
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import re
import logging

logger = logging.getLogger("ultra_pinnacle")

class RateLimiter:
    """Simple in-memory rate limiter"""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, List[float]] = {}

    def is_allowed(self, client_ip: str) -> bool:
        """Check if request is allowed under rate limit"""
        current_time = time.time()
        window_start = current_time - 60  # 1 minute window

        # Clean old requests
        if client_ip in self.requests:
            self.requests[client_ip] = [t for t in self.requests[client_ip] if t > window_start]

        # Check rate limit
        if client_ip in self.requests and len(self.requests[client_ip]) >= self.requests_per_minute:
            return False

        # Record request
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        self.requests[client_ip].append(current_time)

        return True

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # Remove server header for security
        if "server" in response.headers:
            del response.headers["server"]

        return response

class CORSMiddleware(BaseHTTPMiddleware):
    """CORS middleware with configurable origins"""

    def __init__(self, app, allow_origins: List[str] = None, allow_credentials: bool = True,
                 allow_methods: List[str] = None, allow_headers: List[str] = None):
        super().__init__(app)
        self.allow_origins = allow_origins or ["*"]
        self.allow_credentials = allow_credentials
        self.allow_methods = allow_methods or ["*"]
        self.allow_headers = allow_headers or ["*"]

    async def dispatch(self, request: Request, call_next):
        # Handle preflight requests
        if request.method == "OPTIONS":
            response = JSONResponse(content={}, status_code=200)
        else:
            response = await call_next(request)

        # Set CORS headers
        if "*" in self.allow_origins:
            response.headers["Access-Control-Allow-Origin"] = "*"
        elif request.headers.get("origin") in self.allow_origins:
            response.headers["Access-Control-Allow-Origin"] = request.headers.get("origin")

        if self.allow_credentials:
            response.headers["Access-Control-Allow-Credentials"] = "true"

        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)

        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""

    def __init__(self, app, rate_limiter: RateLimiter = None):
        super().__init__(app)
        self.rate_limiter = rate_limiter or RateLimiter()

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"

        if not self.rate_limiter.is_allowed(client_ip):
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."}
            )

        response = await call_next(request)
        return response

def validate_input_safety(text: str) -> bool:
    """Validate input for common security issues"""
    if not text:
        return True

    # Check for SQL injection patterns
    sql_patterns = [
        r';\s*(select|insert|update|delete|drop|create|alter)',
        r'union\s+select',
        r'--\s*$',
        r'/\*.*\*/'
    ]

    for pattern in sql_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            logger.warning("Potential SQL injection detected")
            return False

    # Check for XSS patterns
    xss_patterns = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe[^>]*>.*?</iframe>'
    ]

    for pattern in xss_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            logger.warning("Potential XSS attack detected")
            return False

    # Check for path traversal
    if '..' in text or '../' in text or '..\\' in text:
        logger.warning("Potential path traversal detected")
        return False

    return True

def sanitize_input(text: str) -> str:
    """Sanitize user input"""
    if not text:
        return text

    # Remove potentially dangerous characters
    text = re.sub(r'[<>"\'`]', '', text)

    # Normalize whitespace
    text = ' '.join(text.split())

    return text.strip()

def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """Hash password with salt"""
    if salt is None:
        salt = hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]

    # Use PBKDF2 for password hashing
    hash_obj = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode(),
        salt.encode(),
        100000  # Number of iterations
    )

    return hash_obj.hex(), salt

def verify_password(password: str, hashed: str, salt: str) -> bool:
    """Verify password against hash"""
    hash_obj = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode(),
        salt.encode(),
        100000
    )

    return hmac.compare_digest(hash_obj.hex(), hashed)

def generate_secure_token(length: int = 32) -> str:
    """Generate a secure random token"""
    return hashlib.sha256(str(time.time()).encode() + str(id(length)).encode()).hexdigest()[:length]

# Global instances
rate_limiter = RateLimiter()
security_headers = SecurityHeadersMiddleware
cors_middleware = CORSMiddleware
rate_limit_middleware = RateLimitMiddleware

logger.info("Security module initialized")