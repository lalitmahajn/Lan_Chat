"""WebSocket connection manager — tracks connected clients, routes messages."""

import asyncio
import json
import logging
from typing import Optional

from fastapi import WebSocket

from common.constants import ServerEvent
from common.schemas import WSEvent

logger = logging.getLogger("lan_chat.ws")


class ConnectionManager:
    """Manages active WebSocket connections and message routing."""

    def __init__(self):
        # user_id -> WebSocket
        self._connections: dict[int, WebSocket] = {}
        self._lock = asyncio.Lock()

    @property
    def connected_count(self) -> int:
        return len(self._connections)

    @property
    def connected_user_ids(self) -> set[int]:
        return set(self._connections.keys())

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        """Register connected client."""
        await websocket.accept()
        async with self._lock:
            # Disconnect existing connection for this user (if any)
            old = self._connections.get(user_id)
            if old:
                try:
                    await old.close(code=4000, reason="Connected from another client")
                except Exception:
                    pass
            self._connections[user_id] = websocket
        logger.info(f"User {user_id} connected. Total: {self.connected_count}")

    async def disconnect(self, user_id: int) -> None:
        """Remove disconnected client."""
        async with self._lock:
            self._connections.pop(user_id, None)
        logger.info(f"User {user_id} disconnected. Total: {self.connected_count}")

    def is_connected(self, user_id: int) -> bool:
        return user_id in self._connections

    async def send_to_user(self, user_id: int, event: WSEvent) -> bool:
        """Send event to specific user. Returns True if sent."""
        ws = self._connections.get(user_id)
        if ws is None:
            return False
        try:
            await ws.send_text(event.model_dump_json())
            return True
        except Exception:
            await self.disconnect(user_id)
            return False

    async def broadcast_to_users(self, user_ids: set[int], event: WSEvent) -> None:
        """Broadcast event to multiple users."""
        payload = event.model_dump_json()
        tasks = []
        for uid in user_ids:
            ws = self._connections.get(uid)
            if ws:
                tasks.append(self._safe_send(uid, ws, payload))
        if tasks:
            await asyncio.gather(*tasks)

    async def broadcast_all(self, event: WSEvent) -> None:
        """Broadcast event to all connected users."""
        await self.broadcast_to_users(set(self._connections.keys()), event)

    async def _safe_send(self, user_id: int, ws: WebSocket, payload: str) -> None:
        try:
            await ws.send_text(payload)
        except Exception:
            await self.disconnect(user_id)


# Global instance
ws_manager = ConnectionManager()
