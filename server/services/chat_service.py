"""Chat service — message CRUD, pagination."""

from typing import Optional

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from common.constants import Defaults
from common.utils import utc_now
from server.models import Attachment, Message, User


async def save_message(
    db: AsyncSession,
    sender_id: int,
    content: str,
    department_id: Optional[int] = None,
    recipient_id: Optional[int] = None,
    reply_to_id: Optional[int] = None,
    attachment_ids: Optional[list[int]] = None,
) -> Message:
    """Save new message. Returns message with relationships loaded."""
    msg = Message(
        sender_id=sender_id,
        department_id=department_id,
        recipient_id=recipient_id,
        content=content,
        reply_to_id=reply_to_id,
        created_at=utc_now(),
    )
    db.add(msg)
    await db.flush()

    # Link attachments
    if attachment_ids:
        result = await db.execute(
            select(Attachment).where(
                Attachment.id.in_(attachment_ids),
                Attachment.uploaded_by == sender_id,
                Attachment.message_id.is_(None),
            )
        )
        for att in result.scalars().all():
            att.message_id = msg.id

    # Reload with relationships
    result = await db.execute(
        select(Message)
        .options(
            selectinload(Message.sender),
            selectinload(Message.attachments),
            selectinload(Message.reply_to).selectinload(Message.sender),
        )
        .where(Message.id == msg.id)
    )
    return result.scalar_one()


async def get_department_messages(
    db: AsyncSession,
    department_id: int,
    page: int = 1,
    page_size: int = Defaults.PAGE_SIZE,
) -> tuple[list[Message], int]:
    """Get paginated messages for department. Returns (messages, total_count)."""
    # Count
    count_q = select(func.count()).select_from(Message).where(
        Message.department_id == department_id,
        Message.is_deleted == False,
    )
    total = (await db.execute(count_q)).scalar() or 0

    # Fetch
    offset = (page - 1) * page_size
    q = (
        select(Message)
        .options(
            selectinload(Message.sender),
            selectinload(Message.attachments),
            selectinload(Message.reply_to).selectinload(Message.sender),
        )
        .where(
            Message.department_id == department_id,
            Message.is_deleted == False,
        )
        .order_by(desc(Message.created_at))
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(q)
    messages = list(result.scalars().all())
    messages.reverse()  # oldest first for display
    return messages, total


async def get_dm_messages(
    db: AsyncSession,
    user_id: int,
    other_user_id: int,
    page: int = 1,
    page_size: int = Defaults.PAGE_SIZE,
) -> tuple[list[Message], int]:
    """Get paginated DM messages between two users."""
    dm_filter = and_(
        Message.department_id.is_(None),
        Message.is_deleted == False,
        or_(
            and_(Message.sender_id == user_id, Message.recipient_id == other_user_id),
            and_(Message.sender_id == other_user_id, Message.recipient_id == user_id),
        ),
    )

    count_q = select(func.count()).select_from(Message).where(dm_filter)
    total = (await db.execute(count_q)).scalar() or 0

    offset = (page - 1) * page_size
    q = (
        select(Message)
        .options(
            selectinload(Message.sender),
            selectinload(Message.attachments),
            selectinload(Message.reply_to).selectinload(Message.sender),
        )
        .where(dm_filter)
        .order_by(desc(Message.created_at))
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(q)
    messages = list(result.scalars().all())
    messages.reverse()
    return messages, total


async def delete_message(
    db: AsyncSession, message_id: int, user_id: int, is_admin: bool = False
) -> Message:
    """Soft-delete message. Author or admin can delete."""
    result = await db.execute(select(Message).where(Message.id == message_id))
    msg = result.scalar_one_or_none()

    if msg is None:
        raise ValueError("Message not found")
    if msg.sender_id != user_id and not is_admin:
        raise PermissionError("Cannot delete other's message")

    msg.is_deleted = True
    msg.content = "[deleted]"
    return msg


async def get_message_by_id(db: AsyncSession, message_id: int) -> Optional[Message]:
    result = await db.execute(
        select(Message)
        .options(
            selectinload(Message.sender),
            selectinload(Message.attachments),
        )
        .where(Message.id == message_id)
    )
    return result.scalar_one_or_none()
