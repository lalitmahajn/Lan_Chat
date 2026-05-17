"""Constants shared between server and client."""

# ─── Roles ────────────────────────────────────────────────────────────────────
class Role:
    MEMBER = "member"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


# ─── User Account Status ─────────────────────────────────────────────────────
class AccountStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# ─── Presence States ─────────────────────────────────────────────────────────
class Presence:
    ONLINE = "online"
    AWAY = "away"
    OFFLINE = "offline"


# ─── WebSocket Event Types ───────────────────────────────────────────────────

# Client -> Server
class ClientEvent:
    MESSAGE_SEND = "message.send"
    MESSAGE_DELETE = "message.delete"
    TYPING_START = "typing.start"
    TYPING_STOP = "typing.stop"
    PRESENCE_UPDATE = "presence.update"


# Server -> Client
class ServerEvent:
    MESSAGE_NEW = "message.new"
    MESSAGE_DELETED = "message.deleted"
    TYPING_UPDATE = "typing.update"
    PRESENCE_CHANGED = "presence.changed"
    USER_APPROVED = "user.approved"
    DEPARTMENT_UPDATED = "department.updated"
    SYSTEM_NOTIFICATION = "system.notification"
    ERROR = "error"


# ─── Chat Types ──────────────────────────────────────────────────────────────
class ChatType:
    DEPARTMENT = "department"
    DIRECT_MESSAGE = "dm"


# ─── Server Config Keys ──────────────────────────────────────────────────────
class ConfigKey:
    SERVER_NAME = "server_name"
    SERVER_PORT = "server_port"
    MAX_FILE_SIZE_MB = "max_file_size_mb"
    RETENTION_DAYS = "retention_days"
    IDLE_TIMEOUT_MINUTES = "idle_timeout_minutes"


# ─── Defaults ─────────────────────────────────────────────────────────────────
class Defaults:
    SERVER_NAME = "LAN Chat Server"
    SERVER_PORT = 8765
    MAX_FILE_SIZE_MB = 50
    RETENTION_DAYS = 0  # 0 = keep forever
    IDLE_TIMEOUT_MINUTES = 5
    PAGE_SIZE = 50
    JWT_ACCESS_EXPIRE_MINUTES = 15
    JWT_REFRESH_EXPIRE_DAYS = 7
    BCRYPT_ROUNDS = 12


# ─── MIME Types for Inline Preview ────────────────────────────────────────────
PREVIEWABLE_IMAGE_TYPES = {
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "image/bmp",
    "image/svg+xml",
}

PREVIEWABLE_VIDEO_TYPES = {
    "video/mp4",
    "video/webm",
}
