"""First-run setup wizard — create super_admin, configure server basics."""

import asyncio
import sys

from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from common.constants import Defaults


class SetupWorker(QThread):
    """Run async DB setup in background thread."""
    finished = Signal(bool, str)  # (success, message)

    def __init__(self, username: str, password: str, display_name: str, port: int, server_name: str):
        super().__init__()
        self.username = username
        self.password = password
        self.display_name = display_name
        self.port = port
        self.server_name = server_name

    def run(self):
        try:
            asyncio.run(self._setup())
            self.finished.emit(True, "Setup complete!")
        except Exception as e:
            self.finished.emit(False, str(e))

    async def _setup(self):
        from server.database import create_tables, get_session_factory
        from server.services.user_service import create_super_admin
        from server.config import server_config

        # Update config
        server_config.server_name = self.server_name
        server_config.server_port = self.port

        # Create tables
        await create_tables()

        # Create super admin
        factory = get_session_factory()
        async with factory() as db:
            await create_super_admin(db, self.username, self.password, self.display_name)
            await db.commit()


class SetupWizard(QDialog):
    """First-run setup dialog."""

    setup_complete = Signal(int)  # port

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LAN Chat — First Run Setup")
        self.setFixedSize(480, 420)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._worker = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(32, 24, 32, 24)

        # Title
        title = QLabel("🚀 LAN Chat Server Setup")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Configure your server and create the admin account.")
        subtitle.setFont(QFont("Segoe UI", 10))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #888;")
        layout.addWidget(subtitle)

        layout.addSpacing(8)

        # Form
        form = QFormLayout()
        form.setSpacing(10)

        self.server_name_input = QLineEdit(Defaults.SERVER_NAME)
        self.server_name_input.setPlaceholderText("Server name")
        form.addRow("Server Name:", self.server_name_input)

        self.port_input = QSpinBox()
        self.port_input.setRange(1024, 65535)
        self.port_input.setValue(Defaults.SERVER_PORT)
        form.addRow("Port:", self.port_input)

        # Separator
        sep = QLabel("── Admin Account ──")
        sep.setAlignment(Qt.AlignCenter)
        sep.setStyleSheet("color: #666; margin-top: 8px;")
        form.addRow(sep)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Min 3 characters")
        form.addRow("Username:", self.username_input)

        self.display_name_input = QLineEdit()
        self.display_name_input.setPlaceholderText("Display name in chat")
        form.addRow("Display Name:", self.display_name_input)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Min 6 characters")
        form.addRow("Password:", self.password_input)

        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Confirm:", self.confirm_input)

        layout.addLayout(form)
        layout.addSpacing(8)

        # Buttons
        btn_layout = QHBoxLayout()
        self.setup_btn = QPushButton("Create & Start Server")
        self.setup_btn.setFixedHeight(40)
        self.setup_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.setup_btn.setStyleSheet("""
            QPushButton {
                background-color: #7c3aed;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 24px;
            }
            QPushButton:hover { background-color: #6d28d9; }
            QPushButton:pressed { background-color: #5b21b6; }
            QPushButton:disabled { background-color: #555; }
        """)
        self.setup_btn.clicked.connect(self._on_setup)
        btn_layout.addWidget(self.setup_btn)
        layout.addLayout(btn_layout)

        # Status
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #f87171;")
        layout.addWidget(self.status_label)

    def _validate(self) -> str | None:
        if len(self.server_name_input.text().strip()) < 1:
            return "Server name required"
        if len(self.username_input.text().strip()) < 3:
            return "Username must be at least 3 characters"
        if len(self.display_name_input.text().strip()) < 1:
            return "Display name required"
        if len(self.password_input.text()) < 6:
            return "Password must be at least 6 characters"
        if self.password_input.text() != self.confirm_input.text():
            return "Passwords don't match"
        return None

    def _on_setup(self):
        error = self._validate()
        if error:
            self.status_label.setText(error)
            return

        self.setup_btn.setEnabled(False)
        self.status_label.setText("Setting up...")
        self.status_label.setStyleSheet("color: #60a5fa;")

        self._worker = SetupWorker(
            username=self.username_input.text().strip(),
            password=self.password_input.text(),
            display_name=self.display_name_input.text().strip(),
            port=self.port_input.value(),
            server_name=self.server_name_input.text().strip(),
        )
        self._worker.finished.connect(self._on_setup_done)
        self._worker.start()

    def _on_setup_done(self, success: bool, message: str):
        if success:
            self.setup_complete.emit(self.port_input.value())
            self.accept()
        else:
            self.status_label.setText(f"Error: {message}")
            self.status_label.setStyleSheet("color: #f87171;")
            self.setup_btn.setEnabled(True)
