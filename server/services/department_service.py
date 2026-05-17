"""Department service — CRUD, membership management."""

from typing import Optional

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from common.constants import Role
from server.models import Department, User, UserDepartment


async def create_department(
    db: AsyncSession, name: str, description: Optional[str] = None
) -> Department:
    """Create new department."""
    existing = await db.execute(select(Department).where(Department.name == name))
    if existing.scalar_one_or_none():
        raise ValueError("Department name already exists")

    dept = Department(name=name, description=description)
    db.add(dept)
    await db.flush()
    return dept


async def get_department(db: AsyncSession, dept_id: int) -> Optional[Department]:
    result = await db.execute(select(Department).where(Department.id == dept_id))
    return result.scalar_one_or_none()


async def get_all_departments(db: AsyncSession) -> list[Department]:
    result = await db.execute(select(Department).order_by(Department.name))
    return list(result.scalars().all())


async def update_department(
    db: AsyncSession, dept_id: int, name: Optional[str] = None, description: Optional[str] = None
) -> Department:
    result = await db.execute(select(Department).where(Department.id == dept_id))
    dept = result.scalar_one_or_none()
    if dept is None:
        raise ValueError("Department not found")
    if name:
        dept.name = name
    if description is not None:
        dept.description = description
    return dept


async def delete_department(db: AsyncSession, dept_id: int) -> None:
    result = await db.execute(select(Department).where(Department.id == dept_id))
    dept = result.scalar_one_or_none()
    if dept is None:
        raise ValueError("Department not found")
    await db.delete(dept)


async def add_member(
    db: AsyncSession, dept_id: int, user_id: int, role: str = Role.MEMBER
) -> UserDepartment:
    """Add user to department."""
    # Check exists
    existing = await db.execute(
        select(UserDepartment).where(
            UserDepartment.user_id == user_id,
            UserDepartment.department_id == dept_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("User already in department")

    membership = UserDepartment(
        user_id=user_id,
        department_id=dept_id,
        role=role,
    )
    db.add(membership)
    await db.flush()
    return membership


async def remove_member(db: AsyncSession, dept_id: int, user_id: int) -> None:
    result = await db.execute(
        select(UserDepartment).where(
            UserDepartment.user_id == user_id,
            UserDepartment.department_id == dept_id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise ValueError("User not in department")
    await db.delete(membership)


async def get_department_members(db: AsyncSession, dept_id: int) -> list[tuple[User, str]]:
    """Get department members with their dept role. Returns [(User, role)]."""
    result = await db.execute(
        select(User, UserDepartment.role)
        .join(UserDepartment, UserDepartment.user_id == User.id)
        .where(UserDepartment.department_id == dept_id)
        .order_by(User.username)
    )
    return list(result.all())


async def get_department_member_ids(db: AsyncSession, dept_id: int) -> set[int]:
    """Get set of user IDs in department."""
    result = await db.execute(
        select(UserDepartment.user_id).where(UserDepartment.department_id == dept_id)
    )
    return set(result.scalars().all())


async def get_user_departments(db: AsyncSession, user_id: int) -> list[tuple[Department, str]]:
    """Get departments user belongs to. Returns [(Department, role)]."""
    result = await db.execute(
        select(Department, UserDepartment.role)
        .join(UserDepartment, UserDepartment.department_id == Department.id)
        .where(UserDepartment.user_id == user_id)
        .order_by(Department.name)
    )
    return list(result.all())


async def is_member(db: AsyncSession, dept_id: int, user_id: int) -> bool:
    result = await db.execute(
        select(UserDepartment).where(
            UserDepartment.user_id == user_id,
            UserDepartment.department_id == dept_id,
        )
    )
    return result.scalar_one_or_none() is not None


async def is_dept_admin(db: AsyncSession, dept_id: int, user_id: int) -> bool:
    result = await db.execute(
        select(UserDepartment).where(
            UserDepartment.user_id == user_id,
            UserDepartment.department_id == dept_id,
            UserDepartment.role == Role.ADMIN,
        )
    )
    return result.scalar_one_or_none() is not None
