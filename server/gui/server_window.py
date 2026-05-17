"""Server status dashboard — shows connected users, uptime, logs."""

import logging
import socket
import time
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMainWindow, QPlainTextEdit,
    QPushButton, QStatusBar, QVBoxLayout, QWidget,
)

from server.config import server_config
from server.ws_manager import ws_manager


class QtLogHandler(logging.Handler):
    """Route Python logging to Qt signal."""

    def __init__(self, callback):
        super().__init__()
        self._callback = callback
        self.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s — %(message)s", "%H:%M:%S"))

    def emit(self, record):
        msg = self.format(record)
        self._callback(msg)


class ServerWindow(QMainWindow):
    """Server status dashboard."""

    log_signal = Signal(str)
    stop_requested = Signal()

    def __init__(self):
        super().__init__()
        self._start_time = time.time()
        self.setWindowTitle(f"{server_config.server_name} — Server")
        self.setMinimumSize(700, 500)
        self._build_ui()
        self._setup_logging()
        self._start_timer()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        # ─── Header ──────────────────────────────────
        header = QHBoxLayout()

        title = QLabel(f"🖥️ {server_config.server_name}")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        header.addWidget(title)

        header.addStretch()

        self.stop_btn = QPushButton("Stop Server")
        self.stop_btn.setFixedHeight(36)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 6px 20px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #dc2626; }
        """)
        self.stop_btn.clicked.connect(self._on_stop)
        header.addWidget(self.stop_btn)

        layout.addLayout(header)

        # ─── Stats Cards ─────────────────────────────
        stats = QHBoxLayout()
        stats.setSpacing(12)

        self.ip_card = self._make_card("🌐 Server IP", self._get_local_ip())
        stats.addWidget(self.ip_card)

        self.port_card = self._make_card("🔌 Port", str(server_config.server_port))
        stats.addWidget(self.port_card)

        self.users_card = self._make_card("👥 Connected", "0")
        stats.addWidget(self.users_card)

        self.uptime_card = self._make_card("⏱️ Uptime", "0s")
        stats.addWidget(self.uptime_card)

        layout.addLayout(stats)

        # ─── Log ──────────────────────────────────────
        log_label = QLabel("📋 Server Log")
        log_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        layout.addWidget(log_label)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Consolas", 9))
        self.log_view.setMaximumBlockCount(500)
        self.log_view.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        layout.addWidget(self.log_view)

        # Status bar
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Server running")

    def _make_card(self, title: str, value: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #2a2a3c;
                border: 1px solid #313244;
                border-radius: 10px;
                padding: 12px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(4)

        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Segoe UI", 9))
        lbl_title.setStyleSheet("color: #888; border: none;")
        lbl_title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(lbl_title)

        lbl_value = QLabel(value)
        lbl_value.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        lbl_value.setAlignment(Qt.AlignCenter)
        lbl_value.setStyleSheet("color: #cdd6f4; border: none;")
        lbl_value.setObjectName("card_value")
        card_layout.addWidget(lbl_value)

        return card

    def _update_card_value(self, card: QFrame, value: str):
        label = card.findChild(QLabel, "card_value")
        if label:
            label.setText(value)

    def _setup_logging(self):
        self.log_signal.connect(self._append_log)
        handler = QtLogHandler(lambda msg: self.log_signal.emit(msg))
        handler.setLevel(logging.INFO)

        # Attach to root lan_chat logger
        logger = logging.getLogger("lan_chat")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Also capture uvicorn
        for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
            logging.getLogger(name).addHandler(handler)

    @Slot(str)
    def _append_log(self, msg: str):
        self.log_view.appendPlainText(msg)

    def _start_timer(self):
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_stats)
        self._timer.start(1000)

    def _update_stats(self):
        # Uptime
        elapsed = int(time.time() - self._start_time)
        hours, rem = divmod(elapsed, 3600)
        mins, secs = divmod(rem, 60)
        if hours > 0:
            uptime = f"{hours}h {mins}m"
        elif mins > 0:
            uptime = f"{mins}m {secs}s"
        else:
            uptime = f"{secs}s"
        self._update_card_value(self.uptime_card, uptime)

        # Connected users
        self._update_card_value(self.users_card, str(ws_manager.connected_count))

    def _get_local_ip(self) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def _on_stop(self):
        self.stop_requested.emit()
        self.close()

    def closeEvent(self, event):
        self.stop_requested.emit()
        event.accept()
