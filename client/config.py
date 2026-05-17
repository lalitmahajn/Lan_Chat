"""Client configuration — server address, tokens, theme preference."""

import json
from pathlib import Path
from typing import Optional


_CONFIG_DIR = Path.home() / ".lan_chat_client"
_CONFIG_FILE = _CONFIG_DIR / "config.json"


class ClientConfig:
    """Persistent client settings."""

    def __init__(self):
        self.server_host: str = ""
        self.server_port: int = 8765
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.theme: str = "system"  # 'dark', 'light', 'system'
        self.username: str = ""
        self.user_id: Optional[int] = None
        self.user_role: str = ""
        self.display_name: str = ""
        self.load()

    @property
    def server_url(self) -> str:
        return f"http://{self.server_host}:{self.server_port}"

    @property
    def ws_url(self) -> str:
        return f"ws://{self.server_host}:{self.server_port}/ws/chat?token={self.access_token}"

    @property
    def is_logged_in(self) -> bool:
        return bool(self.access_token and self.server_host)

    def save(self):
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "server_host": self.server_host,
            "server_port": self.server_port,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "theme": self.theme,
            "username": self.username,
            "user_id": self.user_id,
            "user_role": self.user_role,
            "display_name": self.display_name,
        }
        _CONFIG_FILE.write_text(json.dumps(data, indent=2))

    def load(self):
        if not _CONFIG_FILE.exists():
            return
        try:
            data = json.loads(_CONFIG_FILE.read_text())
            self.server_host = data.get("server_host", "")
            self.server_port = data.get("server_port", 8765)
            self.access_token = data.get("access_token")
            self.refresh_token = data.get("refresh_token")
            self.theme = data.get("theme", "system")
            self.username = data.get("username", "")
            self.user_id = data.get("user_id")
            self.user_role = data.get("user_role", "")
            self.display_name = data.get("display_name", "")
        except Exception:
            pass

    def clear_auth(self):
        self.access_token = None
        self.refresh_token = None
        self.user_id = None
        self.username = ""
        self.user_role = ""
        self.display_name = ""
        self.save()


# Global instance
client_config = ClientConfig()
