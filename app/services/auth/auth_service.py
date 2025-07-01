from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.models.user import User
from app.db.session import get_db
from app.core.config import settings

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def authenticate_user(db: Session, email: str, password: str):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def edit_profile(db: Session, user_id: int, name: str, machine_name: str = None, contradiction_tolerance: float = None, belief_sensitivity: str = None):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    user.name = name
    if machine_name is not None:
        user.machine_name = machine_name
    if contradiction_tolerance is not None:
        user.contradiction_tolerance = contradiction_tolerance
    if belief_sensitivity is not None:
        user.belief_sensitivity = belief_sensitivity
    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user_id: int, current_password: str, new_password: str, confirm_password: str):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False, "User not found"
    if not verify_password(current_password, user.hashed_password):
        return False, "Current password is incorrect"
    if new_password != confirm_password:
        return False, "New passwords do not match"
    user.hashed_password = get_password_hash(new_password)
    db.commit()
    return True, "Password updated successfully"

def get_user_from_token(db: Session, token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            return None, "Invalid token"
    except JWTError:
        return None, "Invalid token"
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None, "User not found"
    return user, None


# FastAPI dependency for getting current user
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """FastAPI dependency to get current user from JWT token"""
    token = credentials.credentials
    user, error = get_user_from_token(db, token)
    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error,
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    """FastAPI dependency to get current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user