"""File service — upload, download, thumbnail generation."""

import mimetypes
import uuid
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.constants import PREVIEWABLE_IMAGE_TYPES
from server.config import get_uploads_dir, server_config
from server.models import Attachment


async def save_uploaded_file(
    db: AsyncSession,
    file_content: bytes,
    original_filename: str,
    user_id: int,
) -> Attachment:
    """Save file to disk + create attachment record."""
    # Size check
    if len(file_content) > server_config.max_file_size_bytes:
        raise ValueError(
            f"File too large. Max {server_config.max_file_size_mb}MB"
        )

    # Generate stored filename
    ext = Path(original_filename).suffix.lower()
    stored_filename = f"{uuid.uuid4().hex}{ext}"

    # Detect MIME
    mime_type = mimetypes.guess_type(original_filename)[0] or "application/octet-stream"

    # Save to disk
    uploads_dir = get_uploads_dir()
    file_path = uploads_dir / stored_filename
    file_path.write_bytes(file_content)

    # DB record
    attachment = Attachment(
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_size=len(file_content),
        mime_type=mime_type,
        file_path=str(file_path),
        uploaded_by=user_id,
    )
    db.add(attachment)
    await db.flush()
    return attachment


async def get_attachment(db: AsyncSession, file_id: int) -> Optional[Attachment]:
    result = await db.execute(select(Attachment).where(Attachment.id == file_id))
    return result.scalar_one_or_none()


def get_file_path(attachment: Attachment) -> Path:
    """Resolve file path on disk."""
    return Path(attachment.file_path)


def generate_thumbnail(attachment: Attachment, max_size: int = 300) -> Optional[bytes]:
    """Generate thumbnail for image attachments. Returns bytes or None."""
    if attachment.mime_type not in PREVIEWABLE_IMAGE_TYPES:
        return None

    try:
        from PIL import Image
        import io

        file_path = get_file_path(attachment)
        if not file_path.exists():
            return None

        img = Image.open(file_path)
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

        buf = io.BytesIO()
        fmt = "PNG" if attachment.mime_type == "image/png" else "JPEG"
        img.save(buf, format=fmt)
        return buf.getvalue()
    except Exception:
        return None
