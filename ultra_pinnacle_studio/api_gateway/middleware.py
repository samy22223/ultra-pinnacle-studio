"""
Middleware components for Ultra Pinnacle AI Studio
"""
import time
import logging
from typing import Callable
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
import json
import os

logger = logging.getLogger("ultra_pinnacle")

# Import metrics recording function (will be available after metrics module is loaded)
try:
    from .metrics import record_request
except ImportError:
    # Fallback if metrics module not available
    def record_request(duration: float, status_code: int):
        pass

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"

        # Remove server header for security
        if "server" in response.headers:
            del response.headers["server"]

        return response

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Enhanced request logging with performance monitoring and audit logging"""

    def __init__(self, app):
        super().__init__(app)
        self.enhanced_logger = None
        self.audit_logger = None

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # Get enhanced logger if available
        if self.enhanced_logger is None:
            try:
                from .logging_config import enhanced_logger
                self.enhanced_logger = enhanced_logger
            except ImportError:
                self.enhanced_logger = None

        # Get audit logger if available
        if self.audit_logger is None:
            try:
                from .security_enhanced import audit_logger
                self.audit_logger = audit_logger
            except ImportError:
                self.audit_logger = None

        # Log request with enhanced details
        client_ip = request.client.host if request.client else 'unknown'
        user_agent = request.headers.get('user-agent', 'unknown')
        content_length = request.headers.get('content-length', '0')

        logger.info(f"Request: {request.method} {request.url.path} from {client_ip}",
                   extra={
                       "method": request.method,
                       "path": request.url.path,
                       "client_ip": client_ip,
                       "user_agent": user_agent,
                       "content_length": content_length,
                       "query_params": dict(request.query_params)
                   })

        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            # Log response with performance data
            logger.info(f"Response: {response.status_code} in {process_time:.3f}s",
                        extra={
                            "status_code": response.status_code,
                            "duration": process_time,
                            "response_size": response.headers.get('content-length', '0')
                        })

            # Record metrics
            record_request(process_time, response.status_code)

            # Log to enhanced logger if available
            if self.enhanced_logger:
                self.enhanced_logger.log_request(
                    request.url.path, request.method,
                    response.status_code, process_time
                )
                self.enhanced_logger.log_performance(
                    f"api_{request.method.lower()}_{request.url.path.replace('/', '_')}",
                    process_time,
                    status_code=response.status_code,
                    client_ip=client_ip
                )

            # Audit log successful API access
            if self.audit_logger and request.url.path.startswith('/api/'):
                self.audit_logger.log_event(
                    "api_access",
                    resource=request.url.path,
                    action=request.method,
                    details={
                        "status_code": response.status_code,
                        "duration": process_time,
                        "user_agent": user_agent
                    },
                    ip=client_ip,
                    user_agent=user_agent
                )

            return response

        except Exception as e:
            process_time = time.time() - start_time

            # Enhanced error logging
            logger.error(f"Request failed: {e} in {process_time:.3f}s",
                         extra={
                             "error": str(e),
                             "error_type": type(e).__name__,
                             "duration": process_time,
                             "method": request.method,
                             "path": request.url.path,
                             "client_ip": client_ip
                         }, exc_info=True)

            # Record error metrics
            record_request(process_time, 500)

            # Log to enhanced logger if available
            if self.enhanced_logger:
                self.enhanced_logger.log_error(
                    "api_request_failed",
                    f"{request.method} {request.url.path}: {str(e)}",
                    method=request.method,
                    path=request.url.path,
                    client_ip=client_ip,
                    duration=process_time
                )

            # Audit log failed requests
            if self.audit_logger:
                self.audit_logger.log_event(
                    "request_failed",
                    resource=request.url.path,
                    action=request.method,
                    details={
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "duration": process_time,
                        "user_agent": user_agent
                    },
                    ip=client_ip,
                    user_agent=user_agent
                )

            raise

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Comprehensive rate limiting middleware with user-based and endpoint-specific limits"""

    def __init__(self, app):
        super().__init__(app)
        self.rate_limit_manager = None
        self.audit_logger = None

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Initialize components if not already done
        if self.rate_limit_manager is None:
            try:
                from .rate_limiter import get_rate_limit_manager
                from .security_enhanced import audit_logger
                self.rate_limit_manager = get_rate_limit_manager()
                self.audit_logger = audit_logger
            except ImportError as e:
                logger.warning(f"Rate limiting components not available: {e}")
                # Fallback - allow all requests
                response = await call_next(request)
                return response

        client_ip = request.client.host if request.client else "unknown"
        endpoint = request.url.path
        method = request.method
        user_agent = request.headers.get('user-agent', '')

        # Try to get user ID from JWT token without failing
        user_id = None
        try:
            from .auth import get_current_user
            from fastapi import Depends
            from .database import get_db
            # Try to authenticate user (this will fail silently if no token)
            user = await get_current_user(
                credentials=getattr(request, 'auth_credentials', None),
                db=next(get_db())
            )
            user_id = user.id if user else None
        except Exception:
            # Not authenticated, use None for user_id
            pass

        # Check rate limit
        try:
            result = self.rate_limit_manager.check_rate_limit(
                user_id=user_id,
                client_ip=client_ip,
                endpoint=endpoint,
                method=method
            )

            # Log rate limit check
            if self.audit_logger:
                if not result.allowed:
                    self.audit_logger.log_event(
                        "rate_limit_exceeded",
                        user=str(user_id) if user_id else "anonymous",
                        resource=endpoint,
                        action=method,
                        details={
                            "limit_type": result.limit_type,
                            "remaining_requests": result.remaining_requests,
                            "retry_after": result.retry_after,
                            "user_agent": user_agent
                        },
                        ip=client_ip,
                        user_agent=user_agent
                    )
                elif hash(f"{client_ip}{time.time()}") % 100 == 0:  # Sample 1% of allowed requests
                    self.audit_logger.log_event(
                        "rate_limit_check",
                        user=str(user_id) if user_id else "anonymous",
                        resource=endpoint,
                        action=method,
                        details={
                            "limit_type": result.limit_type,
                            "remaining_requests": result.remaining_requests,
                            "user_agent": user_agent
                        },
                        ip=client_ip,
                        user_agent=user_agent
                    )

            if not result.allowed:
                # Create informative error response
                error_response = {
                    "error": "rate_limit_exceeded",
                    "message": f"Rate limit exceeded for {result.limit_type} requests",
                    "limit_type": result.limit_type,
                    "retry_after": result.retry_after,
                    "reset_time": result.reset_time.isoformat(),
                    "remaining_requests": result.remaining_requests
                }

                response = JSONResponse(
                    status_code=429,
                    content=error_response,
                    headers={
                        "X-RateLimit-Remaining": str(result.remaining_requests),
                        "X-RateLimit-Reset": str(int(result.reset_time.timestamp())),
                        "X-RateLimit-Retry-After": str(result.retry_after or 60),
                        "Retry-After": str(result.retry_after or 60)
                    }
                )
                return response

            # Request is allowed, proceed
            response = await call_next(request)

            # Add rate limit headers to successful responses
            response.headers["X-RateLimit-Remaining"] = str(result.remaining_requests)
            response.headers["X-RateLimit-Reset"] = str(int(result.reset_time.timestamp()))
            response.headers["X-RateLimit-Limit"] = result.limit_type

            return response

        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # On error, allow the request to proceed
            response = await call_next(request)
            return response

