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

        # Remove server header for security
        if "server" in response.headers:
            del response.headers["server"]

        return response

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests with timing and details"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # Log request
        logger.info(f"Request: {request.method} {request.url.path} from {request.client.host if request.client else 'unknown'}")

        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            # Log response
            logger.info(f"Response: {response.status_code} in {process_time:.2f}s")

            # Record metrics
            record_request(process_time, response.status_code)

            return response

        except Exception as e:
            process_time = time.time() - start_time
            logger.error(f"Request failed: {e} in {process_time:.2f}s")

            # Record error metrics
            record_request(process_time, 500)

            raise

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting"""

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        window_start = current_time - 60  # 1 minute window

        # Clean old requests
        if client_ip in self.requests:
            self.requests[client_ip] = [t for t in self.requests[client_ip] if t > window_start]

        # Check rate limit
        if client_ip in self.requests and len(self.requests[client_ip]) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."}
            )

        # Record request
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        self.requests[client_ip].append(current_time)

        response = await call_next(request)
        return response

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

    # Rate limiting
    rate_limit = config.get("security", {}).get("rate_limit_per_minute", 60)
    app.add_middleware(RateLimitMiddleware, requests_per_minute=rate_limit)

    # Request logging
    app.add_middleware(RequestLoggingMiddleware)

    # Error handling (should be last)
    app.add_middleware(ErrorHandlingMiddleware)

    logger.info("Middleware setup completed")