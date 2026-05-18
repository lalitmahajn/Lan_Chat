"""Server configuration management."""

import json
import sys
from pathlib import Path
from typing import Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from common.constants import ConfigKey, Defaults


# ─── Paths ────────────────────────────────────────────────────────────────────

def get_data_dir() -> Path:
    """Get server data directory. Creates if missing."""
    if getattr(sys, 'frozen', False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).parent.parent
    data_dir = base / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir


def get_db_path() -> str:
    """SQLite database path."""
    return str(get_data_dir() / "lan_chat.db")


def get_uploads_dir() -> Path:
    """Attachment storage directory. Creates if missing."""
    uploads = get_data_dir() / "uploads"
    uploads.mkdir(exist_ok=True)
    return uploads


# ─── Runtime Config ──────────────────────────────────────────────────────────

class ServerConfig:
    """Runtime server config. Loaded from DB on startup, cached in memory."""

    def __init__(self):
        self.server_name: str = Defaults.SERVER_NAME
        self.server_port: int = Defaults.SERVER_PORT
        self.max_file_size_mb: int = Defaults.MAX_FILE_SIZE_MB
        self.retention_days: int = Defaults.RETENTION_DAYS
        self.idle_timeout_minutes: int = Defaults.IDLE_TIMEOUT_MINUTES
        self.jwt_secret: Optional[str] = None

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    def to_dict(self) -> dict[str, Any]:
        return {
            ConfigKey.SERVER_NAME: self.server_name,
            ConfigKey.SERVER_PORT: self.server_port,
            ConfigKey.MAX_FILE_SIZE_MB: self.max_file_size_mb,
            ConfigKey.RETENTION_DAYS: self.retention_days,
            ConfigKey.IDLE_TIMEOUT_MINUTES: self.idle_timeout_minutes,
        }

    def update_from_dict(self, data: dict[str, Any]) -> None:
        if ConfigKey.SERVER_NAME in data:
            self.server_name = data[ConfigKey.SERVER_NAME]
        if ConfigKey.SERVER_PORT in data:
            self.server_port = int(data[ConfigKey.SERVER_PORT])
        if ConfigKey.MAX_FILE_SIZE_MB in data:
            self.max_file_size_mb = int(data[ConfigKey.MAX_FILE_SIZE_MB])
        if ConfigKey.RETENTION_DAYS in data:
            self.retention_days = int(data[ConfigKey.RETENTION_DAYS])
        if ConfigKey.IDLE_TIMEOUT_MINUTES in data:
            self.idle_timeout_minutes = int(data[ConfigKey.IDLE_TIMEOUT_MINUTES])
        if "jwt_secret" in data:
            self.jwt_secret = data["jwt_secret"]

    async def load_from_db(self, db: AsyncSession):
        from server.models import ServerConfigEntry
        result = await db.execute(select(ServerConfigEntry))
        rows = result.scalars().all()
        data = {r.key: json.loads(r.value) for r in rows}
        self.update_from_dict(data)

    async def save_to_db(self, db: AsyncSession, updates: dict[str, Any]):
        from server.models import ServerConfigEntry
        import json
        for k, v in updates.items():
            entry = await db.get(ServerConfigEntry, k)
            if not entry:
                entry = ServerConfigEntry(key=k, value=json.dumps(v))
                db.add(entry)
            else:
                entry.value = json.dumps(v)
        await db.commit()
        self.update_from_dict(updates)


# Global config instance
server_config = ServerConfig()
