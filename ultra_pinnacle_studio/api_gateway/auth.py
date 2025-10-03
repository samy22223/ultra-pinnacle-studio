import warnings
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel
import json
from .logging_config import logger
from .database import User, Role, UserRole, AccountLockout, get_db
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .config import config
from .database import RefreshToken, UserSession, get_db
from sqlalchemy.orm import Session
import secrets
import hashlib
# Import moved to avoid circular imports
from passlib.context import CryptContext

SECRET_KEY = config["security"]["secret_key"]
ALGORITHM = config["security"]["algorithm"]
ACCESS_TOKEN_EXPIRE_MINUTES = config["security"]["access_token_expire_minutes"]
REFRESH_TOKEN_EXPIRE_DAYS = config["security"].get("refresh_token_expire_days", 30)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

class AuthUser(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None

# UserInDB removed - using database User model directly

# Mock user database - in production, use real database
fake_users_db = {
    "demo": {
        "username": "demo",
        "full_name": "Demo User",
        "email": "demo@example.com",
        "hashed_password": pwd_context.hash("demo123"),
        "disabled": False,
    }
}


def validate_password(password: str) -> bool:
    """Validate password against policy"""
    import re
    policy = config["security"]["password_policy"]

    if len(password) < policy["min_length"]:
        return False

    if policy["require_uppercase"] and not re.search(r'[A-Z]', password):
        return False

    if policy["require_lowercase"] and not re.search(r'[a-z]', password):
        return False

    if policy["require_digits"] and not re.search(r'\d', password):
        return False

    if policy["require_special_chars"] and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False

    return True

def check_password_history(db: Session, user_id: int, password: str) -> bool:
    """Check if password was used recently"""
    # This is a simplified implementation
    # In production, you'd store password hashes history
    return True

def get_user(db: Session, username: str):
    """Get user from database"""
    return db.query(User).filter(User.username == username).first()

def authenticate_user(db: Session, username: str, password: str):
    """Authenticate user against database"""
    user = get_user(db, username)
    if not user:
        return False

    # Check if account is locked
    if user.lockout_until and user.lockout_until > datetime.now(timezone.utc):
        logger.warning(f"Login attempt for locked account: {username}")
        return False

    # Check if account is active
    if not user.is_active:
        logger.warning(f"Login attempt for inactive account: {username}")
        return False

    if not verify_password(password, user.hashed_password):
        # Increment failed login attempts
        user.failed_login_attempts += 1
        user.last_failed_login = datetime.now(timezone.utc)

        # Check if account should be locked
        max_attempts = config["security"]["password_policy"]["max_failed_attempts"]
        if user.failed_login_attempts >= max_attempts:
            lockout_duration = config["security"]["password_policy"]["lockout_duration_minutes"]
            user.lockout_until = datetime.now(timezone.utc) + timedelta(minutes=lockout_duration)

            # Create lockout record
            lockout = AccountLockout(
                user_id=user.id,
                reason="failed_login_attempts",
                lockout_until=user.lockout_until,
                failed_attempts=user.failed_login_attempts
            )
            db.add(lockout)
            logger.warning(f"Account locked for user {username} due to failed login attempts")

        db.commit()
        return False

    # Successful login - reset failed attempts
    if user.failed_login_attempts > 0:
        user.failed_login_attempts = 0
        user.last_failed_login = None
        user.lockout_until = None
        db.commit()

    return user

def create_user(db: Session, username: str, email: str, password: str, full_name: str = None):
    """Create a new user"""
    try:
        # Validate password
        if not validate_password(password):
            logger.warning(f"Password validation failed for user {username}")
            return None

        hashed_password = get_password_hash(password)
        db_user = User(
            username=username,
            email=email,
            full_name=full_name,
            hashed_password=hashed_password,
            password_changed_at=datetime.now(timezone.utc)
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        # Assign default 'user' role
        user_role = db.query(Role).filter(Role.name == "user").first()
        if user_role:
            user_role_assignment = UserRole(user_id=db_user.id, role_id=user_role.id)
            db.add(user_role_assignment)
            db.commit()

        logger.info(f"User {username} created successfully")
        return db_user
    except IntegrityError:
        db.rollback()
        logger.warning(f"User {username} already exists")
        return None
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating user {username}: {e}")
        return None

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
        logger.debug(f"Using custom expires_delta: {expires_delta}")
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        logger.debug(f"Using configured token expiration: {ACCESS_TOKEN_EXPIRE_MINUTES} minutes")
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(db: Session, user_id: int, device_info: Optional[dict] = None) -> str:
    """Create a new refresh token"""
    token = secrets.token_urlsafe(64)
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    refresh_token = RefreshToken(
        id=secrets.token_urlsafe(32),
        user_id=user_id,
        token_hash=token_hash,
        device_info=device_info,
        expires_at=expires_at
    )

    db.add(refresh_token)
    db.commit()

    logger.info(f"Refresh token created for user {user_id}")
    return token

def verify_refresh_token(db: Session, token: str) -> Optional[RefreshToken]:
    """Verify and return refresh token if valid"""
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    refresh_token = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash,
        RefreshToken.is_active == True,
        RefreshToken.expires_at > datetime.now(timezone.utc)
    ).first()

    if refresh_token:
        # Update last used timestamp
        refresh_token.last_used_at = datetime.now(timezone.utc)
        db.commit()
        return refresh_token

    return None

def revoke_refresh_token(db: Session, token: str):
    """Revoke a refresh token"""
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    refresh_token = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash
    ).first()

    if refresh_token:
        refresh_token.is_active = False
        db.commit()
        logger.info(f"Refresh token revoked for user {refresh_token.user_id}")

