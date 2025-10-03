"""
CSRF Protection Middleware
"""
import secrets
from typing import Optional
from datetime import datetime, timezone
from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from .database import CSRFToken, get_db
from .auth import get_current_user
from sqlalchemy.orm import Session
from .logging_config import logger


class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF Protection Middleware"""

    def __init__(self, app, exempt_paths: Optional[list] = None):
        super().__init__(app)
        self.exempt_paths = exempt_paths or [
            "/auth/login",
            "/auth/register",
            "/auth/refresh",
            "/auth/forgot-password",
            "/auth/reset-password",
            "/auth/oauth",
            "/docs",
            "/redoc",
            "/openapi.json"
        ]

    async def dispatch(self, request: Request, call_next):
        # Skip CSRF check for safe methods
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return await call_next(request)

        # Skip CSRF check for exempt paths
        for path in self.exempt_paths:
            if request.url.path.startswith(path):
                return await call_next(request)

        # Check CSRF token
        csrf_token = await self._get_csrf_token(request)
        if not csrf_token:
            logger.warning(f"CSRF token missing for {request.method} {request.url.path}")
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token missing"}
            )

        # Validate CSRF token
        if not await self._validate_csrf_token(csrf_token, request):
            logger.warning(f"CSRF token invalid for {request.method} {request.url.path}")
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token invalid"}
            )

        response = await call_next(request)
        return response

    async def _get_csrf_token(self, request: Request) -> Optional[str]:
        """Extract CSRF token from request"""
        # Check header first
        token = request.headers.get("X-CSRF-Token")
        if token:
            return token

        # Check form data
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            try:
                form = await request.form()
                if form and "csrf_token" in form:
                    return form["csrf_token"]
            except:
                pass

        # Check JSON body
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            try:
                json_data = request.json()
                if json_data and "csrf_token" in json_data:
                    return json_data["csrf_token"]
            except:
                pass

        return None

    async def _validate_csrf_token(self, token: str, request: Request) -> bool:
        """Validate CSRF token"""
        import hashlib

        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # Get database session
        db_generator = get_db()
        db = next(db_generator)

        try:
            csrf_token = db.query(CSRFToken).filter(
                CSRFToken.token_hash == token_hash,
                CSRFToken.is_active == True,
                CSRFToken.expires_at > datetime.now(timezone.utc)
            ).first()

            if csrf_token:
                # Update last used timestamp
                csrf_token.last_used_at = datetime.now(timezone.utc)
                db.commit()
                return True

            return False
        finally:
            try:
                db_generator.close()
            except:
                pass


async def create_csrf_token(user_id: int, session_id: Optional[str] = None) -> str:
    """Create a new CSRF token for user"""
    import secrets
    import hashlib
    from datetime import datetime, timedelta, timezone

    token = secrets.token_urlsafe(64)
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)  # 24 hour expiry

    db_generator = get_db()
    db = next(db_generator)

    try:
        csrf_token = CSRFToken(
            id=secrets.token_urlsafe(16),
            user_id=user_id,
            session_id=session_id,
            token_hash=token_hash,
            expires_at=expires_at
        )

        db.add(csrf_token)
        db.commit()

        return token
    finally:
        try:
            db_generator.close()
        except:
            pass


async def get_csrf_token(request: Request) -> str:
    """Get or create CSRF token for current user"""
    try:
        user = await get_current_user(request)
        return await create_csrf_token(user.id)
    except:
        # For unauthenticated requests, return a temporary token
        return secrets.token_urlsafe(64)