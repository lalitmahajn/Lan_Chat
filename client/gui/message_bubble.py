"""Message bubble widget for chat display."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)
from client.gui.theme import get_colors
from client.utils.markdown import render_message_content
from common.utils import format_timestamp, format_file_size


class MessageBubble(QWidget):
    delete_requested = Signal(int)
    reply_requested = Signal(dict)
    download_requested = Signal(int, str)

    def __init__(self, msg: dict, current_user_id: int, is_admin: bool = False, parent=None):
        super().__init__(parent)
        self.msg = msg
        self._current_user_id = current_user_id
        self._is_admin = is_admin
        self._build_ui()

    def _build_ui(self):
        c = get_colors()
        is_own = self.msg["sender"]["id"] == self._current_user_id
        is_deleted = self.msg.get("is_deleted", False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)

        # Reply reference
        if self.msg.get("reply_to") and not is_deleted:
            reply = self.msg["reply_to"]
            reply_lbl = QLabel(f"↩ {reply['sender']['display_name']}: {reply['content'][:60]}")
            reply_lbl.setFont(QFont("Segoe UI", 10))
            reply_lbl.setStyleSheet(f"color: {c['text_muted']}; padding: 2px 8px; border-left: 2px solid {c['accent']};")
            layout.addWidget(reply_lbl)

        # Header: name + time
        header = QHBoxLayout()
        name_lbl = QLabel(self.msg["sender"]["display_name"])
        name_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        name_lbl.setStyleSheet(f"color: {c['accent'] if is_own else c['text_primary']};")
        header.addWidget(name_lbl)

        time_lbl = QLabel(self.msg.get("created_at", "")[:16].replace("T", " "))
        time_lbl.setFont(QFont("Segoe UI", 9))
        time_lbl.setStyleSheet(f"color: {c['text_muted']};")
        header.addWidget(time_lbl)
        header.addStretch()

        # Action buttons
        if not is_deleted:
            reply_btn = QPushButton("↩")
            reply_btn.setFixedSize(24, 24)
            reply_btn.setStyleSheet("background:transparent; border:none; font-size:14px;")
            reply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            reply_btn.clicked.connect(lambda: self.reply_requested.emit(self.msg))
            header.addWidget(reply_btn)

            if is_own or self._is_admin:
                del_btn = QPushButton("🗑")
                del_btn.setFixedSize(24, 24)
                del_btn.setStyleSheet("background:transparent; border:none; font-size:14px;")
                del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                del_btn.clicked.connect(lambda: self.delete_requested.emit(self.msg["id"]))
                header.addWidget(del_btn)

        layout.addLayout(header)

        # Content
        if is_deleted:
            content_lbl = QLabel("<i>[message deleted]</i>")
            content_lbl.setStyleSheet(f"color: {c['text_muted']};")
        else:
            content_lbl = QLabel(render_message_content(self.msg["content"]))
            content_lbl.setTextFormat(Qt.TextFormat.RichText)
            content_lbl.setWordWrap(True)
        layout.addWidget(content_lbl)

        # Attachments
        for att in self.msg.get("attachments", []):
            att_row = QHBoxLayout()
            icon = "🖼️" if att["mime_type"].startswith("image/") else "📎"
            att_lbl = QPushButton(f"{icon} {att['original_filename']} ({format_file_size(att['file_size'])})")
            att_lbl.setStyleSheet(f"color: {c['accent']}; background:transparent; text-align:left; border:none;")
            att_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
            att_lbl.clicked.connect(lambda _, a=att: self.download_requested.emit(a["id"], a["original_filename"]))
            att_row.addWidget(att_lbl)
            att_row.addStretch()
            layout.addLayout(att_row)

        # Styling
        bg = c['message_own'] if is_own else c['message_other']
        self.setStyleSheet(f"background-color: {bg}; border-radius: 8px; margin: 2px 0px;")
