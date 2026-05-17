# LAN Chat — Design Document

## Overview

Server-based LAN chat application with PySide6 desktop clients. Supports department-based group chats, direct messages, file attachments, role-based access, and admin management.

---

## Architecture

```
┌─────────────────┐         WebSocket / REST         ┌─────────────────┐
│   Client EXE    │ ◄──────────────────────────────► │   Server EXE    │
│   (PySide6)     │        (plain ws://)             │ (FastAPI+PySide6)│
│                 │                                   │                 │
│ • Chat UI       │                                   │ • Uvicorn (bg)  │
│ • Admin panel   │                                   │ • Status GUI    │
│ • System tray   │                                   │ • SQLite DB     │
│ • Theme engine  │                                   │ • File storage  │
└─────────────────┘                                   └─────────────────┘
```

**Server threading model:** Uvicorn runs in background daemon thread, PySide6 GUI runs on main thread. Communication via Qt Signals/Slots (thread-safe).

---

## Decisions

| # | Topic | Decision |
|---|-------|----------|
| 1 | Network Discovery | Hybrid: mDNS auto-discovery (zeroconf) + manual IP fallback |
| 2 | Protocol | WebSockets (bidirectional, real-time) |
| 3 | Server Framework | FastAPI (WebSocket + REST endpoints) |
| 4 | Database | SQLite (structured data) + filesystem (attachments) |
| 5 | Authentication | Self-registration with admin approval |
| 6 | Roles | Multi-department per user, flat (member/admin) + system super_admin |
| 7 | Chat Structure | Department group chats + direct messages (DMs) |
| 8 | Attachments | Any file type, configurable size limit, inline previews for images/media |
| 9 | Message History | Paginated (load N, scroll for more) + configurable retention policy |
| 10 | Presence | Online/Offline/Away + unread badges + system tray toast notifications |
| 11 | Admin Panel | Embedded in PySide6 client (visible to super_admin only) |
| 12 | Packaging | Two separate EXEs: server (with status GUI) + client |
| 13 | Auth Tokens | JWT access (short-lived) + refresh token (long-lived), plain WS |
| 14 | Message Features | Text, attachments, delete, typing indicators, reply/quote |
| 15 | First-Run Setup | GUI wizard in server app (create super_admin, set port/name) |
| 16 | Client UI Layout | 3-panel: left sidebar, center messages, collapsible right members |
| 17 | Theme | Dark + Light + system-follows default, user-overridable |
| 18 | Search | None (v1) |
| 19 | EXE Packaging | PyInstaller --onedir |
| 20 | Server Architecture | Separate threads (Uvicorn bg + PySide6 main) |
| 21 | Project Structure | Monorepo with shared `common/` package |
| 22 | Message Format | Basic markdown: **bold**, *italic*, `code`, ```code blocks``` |

---

## Project Structure

```
LAN_Chat/
├── common/                  # Shared code (server + client)
│   ├── __init__.py
│   ├── schemas.py           # Pydantic message/event schemas
│   ├── constants.py         # Event types, roles, status codes
│   └── utils.py             # Shared utilities
│
├── server/                  # Server application
│   ├── __init__.py
│   ├── app.py               # FastAPI app factory
│   ├── config.py            # Server configuration
│   ├── database.py          # SQLAlchemy engine/session
│   ├── models.py            # DB models (User, Department, Message, etc.)
│   ├── auth.py              # JWT, password hashing, auth deps
│   ├── ws_manager.py        # WebSocket connection manager
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth_routes.py   # Register, login, refresh
│   │   ├── chat_routes.py   # WebSocket endpoint
│   │   ├── file_routes.py   # Upload/download attachments
│   │   └── admin_routes.py  # User approval, dept mgmt, config
│   ├── services/
│   │   ├── __init__.py
│   │   ├── user_service.py
│   │   ├── chat_service.py
│   │   ├── file_service.py
│   │   └── department_service.py
│   └── gui/                 # Server status GUI
│       ├── __init__.py
│       ├── server_window.py # Main status dashboard
│       └── setup_wizard.py  # First-run setup
│
├── client/                  # Client application
│   ├── __init__.py
│   ├── config.py            # Client settings (theme, server addr)
│   ├── api_client.py        # REST API client (auth, file upload)
│   ├── ws_client.py         # WebSocket client manager
│   ├── discovery.py         # mDNS server discovery
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── main_window.py   # Main chat window (3-panel)
│   │   ├── login_window.py  # Login / registration
│   │   ├── chat_panel.py    # Message feed panel
│   │   ├── sidebar.py       # Departments + DMs list
│   │   ├── members_panel.py # Online members (collapsible)
│   │   ├── message_bubble.py# Individual message widget
│   │   ├── admin_panel.py   # Admin views (super_admin only)
│   │   ├── theme.py         # Dark/Light theme engine
│   │   └── tray.py          # System tray icon + notifications
│   └── utils/
│       ├── __init__.py
│       └── markdown.py      # Basic markdown -> HTML renderer
│
├── assets/                  # Icons, fonts, QSS stylesheets
│   ├── icons/
│   └── styles/
│
├── data/                    # Runtime data (created by server)
│   ├── lan_chat.db          # SQLite database
│   └── uploads/             # Attachment storage
│
├── server_main.py           # Server EXE entry point
├── client_main.py           # Client EXE entry point
├── requirements.txt         # Python dependencies
├── server.spec              # PyInstaller spec for server
├── client.spec              # PyInstaller spec for client
├── DESIGN.md                # This document
└── README.md                # Setup & usage instructions
```

