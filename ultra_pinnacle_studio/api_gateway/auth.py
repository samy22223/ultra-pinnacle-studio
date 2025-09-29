import warnings
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import json
from .logging_config import logger
from .database import User, get_db
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

# Suppress bcrypt version warnings and errors
warnings.filterwarnings("ignore", message=".*bcrypt.*", category=UserWarning)
try:
    import bcrypt
except ImportError:
    pass

from .config import config

SECRET_KEY = config["security"]["secret_key"]
ALGORITHM = config["security"]["algorithm"]
ACCESS_TOKEN_EXPIRE_MINUTES = config["security"]["access_token_expire_minutes"]

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
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

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(db: Session, username: str):
    """Get user from database"""
    return db.query(User).filter(User.username == username).first()

def authenticate_user(db: Session, username: str, password: str):
    """Authenticate user against database"""
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_user(db: Session, username: str, email: str, password: str, full_name: str = None):
    """Create a new user"""
    try:
        hashed_password = get_password_hash(password)
        db_user = User(
            username=username,
            email=email,
            full_name=full_name,
            hashed_password=hashed_password
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
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