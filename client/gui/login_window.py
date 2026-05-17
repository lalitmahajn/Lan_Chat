"""Login & registration window."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QSpinBox,
    QStackedWidget, QVBoxLayout, QWidget,
)

from client.api_client import api_client
from client.config import client_config
from client.discovery import DiscoveryWorker
from client.gui.theme import get_colors


class LoginWindow(QDialog):
    """Login / register / server discovery dialog."""

    login_success = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LAN Chat — Connect")
        self.setFixedSize(440, 520)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._discovery_worker = None
        self._build_ui()

    def _build_ui(self):
        c = get_colors()
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(32, 24, 32, 24)

        # Title
        title = QLabel("💬 LAN Chat")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # ─── Server Connection ────────────────────────
        server_label = QLabel("Server")
        server_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        server_label.setStyleSheet(f"color: {c['text_secondary']};")
        layout.addWidget(server_label)

        server_row = QHBoxLayout()
        self.host_input = QLineEdit(client_config.server_host or "")
        self.host_input.setPlaceholderText("Server IP or hostname")
        server_row.addWidget(self.host_input, 3)

        self.port_input = QSpinBox()
        self.port_input.setRange(1024, 65535)
        self.port_input.setValue(client_config.server_port)
        self.port_input.setFixedWidth(80)
        server_row.addWidget(self.port_input, 1)

        self.scan_btn = QPushButton("🔍")
        self.scan_btn.setFixedSize(36, 36)
        self.scan_btn.setToolTip("Scan LAN for servers")
        self.scan_btn.clicked.connect(self._start_discovery)
        server_row.addWidget(self.scan_btn)

        layout.addLayout(server_row)

        # Discovery results
        self.server_list = QListWidget()
        self.server_list.setMaximumHeight(80)
        self.server_list.setVisible(False)
        self.server_list.itemClicked.connect(self._on_server_selected)
        layout.addWidget(self.server_list)

        # ─── Stacked: Login / Register ────────────────
        self.stack = QStackedWidget()

        # Login page
        login_page = QWidget()
        login_layout = QVBoxLayout(login_page)
        login_layout.setContentsMargins(0, 8, 0, 0)

        lbl = QLabel("Login")
        lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        login_layout.addWidget(lbl)

        self.login_username = QLineEdit()
        self.login_username.setPlaceholderText("Username")
        login_layout.addWidget(self.login_username)

        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("Password")
        self.login_password.setEchoMode(QLineEdit.EchoMode.Password)
        login_layout.addWidget(self.login_password)

        self.login_btn = QPushButton("Login")
        self.login_btn.setFixedHeight(40)
        self.login_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.login_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['accent']};
                color: white;
                border-radius: 8px;
            }}
            QPushButton:hover {{ background-color: {c['accent_hover']}; }}
        """)
        self.login_btn.clicked.connect(self._on_login)
        login_layout.addWidget(self.login_btn)

        self.login_status = QLabel("")
        self.login_status.setStyleSheet(f"color: {c['error']};")
        self.login_status.setWordWrap(True)
        login_layout.addWidget(self.login_status)

        switch_to_register = QPushButton("Don't have an account? Register")
        switch_to_register.setStyleSheet(f"color: {c['accent']}; background: transparent;")
        switch_to_register.setCursor(Qt.CursorShape.PointingHandCursor)
        switch_to_register.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        login_layout.addWidget(switch_to_register)

        login_layout.addStretch()
        self.stack.addWidget(login_page)

        # Register page
        reg_page = QWidget()
        reg_layout = QVBoxLayout(reg_page)
        reg_layout.setContentsMargins(0, 8, 0, 0)

        lbl2 = QLabel("Register")
        lbl2.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        reg_layout.addWidget(lbl2)

        self.reg_username = QLineEdit()
        self.reg_username.setPlaceholderText("Username (min 3 chars)")
        reg_layout.addWidget(self.reg_username)

        self.reg_display_name = QLineEdit()
        self.reg_display_name.setPlaceholderText("Display name")
        reg_layout.addWidget(self.reg_display_name)

        self.reg_password = QLineEdit()
        self.reg_password.setPlaceholderText("Password (min 6 chars)")
        self.reg_password.setEchoMode(QLineEdit.EchoMode.Password)
        reg_layout.addWidget(self.reg_password)

        self.reg_confirm = QLineEdit()
        self.reg_confirm.setPlaceholderText("Confirm password")
        self.reg_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        reg_layout.addWidget(self.reg_confirm)

        self.reg_btn = QPushButton("Register")
        self.reg_btn.setFixedHeight(40)
        self.reg_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.reg_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['accent']};
                color: white;
                border-radius: 8px;
            }}
            QPushButton:hover {{ background-color: {c['accent_hover']}; }}
        """)
        self.reg_btn.clicked.connect(self._on_register)
        reg_layout.addWidget(self.reg_btn)

        self.reg_status = QLabel("")
        self.reg_status.setStyleSheet(f"color: {c['error']};")
        self.reg_status.setWordWrap(True)
        reg_layout.addWidget(self.reg_status)

        switch_to_login = QPushButton("Already have an account? Login")
        switch_to_login.setStyleSheet(f"color: {c['accent']}; background: transparent;")
        switch_to_login.setCursor(Qt.CursorShape.PointingHandCursor)
        switch_to_login.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        reg_layout.addWidget(switch_to_login)

        reg_layout.addStretch()
        self.stack.addWidget(reg_page)

        layout.addWidget(self.stack)

    def _start_discovery(self):
        self.server_list.clear()
        self.server_list.setVisible(True)
        self.scan_btn.setEnabled(False)

        self._discovery_worker = DiscoveryWorker(timeout=3.0)
        self._discovery_worker.server_found.connect(self._on_server_found)
        self._discovery_worker.finished_scan.connect(self._on_scan_done)
        self._discovery_worker.start()

    def _on_server_found(self, host: str, port: int, name: str):
        item = QListWidgetItem(f"🖥️ {name}  —  {host}:{port}")
        item.setData(Qt.ItemDataRole.UserRole, (host, port))
        self.server_list.addItem(item)

    def _on_scan_done(self):
        self.scan_btn.setEnabled(True)
        if self.server_list.count() == 0:
            self.server_list.addItem("No servers found. Enter IP manually.")

    def _on_server_selected(self, item: QListWidgetItem):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            host, port = data
            self.host_input.setText(host)
            self.port_input.setValue(port)

    def _set_server(self) -> bool:
        host = self.host_input.text().strip()
        if not host:
            return False
        client_config.server_host = host
        client_config.server_port = self.port_input.value()
        client_config.save()
        return True

    def _on_login(self):
        if not self._set_server():
            self.login_status.setText("Enter server address")
            return

        username = self.login_username.text().strip()
        password = self.login_password.text()

        if not username or not password:
            self.login_status.setText("Enter username and password")
            return

        self.login_btn.setEnabled(False)
        self.login_status.setText("Connecting...")
        c = get_colors()
        self.login_status.setStyleSheet(f"color: {c['text_secondary']};")

        try:
            # Health check
            if not api_client.health_check():
                self.login_status.setText("Cannot reach server")
                self.login_status.setStyleSheet(f"color: {c['error']};")
                self.login_btn.setEnabled(True)
                return

            data = api_client.login(username, password)
            client_config.access_token = data["access_token"]
            client_config.refresh_token = data["refresh_token"]
            client_config.username = username

            # Decode token payload without verifying signature
            from jose import jwt
            try:
                payload = jwt.get_unverified_claims(data["access_token"])
                client_config.user_id = int(payload["sub"])
                client_config.user_role = payload.get("role", "")
                client_config.username = payload.get("username", username)
            except Exception:
                pass

            client_config.save()
            self.login_success.emit()
            self.accept()

        except Exception as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_msg = e.response.json().get("detail", error_msg)
                except Exception:
                    pass
            self.login_status.setText(error_msg)
            self.login_status.setStyleSheet(f"color: {c['error']};")
            self.login_btn.setEnabled(True)

    def _on_register(self):
        if not self._set_server():
            self.reg_status.setText("Enter server address")
            return

        c = get_colors()
        username = self.reg_username.text().strip()
        display_name = self.reg_display_name.text().strip()
        password = self.reg_password.text()
        confirm = self.reg_confirm.text()

        if len(username) < 3:
            self.reg_status.setText("Username min 3 chars")
            return
        if not display_name:
            self.reg_status.setText("Display name required")
            return
        if len(password) < 6:
            self.reg_status.setText("Password min 6 chars")
            return
        if password != confirm:
            self.reg_status.setText("Passwords don't match")
            return

        self.reg_btn.setEnabled(False)
        self.reg_status.setText("Registering...")
        self.reg_status.setStyleSheet(f"color: {c['text_secondary']};")

        try:
            if not api_client.health_check():
                self.reg_status.setText("Cannot reach server")
                self.reg_status.setStyleSheet(f"color: {c['error']};")
                self.reg_btn.setEnabled(True)
                return

            api_client.register(username, password, display_name)
            self.reg_status.setText("✅ Registered! Waiting for admin approval.")
            self.reg_status.setStyleSheet(f"color: {c['success']};")

        except Exception as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_msg = e.response.json().get("detail", error_msg)
                except Exception:
                    pass
            self.reg_status.setText(error_msg)
            self.reg_status.setStyleSheet(f"color: {c['error']};")
            self.reg_btn.setEnabled(True)
