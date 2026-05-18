"""Main chat window — 3-panel layout orchestrating sidebar, chat, and members."""

import logging
import os
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QMainWindow, QMessageBox,
    QPushButton, QSplitter, QVBoxLayout, QWidget,
)
import qtawesome as qta
from client.api_client import api_client
from client.config import client_config
from client.gui.admin_panel import AdminPanel
from client.gui.chat_panel import ChatPanel
from client.gui.members_panel import MembersPanel
from client.gui.sidebar import Sidebar
from client.gui.theme import get_colors
from client.gui.tray import TrayManager
from client.ws_client import WSClient
from common.constants import ClientEvent, Role, ServerEvent
from common.schemas import WSEvent

logger = logging.getLogger("lan_chat.main")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"LAN Chat — {client_config.display_name}")
        self.setMinimumSize(900, 600)
        self.resize(1100, 700)

        self._current_chat_type = None  # 'dept' or 'dm'
        self._current_chat_id = None
        self._current_page = 1
        self._members_visible = True
        self._dm_users = {}

        self._build_ui()
        self._setup_ws()
        self._setup_tray()
        self._load_initial_data()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Sidebar
        self.sidebar = Sidebar()
        self.sidebar.department_selected.connect(self._on_dept_selected)
        self.sidebar.dm_selected.connect(self._on_dm_selected)
        self.sidebar.admin_clicked.connect(self._show_admin)
        self.sidebar.settings_clicked.connect(self._show_settings)
        self.sidebar.logout_clicked.connect(self._on_logout)
        is_admin = client_config.user_role == Role.SUPER_ADMIN
        self.sidebar.show_admin_button(is_admin)

        # Chat panel
        self.chat = ChatPanel()
        self.chat.set_user_info(client_config.user_id, is_admin)
        self.chat.send_message.connect(self._on_send)
        self.chat.delete_message.connect(self._on_delete)
        self.chat.load_more.connect(self._on_load_more)
        self.chat.file_upload.connect(self._on_upload)
        self.chat.typing_started.connect(self._on_typing_start)
        self.chat.typing_stopped.connect(self._on_typing_stop)

        # Members panel
        self.members = MembersPanel()
        self.members.user_clicked.connect(self._on_member_dm)

        # Toggle members button
        c = get_colors()
        self.toggle_btn = QPushButton("")
        self.toggle_btn.setIcon(qta.icon('fa5s.users', color=c['text_primary']))
        self.toggle_btn.setFixedSize(28, 28)
        self.toggle_btn.setStyleSheet("background:transparent; border:none;")
        self.toggle_btn.clicked.connect(self._toggle_members)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.sidebar)
        splitter.addWidget(self.chat)
        splitter.addWidget(self.members)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        layout.addWidget(splitter)

    def _setup_ws(self):
        self.ws = WSClient()
        self.ws.connected.connect(self._on_ws_connected)
        self.ws.disconnected.connect(self._on_ws_disconnected)
        self.ws.event_received.connect(self._on_ws_event)
        self.ws.start()

    def _setup_tray(self):
        self.tray = TrayManager(self)
        self.tray.show()

    def _load_initial_data(self):
        try:
            # Load departments user belongs to
            depts = api_client.get_my_departments()
            self.sidebar.set_departments(depts)

            # For DM users: use approved users endpoint
            try:
                users = api_client.get_approved_users()
                self._dm_users = {u["id"]: u for u in users}
                self.sidebar.set_dm_users(list(self._dm_users.values()))
            except Exception as e:
                logger.error(f"Failed to load DM users: {e}")
        except Exception as e:
            logger.error(f"Failed to load initial data: {e}")

    # ─── WebSocket Events ─────────────────────────────────────────────

    @Slot()
    def _on_ws_connected(self):
        logger.info("WebSocket connected")
        self.statusBar().showMessage("Connected", 3000)

    @Slot()
    def _on_ws_disconnected(self):
        logger.info("WebSocket disconnected")
        self.statusBar().showMessage("Disconnected — reconnecting...", 5000)

    @Slot(dict)
    def _on_ws_event(self, data: dict):
        event = data.get("event", "")
        payload = data.get("data", {})

        if event == ServerEvent.MESSAGE_NEW:
            self._handle_new_message(payload)
        elif event == ServerEvent.MESSAGE_DELETED:
            self._handle_deleted_message(payload)
        elif event == ServerEvent.TYPING_UPDATE:
            self._handle_typing(payload)
        elif event == ServerEvent.PRESENCE_CHANGED:
            self._handle_presence(payload)
        elif event == ServerEvent.SYSTEM_NOTIFICATION:
            self.tray.notify("LAN Chat", payload.get("message", ""))

    def _handle_new_message(self, msg):
        # Check if message belongs to current chat
        in_current = False
        if self._current_chat_type == "dept" and msg.get("department_id") == self._current_chat_id:
            in_current = True
        elif self._current_chat_type == "dm":
            sender = msg["sender"]["id"]
            recipient = msg.get("recipient_id")
            if (sender == self._current_chat_id or recipient == self._current_chat_id):
                in_current = True

        if in_current:
            self.chat.add_messages([msg])
        else:
            # Notify
            sender_name = msg["sender"]["display_name"]
            content = msg["content"][:50]
            self.tray.notify(f"Message from {sender_name}", content)
            
            # Unread badge
            if msg.get("department_id"):
                self.sidebar.increment_unread("dept", msg["department_id"])
            elif msg.get("recipient_id"):
                self.sidebar.increment_unread("dm", msg["sender"]["id"])

        # Update DM users list if new DM partner
        sender = msg["sender"]
        if msg.get("recipient_id") and sender["id"] not in self._dm_users and sender["id"] != client_config.user_id:
            self._dm_users[sender["id"]] = sender
            self.sidebar.set_dm_users(list(self._dm_users.values()))

    def _handle_deleted_message(self, data):
        msg_id = data.get("message_id")
        if msg_id:
            self.chat.remove_message(msg_id)

    def _handle_typing(self, data):
        if self._current_chat_type == "dept" and data.get("department_id") == self._current_chat_id:
            self.chat.show_typing(data["username"], data["is_typing"])
        elif self._current_chat_type == "dm" and data.get("user_id") == self._current_chat_id:
            self.chat.show_typing(data["username"], data["is_typing"])

    def _handle_presence(self, data):
        uid = data.get("user_id")
        if uid in self._dm_users:
            self._dm_users[uid]["presence"] = data["presence"]
            self.sidebar.set_dm_users(list(self._dm_users.values()))

    # ─── Chat Actions ─────────────────────────────────────────────────

    def _on_dept_selected(self, dept_id: int, name: str):
        self._current_chat_type = "dept"
        self._current_chat_id = dept_id
        self._current_page = 1
        self.chat.set_chat_header(f"# {name}")
        self.chat.clear_messages()
        
        try:
            members = api_client.get_department_members(dept_id)
            self.members.set_members(members)
            self.members.setVisible(self._members_visible)
        except Exception as e:
            logger.error(f"Failed to load members: {e}")

        self._load_messages()

    def _on_dm_selected(self, user_id: int, display_name: str):
        self._current_chat_type = "dm"
        self._current_chat_id = user_id
        self._current_page = 1
        self.chat.set_chat_header(f"💬 {display_name}")
        self.chat.clear_messages()
        self.members.setVisible(False)
        self._load_messages()

    def _load_messages(self):
        try:
            if self._current_chat_type == "dept":
                data = api_client.get_department_messages(self._current_chat_id, self._current_page)
            else:
                data = api_client.get_dm_messages(self._current_chat_id, self._current_page)

            prepend = self._current_page > 1
            self.chat.add_messages(data.get("items", []), prepend=prepend)
            self.chat.set_has_more(data.get("has_more", False))
        except Exception as e:
            logger.error(f"Failed to load messages: {e}")

    def _on_load_more(self):
        self._current_page += 1
        self._load_messages()

    def _on_send(self, content: str, attachment_ids: list):
        if not content and not attachment_ids:
            return
        event_data = {"content": content or " ", "attachment_ids": attachment_ids}
        if self._current_chat_type == "dept":
            event_data["department_id"] = self._current_chat_id
        else:
            event_data["recipient_id"] = self._current_chat_id

        reply_id = self.chat.get_reply_to_id()
        if reply_id:
            event_data["reply_to_id"] = reply_id

        self.ws.send_event(WSEvent(event=ClientEvent.MESSAGE_SEND, data=event_data))

    def _on_delete(self, message_id: int):
        self.ws.send_event(WSEvent(event=ClientEvent.MESSAGE_DELETE, data={"message_id": message_id}))

    def _on_upload(self, filepath: str):
        try:
            result = api_client.upload_file(filepath)
            self.chat._attachment_ids.append(result["id"])
            self.statusBar().showMessage(f"Uploaded: {os.path.basename(filepath)}", 3000)
        except Exception as e:
            QMessageBox.warning(self, "Upload Failed", str(e))

    def _on_typing_start(self):
        data = {}
        if self._current_chat_type == "dept":
            data["department_id"] = self._current_chat_id
        else:
            data["recipient_id"] = self._current_chat_id
        self.ws.send_event(WSEvent(event=ClientEvent.TYPING_START, data=data))

    def _on_typing_stop(self):
        data = {}
        if self._current_chat_type == "dept":
            data["department_id"] = self._current_chat_id
        else:
            data["recipient_id"] = self._current_chat_id
        self.ws.send_event(WSEvent(event=ClientEvent.TYPING_STOP, data=data))

    def _on_member_dm(self, user_id: int, display_name: str):
        self._on_dm_selected(user_id, display_name)

    def _toggle_members(self):
        self._members_visible = not self._members_visible
        self.members.setVisible(self._members_visible)

    def _show_admin(self):
        panel = AdminPanel(self)
        panel.data_changed.connect(self._load_initial_data)
        panel.exec()

    def _show_settings(self):
        from client.config import client_config
        # Simple theme toggle for now
        themes = ["system", "dark", "light"]
        current = themes.index(client_config.theme) if client_config.theme in themes else 0
        next_theme = themes[(current + 1) % len(themes)]
        client_config.theme = next_theme
        client_config.save()
        QMessageBox.information(self, "Theme", f"Theme set to: {next_theme}\nRestart app to apply.")

    def _on_logout(self):
        reply = QMessageBox.question(
            self,
            "Log Out",
            "Are you sure you want to log out of LAN Chat?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            client_config.clear_auth()
            self.ws.stop()
            self.tray.hide()
            api_client.close()
            from PySide6.QtWidgets import QApplication
            QApplication.quit()

    def closeEvent(self, event):
        self.ws.stop()
        self.tray.hide()
        api_client.close()
        event.accept()
        from PySide6.QtWidgets import QApplication
        QApplication.quit()

