"""User-facing routes — departments list, users list, profile."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from common.schemas import DepartmentSchema, UserBrief, UserSchema
from server.auth import get_current_user
from server.database import get_db
from server.models import User
from server.services import department_service, user_service

router = APIRouter(prefix="/api", tags=["user"])


@router.get("/departments", response_model=list[DepartmentSchema])
async def get_my_departments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get departments the current user belongs to."""
    dept_roles = await department_service.get_user_departments(db, current_user.id)
    result = []
    for dept, role in dept_roles:
        members = await department_service.get_department_member_ids(db, dept.id)
        result.append(DepartmentSchema(
            id=dept.id,
            name=dept.name,
            description=dept.description,
            created_at=dept.created_at,
            member_count=len(members),
            user_role=role,
        ))
    return result


@router.get("/departments/{dept_id}/members", response_model=list[UserBrief])
async def get_department_members(
    dept_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get members of a department."""
    if not current_user.is_super_admin:
        if not await department_service.is_member(db, dept_id, current_user.id):
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Not a member")

    members = await department_service.get_department_members(db, dept_id)
    return [
        UserBrief(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            presence=user.presence,
        )
        for user, role in members
    ]


@router.get("/users/approved", response_model=list[UserBrief])
async def get_approved_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all approved users (for DM list)."""
    users = await user_service.get_all_users(db)
    return [
        UserBrief(
            id=u.id,
            username=u.username,
            display_name=u.display_name,
            presence=u.presence,
        )
        for u in users
        if u.status == "approved" and u.id != current_user.id
    ]


@router.get("/me", response_model=UserSchema)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user profile."""
    return UserSchema.model_validate(current_user)
