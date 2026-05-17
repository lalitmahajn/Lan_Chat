"""Chat routes — WebSocket endpoint + REST message history."""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from common.constants import ClientEvent, Defaults, Presence, Role, ServerEvent
from common.schemas import (
    MessageDelete,
    MessageSchema,
    MessageSend,
    PaginatedResponse,
    TypingEvent,
    UserBrief,
    WSEvent,
)
from server.auth import authenticate_websocket, get_current_user
from server.database import get_db, get_session_factory
from server.models import User
from server.services import chat_service, department_service
from server.services.user_service import update_user_presence
from server.ws_manager import ws_manager

logger = logging.getLogger("lan_chat.chat")

router = APIRouter(tags=["chat"])


# ─── REST: Message History ────────────────────────────────────────────────────

@router.get("/api/messages/{dept_id}", response_model=PaginatedResponse)
async def get_department_messages(
    dept_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(Defaults.PAGE_SIZE, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify membership
    if not current_user.is_super_admin:
        if not await department_service.is_member(db, dept_id, current_user.id):
            raise HTTPException(status_code=403, detail="Not a member of this department")

    messages, total = await chat_service.get_department_messages(db, dept_id, page, limit)
    return PaginatedResponse(
        items=[_msg_to_schema(m).model_dump(mode="json") for m in messages],
        total=total,
        page=page,
        page_size=limit,
        has_more=(page * limit) < total,
    )


@router.get("/api/messages/dm/{user_id}", response_model=PaginatedResponse)
async def get_dm_messages(
    user_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(Defaults.PAGE_SIZE, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    messages, total = await chat_service.get_dm_messages(
        db, current_user.id, user_id, page, limit
    )
    return PaginatedResponse(
        items=[_msg_to_schema(m).model_dump(mode="json") for m in messages],
        total=total,
        page=page,
        page_size=limit,
        has_more=(page * limit) < total,
    )


# ─── WebSocket ────────────────────────────────────────────────────────────────

@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """Main WebSocket endpoint. Auth via ?token= query param."""
    factory = get_session_factory()

    # Auth
    async with factory() as db:
        user = await authenticate_websocket(websocket, db)
        if user is None:
            await websocket.close(code=4001, reason="Unauthorized")
            return
        user_id = user.id
        username = user.username
        display_name = user.display_name
        user_role = user.role

    await ws_manager.connect(user_id, websocket)

    # Broadcast presence
    async with factory() as db:
        await update_user_presence(db, user_id, Presence.ONLINE)
        await db.commit()

    await ws_manager.broadcast_all(WSEvent(
        event=ServerEvent.PRESENCE_CHANGED,
        data={"user_id": user_id, "username": username, "presence": Presence.ONLINE},
    ))

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                event = WSEvent.model_validate_json(raw)
            except Exception:
                await ws_manager.send_to_user(user_id, WSEvent(
                    event=ServerEvent.ERROR,
                    data={"message": "Invalid event format"},
                ))
                continue

            async with factory() as db:
                await _handle_event(db, event, user_id, username, display_name, user_role)
                await db.commit()

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WS error for user {user_id}: {e}")
    finally:
        await ws_manager.disconnect(user_id)
        async with factory() as db:
            await update_user_presence(db, user_id, Presence.OFFLINE)
            await db.commit()
        await ws_manager.broadcast_all(WSEvent(
            event=ServerEvent.PRESENCE_CHANGED,
            data={"user_id": user_id, "username": username, "presence": Presence.OFFLINE},
        ))


async def _handle_event(
    db: AsyncSession,
    event: WSEvent,
    user_id: int,
    username: str,
    display_name: str,
    user_role: str,
):
    """Route incoming WS event to handler."""
    if event.event == ClientEvent.MESSAGE_SEND:
        await _handle_message_send(db, event.data, user_id)

    elif event.event == ClientEvent.MESSAGE_DELETE:
        await _handle_message_delete(db, event.data, user_id, user_role)

    elif event.event in (ClientEvent.TYPING_START, ClientEvent.TYPING_STOP):
        await _handle_typing(db, event, user_id, username)

    elif event.event == ClientEvent.PRESENCE_UPDATE:
        presence = event.data.get("status", Presence.ONLINE)
        await update_user_presence(db, user_id, presence)
        await ws_manager.broadcast_all(WSEvent(
            event=ServerEvent.PRESENCE_CHANGED,
            data={"user_id": user_id, "username": username, "presence": presence},
        ))
    else:
        await ws_manager.send_to_user(user_id, WSEvent(
            event=ServerEvent.ERROR,
            data={"message": f"Unknown event: {event.event}"},
        ))


async def _handle_message_send(db: AsyncSession, data: dict, user_id: int):
    """Handle message.send event."""
    try:
        payload = MessageSend(**data)
    except Exception:
        await ws_manager.send_to_user(user_id, WSEvent(
            event=ServerEvent.ERROR, data={"message": "Invalid message payload"}
        ))
        return

    # Validate target
    if payload.department_id is None and payload.recipient_id is None:
        await ws_manager.send_to_user(user_id, WSEvent(
            event=ServerEvent.ERROR, data={"message": "Must specify department_id or recipient_id"}
        ))
        return

    # Check membership for dept messages
    if payload.department_id is not None:
        if not await department_service.is_member(db, payload.department_id, user_id):
            await ws_manager.send_to_user(user_id, WSEvent(
                event=ServerEvent.ERROR, data={"message": "Not a member of this department"}
            ))
            return

    msg = await chat_service.save_message(
        db,
        sender_id=user_id,
        content=payload.content,
        department_id=payload.department_id,
        recipient_id=payload.recipient_id,
        reply_to_id=payload.reply_to_id,
        attachment_ids=payload.attachment_ids,
    )

    msg_schema = _msg_to_schema(msg)
    ws_event = WSEvent(event=ServerEvent.MESSAGE_NEW, data=msg_schema.model_dump(mode="json"))

    if payload.department_id is not None:
        # Broadcast to dept members
        member_ids = await department_service.get_department_member_ids(db, payload.department_id)
        await ws_manager.broadcast_to_users(member_ids, ws_event)
    else:
        # DM: send to recipient + sender
        await ws_manager.send_to_user(user_id, ws_event)
        if payload.recipient_id and payload.recipient_id != user_id:
            await ws_manager.send_to_user(payload.recipient_id, ws_event)


async def _handle_message_delete(db: AsyncSession, data: dict, user_id: int, user_role: str):
    """Handle message.delete event."""
    message_id = data.get("message_id")
    if not message_id:
        return

    try:
        is_admin = user_role in (Role.SUPER_ADMIN, Role.ADMIN)
        msg = await chat_service.delete_message(db, message_id, user_id, is_admin)

        delete_event = WSEvent(
            event=ServerEvent.MESSAGE_DELETED,
            data={
                "message_id": message_id,
                "department_id": msg.department_id,
                "recipient_id": msg.recipient_id,
            },
        )

        if msg.department_id:
            member_ids = await department_service.get_department_member_ids(db, msg.department_id)
            await ws_manager.broadcast_to_users(member_ids, delete_event)
        else:
            await ws_manager.send_to_user(user_id, delete_event)
            if msg.recipient_id and msg.recipient_id != user_id:
                await ws_manager.send_to_user(msg.recipient_id, delete_event)

    except (ValueError, PermissionError) as e:
        await ws_manager.send_to_user(user_id, WSEvent(
            event=ServerEvent.ERROR, data={"message": str(e)}
        ))


async def _handle_typing(db: AsyncSession, event: WSEvent, user_id: int, username: str):
    """Handle typing start/stop events."""
    dept_id = event.data.get("department_id")
    recipient_id = event.data.get("recipient_id")
    is_typing = event.event == ClientEvent.TYPING_START

    typing_event = WSEvent(
        event=ServerEvent.TYPING_UPDATE,
        data={
            "user_id": user_id,
            "username": username,
            "department_id": dept_id,
            "recipient_id": recipient_id,
            "is_typing": is_typing,
        },
    )

    if dept_id:
        member_ids = await department_service.get_department_member_ids(db, dept_id)
        member_ids.discard(user_id)  # Don't echo back
        await ws_manager.broadcast_to_users(member_ids, typing_event)
    elif recipient_id:
        await ws_manager.send_to_user(recipient_id, typing_event)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _msg_to_schema(msg) -> MessageSchema:
    """Convert ORM Message to Pydantic schema."""
    from common.schemas import AttachmentSchema, MessageBrief

    reply_to = None
    if msg.reply_to and not msg.reply_to.is_deleted:
        reply_to = MessageBrief(
            id=msg.reply_to.id,
            sender=UserBrief(
                id=msg.reply_to.sender.id,
                username=msg.reply_to.sender.username,
                display_name=msg.reply_to.sender.display_name,
                presence=msg.reply_to.sender.presence,
            ),
            content=msg.reply_to.content[:100],
            created_at=msg.reply_to.created_at,
        )

    return MessageSchema(
        id=msg.id,
        sender=UserBrief(
            id=msg.sender.id,
            username=msg.sender.username,
            display_name=msg.sender.display_name,
            presence=msg.sender.presence,
        ),
        department_id=msg.department_id,
        recipient_id=msg.recipient_id,
        content=msg.content,
        reply_to_id=msg.reply_to_id,
        reply_to=reply_to,
        attachments=[
            AttachmentSchema(
                id=a.id,
                original_filename=a.original_filename,
                file_size=a.file_size,
                mime_type=a.mime_type,
            )
            for a in (msg.attachments or [])
        ],
        is_deleted=msg.is_deleted,
        created_at=msg.created_at,
    )
