"""
Role-Based Access Control (RBAC) middleware
"""
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional, Callable
from functools import wraps
from .auth import get_current_user
from .database import User, get_db
from sqlalchemy.orm import Session
from .logging_config import logger


class RBACMiddleware:
    """Role-Based Access Control middleware"""

    def __init__(self):
        self.security = HTTPBearer()

    async def __call__(
        self,
        request: Request,
        required_permissions: Optional[List[str]] = None,
        required_roles: Optional[List[str]] = None,
        allow_superuser: bool = True
    ):
        """Check if user has required permissions/roles"""
        # Get current user
        credentials = await self.security(request)
        if not credentials:
            raise HTTPException(status_code=401, detail="Not authenticated")

        # Get user from token
        user = await self._get_user_from_token(credentials.credentials, request)

        # Check superuser override
        if allow_superuser and user.is_superuser:
            return user

        # Check roles
        if required_roles:
            user_roles = [role.name for role in user.roles]
            if not any(role in user_roles for role in required_roles):
                logger.warning(f"Access denied for user {user.username}: missing required roles {required_roles}")
                raise HTTPException(status_code=403, detail="Insufficient permissions: missing required roles")

        # Check permissions
        if required_permissions:
            user_permissions = set()
            for role in user.roles:
                for permission in role.permissions:
                    user_permissions.add(permission.name)

            missing_permissions = [perm for perm in required_permissions if perm not in user_permissions]
            if missing_permissions:
                logger.warning(f"Access denied for user {user.username}: missing permissions {missing_permissions}")
                raise HTTPException(status_code=403, detail="Insufficient permissions: missing required permissions")

        return user

    async def _get_user_from_token(self, token: str, request: Request) -> User:
        """Get user from JWT token"""
        from .auth import get_current_user
        from .database import get_db
        from sqlalchemy.orm import Session

        # This is a simplified version - in production you'd validate the token properly
        try:
            from jose import JWTError, jwt
            from .config import config

            SECRET_KEY = config["security"]["secret_key"]
            ALGORITHM = config["security"]["algorithm"]

            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise HTTPException(status_code=401, detail="Invalid token")

            # Get database session
            db_generator = get_db()
            db = next(db_generator)

            try:
                from .auth import get_user
                user = get_user(db, username)
                if user is None:
                    raise HTTPException(status_code=401, detail="User not found")

                # Check if user is active
                if not user.is_active:
                    raise HTTPException(status_code=401, detail="User is inactive")

                return user
            finally:
                try:
                    db_generator.close()
                except:
                    pass

        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")


def require_permissions(permissions: List[str]):
    """Decorator to require specific permissions"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                for key, value in kwargs.items():
                    if isinstance(value, Request):
                        request = value
                        break

            if not request:
                raise HTTPException(status_code=500, detail="Request object not found")

            rbac = RBACMiddleware()
            user = await rbac(request, required_permissions=permissions)
            kwargs['current_user'] = user
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_roles(roles: List[str]):
    """Decorator to require specific roles"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                for key, value in kwargs.items():
                    if isinstance(value, Request):
                        request = value
                        break

            if not request:
                raise HTTPException(status_code=500, detail="Request object not found")

            rbac = RBACMiddleware()
            user = await rbac(request, required_roles=roles)
            kwargs['current_user'] = user
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_admin(func: Callable):
    """Decorator to require admin role"""
    return require_roles(['admin'])(func)


def require_moderator(func: Callable):
    """Decorator to require moderator role or higher"""
    return require_roles(['admin', 'moderator'])(func)


# Dependency functions for FastAPI
async def get_current_user_with_permissions(
    required_permissions: Optional[List[str]] = None,
    required_roles: Optional[List[str]] = None
) -> User:
    """FastAPI dependency for RBAC checks"""
    from fastapi import Request
    import inspect

    # Get the request object from the current frame
    frame = inspect.currentframe()
    while frame:
        if 'request' in frame.f_locals:
            request = frame.f_locals['request']
            break
        frame = frame.f_back

    if not request:
        raise HTTPException(status_code=500, detail="Request object not found")

    rbac = RBACMiddleware()
    return await rbac(request, required_permissions=required_permissions, required_roles=required_roles)


# Permission constants
PERMISSIONS = {
    # User management
    'CREATE_USER': 'create_user',
    'READ_USER': 'read_user',
    'UPDATE_USER': 'update_user',
    'DELETE_USER': 'delete_user',
    'MANAGE_USER_ROLES': 'manage_user_roles',

    # Content management
    'CREATE_CONTENT': 'create_content',
    'READ_CONTENT': 'read_content',
    'UPDATE_CONTENT': 'update_content',
    'DELETE_CONTENT': 'delete_content',
    'MODERATE_CONTENT': 'moderate_content',

    # System management
    'MANAGE_SYSTEM': 'manage_system',
    'VIEW_ANALYTICS': 'view_analytics',
    'MANAGE_SECURITY': 'manage_security',
}

ROLES = {
    'ADMIN': 'admin',
    'MODERATOR': 'moderator',
    'PREMIUM': 'premium',
    'USER': 'user',
}