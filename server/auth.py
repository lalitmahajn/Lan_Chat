"""Authentication — JWT, password hashing, FastAPI dependencies."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status, WebSocket
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.constants import AccountStatus, Defaults, Role
from server.config import server_config
from server.database import get_db
from server.models import RefreshToken, User


# ─── Password Hashing ────────────────────────────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ─── JWT ──────────────────────────────────────────────────────────────────────

ALGORITHM = "HS256"


def _get_secret() -> str:
    """Get JWT secret. Generate if not set."""
    if not server_config.jwt_secret:
        server_config.jwt_secret = secrets.token_hex(32)
    return server_config.jwt_secret


def create_access_token(user_id: int, username: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=Defaults.JWT_ACCESS_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, _get_secret(), algorithm=ALGORITHM)


def create_refresh_token_value() -> str:
    """Generate opaque refresh token string."""
    return secrets.token_urlsafe(64)


def decode_access_token(token: str) -> Optional[dict]:
    """Decode + validate access token. Returns payload or None."""
    try:
        payload = jwt.decode(token, _get_secret(), algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


# ─── Token Extraction ────────────────────────────────────────────────────────

_bearer_scheme = HTTPBearer(auto_error=False)


async def _extract_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    return credentials.credentials


# ─── FastAPI Dependencies ─────────────────────────────────────────────────────

async def get_current_user(
    token: str = Depends(_extract_token),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate current user from JWT Bearer token."""
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if user.status != AccountStatus.APPROVED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account not approved")

    return user


async def require_super_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require super_admin role."""
    if not current_user.is_super_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super admin required")
    return current_user


# ─── WebSocket Auth ───────────────────────────────────────────────────────────

async def authenticate_websocket(websocket: WebSocket, db: AsyncSession) -> Optional[User]:
    """Authenticate WS connection from token query param."""
    token = websocket.query_params.get("token")
    if not token:
        return None

    payload = decode_access_token(token)
    if payload is None:
        return None

    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or user.status != AccountStatus.APPROVED:
        return None

    return user
