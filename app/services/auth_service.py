"""
Auth service - JWT-based (works with zero external setup).
"""
import os
import warnings
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

_DEFAULT_DEV_SECRET = "dev-secret-key-change-this-before-deploying"
SECRET_KEY = os.getenv("JWT_SECRET_KEY", _DEFAULT_DEV_SECRET)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

if SECRET_KEY == _DEFAULT_DEV_SECRET:
    warnings.warn(
        "Using the default dev JWT secret. Set JWT_SECRET_KEY in your environment "
        "before deploying anywhere public.",
        stacklevel=2,
    )

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def get_current_user_id(token: str = Depends(oauth2_scheme)) -> int:
    """FastAPI dependency — extracts user_id from the Bearer token."""
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return int(payload["sub"])


def require_roles(*roles: str):
    """FastAPI dependency factory — raises 403 if user's role isn't in the allowed set."""
    def _check(token: str = Depends(oauth2_scheme)) -> dict:
        payload = decode_access_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired token.")
        if payload.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions.")
        return payload
    return _check
