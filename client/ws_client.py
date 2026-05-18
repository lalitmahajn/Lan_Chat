"""WebSocket client — runs in QThread, emits signals for incoming events."""

import asyncio
import json
import logging

from PySide6.QtCore import QThread, Signal

import websockets

from client.config import client_config
from common.schemas import WSEvent

logger = logging.getLogger("lan_chat.ws_client")


class WSClient(QThread):
    """WebSocket client running in background thread."""

    connected = Signal()
    disconnected = Signal()
    event_received = Signal(dict)  # raw event dict
    error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._ws = None
        self._loop = None

    def run(self):
        self._running = True
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._connect_loop())
        except Exception as e:
            logger.error(f"WS thread error: {e}")
        finally:
            self._loop.close()

    async def _connect_loop(self):
        """Connect with auto-reconnect."""
        while self._running:
            try:
                url = client_config.ws_url
                async with websockets.connect(url) as ws:
                    self._ws = ws
                    self.connected.emit()
                    logger.info("WebSocket connected")

                    async for message in ws:
                        if not self._running:
                            break
                        try:
                            data = json.loads(message)
                            self.event_received.emit(data)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid WS message: {message[:100]}")

            except websockets.ConnectionClosed:
                logger.info("WebSocket connection closed")
            except Exception as e:
                logger.error(f"WS connection error: {e}")

            self._ws = None
            self.disconnected.emit()

            if self._running:
                # Reconnect delay
                await asyncio.sleep(3)

    def send_event(self, event: WSEvent):
        """Queue event to send (thread-safe)."""
        if self._ws and self._loop and self._running:
            asyncio.run_coroutine_threadsafe(
                self._send(event.model_dump_json()), self._loop
            )

    async def _send(self, payload: str):
        if self._ws:
            try:
                await self._ws.send(payload)
            except Exception as e:
                logger.error(f"WS send error: {e}")

    def stop(self):
        self._running = False
        if self._ws and self._loop and self._loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(self._ws.close(), self._loop)
                self._loop.call_soon_threadsafe(self._loop.stop)
            except Exception:
                pass
        self.quit()

