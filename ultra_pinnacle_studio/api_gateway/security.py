"""
Security enhancements for Ultra Pinnacle AI Studio
Includes rate limiting, CORS, security headers, and input validation
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import re
import bleach
from typing import Dict, List, Optional
import json
import logging

logger = logging.getLogger(__name__)

class SecurityManager:
    """Manages security configurations and validations"""

    def __init__(self, config: Dict):
        self.config = config
        self.security_config = config.get('security', {})

        # Rate limiting settings
        self.rate_limit_requests = self.security_config.get('rate_limit_requests', 100)
        self.rate_limit_window = self.security_config.get('rate_limit_window', 60)

        # CORS settings
        self.cors_origins = config.get('app', {}).get('cors_origins', ["*"])
        self.cors_enabled = self.security_config.get('cors_enabled', True)

        # Security headers
        self.security_headers_enabled = self.security_config.get('security_headers', True)

        # Input validation patterns
        self.input_patterns = {
            'username': re.compile(r'^[a-zA-Z0-9_-]{3,30}$'),
            'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
            'filename': re.compile(r'^[a-zA-Z0-9._\-\s]{1,255}$'),
            'task_type': re.compile(r'^(analyze|generate|refactor|debug)$'),
            'model_name': re.compile(r'^[a-zA-Z0-9_-]{1,50}$')
        }

        # File upload restrictions
        self.allowed_extensions = {
            'images': ['.jpg', '.jpeg', '.png', '.gif', '.webp'],
            'documents': ['.txt', '.md', '.pdf', '.doc', '.docx'],
            'code': ['.py', '.js', '.java', '.cpp', '.c', '.h', '.html', '.css'],
            'data': ['.json', '.csv', '.xml', '.yaml', '.yml']
        }
        self.max_file_size = 10 * 1024 * 1024  # 10MB

    def get_cors_middleware(self):
        """Get CORS middleware configuration"""
        if not self.cors_enabled:
            return None

        return CORSMiddleware(
            allow_origins=self.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
            max_age=86400  # 24 hours
        )

    def get_rate_limiter(self):
        """Get rate limiter configuration"""
        limiter = Limiter(
            key_func=get_remote_address,
            default_limits=[f"{self.rate_limit_requests} per {self.rate_limit_window} seconds"]
        )
        return limiter

    def get_security_headers_middleware(self):
        """Get security headers middleware"""
        if not self.security_headers_enabled:
            return None

        async def add_security_headers(request: Request, call_next):
            response = await call_next(request)

            # Security headers
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'

            # Custom headers
            response.headers['X-API-Version'] = self.config.get('app', {}).get('version', '1.0.0')
            response.headers['X-Powered-By'] = 'Ultra Pinnacle AI Studio'

            return response

        return add_security_headers

    def validate_input(self, field: str, value: str) -> bool:
        """Validate input against security patterns"""
        if field not in self.input_patterns:
            return True  # No validation rule for this field

        pattern = self.input_patterns[field]
        return bool(pattern.match(str(value)))

    def sanitize_html(self, content: str) -> str:
        """Sanitize HTML content to prevent XSS"""
        allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
        allowed_attributes = {}

        return bleach.clean(content, tags=allowed_tags, attributes=allowed_attributes, strip=True)

    def validate_file_upload(self, filename: str, file_size: int, content_type: str) -> bool:
        """Validate file upload parameters"""
        # Check filename
        if not self.validate_input('filename', filename):
            logger.warning(f"Invalid filename: {filename}")
            return False

        # Check file size
        if file_size > self.max_file_size:
            logger.warning(f"File too large: {file_size} bytes")
            return False

        # Check file extension
        file_ext = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
        allowed_exts = []
        for category in self.allowed_extensions.values():
            allowed_exts.extend(category)

        if file_ext not in allowed_exts:
            logger.warning(f"Disallowed file extension: {file_ext}")
            return False

        # Check content type (basic validation)
        dangerous_types = ['application/x-executable', 'application/x-msdownload']
        if content_type.lower() in dangerous_types:
            logger.warning(f"Dangerous content type: {content_type}")
            return False

        return True

    def log_security_event(self, event_type: str, details: Dict, request: Optional[Request] = None):
        """Log security-related events"""
        log_data = {
            'event_type': event_type,
            'timestamp': json.dumps(details, default=str),
            'ip_address': request.client.host if request and request.client else 'unknown',
            'user_agent': request.headers.get('user-agent', 'unknown') if request else 'unknown'
        }

        logger.warning(f"SECURITY EVENT: {event_type} - {log_data}")

    def create_error_response(self, message: str, status_code: int = 400) -> JSONResponse:
        """Create standardized error response"""
        return JSONResponse(
            status_code=status_code,
            content={
                'error': {
                    'message': message,
                    'type': 'security_error',
                    'timestamp': json.dumps({'timestamp': str(datetime.now())})
                }
            }
        )

# Rate limiting error handler
def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded errors"""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            'error': {
                'message': 'Rate limit exceeded. Please try again later.',
                'type': 'rate_limit_error',
                'retry_after': exc.retry_after
            }
        },
        headers={'Retry-After': str(exc.retry_after)}
    )