def revoke_all_user_refresh_tokens(db: Session, user_id: int):
    """Revoke all refresh tokens for a user"""
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.is_active == True
    ).update({"is_active": False})
    db.commit()
    logger.info(f"All refresh tokens revoked for user {user_id}")

def refresh_access_token(db: Session, refresh_token_str: str) -> Optional[str]:
    """Create new access token using refresh token"""
    refresh_token = verify_refresh_token(db, refresh_token_str)
    if not refresh_token:
        return None

    # Create new access token
    access_token = create_access_token(data={"sub": refresh_token.user.username})
    return access_token

def create_user_session(db: Session, user_id: int, device_info: Optional[dict] = None,
                       ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> str:
    """Create a new user session"""
    session_id = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=config["security"]["session"]["session_timeout_hours"])

    session = UserSession(
        id=session_id,
        user_id=user_id,
        device_info=device_info,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=expires_at
    )

    db.add(session)
    db.commit()

    logger.info(f"User session created for user {user_id}")
    return session_id

def validate_user_session(db: Session, session_id: str) -> Optional[UserSession]:
    """Validate user session"""
    session = db.query(UserSession).filter(
        UserSession.id == session_id,
        UserSession.is_active == True,
        UserSession.expires_at > datetime.now(timezone.utc)
    ).first()

    if session:
        # Update last activity
        session.last_activity = datetime.now(timezone.utc)
        db.commit()
        return session

    return None

def invalidate_user_session(db: Session, session_id: str):
    """Invalidate a user session"""
    session = db.query(UserSession).filter(UserSession.id == session_id).first()
    if session:
        session.is_active = False
        db.commit()
        logger.info(f"User session invalidated for user {session.user_id}")

def invalidate_all_user_sessions(db: Session, user_id: int):
    """Invalidate all sessions for a user"""
    db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.is_active == True
    ).update({"is_active": False})
    db.commit()
    logger.info(f"All sessions invalidated for user {user_id}")

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security), db: Session = Depends(get_db)) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user(db, username=username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """Get current user and ensure they have admin role"""
    user_roles = [user_role.role.name for user_role in current_user.user_roles]
    if 'admin' not in user_roles and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

async def get_current_moderator_user(current_user: User = Depends(get_current_active_user)) -> User:
    """Get current user and ensure they have moderator role or higher"""
    user_roles = [user_role.role.name for user_role in current_user.user_roles]
    if not ('admin' in user_roles or 'moderator' in user_roles or current_user.is_superuser):
        raise HTTPException(status_code=403, detail="Moderator access required")
    return current_user

def has_permission(user: User, permission: str) -> bool:
    """Check if user has a specific permission"""
    if user.is_superuser:
        return True

    user_permissions = set()
    for user_role in user.user_roles:
        for role_permission in user_role.role.role_permissions:
            user_permissions.add(role_permission.permission.name)

    return permission in user_permissions

def has_role(user: User, role: str) -> bool:
    """Check if user has a specific role"""
    if user.is_superuser:
        return True

    user_roles = [user_role.role.name for user_role in user.user_roles]
    return role in user_roles

def get_password_hash(password: str) -> str:
    """Hash a password for storing"""
    try:
        return pwd_context.hash(password)
    except Exception as e:
        # Fallback to simple bcrypt if passlib fails
        import bcrypt
        import hashlib
        # Use a fixed salt for development - in production use proper salt generation
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

# These functions are already defined in the file but may be missing from imports
# Adding them here for clarity and to ensure they're available