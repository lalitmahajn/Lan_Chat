"""User service — registration, login, approval, queries."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from common.constants import AccountStatus, Defaults, Presence, Role
from common.utils import utc_now
from server.auth import (
    create_access_token,
    create_refresh_token_value,
    hash_password,
    verify_password,
)
from server.models import RefreshToken, User


async def register_user(
    db: AsyncSession, username: str, password: str, display_name: str
) -> User:
    """Register new user (status=pending)."""
    # Check dupe
    existing = await db.execute(select(User).where(User.username == username))
    if existing.scalar_one_or_none():
        raise ValueError("Username already taken")

    user = User(
        username=username,
        display_name=display_name,
        password_hash=hash_password(password),
        role=Role.MEMBER,
        status=AccountStatus.PENDING,
    )
    db.add(user)
    await db.flush()
    return user


async def login_user(
    db: AsyncSession, username: str, password: str
) -> tuple[User, str, str]:
    """Login -> (user, access_token, refresh_token_str). Raises on fail."""
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(password, user.password_hash):
        raise ValueError("Invalid username or password")

    if user.status == AccountStatus.PENDING:
        raise ValueError("Account pending approval")
    if user.status == AccountStatus.REJECTED:
        raise ValueError("Account has been rejected")

    # Create tokens
    access_token = create_access_token(user.id, user.username, user.role)
    refresh_value = create_refresh_token_value()

    # Store refresh token
    refresh = RefreshToken(
        user_id=user.id,
        token=refresh_value,
        expires_at=utc_now() + timedelta(days=Defaults.JWT_REFRESH_EXPIRE_DAYS),
    )
    db.add(refresh)

    # Update presence
    user.presence = Presence.ONLINE
    user.last_seen = utc_now()

    return user, access_token, refresh_value


async def refresh_access_token(
    db: AsyncSession, refresh_token_str: str
) -> tuple[str, str]:
    """Validate refresh token, return new (access_token, refresh_token)."""
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == refresh_token_str)
    )
    token_entry = result.scalar_one_or_none()

    if token_entry is None:
        raise ValueError("Invalid refresh token")
    if token_entry.expires_at < datetime.now(timezone.utc):
        await db.delete(token_entry)
        raise ValueError("Refresh token expired")

    # Load user
    result = await db.execute(select(User).where(User.id == token_entry.user_id))
    user = result.scalar_one_or_none()
    if user is None or user.status != AccountStatus.APPROVED:
        raise ValueError("User invalid")

    # Rotate: delete old, create new
    await db.delete(token_entry)

    new_access = create_access_token(user.id, user.username, user.role)
    new_refresh = create_refresh_token_value()
    db.add(RefreshToken(
        user_id=user.id,
        token=new_refresh,
        expires_at=utc_now() + timedelta(days=Defaults.JWT_REFRESH_EXPIRE_DAYS),
    ))

    return new_access, new_refresh


async def logout_user(db: AsyncSession, refresh_token_str: str) -> None:
    """Invalidate refresh token."""
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == refresh_token_str)
    )
    token_entry = result.scalar_one_or_none()
    if token_entry:
        await db.delete(token_entry)


async def approve_user(db: AsyncSession, user_id: int) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise ValueError("User not found")
    user.status = AccountStatus.APPROVED
    return user


async def reject_user(db: AsyncSession, user_id: int) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise ValueError("User not found")
    user.status = AccountStatus.REJECTED
    return user


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_pending_users(db: AsyncSession) -> list[User]:
    result = await db.execute(
        select(User).where(User.status == AccountStatus.PENDING).order_by(User.created_at)
    )
    return list(result.scalars().all())


async def get_all_users(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User).order_by(User.username))
    return list(result.scalars().all())


async def update_user_presence(
    db: AsyncSession, user_id: int, presence: str
) -> None:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        user.presence = presence
        user.last_seen = utc_now()


async def create_super_admin(
    db: AsyncSession, username: str, password: str, display_name: str
) -> User:
    """Create super_admin account (first-run setup)."""
    user = User(
        username=username,
        display_name=display_name,
        password_hash=hash_password(password),
        role=Role.SUPER_ADMIN,
        status=AccountStatus.APPROVED,
    )
    db.add(user)
    await db.flush()
    return user
