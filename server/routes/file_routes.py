"""File routes — upload, download, thumbnail."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from common.schemas import AttachmentSchema
from server.auth import get_current_user
from server.database import get_db
from server.models import User
from server.services import file_service

router = APIRouter(prefix="/api/files", tags=["files"])


@router.post("/upload", response_model=AttachmentSchema, status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload attachment. Returns attachment metadata with ID for linking to message."""
    content = await file.read()
    try:
        attachment = await file_service.save_uploaded_file(
            db, content, file.filename or "unnamed", current_user.id
        )
        return AttachmentSchema.model_validate(attachment)
    except ValueError as e:
        raise HTTPException(status_code=413, detail=str(e))


@router.get("/{file_id}")
async def download_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download attachment by ID."""
    attachment = await file_service.get_attachment(db, file_id)
    if attachment is None:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = file_service.get_file_path(attachment)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File missing from storage")

    return FileResponse(
        path=str(file_path),
        filename=attachment.original_filename,
        media_type=attachment.mime_type,
    )


@router.get("/{file_id}/thumbnail")
async def get_thumbnail(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get image thumbnail (300px max)."""
    attachment = await file_service.get_attachment(db, file_id)
    if attachment is None:
        raise HTTPException(status_code=404, detail="File not found")

    thumb = file_service.generate_thumbnail(attachment)
    if thumb is None:
        raise HTTPException(status_code=404, detail="No thumbnail available")

    mime = "image/png" if attachment.mime_type == "image/png" else "image/jpeg"
    return Response(content=thumb, media_type=mime)
