"""
Authentication utilities - separated to avoid circular imports
"""
import warnings
from passlib.context import CryptContext

# Suppress bcrypt version warnings and errors
warnings.filterwarnings("ignore", message=".*bcrypt.*", category=UserWarning)
try:
    import bcrypt
except ImportError:
    pass

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)