class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Redirect HTTP requests to HTTPS in production"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if we should enforce HTTPS
        import os
        enforce_https = os.getenv('ENFORCE_HTTPS', 'false').lower() == 'true'

        if enforce_https and request.url.scheme == 'http':
            https_url = request.url.replace(scheme='https')
            return Response(
                status_code=301,
                headers={"Location": str(https_url)}
            )

        return await call_next(request)

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response

        except HTTPException:
            # Let FastAPI handle HTTP exceptions
            raise

        except Exception as e:
            logger.error(f"Unhandled error: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "request_id": getattr(request.state, 'request_id', 'unknown')
                }
            )

def setup_middleware(app, config):
    """Setup all middleware for the FastAPI app"""
    # Config is passed from main.py

    # HTTPS redirect (only in production)
    if config.get("app", {}).get("env", "development") == "production":
        app.add_middleware(HTTPSRedirectMiddleware)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.get("security", {}).get("cors_origins", ["*"]),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Trusted host middleware (only in production)
    if config.get("app", {}).get("env", "development") == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=config.get("security", {}).get("allowed_hosts", ["*"])
        )

    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)

    # Advanced rate limiting with threat detection
    app.add_middleware(RateLimitMiddleware)

    # CSRF protection (temporarily disabled due to async issues)
    # from .csrf_middleware import CSRFMiddleware
    # app.add_middleware(CSRFMiddleware)

    # Request logging
    app.add_middleware(RequestLoggingMiddleware)

    # Error handling (should be last)
    app.add_middleware(ErrorHandlingMiddleware)

    logger.info("Middleware setup completed")