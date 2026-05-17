"""Chat panel — message feed + input box."""

import os
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QTextEdit, QVBoxLayout, QWidget,
)
import qtawesome as qta
from client.gui.message_bubble import MessageBubble
from client.gui.theme import get_colors


class ChatPanel(QWidget):
    send_message = Signal(str, list)  # content, attachment_ids
    delete_message = Signal(int)
    reply_to_message = Signal(dict)
    typing_started = Signal()
    typing_stopped = Signal()
    load_more = Signal()
    file_upload = Signal(str)  # filepath

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_user_id = None
        self._is_admin = False
        self._reply_msg = None
        self._typing_timer = QTimer(self)
        self._typing_timer.setSingleShot(True)
        self._typing_timer.timeout.connect(self.typing_stopped.emit)
        self._attachment_ids = []
        self._build_ui()

    def _build_ui(self):
        c = get_colors()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        self.header = QLabel("Select a chat")
        self.header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.header.setStyleSheet(f"padding: 16px 24px; border-bottom: 1px solid {c['border']}; background-color: {c['bg_secondary']};")
        layout.addWidget(self.header)

        # Messages scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("border: none;")

        self.msg_container = QWidget()
        self.msg_layout = QVBoxLayout(self.msg_container)
        self.msg_layout.setAlignment(Qt.AlignTop)
        self.msg_layout.setSpacing(4)
        self.msg_layout.setContentsMargins(8, 8, 8, 8)

        # Load more button
        self.load_more_btn = QPushButton("Load older messages...")
        self.load_more_btn.setStyleSheet(f"color: {c['accent']}; background: transparent;")
        self.load_more_btn.clicked.connect(self.load_more.emit)
        self.load_more_btn.setVisible(False)
        self.msg_layout.addWidget(self.load_more_btn)

        self.msg_layout.addStretch()
        self.scroll.setWidget(self.msg_container)
        layout.addWidget(self.scroll, 1)

        # Typing indicator
        self.typing_label = QLabel("")
        self.typing_label.setFont(QFont("Segoe UI", 10))
        self.typing_label.setStyleSheet(f"color: {c['text_muted']}; padding: 2px 16px;")
        self.typing_label.setVisible(False)
        layout.addWidget(self.typing_label)

        # Reply preview
        self.reply_bar = QWidget()
        reply_layout = QHBoxLayout(self.reply_bar)
        reply_layout.setContentsMargins(12, 4, 12, 4)
        self.reply_label = QLabel("")
        self.reply_label.setStyleSheet(f"color: {c['text_secondary']}; border-left: 2px solid {c['accent']}; padding-left: 8px;")
        reply_layout.addWidget(self.reply_label, 1)
        cancel_reply = QPushButton("✕")
        cancel_reply.setFixedSize(24, 24)
        cancel_reply.setStyleSheet("background:transparent; border:none;")
        cancel_reply.clicked.connect(self._cancel_reply)
        reply_layout.addWidget(cancel_reply)
        self.reply_bar.setVisible(False)
        layout.addWidget(self.reply_bar)

        # Input area
        input_container = QWidget()
        input_container.setStyleSheet(f"background-color: {c['bg_secondary']}; border-top: 1px solid {c['border']};")
        input_row = QHBoxLayout(input_container)
        input_row.setContentsMargins(16, 12, 16, 16)
        input_row.setSpacing(12)

        attach_btn = QPushButton(" Attach")
        attach_btn.setIcon(qta.icon('fa5s.paperclip', color=c['text_primary']))
        attach_btn.setFixedSize(90, 44)
        attach_btn.setStyleSheet(f"background:{c['bg_tertiary']}; border-radius:8px; font-weight:bold;")
        attach_btn.clicked.connect(self._on_attach)
        input_row.addWidget(attach_btn)

        self.input_box = QTextEdit()
        self.input_box.setFixedHeight(44)
        self.input_box.setPlaceholderText("Type a message...")
        self.input_box.setStyleSheet(f"background:{c['input_bg']}; border:1px solid {c['border']}; border-radius:8px; padding:10px 14px; font-size:14px;")
        self.input_box.textChanged.connect(self._on_typing)
        input_row.addWidget(self.input_box, 1)

        send_btn = QPushButton(" Send")
        send_btn.setIcon(qta.icon('fa5s.paper-plane', color='white'))
        send_btn.setFixedSize(90, 44)
        send_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        send_btn.setStyleSheet(f"background:{c['accent']}; color:white; border-radius:8px;")
        send_btn.clicked.connect(self._on_send)
        input_row.addWidget(send_btn)

        layout.addWidget(input_container)

    def set_user_info(self, user_id, is_admin):
        self._current_user_id = user_id
        self._is_admin = is_admin

    def set_chat_header(self, name: str):
        self.header.setText(name)

    def clear_messages(self):
        while self.msg_layout.count() > 2:  # keep load_more + stretch
            item = self.msg_layout.takeAt(1)  # after load_more
            w = item.widget()
            if w and w is not self.load_more_btn:
                w.deleteLater()

    def add_message(self, msg: dict, prepend=False):
        bubble = MessageBubble(msg, self._current_user_id, self._is_admin)
        bubble.delete_requested.connect(self.delete_message.emit)
        bubble.reply_requested.connect(self._set_reply)
        bubble.download_requested.connect(self._on_download)
        idx = self.msg_layout.count() - 1  # before stretch
        if prepend:
            idx = 1  # after load_more
        self.msg_layout.insertWidget(idx, bubble)

    def add_messages(self, messages: list, prepend=False):
        for m in messages:
            self.add_message(m, prepend)
        if not prepend:
            QTimer.singleShot(50, self._scroll_bottom)

    def remove_message(self, message_id: int):
        for i in range(self.msg_layout.count()):
            w = self.msg_layout.itemAt(i).widget()
            if isinstance(w, MessageBubble) and w.msg["id"] == message_id:
                w.msg["is_deleted"] = True
                w.msg["content"] = "[deleted]"
                # Rebuild
                self.msg_layout.removeWidget(w)
                w.deleteLater()
                break

    def set_has_more(self, has_more: bool):
        self.load_more_btn.setVisible(has_more)

    def show_typing(self, username: str, is_typing: bool):
        if is_typing:
            self.typing_label.setText(f"{username} is typing...")
            self.typing_label.setVisible(True)
        else:
            self.typing_label.setVisible(False)

    def _set_reply(self, msg):
        self._reply_msg = msg
        self.reply_label.setText(f"↩ {msg['sender']['display_name']}: {msg['content'][:60]}")
        self.reply_bar.setVisible(True)

    def _cancel_reply(self):
        self._reply_msg = None
        self.reply_bar.setVisible(False)

    def _on_send(self):
        text = self.input_box.toPlainText().strip()
        if not text and not self._attachment_ids:
            return
        self.send_message.emit(text, self._attachment_ids.copy())
        self.input_box.clear()
        self._attachment_ids.clear()
        self._cancel_reply()

    def _on_typing(self):
        self.typing_started.emit()
        self._typing_timer.start(2000)

    def _on_attach(self):
        path, _ = QFileDialog.getOpenFileName(self, "Attach File")
        if path:
            self.file_upload.emit(path)

    def _on_download(self, file_id, filename):
        self.download_requested_signal_needed = True  # handled by main window

    def _scroll_bottom(self):
        sb = self.scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

    def get_reply_to_id(self):
        return self._reply_msg["id"] if self._reply_msg else None
