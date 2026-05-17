"""Admin routes — user approval, department management, server config."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from common.schemas import (
    DepartmentCreate,
    DepartmentMemberAdd,
    DepartmentSchema,
    ServerConfigUpdate,
    UserSchema,
)
from server.auth import require_super_admin
from server.database import get_db
from server.models import User
from server.services import department_service, user_service
from server.config import server_config

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ─── User Management ─────────────────────────────────────────────────────────

@router.get("/users/pending", response_model=list[UserSchema])
async def get_pending_users(
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    users = await user_service.get_pending_users(db)
    return [UserSchema.model_validate(u) for u in users]


@router.get("/users", response_model=list[UserSchema])
async def get_all_users(
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    users = await user_service.get_all_users(db)
    return [UserSchema.model_validate(u) for u in users]


@router.post("/users/{user_id}/approve", response_model=UserSchema)
async def approve_user(
    user_id: int,
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await user_service.approve_user(db, user_id)
        return UserSchema.model_validate(user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/users/{user_id}/reject", response_model=UserSchema)
async def reject_user(
    user_id: int,
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await user_service.reject_user(db, user_id)
        return UserSchema.model_validate(user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ─── Department Management ───────────────────────────────────────────────────

@router.get("/departments", response_model=list[DepartmentSchema])
async def get_all_departments(
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    depts = await department_service.get_all_departments(db)
    return [DepartmentSchema.model_validate(d) for d in depts]

@router.post("/departments", response_model=DepartmentSchema, status_code=201)
async def create_department(
    req: DepartmentCreate,
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        dept = await department_service.create_department(db, req.name, req.description)
        await department_service.add_member(db, dept.id, admin.id, "admin")
        return DepartmentSchema.model_validate(dept)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.put("/departments/{dept_id}", response_model=DepartmentSchema)
async def update_department(
    dept_id: int,
    req: DepartmentCreate,
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        dept = await department_service.update_department(db, dept_id, req.name, req.description)
        return DepartmentSchema.model_validate(dept)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/departments/{dept_id}", status_code=204)
async def delete_department(
    dept_id: int,
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        await department_service.delete_department(db, dept_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/departments/{dept_id}/members", status_code=201)
async def add_member(
    dept_id: int,
    req: DepartmentMemberAdd,
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        await department_service.add_member(db, dept_id, req.user_id, req.role)
        return {"status": "added"}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete("/departments/{dept_id}/members/{user_id}", status_code=204)
async def remove_member(
    dept_id: int,
    user_id: int,
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        await department_service.remove_member(db, dept_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ─── Server Config ───────────────────────────────────────────────────────────

@router.get("/config")
async def get_config(admin: User = Depends(require_super_admin)):
    return server_config.to_dict()


@router.put("/config")
async def update_config(
    req: ServerConfigUpdate,
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    updates = req.model_dump(exclude_none=True)
    await server_config.save_to_db(db, updates)
    return server_config.to_dict()