# Input validation decorators
def validate_username(func):
    """Decorator to validate username parameter"""
    async def wrapper(*args, **kwargs):
        if 'username' in kwargs:
            username = kwargs['username']
            security_manager = kwargs.get('security_manager')
            if security_manager and not security_manager.validate_input('username', username):
                raise HTTPException(status_code=400, detail="Invalid username format")
        return await func(*args, **kwargs)
    return wrapper

def validate_email(func):
    """Decorator to validate email parameter"""
    async def wrapper(*args, **kwargs):
        if 'email' in kwargs:
            email = kwargs['email']
            security_manager = kwargs.get('security_manager')
            if security_manager and not security_manager.validate_input('email', email):
                raise HTTPException(status_code=400, detail="Invalid email format")
        return await func(*args, **kwargs)
    return wrapper

def sanitize_input(func):
    """Decorator to sanitize HTML input"""
    async def wrapper(*args, **kwargs):
        security_manager = kwargs.get('security_manager')
        if security_manager:
            # Sanitize text inputs that might contain HTML
            text_fields = ['prompt', 'message', 'code', 'content']
            for field in text_fields:
                if field in kwargs and isinstance(kwargs[field], str):
                    kwargs[field] = security_manager.sanitize_html(kwargs[field])
        return await func(*args, **kwargs)
    return wrapper

# Security monitoring middleware
async def security_monitoring_middleware(request: Request, call_next):
    """Monitor requests for security threats"""
    # Log suspicious patterns
    suspicious_patterns = [
        ('sql_injection', ['union', 'select', 'drop', 'delete', 'update', 'insert']),
        ('xss_attempt', ['<script', 'javascript:', 'onload=', 'onerror=']),
        ('path_traversal', ['../', '..\\', '/etc/', 'c:\\']),
    ]

    request_body = await request.body()
    request_text = request_body.decode('utf-8', errors='ignore').lower()

    for threat_type, patterns in suspicious_patterns:
        for pattern in patterns:
            if pattern in request_text:
                logger.warning(f"Potential {threat_type} detected in request from {request.client.host}")
                break

    response = await call_next(request)
    return response

def setup_security(app, config: Dict):
    """Setup all security middleware and configurations"""
    security_manager = SecurityManager(config)

    # Add CORS middleware
    cors_middleware = security_manager.get_cors_middleware()
    if cors_middleware:
        app.add_middleware(type(cors_middleware))

    # Add rate limiting
    limiter = security_manager.get_rate_limiter()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # Add security headers
    security_headers = security_manager.get_security_headers_middleware()
    if security_headers:
        app.middleware('http')(security_headers)

    # Add security monitoring
    app.middleware('http')(security_monitoring_middleware)

    # Add trusted host middleware (for production)
    if config.get('app', {}).get('environment') == 'production':
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=config.get('app', {}).get('allowed_hosts', ['*'])
        )

    return security_manager