---

## Database Schema

### Users
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| username | TEXT UNIQUE | Login identifier |
| display_name | TEXT | Shown in chat |
| password_hash | TEXT | bcrypt hashed |
| role | TEXT | 'user' or 'super_admin' |
| status | TEXT | 'pending', 'approved', 'rejected' |
| is_online | BOOLEAN | Current connection state |
| presence | TEXT | 'online', 'away', 'offline' |
| last_seen | DATETIME | Last activity timestamp |
| created_at | DATETIME | Registration time |

### Departments
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| name | TEXT UNIQUE | Department name |
| description | TEXT | Optional |
| created_at | DATETIME | |

### UserDepartments (Many-to-Many)
| Column | Type | Notes |
|--------|------|-------|
| user_id | INTEGER FK | -> Users.id |
| department_id | INTEGER FK | -> Departments.id |
| role | TEXT | 'member' or 'admin' |

### Messages
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| sender_id | INTEGER FK | -> Users.id |
| department_id | INTEGER FK | NULL for DMs |
| recipient_id | INTEGER FK | NULL for group chats |
| content | TEXT | Message text (markdown) |
| reply_to_id | INTEGER FK | NULL or -> Messages.id |
| is_deleted | BOOLEAN | Soft delete |
| created_at | DATETIME | |

### Attachments
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| message_id | INTEGER FK | -> Messages.id |
| original_filename | TEXT | User's filename |
| stored_filename | TEXT | UUID-based on disk |
| file_size | INTEGER | Bytes |
| mime_type | TEXT | e.g., 'image/png' |
| file_path | TEXT | Relative path in uploads/ |

### ServerConfig
| Column | Type | Notes |
|--------|------|-------|
| key | TEXT PK | Config key |
| value | TEXT | JSON-encoded value |

---

## WebSocket Event Types

### Client -> Server
| Event | Payload | Description |
|-------|---------|-------------|
| `message.send` | `{department_id?, recipient_id?, content, reply_to_id?, attachment_ids?}` | Send message |
| `message.delete` | `{message_id}` | Delete own message (or any if admin) |
| `typing.start` | `{department_id?, recipient_id?}` | Typing indicator on |
| `typing.stop` | `{department_id?, recipient_id?}` | Typing indicator off |
| `presence.update` | `{status: 'online'|'away'}` | Update presence |

### Server -> Client
| Event | Payload | Description |
|-------|---------|-------------|
| `message.new` | `{message object}` | New message in subscribed chat |
| `message.deleted` | `{message_id, department_id?, recipient_id?}` | Message was deleted |
| `typing.update` | `{user_id, username, department_id?, recipient_id?, is_typing}` | Someone typing |
| `presence.changed` | `{user_id, username, presence}` | User presence changed |
| `user.approved` | `{user_id}` | Registration approved |
| `department.updated` | `{department object}` | Department membership changed |
| `system.notification` | `{message, type}` | System-level notification |

---

## REST API Endpoints

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/register` | Self-register (pending approval) |
| POST | `/api/auth/login` | Login -> JWT + refresh token |
| POST | `/api/auth/refresh` | Refresh access token |
| POST | `/api/auth/logout` | Invalidate refresh token |

### Chat
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/messages/{dept_id}?page=&limit=` | Paginated dept messages |
| GET | `/api/messages/dm/{user_id}?page=&limit=` | Paginated DM messages |
| WS | `/ws/chat` | Main WebSocket endpoint |

### Files
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/files/upload` | Upload attachment (multipart) |
| GET | `/api/files/{file_id}` | Download attachment |
| GET | `/api/files/{file_id}/thumbnail` | Get image thumbnail |

### Admin (super_admin only)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/admin/users/pending` | List pending registrations |
| POST | `/api/admin/users/{id}/approve` | Approve user |
| POST | `/api/admin/users/{id}/reject` | Reject user |
| POST | `/api/admin/departments` | Create department |
| PUT | `/api/admin/departments/{id}` | Update department |
| DELETE | `/api/admin/departments/{id}` | Delete department |
| POST | `/api/admin/departments/{id}/members` | Add user to dept |
| DELETE | `/api/admin/departments/{id}/members/{uid}` | Remove from dept |
| GET | `/api/admin/config` | Get server config |
| PUT | `/api/admin/config` | Update server config |

---

## Security

- Passwords: bcrypt hashed (12 rounds)
- Auth: JWT access token (15min) + refresh token (7 days)
- WebSocket: Token sent on connection handshake, validated before accepting
- Admin routes: Dependency injection checks for super_admin role
- File uploads: Configurable max size (default 50MB)
- Transport: Plain ws:// / http:// (LAN trusted network)

---

## Dependencies

```
# Server
fastapi
uvicorn[standard]
sqlalchemy
aiosqlite
python-jose[cryptography]    # JWT
passlib[bcrypt]               # Password hashing
python-multipart              # File uploads
zeroconf                      # mDNS discovery

# Client + Server GUI
PySide6

# Packaging
pyinstaller
```

---

## Future (v2)

- Message search (per-chat + global)
- Message editing with history
- Read receipts
- Sub-channels per department
- TLS/WSS support
- File type restrictions
- User avatars
- Emoji picker
