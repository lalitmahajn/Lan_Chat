# 🛡️ LAN Chat Application

A high-performance, secure, offline-first local network chat application built with **FastAPI** (WebSockets + REST) on the backend and **PySide6** (Qt for Python) on the desktop client.

Designed for corporate and local network environments where external internet connectivity is unavailable or restricted. Features zero-configuration discovery via mDNS, role-based access control, department-level channels, and end-to-end management tools.

---

## ✨ Features

- **⚡ Real-Time WebSockets:** Bidirectional communication for instant messaging, typing indicators, and real-time presence updates.
- **🏢 Department Channels:** Group discussions organized by department (e.g., IT, HR, Engineering) with configurable membership permissions.
- **📩 Direct Messages (DMs):** One-to-one private conversations between approved network peers.
- **📎 Rich Attachments & Previews:** Drag-and-drop file sharing with auto-generated inline thumbnails for images.
- **🎨 Catppuccin Theming:** Premium Dark & Light UI palettes featuring FontAwesome 5 iconography (`qtawesome`) and smooth QSS styling.
- **🔔 System Tray Integration:** Native Windows desktop notifications and background taskbar presence.
- **🛡️ Embedded Admin Panel:** Complete super-admin dashboard for user approvals, department membership management, and server configuration adjustments.
- **📦 Zero-Install Standalone EXEs:** Packaged into portable Windows executables (`.exe`) via PyInstaller.

---

## 🏛️ System Architecture

```
┌─────────────────────────┐        WebSocket / REST        ┌─────────────────────────┐
│     Client App EXE      │ ◄────────────────────────────► │     Server App EXE      │
│        (PySide6)        │          (ws:// / http://)     │    (FastAPI + PySide6)  │
│                         │                                │                         │
│ • Chat & Members GUI    │                                │ • Uvicorn Daemon Thread │
│ • Admin Management Panel│                                │ • SQLite Database       │
│ • System Tray Manager   │                                │ • Server Status GUI     │
│ • Catppuccin QSS Engine │                                │ • Uploads File Storage  │
└─────────────────────────┘                                └─────────────────────────┘
```

The server app bundles a **PySide6 Status Dashboard** running on the main Qt thread while hosting the **FastAPI/Uvicorn** ASGI server in a background daemon thread. Clients connect securely over the LAN via JWT authentication.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+ (if running from source)
- Windows OS (for precompiled `.bat` build scripts)

### Running from Source

1. **Clone Repository & Install Dependencies:**
   ```bash
   git clone https://github.com/lalitmahajn/Lan_Chat.git
   cd Lan_Chat
   pip install -r requirements.txt
   ```

2. **Start Server:**
   ```bash
   python server_main.py
   ```
   *On first launch, a GUI setup wizard will guide you through creating the `super_admin` credentials and setting network ports.*

3. **Start Client:**
   ```bash
   python client_main.py
   ```
   *The client automatically discovers the local server using mDNS zeroconf broadcasts.*

---

## 📦 Building Executables

Portable `.exe` packages can be built instantly using the bundled PyInstaller specifications.

### Build Server
Run `build_server.bat` or execute:
```bash
python -m PyInstaller server.spec --clean -y
```
Output located at: `dist/LAN_Chat_Server/LAN_Chat_Server.exe`

### Build Client
Run `build_client.bat` or execute:
```bash
python -m PyInstaller client.spec --clean -y
```
Output located at: `dist/LAN_Chat_Client/LAN_Chat_Client.exe`

---

## 🛠️ Tech Stack

- **Backend:** [FastAPI](https://fastapi.tiangolo.com/), [Uvicorn](https://www.uvicorn.org/), [SQLAlchemy (Async)](https://www.sqlalchemy.org/), [aiosqlite](https://aiosqlite.omnilib.dev/)
- **Security:** Python-JOSE (JWT Bearer tokens), Passlib (bcrypt 3.x hashing)
- **Frontend & GUI:** [PySide6 (Qt6)](https://doc.qt.io/qtforpython-6/), QtAwesome, Markdown-to-HTML parsing
- **Network Discovery:** Zeroconf (mDNS)

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
