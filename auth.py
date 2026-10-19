# auth.py
from datetime import datetime, timedelta
from typing import Optional, Dict
import jwt
from jwt import PyJWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import logging

from database import get_db
from models import User
from config import config

logger = logging.getLogger(__name__)

# Password hashing - use simple bcrypt without version issues
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

# Security
SECRET_KEY = config.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification failed: {e}")
        return False

def get_password_hash(password: str) -> str:
    """Hash a password"""
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Password hashing failed: {e}")
        # Fallback to a simple hash for POC
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    
    # CRITICAL: Ensure 'sub' is a string (JWT spec requirement)
    if 'sub' in to_encode:
        to_encode['sub'] = str(to_encode['sub'])
    else:
        raise ValueError("Missing 'sub' field in token data")
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    try:
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    except Exception as e:
        logger.error(f"JWT creation failed: {e}")
        raise

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate a user by email and password"""
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            logger.warning(f"User not found: {email}")
            return None
        
        # Try bcrypt verification
        if not verify_password(password, user.hashed_password):
            # If bcrypt fails, try simple hash (for POC)
            import hashlib
            simple_hash = hashlib.sha256(password.encode()).hexdigest()
            if user.hashed_password != simple_hash:
                logger.warning(f"Invalid password for user: {email}")
                return None
        
        logger.info(f"User authenticated: {email}")
        return user
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return None

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Dict:
    """Get the current authenticated user"""
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        
        if user_id is None:
            logger.error("No 'sub' field in token")
            raise credentials_exception
        
        # Convert to int for database query
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid user_id format: {user_id}")
            raise credentials_exception
        
    except PyJWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        logger.error(f"User not found: {user_id}")
        raise credentials_exception
    
    return {"id": user.id, "email": user.email, "full_name": user.full_name}
